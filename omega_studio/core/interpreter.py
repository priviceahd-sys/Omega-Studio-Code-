"""
Interpréteur Pas-à-Pas basé sur générateur Python pour Alg_32 / Omega Studio Code.
Permet l'exécution continue, pas-à-pas (Step Into / Step Over), points d'arrêt,
saisie clavier non bloquante, gestion de fichiers Alg_32 et moteur SQL SQLite3 intégré.
"""

from __future__ import annotations

import copy
import datetime
import json
import math
import os
import random
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from .ast_nodes import (
    AfficherStmt,
    AssignStmt,
    BinaryOp,
    CallExpr,
    CallStmt,
    ConstDecl,
    CopieStmt,
    Expr,
    FieldAccess,
    FileDecl,
    FileOpStmt,
    IfStmt,
    IndexAccess,
    IterStmt,
    Literal,
    PourStmt,
    Program,
    RepeterStmt,
    ReturnStmt,
    SaisirStmt,
    ScreenCmdStmt,
    SelonStmt,
    SortirSiStmt,
    SqlStmt,
    Stmt,
    SubprogramDecl,
    TantQueStmt,
    TypeDefDecl,
    TypeSpec,
    UnaryOp,
    VarDecl,
    VarRef,
)
from .keywords import KeywordProfile, norm_key, read_alg_file_smart
from .parser import parse_source


class AlgRuntimeError(Exception):
    def __init__(self, message: str, line: int) -> None:
        super().__init__(message)
        self.message = message
        self.line = line


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class _ExitIterSignal(Exception):
    pass


@dataclass
class TabStopMarker:
    col: int


@dataclass
class ArrayValue:
    base_type: str
    dimensions: List[Tuple[int, int]]  # [(lo, hi), ...]
    cells: Dict[Tuple[int, ...], Any] = field(default_factory=dict)
    explicit_lower_bounds: bool = False

    def get_cell(self, indices: List[int], line: int) -> Any:
        key = self._validate_indices(indices, line)
        return self.cells.get(key)

    def set_cell(self, indices: List[int], val: Any, line: int) -> None:
        key = self._validate_indices(indices, line)
        self.cells[key] = val

    def _validate_indices(self, indices: List[int], line: int) -> Tuple[int, ...]:
        if len(indices) != len(self.dimensions):
            raise AlgRuntimeError(
                f"Nombre d'indices incorrect : {len(indices)} fourni(s), {len(self.dimensions)} attendu(s).",
                line,
            )
        checked: List[int] = []
        for dim_idx, (idx_val, (lo, hi)) in enumerate(zip(indices, self.dimensions), start=1):
            if not isinstance(idx_val, int) or isinstance(idx_val, bool):
                raise AlgRuntimeError(f"L'indice n°{dim_idx} doit être un entier (reçu {idx_val!r}).", line)
            # Tolérance pédagogique : si déclaré t[10] (lo=1, hi=10 implicite), autorise 0..10
            min_allowed = lo if self.explicit_lower_bounds else min(0, lo)
            if hi > 0 and (idx_val < min_allowed or idx_val > hi):
                raise AlgRuntimeError(
                    f"Indice hors limites : {idx_val} (bornes autorisées [{lo}..{hi}]).",
                    line,
                )
            checked.append(idx_val)
        return tuple(checked)


@dataclass
class StructValue:
    type_name: str
    fields: Dict[str, Any] = field(default_factory=dict)  # norm_name -> val
    display_names: Dict[str, str] = field(default_factory=dict)  # norm_name -> original_name

    def get_field(self, fname: str, line: int) -> Any:
        nk = norm_key(fname)
        if nk not in self.fields:
            raise AlgRuntimeError(f"Champ '{fname}' inexistant dans la structure '{self.type_name}'.", line)
        return self.fields[nk]

    def set_field(self, fname: str, val: Any, line: int) -> None:
        nk = norm_key(fname)
        if nk not in self.fields:
            raise AlgRuntimeError(f"Champ '{fname}' inexistant dans la structure '{self.type_name}'.", line)
        self.fields[nk] = val


@dataclass
class StackFrame:
    name: str
    line: int
    vars: Dict[str, Any] = field(default_factory=dict)  # norm_name -> val
    var_types: Dict[str, TypeSpec] = field(default_factory=dict)
    display_names: Dict[str, str] = field(default_factory=dict)
    consts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VirtualFileState:
    decl: FileDecl
    is_open: bool = False
    mode: str = "FERME"
    cursor: int = 0
    eof: bool = False
    last_error: bool = False
    last_exists: bool = False
    records: List[Dict[str, Any]] = field(default_factory=list)
    indexed_records: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    binary_data: List[Any] = field(default_factory=list)


@dataclass
class StepEvent:
    kind: str  # "STEP", "OUTPUT", "PRINTER", "SCREEN_CMD", "INPUT_REQUEST", "SQL_RESULT", "FINISHED", "ERROR"
    line: int = 1
    text: str = ""
    newline: bool = True
    prompt: str = ""
    target_name: str = ""
    target_type: str = "CHAINE"
    fg_color: Optional[int] = None
    bg_color: Optional[int] = None
    cursor_pos: Optional[Tuple[int, int]] = None
    sql_columns: List[str] = field(default_factory=list)
    sql_rows: List[Tuple[Any, ...]] = field(default_factory=list)


class AlgInterpreter:
    """Exécuteur complet du langage Alg_32 avec inspection d'état en direct."""

    def __init__(
        self,
        program: Program,
        profile: Optional[KeywordProfile] = None,
        working_dir: Optional[str] = None,
        max_steps: int = 2_000_000,
    ) -> None:
        self.program = program
        self.profile = profile or KeywordProfile()
        self.working_dir = Path(working_dir or os.getcwd())
        self.max_steps = max_steps

        self.user_types: Dict[str, TypeDefDecl] = {norm_key(t.name): t for t in program.types}
        self.subprograms: Dict[str, SubprogramDecl] = {norm_key(sp.name): sp for sp in program.subprograms}

        self.global_frame = StackFrame(name="Principal", line=program.line)
        self.call_stack: List[StackFrame] = [self.global_frame]
        self.global_var_keys: Set[str] = set()

        self.files: Dict[str, VirtualFileState] = {}
        self.record_to_file: Dict[str, str] = {}

        # État écran virtuel 24x80 (compatible Alg_32)
        self.cursor_line: int = 1
        self.cursor_col: int = 1
        self.fg_color: int = 7
        self.bg_color: int = 0
        self.printer_buffer: List[str] = []

        # État SQLite intégré (remplace MS Access 2.0 / DAO 3.5 sur Linux / Omarchy)
        self.sql_conn: Optional[sqlite3.Connection] = None
        self.sql_db_name: str = ""
        self.sql_cursors: Dict[str, Tuple[str, Optional[sqlite3.Cursor]]] = {}
        self.sql_last_error: bool = False
        self.sql_eof: bool = False

        self.step_count: int = 0
        self.current_line: int = program.line

    # ==========================================
    # Initialisation des données et types
    # ==========================================

    def _default_for_type(self, ts: TypeSpec) -> Any:
        if ts.is_array and ts.dimensions:
            arr = ArrayValue(base_type=ts.base_type, dimensions=list(ts.dimensions))
            elem_ts = TypeSpec(
                line=ts.line,
                base_type=ts.base_type,
                size=ts.size,
                decimals=ts.decimals,
                is_array=False,
                struct_fields=ts.struct_fields,
            )
            # Pré-remplit les tableaux de taille raisonnable pour l'espion visuel
            total_cells = 1
            for lo, hi in ts.dimensions:
                span = max(1, hi - min(0, lo) + 1)
                total_cells *= span
            if total_cells <= 5000:
                self._populate_array_cells(arr, elem_ts, 0, [])
            return arr

        bt = norm_key(ts.base_type)
        if bt == "ENTIER":
            return 0
        if bt in ("REEL", "DECIMAL"):
            return 0.0
        if bt in ("CHAINE", "CAR"):
            return ""
        if bt == "BOOLEEN":
            return False
        if bt == "STRUCTURE":
            sv = StructValue(type_name="STRUCTURE")
            for fdecl in ts.struct_fields:
                for fname in fdecl.names:
                    fk = norm_key(fname)
                    sv.fields[fk] = self._default_for_type(fdecl.type_spec)
                    sv.display_names[fk] = fname
            return sv
        if bt in self.user_types:
            tdef = self.user_types[bt]
            sv = StructValue(type_name=tdef.name)
            for fdecl in tdef.fields:
                for fname in fdecl.names:
                    fk = norm_key(fname)
                    sv.fields[fk] = self._default_for_type(fdecl.type_spec)
                    sv.display_names[fk] = fname
            return sv
        return 0

    def _populate_array_cells(
        self, arr: ArrayValue, elem_ts: TypeSpec, dim_i: int, prefix: List[int]
    ) -> None:
        if dim_i >= len(arr.dimensions):
            arr.cells[tuple(prefix)] = self._default_for_type(elem_ts)
            return
        lo, hi = arr.dimensions[dim_i]
        for idx in range(lo, hi + 1):
            self._populate_array_cells(arr, elem_ts, dim_i + 1, prefix + [idx])

    def _coerce_value(self, val: Any, ts: Optional[TypeSpec], line: int) -> Any:
        if ts is None or ts.is_array:
            return copy.deepcopy(val)
        bt = norm_key(ts.base_type)
        if bt == "ENTIER":
            if isinstance(val, bool):
                return 1 if val else 0
            if isinstance(val, (int, float)):
                return int(val)
            raise AlgRuntimeError(f"Type incompatible : entier attendu, reçu {val!r}.", line)
        if bt == "REEL":
            if isinstance(val, bool):
                return 1.0 if val else 0.0
            if isinstance(val, (int, float)):
                return float(val)
            raise AlgRuntimeError(f"Type incompatible : réel attendu, reçu {val!r}.", line)
        if bt == "DECIMAL":
            if isinstance(val, (int, float)):
                dec = ts.decimals if ts.decimals is not None else 2
                return round(float(val), dec)
            raise AlgRuntimeError(f"Type incompatible : décimal attendu, reçu {val!r}.", line)
        if bt == "CAR":
            s = str(val)
            return s[:1] if s else ""
        if bt == "CHAINE":
            s = self._format_scalar(val) if not isinstance(val, str) else val
            if ts.size is not None and ts.size > 0:
                return s[: ts.size]
            return s
        if bt == "BOOLEEN":
            if isinstance(val, bool):
                return val
            if isinstance(val, int) and val in (0, 1):
                return bool(val)
            raise AlgRuntimeError(f"Type incompatible : booléen attendu, reçu {val!r}.", line)
        if isinstance(val, StructValue):
            return copy.deepcopy(val)
        return copy.deepcopy(val)

    def _init_frame_decls(
        self, frame: StackFrame, consts: List[ConstDecl], vars_list: List[VarDecl], is_main: bool = False
    ) -> Generator[StepEvent, Any, None]:
        for c in consts:
            ck = norm_key(c.name)
            val = yield from self._eval_expr(c.value_expr)
            frame.consts[ck] = val
            frame.display_names[ck] = c.name

        for vd in vars_list:
            for vname in vd.names:
                vk = norm_key(vname)
                frame.vars[vk] = self._default_for_type(vd.type_spec)
                frame.var_types[vk] = vd.type_spec
                frame.display_names[vk] = vname
                if is_main and vd.is_global:
                    self.global_var_keys.add(vk)

    def _init_files(self) -> None:
        for fdecl in self.program.files:
            fk = norm_key(fdecl.name)
            vfs = VirtualFileState(decl=fdecl)
            self.files[fk] = vfs
            if fdecl.record_name:
                self.record_to_file[norm_key(fdecl.record_name)] = fk
            # Les champs d'enregistrement sont accessibles comme variables globales dans Alg_32
            for rf in fdecl.record_fields:
                for rname in rf.names:
                    rk = norm_key(rname)
                    self.global_frame.vars[rk] = self._default_for_type(rf.type_spec)
                    self.global_frame.var_types[rk] = rf.type_spec
                    self.global_frame.display_names[rk] = rname
                    self.global_var_keys.add(rk)

    # ==========================================
    # Boucle principale du générateur
    # ==========================================

    def run_generator(self) -> Generator[StepEvent, Any, None]:
        try:
            self._init_files()
            yield from self._init_frame_decls(
                self.global_frame, self.program.consts, self.program.vars, is_main=True
            )
            yield from self._exec_block(self.program.body)
            self.current_line = self.program.end_line
            yield StepEvent(kind="FINISHED", line=self.program.end_line, text="Exécution terminée normalement.")
        except AlgRuntimeError as err:
            self.current_line = err.line
            yield StepEvent(kind="ERROR", line=err.line, text=err.message)
        finally:
            if self.sql_conn is not None:
                try:
                    self.sql_conn.close()
                except Exception:
                    pass
                self.sql_conn = None

    def _tick_step(self, line: int) -> StepEvent:
        self.step_count += 1
        if self.step_count > self.max_steps:
            raise AlgRuntimeError(
                f"Limite de sécurité atteinte ({self.max_steps:,} instructions) : boucle infinie probable.",
                line,
            )
        self.current_line = line
        if self.call_stack:
            self.call_stack[-1].line = line
        return StepEvent(kind="STEP", line=line)

    # ==========================================
    # Résolution des variables & affectations
    # ==========================================

    def _find_var_frame(self, name: str) -> Optional[StackFrame]:
        nk = norm_key(name)
        top = self.call_stack[-1]
        if nk in top.vars or nk in top.consts:
            return top
        if len(self.call_stack) == 1:
            return self.global_frame if (nk in self.global_frame.vars or nk in self.global_frame.consts) else None
        # Dans un sous-programme, les variables GLOBALES et constantes principales sont visibles
        if nk in self.global_var_keys or nk in self.global_frame.consts:
            return self.global_frame
        return None

    def _read_lvalue(self, expr: Expr) -> Generator[StepEvent, Any, Any]:
        if isinstance(expr, VarRef):
            nk = norm_key(expr.name)
            frame = self._find_var_frame(expr.name)
            if frame is None:
                raise AlgRuntimeError(f"Variable '{expr.name}' non déclarée dans cette portée.", expr.line)
            if nk in frame.consts:
                return frame.consts[nk]
            return frame.vars[nk]

        if isinstance(expr, IndexAccess):
            container = yield from self._read_lvalue(expr.target)
            idx_vals: List[int] = []
            for ie in expr.indices:
                iv = yield from self._eval_expr(ie)
                idx_vals.append(int(iv) if isinstance(iv, float) and iv.is_integer() else iv)
            if isinstance(container, ArrayValue):
                val = container.get_cell(idx_vals, expr.line)
                if val is None:
                    elem_ts = TypeSpec(base_type=container.base_type)
                    val = self._default_for_type(elem_ts)
                    container.set_cell(idx_vals, val, expr.line)
                return val
            if isinstance(container, str) and len(idx_vals) == 1:
                pos = int(idx_vals[0])
                if 1 <= pos <= len(container):
                    return container[pos - 1]
                raise AlgRuntimeError(f"Indice de chaîne {pos} hors limites (1..{len(container)}).", expr.line)
            raise AlgRuntimeError("Tentative d'indiçage sur une variable qui n'est pas un tableau.", expr.line)

        if isinstance(expr, FieldAccess):
            container = yield from self._read_lvalue(expr.target)
            if not isinstance(container, StructValue):
                raise AlgRuntimeError("Accès '.' sur une variable qui n'est pas une structure.", expr.line)
            return container.get_field(expr.field_name, expr.line)

        raise AlgRuntimeError("Cible de lecture invalide.", expr.line)

    def _write_lvalue(self, target: Expr, value: Any, line: int) -> Generator[StepEvent, Any, None]:
        if isinstance(target, VarRef):
            nk = norm_key(target.name)
            frame = self._find_var_frame(target.name)
            if frame is None:
                raise AlgRuntimeError(f"Variable '{target.name}' non déclarée.", line)
            if nk in frame.consts:
                raise AlgRuntimeError(f"Impossible de modifier la constante '{target.name}'.", line)
            ts = frame.var_types.get(nk)
            frame.vars[nk] = self._coerce_value(value, ts, line)
            return

        if isinstance(target, IndexAccess):
            container = yield from self._read_lvalue(target.target)
            if not isinstance(container, ArrayValue):
                raise AlgRuntimeError("Affectation indicée impossible : la cible n'est pas un tableau.", line)
            idx_vals: List[int] = []
            for ie in target.indices:
                iv = yield from self._eval_expr(ie)
                idx_vals.append(int(iv) if isinstance(iv, float) and iv.is_integer() else iv)
            elem_ts = TypeSpec(line=line, base_type=container.base_type)
            container.set_cell(idx_vals, self._coerce_value(value, elem_ts, line), line)
            return

        if isinstance(target, FieldAccess):
            container = yield from self._read_lvalue(target.target)
            if not isinstance(container, StructValue):
                raise AlgRuntimeError("Affectation de champ impossible : la cible n'est pas une structure.", line)
            container.set_field(target.field_name, copy.deepcopy(value), line)
            return

        raise AlgRuntimeError("Cible d'affectation invalide.", line)

    def _infer_target_type_name(self, target: Expr) -> str:
        if isinstance(target, VarRef):
            frame = self._find_var_frame(target.name)
            if frame:
                ts = frame.var_types.get(norm_key(target.name))
                if ts:
                    return norm_key(ts.base_type)
        elif isinstance(target, IndexAccess) and isinstance(target.target, VarRef):
            frame = self._find_var_frame(target.target.name)
            if frame:
                ts = frame.var_types.get(norm_key(target.target.name))
                if ts:
                    return norm_key(ts.base_type)
        return "AUTO"

    # ==========================================
    # Exécution des instructions
    # ==========================================

    def _exec_block(self, stmts: List[Stmt]) -> Generator[StepEvent, Any, None]:
        for st in stmts:
            yield from self._exec_stmt(st)

    def _exec_stmt(self, st: Stmt) -> Generator[StepEvent, Any, None]:
        yield self._tick_step(st.line)

        if isinstance(st, AssignStmt):
            val = yield from self._eval_expr(st.value)
            yield from self._write_lvalue(st.target, val, st.line)
            return

        if isinstance(st, SaisirStmt):
            if st.prompt is not None:
                p_val = yield from self._eval_expr(st.prompt)
                p_str = self._format_scalar(p_val)
                if p_str:
                    self._advance_cursor_for_text(p_str, False)
                    yield StepEvent(kind="OUTPUT", line=st.line, text=p_str, newline=False)
            else:
                p_str = ""

            for idx, tgt in enumerate(st.targets):
                t_label = self._expr_label(tgt)
                t_type = self._infer_target_type_name(tgt)
                req_prompt = p_str if idx == 0 and p_str else f"{t_label} ({t_type.lower()}) ? "
                raw_input = yield StepEvent(
                    kind="INPUT_REQUEST",
                    line=st.line,
                    prompt=req_prompt,
                    target_name=t_label,
                    target_type=t_type,
                )
                parsed_val = self._parse_user_input(raw_input, t_type, st.line)
                yield from self._write_lvalue(tgt, parsed_val, st.line)
            return

        if isinstance(st, AfficherStmt):
            chunks: List[str] = []
            cur_col = self.cursor_col
            for item in st.items:
                v = yield from self._eval_expr(item)
                if isinstance(v, TabStopMarker):
                    spaces = max(0, v.col - cur_col)
                    chunks.append(" " * spaces)
                    cur_col = v.col
                else:
                    s = self._format_scalar(v)
                    chunks.append(s)
                    cur_col += len(s)

            full_text = "".join(chunks)
            if st.to_printer:
                self.printer_buffer.append(full_text + ("\n" if st.newline else ""))
                yield StepEvent(kind="PRINTER", line=st.line, text=full_text, newline=st.newline)
            else:
                self._advance_cursor_for_text(full_text, st.newline)
                yield StepEvent(kind="OUTPUT", line=st.line, text=full_text, newline=st.newline)
            return

        if isinstance(st, ScreenCmdStmt):
            if st.cmd == "EFFACE_ECRAN":
                self.cursor_line, self.cursor_col = 1, 1
                yield StepEvent(kind="SCREEN_CMD", line=st.line, text="EFFACE_ECRAN")
            elif st.cmd == "A_LA_LIGNE":
                self.cursor_line = min(24, self.cursor_line + 1)
                self.cursor_col = 1
                yield StepEvent(kind="OUTPUT", line=st.line, text="", newline=True)
            elif st.cmd == "CURSEUR":
                lig = int((yield from self._eval_expr(st.args[0])))
                col = int((yield from self._eval_expr(st.args[1])))
                if not (1 <= lig <= 24):
                    raise AlgRuntimeError(f"CURSEUR : numéro de ligne {lig} hors limites (1..24).", st.line)
                if not (1 <= col <= 80):
                    raise AlgRuntimeError(f"CURSEUR : numéro de colonne {col} hors limites (1..80).", st.line)
                self.cursor_line, self.cursor_col = lig, col
                yield StepEvent(kind="SCREEN_CMD", line=st.line, text="CURSEUR", cursor_pos=(lig, col))
            elif st.cmd == "COULEUR":
                fg = int((yield from self._eval_expr(st.args[0])))
                bg = int((yield from self._eval_expr(st.args[1])))
                if not (0 <= fg <= 15) or not (0 <= bg <= 15):
                    raise AlgRuntimeError("COULEUR : les codes encre et fond doivent être entre 0 et 15.", st.line)
                self.fg_color, self.bg_color = fg, bg
                yield StepEvent(kind="SCREEN_CMD", line=st.line, text="COULEUR", fg_color=fg, bg_color=bg)
            return

        if isinstance(st, IfStmt):
            for idx, br in enumerate(st.branches):
                if idx > 0:
                    yield self._tick_step(br.line)
                cond_val = yield from self._eval_expr(br.condition)
                if bool(cond_val):
                    yield from self._exec_block(br.body)
                    return
            if st.else_body:
                yield from self._exec_block(st.else_body)
            return

        if isinstance(st, SelonStmt):
            sel_val = yield from self._eval_expr(st.selector)
            for cb in st.cases:
                matched = False
                for ve in cb.values:
                    cv = yield from self._eval_expr(ve)
                    if sel_val == cv:
                        matched = True
                        break
                if not matched:
                    for r1, r2 in cb.ranges:
                        lo_v = yield from self._eval_expr(r1)
                        hi_v = yield from self._eval_expr(r2)
                        if lo_v <= sel_val <= hi_v:
                            matched = True
                            break
                if matched:
                    yield from self._exec_block(cb.body)
                    return
            if st.else_body:
                yield from self._exec_block(st.else_body)
            return

        if isinstance(st, PourStmt):
            start_v = yield from self._eval_expr(st.start_expr)
            end_v = yield from self._eval_expr(st.end_expr)
            step_v = (yield from self._eval_expr(st.step_expr)) if st.step_expr is not None else 1
            if step_v == 0:
                raise AlgRuntimeError("Le PAS d'une boucle POUR ne peut pas valoir 0.", st.line)

            cur_v = start_v
            yield from self._write_lvalue(st.var_target, cur_v, st.line)
            while (step_v > 0 and cur_v <= end_v) or (step_v < 0 and cur_v >= end_v):
                yield from self._exec_block(st.body)
                yield self._tick_step(st.end_line)
                cur_v = (yield from self._read_lvalue(st.var_target)) + step_v
                yield from self._write_lvalue(st.var_target, cur_v, st.end_line)
            return

        if isinstance(st, TantQueStmt):
            while True:
                cond_v = yield from self._eval_expr(st.condition)
                if not bool(cond_v):
                    break
                yield from self._exec_block(st.body)
                yield self._tick_step(st.line)
            return

        if isinstance(st, RepeterStmt):
            while True:
                yield from self._exec_block(st.body)
                yield self._tick_step(st.until_line)
                until_v = yield from self._eval_expr(st.until_condition)
                if bool(until_v):
                    break
            return

        if isinstance(st, IterStmt):
            try:
                while True:
                    yield from self._exec_block(st.body)
                    yield self._tick_step(st.line)
            except _ExitIterSignal:
                pass
            return

        if isinstance(st, SortirSiStmt):
            cond_v = yield from self._eval_expr(st.condition)
            if bool(cond_v):
                raise _ExitIterSignal()
            return

        if isinstance(st, CallStmt):
            yield from self._invoke_subprogram(st.name, st.args, st.line, expect_value=False)
            return

        if isinstance(st, ReturnStmt):
            ret_val = yield from self._eval_expr(st.value)
            raise _ReturnSignal(ret_val)

        if isinstance(st, CopieStmt):
            mod_path = Path(st.module_path)
            if not mod_path.is_absolute():
                mod_path = self.working_dir / mod_path
            if not mod_path.exists():
                raise AlgRuntimeError(f"Module COPIE introuvable : '{st.module_path}'.", st.line)
            mod_src = read_alg_file_smart(mod_path)
            mod_prog = parse_source(mod_src, profile=self.profile)
            for sp in mod_prog.subprograms:
                self.subprograms[norm_key(sp.name)] = sp
            if mod_prog.body:
                yield from self._exec_block(mod_prog.body)
            return

        if isinstance(st, FileOpStmt):
            yield from self._exec_file_op(st)
            return

        if isinstance(st, SqlStmt):
            yield from self._exec_sql_block(st)
            return

    # ==========================================
    # Sous-programmes (PROCEDURE & FONCTION)
    # ==========================================

    def _invoke_subprogram(
        self, name: str, arg_exprs: List[Expr], call_line: int, expect_value: bool
    ) -> Generator[StepEvent, Any, Any]:
        spk = norm_key(name)
        if spk not in self.subprograms:
            raise AlgRuntimeError(f"Sous-programme '{name}' introuvable.", call_line)
        sp = self.subprograms[spk]
        if len(arg_exprs) != len(sp.params):
            raise AlgRuntimeError(
                f"Appel à '{sp.name}' : {len(sp.params)} argument(s) attendu(s), {len(arg_exprs)} fourni(s).",
                call_line,
            )

        if len(self.call_stack) > 300:
            raise AlgRuntimeError(
                f"Dépassement de la pile d'appels (> 300 appels récursifs dans '{sp.name}').",
                call_line,
            )

        # Évalue d'abord les arguments dans le cadre de l'appelant
        evaluated_args: List[Any] = []
        writeback_targets: List[Tuple[str, Expr]] = []
        for arg_e, pdecl in zip(arg_exprs, sp.params):
            if pdecl.mode == "OUT":
                evaluated_args.append(self._default_for_type(pdecl.type_spec))
                writeback_targets.append((norm_key(pdecl.name), arg_e))
            elif pdecl.mode == "INOUT":
                val = yield from self._eval_expr(arg_e)
                # Les tableaux en INOUT partagent la référence ; les scalaires sont recopiés au retour
                if isinstance(val, ArrayValue):
                    evaluated_args.append(val)
                else:
                    evaluated_args.append(copy.deepcopy(val))
                    if isinstance(arg_e, (VarRef, IndexAccess, FieldAccess)):
                        writeback_targets.append((norm_key(pdecl.name), arg_e))
            else:
                val = yield from self._eval_expr(arg_e)
                evaluated_args.append(copy.deepcopy(val))

        callee_frame = StackFrame(name=sp.name, line=sp.line)
        # Pour une FONCTION, Alg_32 autorise `nom_fonction := résultat` !
        if sp.kind == "FONCTION" and sp.return_type is not None:
            fn_key = norm_key(sp.name)
            callee_frame.vars[fn_key] = self._default_for_type(sp.return_type)
            callee_frame.var_types[fn_key] = sp.return_type
            callee_frame.display_names[fn_key] = sp.name

        for pdecl, aval in zip(sp.params, evaluated_args):
            pk = norm_key(pdecl.name)
            callee_frame.vars[pk] = (
                aval if isinstance(aval, ArrayValue) else self._coerce_value(aval, pdecl.type_spec, call_line)
            )
            callee_frame.var_types[pk] = pdecl.type_spec
            callee_frame.display_names[pk] = pdecl.name

        self.call_stack.append(callee_frame)
        return_val: Any = None
        has_explicit_return = False

        try:
            yield from self._init_frame_decls(callee_frame, sp.consts, sp.vars, is_main=False)
            yield from self._exec_block(sp.body)
        except _ReturnSignal as sig:
            return_val = sig.value
            has_explicit_return = True
        finally:
            self.call_stack.pop()

        # Répercute les paramètres OUT / INOUT dans le cadre appelant
        for pk, caller_target in writeback_targets:
            out_val = callee_frame.vars.get(pk)
            yield from self._write_lvalue(caller_target, out_val, call_line)

        if sp.kind == "FONCTION":
            if not has_explicit_return:
                return_val = callee_frame.vars.get(norm_key(sp.name))
            return self._coerce_value(return_val, sp.return_type, call_line)
        return None

    # ==========================================
    # Évaluation des expressions & Fonctions Alg_32
    # ==========================================

    def _eval_expr(self, expr: Expr) -> Generator[StepEvent, Any, Any]:
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, VarRef):
            if self._find_var_frame(expr.name) is not None:
                return (yield from self._read_lvalue(expr))
            b_canon = self.profile.resolve_builtin(expr.name)
            if b_canon in ("ALEA", "DATESYST", "HEURESYST", "COLONNE", "LIGNE", "UNCAR", "UNETOUCHE", "ERREUR_SQL"):
                return (yield from self._eval_builtin(b_canon, [], expr.line))
            return (yield from self._read_lvalue(expr))

        if isinstance(expr, (IndexAccess, FieldAccess)):
            return (yield from self._read_lvalue(expr))

        if isinstance(expr, UnaryOp):
            val = yield from self._eval_expr(expr.operand)
            if expr.op == "-":
                return -val
            if expr.op == "+":
                return +val
            if expr.op == "NON":
                return not bool(val)
            raise AlgRuntimeError(f"Opérateur unaire inconnu : {expr.op}", expr.line)

        if isinstance(expr, BinaryOp):
            # Court-circuit logique optionnel
            if expr.op == "ET":
                lv = yield from self._eval_expr(expr.left)
                if not bool(lv):
                    return False
                rv = yield from self._eval_expr(expr.right)
                return bool(rv)
            if expr.op == "OU":
                lv = yield from self._eval_expr(expr.left)
                if bool(lv):
                    return True
                rv = yield from self._eval_expr(expr.right)
                return bool(rv)

            lv = yield from self._eval_expr(expr.left)
            rv = yield from self._eval_expr(expr.right)
            return self._apply_binary(expr.op, lv, rv, expr.line)

        if isinstance(expr, CallExpr):
            b_canon = self.profile.resolve_builtin(expr.name)
            if b_canon is not None:
                return (yield from self._eval_builtin(b_canon, expr.args, expr.line))
            return (yield from self._invoke_subprogram(expr.name, expr.args, expr.line, expect_value=True))

        raise AlgRuntimeError("Expression non évaluable.", expr.line)

    def _apply_binary(self, op: str, lv: Any, rv: Any, line: int) -> Any:
        try:
            if op == "+":
                if isinstance(lv, str) or isinstance(rv, str):
                    return self._format_scalar(lv) + self._format_scalar(rv)
                return lv + rv
            if op == "-":
                return lv - rv
            if op == "*":
                return lv * rv
            if op == "/":
                if rv == 0:
                    raise AlgRuntimeError("Division par zéro impossible !", line)
                res = lv / rv
                return res
            if op == "DIV":
                if rv == 0:
                    raise AlgRuntimeError("Division entière (DIV) par zéro impossible !", line)
                return int(lv) // int(rv)
            if op == "MOD":
                if rv == 0:
                    raise AlgRuntimeError("Modulo (MOD) par zéro impossible !", line)
                return int(lv) % int(rv)
            if op == "^":
                return lv**rv
            if op == "=":
                return lv == rv
            if op == "<>":
                return lv != rv
            if op == "<":
                return lv < rv
            if op == "<=":
                return lv <= rv
            if op == ">":
                return lv > rv
            if op == ">=":
                return lv >= rv
            if op == "OUX":
                return bool(lv) ^ bool(rv)
        except AlgRuntimeError:
            raise
        except TypeError as exc:
            raise AlgRuntimeError(
                f"Types incompatibles pour l'opérateur '{op}' ({type(lv).__name__} et {type(rv).__name__}).",
                line,
            ) from exc
        raise AlgRuntimeError(f"Opérateur binaire inconnu : {op}", line)

    def _eval_builtin(self, canon: str, arg_exprs: List[Expr], line: int) -> Generator[StepEvent, Any, Any]:
        # Fonctions prenant un nom de fichier ou d'enregistrement sans l'évaluer comme variable ordinaire
        if canon in ("FF", "EXISTE", "ERREUR"):
            if not arg_exprs:
                return self.sql_eof if canon == "FF" else False
            first = arg_exprs[0]
            if isinstance(first, VarRef):
                fk = norm_key(first.name)
                if fk in self.record_to_file:
                    fk = self.record_to_file[fk]
                vfs = self.files.get(fk)
                if vfs:
                    if canon == "FF":
                        return vfs.eof
                    if canon == "EXISTE":
                        return vfs.last_exists
                    if canon == "ERREUR":
                        return vfs.last_error
            return False

        args: List[Any] = []
        for ae in arg_exprs:
            args.append((yield from self._eval_expr(ae)))

        if canon == "LONG":
            return len(str(args[0]))
        if canon == "GAUCHE":
            n = max(0, int(args[1]))
            return str(args[0])[:n]
        if canon == "DROITE":
            n = max(0, int(args[1]))
            return "" if n == 0 else str(args[0])[-n:]
        if canon == "MILIEU":
            s = str(args[0])
            pos = max(1, int(args[1]))
            length = max(0, int(args[2]))
            return s[pos - 1 : pos - 1 + length]
        if canon == "RANG":
            hay = str(args[0])
            needle = str(args[1])
            start = max(1, int(args[2])) if len(args) >= 3 else 1
            found = hay.find(needle, start - 1)
            return (found + 1) if found != -1 else 0
        if canon == "SUPPR":
            s = str(args[0])
            pos = max(1, int(args[1]))
            length = max(0, int(args[2]))
            return s[: pos - 1] + s[pos - 1 + length :]
        if canon == "ESPACE":
            n = int(args[0])
            if n < 0:
                raise AlgRuntimeError("ESPACE(n) : n doit être positif ou nul.", line)
            return " " * n
        if canon == "REPETECAR":
            count = max(0, int(args[0]))
            code = int(args[1])
            if not (0 <= code <= 0x10FFFF):
                raise AlgRuntimeError("RÉPÈTECAR : code caractère invalide.", line)
            ch = bytes([code]).decode("cp1252", errors="replace") if code <= 255 else chr(code)
            return ch * count
        if canon == "MAJ":
            return str(args[0]).upper()
        if canon == "MIN":
            return str(args[0]).lower()
        if canon == "ESPACEDROITE":
            return str(args[0]).rstrip(" ")
        if canon == "ESPACEGAUCHE":
            return str(args[0]).lstrip(" ")
        if canon == "ANSI":
            s = str(args[0])
            if not s:
                return 0
            try:
                return s[0].encode("cp1252")[0]
            except UnicodeEncodeError:
                return ord(s[0])
        if canon == "CAR":
            code = int(args[0])
            if not (0 <= code <= 0x10FFFF):
                raise AlgRuntimeError(f"CAR({code}) : le code caractère doit être >= 0.", line)
            if code <= 255:
                return bytes([code]).decode("cp1252", errors="replace")
            return chr(code)
        if canon == "CVCHAINE":
            return self._format_scalar(args[0])
        if canon == "CHNOMBRE":
            raw_s = str(args[0]).strip().replace(",", ".")
            try:
                return float(raw_s) if ("." in raw_s or "e" in raw_s.lower()) else int(raw_s)
            except ValueError:
                return 0
        if canon == "HEX":
            return format(int(args[0]), "X")
        if canon == "ABS":
            return abs(args[0])
        if canon == "ENT":
            return math.trunc(float(args[0]))
        if canon == "DECIMALE":
            x = float(args[0])
            return round(x - math.trunc(x), 10)
        if canon == "ARRONDI":
            x = float(args[0])
            return int(math.floor(x + 0.5)) if x >= 0 else int(math.ceil(x - 0.5))
        if canon == "RAC2":
            x = float(args[0])
            if x < 0:
                raise AlgRuntimeError("RAC2 : la racine carrée d'un nombre négatif est impossible !", line)
            res = math.sqrt(x)
            return int(res) if res.is_integer() and isinstance(args[0], int) else res
        if canon == "SIN":
            return math.sin(float(args[0]))
        if canon == "COS":
            return math.cos(float(args[0]))
        if canon == "TAN":
            return math.tan(float(args[0]))
        if canon == "ATN":
            return math.atan(float(args[0]))
        if canon == "EXP":
            return math.exp(float(args[0]))
        if canon == "LN":
            x = float(args[0])
            if x <= 0:
                raise AlgRuntimeError("LN : argument strictement positif requis.", line)
            return math.log(x)
        if canon == "ALEA":
            return random.random()
        if canon == "ALEA_ENTIER":
            return random.randint(int(args[0]), int(args[1]))
        if canon == "DATESYST":
            return datetime.datetime.now().strftime("%d/%m/%Y")
        if canon == "HEURESYST":
            return datetime.datetime.now().strftime("%H:%M:%S")
        if canon == "COLONNE":
            return self.cursor_col
        if canon == "LIGNE":
            return self.cursor_line
        if canon == "TAB":
            col = int(args[0])
            if not (1 <= col <= 132):
                raise AlgRuntimeError("TAB(col) : col doit être compris entre 1 et 132.", line)
            return TabStopMarker(col=col)
        if canon in ("UNCAR", "UNETOUCHE"):
            val = yield StepEvent(
                kind="INPUT_REQUEST",
                line=line,
                prompt="Appuyez sur un caractère puis Entrée : ",
                target_name=canon,
                target_type="CAR",
            )
            s = str(val)
            return s[:1] if s else ""
        if canon == "ERREUR_SQL":
            return self.sql_last_error

        raise AlgRuntimeError(f"Fonction intégrée non implémentée : {canon}", line)

    # ==========================================
    # Gestion des fichiers Alg_32
    # ==========================================

    def _resolve_vfs(self, name: str, line: int) -> VirtualFileState:
        nk = norm_key(name)
        if nk in self.record_to_file:
            nk = self.record_to_file[nk]
        if nk not in self.files:
            raise AlgRuntimeError(f"Fichier ou enregistrement '{name}' non déclaré.", line)
        return self.files[nk]

    def _file_disk_path(self, vfs: VirtualFileState) -> Path:
        folder = self.working_dir / ".omega_files"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{norm_key(vfs.decl.name).lower()}.algfile.json"

    def _capture_record_vars(self, vfs: VirtualFileState) -> Dict[str, Any]:
        rec: Dict[str, Any] = {}
        for rf in vfs.decl.record_fields:
            for rname in rf.names:
                rk = norm_key(rname)
                rec[rk] = copy.deepcopy(self.global_frame.vars.get(rk))
        return rec

    def _restore_record_vars(self, vfs: VirtualFileState, rec: Dict[str, Any]) -> None:
        for rf in vfs.decl.record_fields:
            for rname in rf.names:
                rk = norm_key(rname)
                if rk in rec:
                    self.global_frame.vars[rk] = copy.deepcopy(rec[rk])

    def _save_vfs_to_disk(self, vfs: VirtualFileState) -> None:
        try:
            payload = {
                "organisation": vfs.decl.organisation,
                "records": vfs.records,
                "indexed_records": vfs.indexed_records,
                "binary_data": vfs.binary_data,
            }
            self._file_disk_path(vfs).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_vfs_from_disk(self, vfs: VirtualFileState) -> None:
        p = self._file_disk_path(vfs)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                vfs.records = list(data.get("records", []))
                vfs.indexed_records = dict(data.get("indexed_records", {}))
                vfs.binary_data = list(data.get("binary_data", []))
            except Exception:
                pass

    def _exec_file_op(self, st: FileOpStmt) -> Generator[StepEvent, Any, None]:
        if st.op == "OUVRIR":
            vfs = self._resolve_vfs(st.target_names[0], st.line)
            self._load_vfs_from_disk(vfs)
            vfs.is_open = True
            vfs.mode = st.mode
            vfs.last_error = False
            vfs.eof = False
            if st.mode == "ECRITURE" and vfs.decl.organisation == "SEQUENTIELLE":
                vfs.records = []
                vfs.cursor = 0
            elif st.mode == "EXTENSION":
                vfs.cursor = len(vfs.records)
            else:
                vfs.cursor = 0
            return

        if st.op == "FERMER":
            for fname in st.target_names:
                vfs = self._resolve_vfs(fname, st.line)
                self._save_vfs_to_disk(vfs)
                vfs.is_open = False
                vfs.mode = "FERME"
            return

        vfs = self._resolve_vfs(st.target_names[0], st.line)
        if not vfs.is_open:
            raise AlgRuntimeError(f"Le fichier '{vfs.decl.name}' n'est pas ouvert.", st.line)

        org = vfs.decl.organisation
        if st.op == "ECRIRE":
            if org == "BINAIRE" and st.var_target is not None:
                val = yield from self._eval_expr(st.var_target)
                pos = int((yield from self._eval_expr(st.position_expr))) if st.position_expr else vfs.cursor
                while len(vfs.binary_data) <= pos:
                    vfs.binary_data.append(None)
                vfs.binary_data[pos] = copy.deepcopy(val)
                vfs.cursor = pos + 1
            elif org in ("INDEXEE", "RELATIVE") and vfs.decl.primary_key:
                rec = self._capture_record_vars(vfs)
                pk_norm = norm_key(vfs.decl.primary_key)
                key_val = str(rec.get(pk_norm, self.global_frame.vars.get(pk_norm, "")))
                vfs.indexed_records[key_val] = rec
                vfs.last_error = False
            else:
                vfs.records.append(self._capture_record_vars(vfs))
                vfs.cursor = len(vfs.records)
            self._save_vfs_to_disk(vfs)
            return

        if st.op == "LIRE":
            if org == "BINAIRE" and st.var_target is not None:
                pos = int((yield from self._eval_expr(st.position_expr))) if st.position_expr else vfs.cursor
                if 0 <= pos < len(vfs.binary_data):
                    yield from self._write_lvalue(st.var_target, vfs.binary_data[pos], st.line)
                    vfs.cursor = pos + 1
                    vfs.eof = False
                else:
                    vfs.eof = True
                return

            if st.key_expr is not None:
                kval = str((yield from self._eval_expr(st.key_expr)))
                if kval in vfs.indexed_records:
                    self._restore_record_vars(vfs, vfs.indexed_records[kval])
                    vfs.last_exists = True
                    vfs.last_error = False
                    vfs.eof = False
                else:
                    vfs.last_exists = False
                    vfs.last_error = True
                return

            if org in ("INDEXEE", "RELATIVE") and vfs.indexed_records and not vfs.records:
                keys_sorted = sorted(vfs.indexed_records.keys())
                if vfs.cursor < len(keys_sorted):
                    self._restore_record_vars(vfs, vfs.indexed_records[keys_sorted[vfs.cursor]])
                    vfs.cursor += 1
                    vfs.eof = False
                    vfs.last_exists = True
                else:
                    vfs.eof = True
                    vfs.last_exists = False
                return

            if vfs.cursor < len(vfs.records):
                self._restore_record_vars(vfs, vfs.records[vfs.cursor])
                vfs.cursor += 1
                vfs.eof = False
                vfs.last_exists = True
            else:
                vfs.eof = True
                vfs.last_exists = False
            return

        if st.op == "REECRIRE":
            if vfs.decl.primary_key:
                rec = self._capture_record_vars(vfs)
                pk_norm = norm_key(vfs.decl.primary_key)
                key_val = str(rec.get(pk_norm, self.global_frame.vars.get(pk_norm, "")))
                if key_val in vfs.indexed_records:
                    vfs.indexed_records[key_val] = rec
                    vfs.last_error = False
                else:
                    vfs.last_error = True
            self._save_vfs_to_disk(vfs)
            return

        if st.op == "SUPPRIMER":
            if vfs.decl.primary_key:
                pk_norm = norm_key(vfs.decl.primary_key)
                key_val = str(self.global_frame.vars.get(pk_norm, ""))
                vfs.last_error = key_val not in vfs.indexed_records
                vfs.indexed_records.pop(key_val, None)
            self._save_vfs_to_disk(vfs)
            return

        if st.op == "POSITIONNER":
            if st.key_expr is not None and vfs.indexed_records:
                kval = str((yield from self._eval_expr(st.key_expr)))
                keys_sorted = sorted(vfs.indexed_records.keys())
                if kval in keys_sorted:
                    vfs.cursor = keys_sorted.index(kval)
                    vfs.last_exists = True
                else:
                    vfs.last_exists = False
            elif st.position_expr is not None:
                vfs.cursor = max(0, int((yield from self._eval_expr(st.position_expr))))

    # ==========================================
    # Moteur SQL intégré (SQLite3)
    # ==========================================

    def _exec_sql_block(self, st: SqlStmt) -> Generator[StepEvent, Any, None]:
        raw = st.raw_sql.strip().rstrip(";")
        up = " ".join(raw.upper().split())
        self.sql_last_error = False

        try:
            if up.startswith("START DATABASE"):
                db_name = raw.split(None, 2)[2].strip().strip('"').strip("'")
                if self.sql_conn is not None:
                    self.sql_conn.close()
                if db_name.upper() in (":MEMORY:", "MEMOIRE"):
                    self.sql_conn = sqlite3.connect(":memory:")
                    self.sql_db_name = ":memory:"
                else:
                    db_dir = self.working_dir / ".omega_sql"
                    db_dir.mkdir(parents=True, exist_ok=True)
                    clean_name = db_name if db_name.endswith((".db", ".sqlite")) else f"{db_name}.sqlite"
                    db_path = db_dir / clean_name
                    self.sql_conn = sqlite3.connect(str(db_path))
                    self.sql_db_name = str(db_path)
                return

            if up.startswith("STOP DATABASE"):
                if self.sql_conn is not None:
                    self.sql_conn.commit()
                    self.sql_conn.close()
                    self.sql_conn = None
                return

            if self.sql_conn is None:
                # Ouvre automatiquement une base en mémoire si l'étudiant oublie START DATABASE
                self.sql_conn = sqlite3.connect(":memory:")
                self.sql_db_name = ":memory: (auto)"

            # Gestion des curseurs SQL d'Alg_32 : DECLARE, OPEN, FETCH, CLOSE
            m_decl = re.match(r"(?is)^DECLARE\s+(\w+)\s+CURSOR\s+FOR\s+(SELECT\s+.+)$", raw)
            if m_decl:
                cname = norm_key(m_decl.group(1))
                self.sql_cursors[cname] = (m_decl.group(2), None)
                return

            m_open = re.match(r"(?is)^OPEN\s+(\w+)$", raw)
            if m_open:
                cname = norm_key(m_open.group(1))
                if cname not in self.sql_cursors:
                    raise AlgRuntimeError(f"Curseur SQL '{m_open.group(1)}' non déclaré.", st.line)
                query_tpl, _ = self.sql_cursors[cname]
                sql_q, params = self._bind_sql_host_vars(query_tpl, st.line)
                cur = self.sql_conn.cursor()
                cur.execute(sql_q, params)
                self.sql_cursors[cname] = (query_tpl, cur)
                self.sql_eof = False
                return

            m_close = re.match(r"(?is)^CLOSE\s+(\w+)$", raw)
            if m_close:
                cname = norm_key(m_close.group(1))
                if cname in self.sql_cursors and self.sql_cursors[cname][1] is not None:
                    self.sql_cursors[cname][1].close()  # type: ignore[union-attr]
                    self.sql_cursors[cname] = (self.sql_cursors[cname][0], None)
                return

            m_fetch = re.match(r"(?is)^FETCH\s+(\w+)\s+INTO\s+(.+)$", raw)
            if m_fetch:
                cname = norm_key(m_fetch.group(1))
                if cname not in self.sql_cursors or self.sql_cursors[cname][1] is None:
                    raise AlgRuntimeError(f"Curseur SQL '{m_fetch.group(1)}' non ouvert.", st.line)
                cur = self.sql_cursors[cname][1]
                row = cur.fetchone()  # type: ignore[union-attr]
                if row is None:
                    self.sql_eof = True
                else:
                    self.sql_eof = False
                    host_vars = [v.strip().lstrip(":") for v in m_fetch.group(2).split(",")]
                    for hname, col_val in zip(host_vars, row):
                        yield from self._write_lvalue(VarRef(line=st.line, name=hname), col_val, st.line)
                return

            # SELECT ... INTO :v1, :v2 FROM ...
            m_sel_into = re.match(r"(?is)^SELECT\s+(.+?)\s+INTO\s+(.+?)\s+(FROM\s+.+)$", raw)
            if m_sel_into:
                cols_part, into_part, from_part = m_sel_into.groups()
                clean_select = f"SELECT {cols_part} {from_part}"
                sql_q, params = self._bind_sql_host_vars(clean_select, st.line)
                cur = self.sql_conn.cursor()
                cur.execute(sql_q, params)
                row = cur.fetchone()
                if row is None:
                    self.sql_eof = True
                else:
                    self.sql_eof = False
                    host_vars = [v.strip().lstrip(":") for v in into_part.split(",")]
                    for hname, col_val in zip(host_vars, row):
                        yield from self._write_lvalue(VarRef(line=st.line, name=hname), col_val, st.line)
                return

            # Autres requêtes (CREATE TABLE, INSERT, UPDATE, DELETE, SELECT direct)
            sql_q, params = self._bind_sql_host_vars(raw, st.line)
            cur = self.sql_conn.cursor()
            cur.execute(sql_q, params)
            if up.startswith("SELECT"):
                rows = cur.fetchall()
                cols = [d[0] for d in (cur.description or [])]
                yield StepEvent(kind="SQL_RESULT", line=st.line, sql_columns=cols, sql_rows=rows)
            else:
                self.sql_conn.commit()
        except AlgRuntimeError:
            raise
        except Exception as exc:
            self.sql_last_error = True
            raise AlgRuntimeError(f"Erreur SQL : {exc}", st.line) from exc

    def _bind_sql_host_vars(self, sql_text: str, line: int) -> Tuple[str, List[Any]]:
        params: List[Any] = []

        def repl(match: re.Match[str]) -> str:
            vname = match.group(1)
            frame = self._find_var_frame(vname)
            nk = norm_key(vname)
            if frame is None:
                raise AlgRuntimeError(f"Variable hôte SQL ':{vname}' non déclarée.", line)
            val = frame.consts[nk] if nk in frame.consts else frame.vars[nk]
            params.append(val)
            return "?"

        converted = re.sub(r":([A-Za-z_À-ÿ][A-Za-z0-9_À-ÿ]*)", repl, sql_text)
        return converted, params

    # ==========================================
    # Utilitaires d'affichage et d'inspection
    # ==========================================

    def _advance_cursor_for_text(self, text: str, newline: bool) -> None:
        for ch in text:
            if ch == "\n":
                self.cursor_line = min(24, self.cursor_line + 1)
                self.cursor_col = 1
            else:
                self.cursor_col += 1
                if self.cursor_col > 80:
                    self.cursor_col = 1
                    self.cursor_line = min(24, self.cursor_line + 1)
        if newline:
            self.cursor_line = min(24, self.cursor_line + 1)
            self.cursor_col = 1

    def _format_scalar(self, val: Any) -> str:
        if isinstance(val, bool):
            return ".VRAI." if val else ".FAUX."
        if isinstance(val, float):
            if val.is_integer():
                return str(int(val))
            return f"{val:.10g}"
        if val is None:
            return ""
        return str(val)

    def _parse_user_input(self, raw: Any, expected_type: str, line: int) -> Any:
        text = "" if raw is None else str(raw)
        s = text.strip()
        if expected_type == "CHAINE":
            return text
        if expected_type == "CAR":
            return text[:1] if text else ""
        if expected_type == "BOOLEEN":
            up = norm_key(s.strip("."))
            if up in ("VRAI", "1", "OUI", "TRUE", "V"):
                return True
            if up in ("FAUX", "0", "NON", "FALSE", "F"):
                return False
            raise AlgRuntimeError(
                f"Saisie booléenne invalide ({text!r}) : entrez .VRAI., .FAUX., 1 ou 0.",
                line,
            )
        if expected_type == "ENTIER":
            try:
                return int(s)
            except ValueError as exc:
                raise AlgRuntimeError(f"Saisie entière invalide : {text!r} n'est pas un entier.", line) from exc
        if expected_type in ("REEL", "DECIMAL"):
            try:
                return float(s.replace(",", "."))
            except ValueError as exc:
                raise AlgRuntimeError(f"Saisie numérique invalide : {text!r} n'est pas un nombre réel.", line) from exc

        # Mode AUTO (ex: champ de structure)
        if s.upper() in (".VRAI.", "VRAI"):
            return True
        if s.upper() in (".FAUX.", "FAUX"):
            return False
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return text

    def _expr_label(self, expr: Expr) -> str:
        if isinstance(expr, VarRef):
            return expr.name
        if isinstance(expr, FieldAccess):
            return f"{self._expr_label(expr.target)}.{expr.field_name}"
        if isinstance(expr, IndexAccess):
            return f"{self._expr_label(expr.target)}[...]"
        return "valeur"

    def snapshot_state(self) -> Dict[str, Any]:
        """Retourne un instantané complet des variables, tableaux, pile d'appels, fichiers et tables SQL."""
        frames_info = []
        for fr in self.call_stack:
            v_dict: Dict[str, Any] = {}
            for vk, val in fr.vars.items():
                disp = fr.display_names.get(vk, vk)
                v_dict[disp] = val
            c_dict: Dict[str, Any] = {}
            for ck, val in fr.consts.items():
                disp = fr.display_names.get(ck, ck)
                c_dict[disp] = val
            frames_info.append(
                {
                    "name": fr.name,
                    "line": fr.line,
                    "vars": v_dict,
                    "consts": c_dict,
                }
            )

        sql_tables: Dict[str, Tuple[List[str], List[Tuple[Any, ...]]]] = {}
        if self.sql_conn is not None:
            try:
                cur = self.sql_conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                for (tname,) in cur.fetchall():
                    cur.execute(f'SELECT * FROM "{tname}" LIMIT 100')
                    rows = cur.fetchall()
                    cols = [d[0] for d in (cur.description or [])]
                    sql_tables[tname] = (cols, rows)
            except Exception:
                pass

        files_info = {
            vfs.decl.name: {
                "organisation": vfs.decl.organisation,
                "open": vfs.is_open,
                "mode": vfs.mode,
                "count": len(vfs.indexed_records) if vfs.indexed_records else len(vfs.records),
                "eof": vfs.eof,
            }
            for vfs in self.files.values()
        }

        return {
            "line": self.current_line,
            "steps": self.step_count,
            "frames": frames_info,
            "sql_db": self.sql_db_name,
            "sql_tables": sql_tables,
            "files": files_info,
        }
