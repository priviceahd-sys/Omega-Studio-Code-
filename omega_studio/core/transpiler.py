"""
Transpileur multi-langages : traduit un AST Alg_32 / Omega Studio Code
en code propre et idiomatique vers Python 3, C (C11), JavaScript (ES6) et Pascal.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

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
from .keywords import KeywordProfile, norm_key, strip_accents


def _safe_id(name: str) -> str:
    s = strip_accents(name)
    cleaned = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in s)
    return cleaned or "ident"


def expr_to_display(expr: Expr) -> str:
    """Représentation lisible d'une expression Alg_32 (utilisée aussi pour l'organigramme)."""
    if isinstance(expr, Literal):
        if expr.lit_type == "CHAINE":
            return f'"{expr.value}"'
        if expr.lit_type == "BOOLEEN":
            return "VRAI" if expr.value else "FAUX"
        return str(expr.value)
    if isinstance(expr, VarRef):
        return expr.name
    if isinstance(expr, IndexAccess):
        idxs = ", ".join(expr_to_display(i) for i in expr.indices)
        return f"{expr_to_display(expr.target)}[{idxs}]"
    if isinstance(expr, FieldAccess):
        return f"{expr_to_display(expr.target)}.{expr.field_name}"
    if isinstance(expr, UnaryOp):
        sep = " " if expr.op == "NON" else ""
        return f"{expr.op}{sep}{expr_to_display(expr.operand)}"
    if isinstance(expr, BinaryOp):
        return f"{expr_to_display(expr.left)} {expr.op} {expr_to_display(expr.right)}"
    if isinstance(expr, CallExpr):
        args = ", ".join(expr_to_display(a) for a in expr.args)
        return f"{expr.name}({args})"
    return "?"


class MultiTranspiler:
    def __init__(self, program: Program, profile: Optional[KeywordProfile] = None) -> None:
        self.program = program
        self.profile = profile or KeywordProfile()
        self.var_types: Dict[str, TypeSpec] = {}
        for vd in program.vars:
            for n in vd.names:
                self.var_types[norm_key(n)] = vd.type_spec

    def transpile(self, target: str) -> str:
        lang = target.lower()
        if lang == "python":
            return self._to_python()
        if lang == "c":
            return self._to_c()
        if lang in ("javascript", "js"):
            return self._to_javascript()
        if lang == "pascal":
            return self._to_pascal()
        raise ValueError(f"Langage cible inconnu : {target}")

    # ==========================================
    # 1. PYTHON 3
    # ==========================================

    def _to_python(self) -> str:
        lines: List[str] = [
            f"# Généré par Omega Studio Code depuis l'algorithme : {self.program.name}",
            "import datetime",
            "import math",
            "import random",
            "from dataclasses import dataclass, field",
            "",
        ]

        # Types utilisateurs & structures inline
        for td in self.program.types:
            lines.append("@dataclass")
            lines.append(f"class {_safe_id(td.name)}:")
            if not td.fields:
                lines.append("    pass")
            for fd in td.fields:
                for fn in fd.names:
                    lines.append(f"    {_safe_id(fn)}: {self._py_type_hint(fd.type_spec)} = {self._py_default(fd.type_spec)}")
            lines.append("")

        for vd in self.program.vars:
            if norm_key(vd.type_spec.base_type) == "STRUCTURE":
                for sname in vd.names:
                    cls_name = f"Struct_{_safe_id(sname)}"
                    lines.append("@dataclass")
                    lines.append(f"class {cls_name}:")
                    for fd in vd.type_spec.struct_fields:
                        for fn in fd.names:
                            lines.append(
                                f"    {_safe_id(fn)}: {self._py_type_hint(fd.type_spec)} = {self._py_default(fd.type_spec)}"
                            )
                    lines.append("")

        # Constantes globales
        if self.program.consts:
            for c in self.program.consts:
                lines.append(f"{_safe_id(c.name)} = {self._py_expr(c.value_expr)}")
            lines.append("")

        # Sous-programmes
        for sp in self.program.subprograms:
            params_str = ", ".join(_safe_id(p.name) for p in sp.params)
            lines.append(f"def {_safe_id(sp.name)}({params_str}):")
            sp_body: List[str] = []
            if sp.kind == "FONCTION" and sp.return_type:
                sp_body.append(f"    {_safe_id(sp.name)}_ret = {self._py_default(sp.return_type)}")
            for c in sp.consts:
                sp_body.append(f"    {_safe_id(c.name)} = {self._py_expr(c.value_expr)}")
            for vd in sp.vars:
                for vn in vd.names:
                    sp_body.append(f"    {_safe_id(vn)} = {self._py_default(vd.type_spec)}")
            out_params = [_safe_id(p.name) for p in sp.params if p.mode in ("OUT", "INOUT") and not p.type_spec.is_array]
            sp_body.extend(self._py_stmts(sp.body, indent=1, fn_name=sp.name if sp.kind == "FONCTION" else None))
            if sp.kind == "FONCTION":
                sp_body.append(f"    return {_safe_id(sp.name)}_ret")
            elif out_params:
                sp_body.append(f"    return {', '.join(out_params)}")
            if not sp_body:
                sp_body.append("    pass")
            lines.extend(sp_body)
            lines.append("")

        # Fonction principale main()
        lines.append("def main() -> None:")
        main_lines: List[str] = []
        for vd in self.program.vars:
            for vn in vd.names:
                if norm_key(vd.type_spec.base_type) == "STRUCTURE":
                    main_lines.append(f"    {_safe_id(vn)} = Struct_{_safe_id(vn)}()")
                else:
                    main_lines.append(f"    {_safe_id(vn)} = {self._py_default(vd.type_spec)}")
        main_lines.extend(self._py_stmts(self.program.body, indent=1))
        if not main_lines:
            main_lines.append("    pass")
        lines.extend(main_lines)
        lines.extend(["", 'if __name__ == "__main__":', "    main()", ""])
        return "\n".join(lines)

    def _py_type_hint(self, ts: TypeSpec) -> str:
        if ts.is_array:
            return "list"
        bt = norm_key(ts.base_type)
        return {
            "ENTIER": "int",
            "REEL": "float",
            "DECIMAL": "float",
            "CHAINE": "str",
            "CAR": "str",
            "BOOLEEN": "bool",
        }.get(bt, _safe_id(ts.base_type))

    def _py_default(self, ts: TypeSpec) -> str:
        if ts.is_array and ts.dimensions:
            elem_ts = TypeSpec(base_type=ts.base_type)
            inner = self._py_default(elem_ts)
            for lo, hi in reversed(ts.dimensions):
                size = max(1, hi + 1)
                inner = f"[{inner} for _ in range({size})]"
            return inner
        bt = norm_key(ts.base_type)
        if bt == "ENTIER":
            return "0"
        if bt in ("REEL", "DECIMAL"):
            return "0.0"
        if bt in ("CHAINE", "CAR"):
            return '""'
        if bt == "BOOLEEN":
            return "False"
        return f"field(default_factory={_safe_id(ts.base_type)})" if False else f"{_safe_id(ts.base_type)}()"

    def _py_stmts(self, stmts: List[Stmt], indent: int, fn_name: Optional[str] = None) -> List[str]:
        pad = "    " * indent
        out: List[str] = []
        sub_map = {norm_key(s.name): s for s in self.program.subprograms}

        for st in stmts:
            if isinstance(st, AssignStmt):
                if fn_name and isinstance(st.target, VarRef) and norm_key(st.target.name) == norm_key(fn_name):
                    out.append(f"{pad}{_safe_id(fn_name)}_ret = {self._py_expr(st.value)}")
                else:
                    out.append(f"{pad}{self._py_expr(st.target)} = {self._py_expr(st.value)}")
            elif isinstance(st, SaisirStmt):
                prompt_code = self._py_expr(st.prompt) if st.prompt else '""'
                for idx, tgt in enumerate(st.targets):
                    p_str = prompt_code if idx == 0 and st.prompt else f'"{self._py_expr(tgt)} ? "'
                    cast = self._py_input_cast(tgt, f"input({p_str})")
                    out.append(f"{pad}{self._py_expr(tgt)} = {cast}")
            elif isinstance(st, AfficherStmt):
                args = ", ".join(self._py_expr(it) for it in st.items)
                end_kw = ', end=""' if not st.newline else ""
                sep_kw = ', sep=""' if len(st.items) > 1 else ""
                out.append(f"{pad}print({args}{sep_kw}{end_kw})")
            elif isinstance(st, ScreenCmdStmt):
                if st.cmd == "A_LA_LIGNE":
                    out.append(f"{pad}print()")
                elif st.cmd == "EFFACE_ECRAN":
                    out.append(f'{pad}print("\\033[2J\\033[H", end="")')
                else:
                    out.append(f"{pad}# {st.cmd}({', '.join(self._py_expr(a) for a in st.args)})")
            elif isinstance(st, IfStmt):
                for idx, br in enumerate(st.branches):
                    kw = "if" if idx == 0 else "elif"
                    out.append(f"{pad}{kw} {self._py_expr(br.condition)}:")
                    body_l = self._py_stmts(br.body, indent + 1, fn_name)
                    out.extend(body_l or [f"{pad}    pass"])
                if st.else_body:
                    out.append(f"{pad}else:")
                    body_e = self._py_stmts(st.else_body, indent + 1, fn_name)
                    out.extend(body_e or [f"{pad}    pass"])
            elif isinstance(st, SelonStmt):
                sel = self._py_expr(st.selector)
                for idx, cb in enumerate(st.cases):
                    kw = "if" if idx == 0 else "elif"
                    conds = [f"{sel} == {self._py_expr(v)}" for v in cb.values]
                    conds += [f"({self._py_expr(r1)} <= {sel} <= {self._py_expr(r2)})" for r1, r2 in cb.ranges]
                    out.append(f"{pad}{kw} {' or '.join(conds) or 'False'}:")
                    out.extend(self._py_stmts(cb.body, indent + 1, fn_name) or [f"{pad}    pass"])
                if st.else_body:
                    out.append(f"{pad}else:")
                    out.extend(self._py_stmts(st.else_body, indent + 1, fn_name) or [f"{pad}    pass"])
            elif isinstance(st, PourStmt):
                v = self._py_expr(st.var_target)
                s_e = self._py_expr(st.start_expr)
                e_e = self._py_expr(st.end_expr)
                if st.step_expr is None:
                    out.append(f"{pad}for {v} in range({s_e}, ({e_e}) + 1):")
                else:
                    st_e = self._py_expr(st.step_expr)
                    out.append(f"{pad}_step = {st_e}")
                    out.append(f"{pad}for {v} in range({s_e}, ({e_e}) + (1 if _step > 0 else -1), _step):")
                out.extend(self._py_stmts(st.body, indent + 1, fn_name) or [f"{pad}    pass"])
            elif isinstance(st, TantQueStmt):
                out.append(f"{pad}while {self._py_expr(st.condition)}:")
                out.extend(self._py_stmts(st.body, indent + 1, fn_name) or [f"{pad}    pass"])
            elif isinstance(st, RepeterStmt):
                out.append(f"{pad}while True:")
                out.extend(self._py_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}    if {self._py_expr(st.until_condition)}:")
                out.append(f"{pad}        break")
            elif isinstance(st, IterStmt):
                out.append(f"{pad}while True:")
                out.extend(self._py_stmts(st.body, indent + 1, fn_name) or [f"{pad}    pass"])
            elif isinstance(st, SortirSiStmt):
                out.append(f"{pad}if {self._py_expr(st.condition)}:")
                out.append(f"{pad}    break")
            elif isinstance(st, CallStmt):
                args_str = ", ".join(self._py_expr(a) for a in st.args)
                sp = sub_map.get(norm_key(st.name))
                out_targets = [
                    self._py_expr(arg)
                    for arg, p in zip(st.args, sp.params)
                    if p.mode in ("OUT", "INOUT") and not p.type_spec.is_array
                ] if sp else []
                if out_targets:
                    out.append(f"{pad}{', '.join(out_targets)} = {_safe_id(st.name)}({args_str})")
                else:
                    out.append(f"{pad}{_safe_id(st.name)}({args_str})")
            elif isinstance(st, ReturnStmt):
                out.append(f"{pad}return {self._py_expr(st.value)}")
            elif isinstance(st, SqlStmt):
                out.append(f"{pad}# SQL: {st.raw_sql.splitlines()[0] if st.raw_sql else ''}")
            elif isinstance(st, (FileOpStmt, CopieStmt)):
                out.append(f"{pad}# Opération Alg_32 : {type(st).__name__}")
        return out

    def _py_input_cast(self, target: Expr, call_str: str) -> str:
        if isinstance(target, VarRef):
            ts = self.var_types.get(norm_key(target.name))
            if ts:
                bt = norm_key(ts.base_type)
                if bt == "ENTIER":
                    return f"int({call_str})"
                if bt in ("REEL", "DECIMAL"):
                    return f"float({call_str})"
                if bt == "BOOLEEN":
                    return f"({call_str}.strip().upper() in ('.VRAI.', 'VRAI', '1'))"
        elif isinstance(target, IndexAccess) and isinstance(target.target, VarRef):
            ts = self.var_types.get(norm_key(target.target.name))
            if ts:
                bt = norm_key(ts.base_type)
                if bt == "ENTIER":
                    return f"int({call_str})"
                if bt in ("REEL", "DECIMAL"):
                    return f"float({call_str})"
        return call_str

    def _py_expr(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "CHAINE":
                return repr(str(expr.value))
            if expr.lit_type == "BOOLEEN":
                return "True" if expr.value else "False"
            return str(expr.value)
        if isinstance(expr, VarRef):
            b = self.profile.resolve_builtin(expr.name)
            if b == "ALEA":
                return "random.random()"
            return _safe_id(expr.name)
        if isinstance(expr, IndexAccess):
            base = self._py_expr(expr.target)
            for idx_e in expr.indices:
                base = f"{base}[{self._py_expr(idx_e)}]"
            return base
        if isinstance(expr, FieldAccess):
            return f"{self._py_expr(expr.target)}.{_safe_id(expr.field_name)}"
        if isinstance(expr, UnaryOp):
            if expr.op == "NON":
                return f"(not {self._py_expr(expr.operand)})"
            return f"({expr.op}{self._py_expr(expr.operand)})"
        if isinstance(expr, BinaryOp):
            l_s = self._py_expr(expr.left)
            r_s = self._py_expr(expr.right)
            op_map = {
                "=": "==",
                "<>": "!=",
                "ET": "and",
                "OU": "or",
                "OUX": "^",
                "DIV": "//",
                "MOD": "%",
                "^": "**",
            }
            if expr.op == "+" and (
                (isinstance(expr.left, Literal) and expr.left.lit_type == "CHAINE")
                or (isinstance(expr.right, Literal) and expr.right.lit_type == "CHAINE")
            ):
                return f"(str({l_s}) + str({r_s}))"
            py_op = op_map.get(expr.op, expr.op)
            return f"({l_s} {py_op} {r_s})"
        if isinstance(expr, CallExpr):
            b = self.profile.resolve_builtin(expr.name)
            a = [self._py_expr(x) for x in expr.args]
            if b == "LONG":
                return f"len({a[0]})"
            if b == "GAUCHE":
                return f"{a[0]}[:{a[1]}]"
            if b == "DROITE":
                return f"{a[0]}[-({a[1]}):]"
            if b == "MILIEU":
                return f"{a[0]}[({a[1]}) - 1 : ({a[1]}) - 1 + ({a[2]})]"
            if b == "RANG":
                start = f"({a[2]}) - 1" if len(a) >= 3 else "0"
                return f"({a[0]}.find({a[1]}, {start}) + 1)"
            if b == "MAJ":
                return f"{a[0]}.upper()"
            if b == "MIN":
                return f"{a[0]}.lower()"
            if b == "ESPACE":
                return f"(' ' * {a[0]})"
            if b == "ESPACEDROITE":
                return f"{a[0]}.rstrip()"
            if b == "ESPACEGAUCHE":
                return f"{a[0]}.lstrip()"
            if b == "ABS":
                return f"abs({a[0]})"
            if b == "ENT":
                return f"math.trunc({a[0]})"
            if b == "ARRONDI":
                return f"round({a[0]})"
            if b == "RAC2":
                return f"math.sqrt({a[0]})"
            if b in ("SIN", "COS", "TAN", "EXP"):
                return f"math.{b.lower()}({a[0]})"
            if b == "ATN":
                return f"math.atan({a[0]})"
            if b == "LN":
                return f"math.log({a[0]})"
            if b == "ALEA":
                return "random.random()"
            if b == "ALEA_ENTIER":
                return f"random.randint({a[0]}, {a[1]})"
            if b == "CVCHAINE":
                return f"str({a[0]})"
            if b == "CHNOMBRE":
                return f"float({a[0]})"
            if b == "CAR":
                return f"chr({a[0]})"
            if b == "ANSI":
                return f"ord({a[0]}[0])"
            if b == "HEX":
                return f"format({a[0]}, 'X')"
            if b == "DATESYST":
                return 'datetime.datetime.now().strftime("%d/%m/%Y")'
            if b == "HEURESYST":
                return 'datetime.datetime.now().strftime("%H:%M:%S")'
            return f"{_safe_id(expr.name)}({', '.join(a)})"
        return "None"

    # ==========================================
    # 2. LANGAGE C (C11)
    # ==========================================

    def _to_c(self) -> str:
        lines: List[str] = [
            f"/* Généré par Omega Studio Code depuis l'algorithme : {self.program.name} */",
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <stdbool.h>",
            "#include <string.h>",
            "#include <math.h>",
            "",
        ]

        for td in self.program.types:
            lines.append("typedef struct {")
            for fd in td.fields:
                for fn in fd.names:
                    lines.append(f"    {self._c_var_decl(fn, fd.type_spec)};")
            lines.append(f"}} {_safe_id(td.name)};\n")

        for c in self.program.consts:
            lines.append(f"#define {_safe_id(c.name)} ({self._c_expr(c.value_expr)})")
        if self.program.consts:
            lines.append("")

        for sp in self.program.subprograms:
            ret_t = self._c_base_type(sp.return_type) if (sp.kind == "FONCTION" and sp.return_type) else "void"
            p_list = []
            for p in sp.params:
                ptr = "*" if (p.mode in ("OUT", "INOUT") and not p.type_spec.is_array and norm_key(p.type_spec.base_type) != "CHAINE") else ""
                p_list.append(self._c_var_decl(f"{ptr}{_safe_id(p.name)}", p.type_spec))
            lines.append(f"{ret_t} {_safe_id(sp.name)}({', '.join(p_list) or 'void'}) {{")
            if sp.kind == "FONCTION" and sp.return_type:
                lines.append(f"    {ret_t} {_safe_id(sp.name)}_ret = 0;")
            for vd in sp.vars:
                for vn in vd.names:
                    lines.append(f"    {self._c_var_decl(vn, vd.type_spec)};")
            ptr_names = {_safe_id(p.name) for p in sp.params if p.mode in ("OUT", "INOUT") and not p.type_spec.is_array and norm_key(p.type_spec.base_type) != "CHAINE"}
            lines.extend(self._c_stmts(sp.body, 1, sp.name if sp.kind == "FONCTION" else None, ptr_names))
            if sp.kind == "FONCTION":
                lines.append(f"    return {_safe_id(sp.name)}_ret;")
            lines.append("}\n")

        lines.append("int main(void) {")
        for vd in self.program.vars:
            for vn in vd.names:
                if norm_key(vd.type_spec.base_type) == "STRUCTURE":
                    lines.append("    struct {")
                    for fd in vd.type_spec.struct_fields:
                        for fn in fd.names:
                            lines.append(f"        {self._c_var_decl(fn, fd.type_spec)};")
                    lines.append(f"    }} {_safe_id(vn)};")
                else:
                    lines.append(f"    {self._c_var_decl(vn, vd.type_spec)};")
        lines.extend(self._c_stmts(self.program.body, 1))
        lines.append("    return 0;")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _c_base_type(self, ts: Optional[TypeSpec]) -> str:
        if ts is None:
            return "int"
        bt = norm_key(ts.base_type)
        return {
            "ENTIER": "int",
            "REEL": "double",
            "DECIMAL": "double",
            "CAR": "char",
            "BOOLEEN": "bool",
            "CHAINE": "char*",
        }.get(bt, _safe_id(ts.base_type))

    def _c_var_decl(self, name: str, ts: TypeSpec) -> str:
        bt = norm_key(ts.base_type)
        dims = "".join(f"[{max(1, hi + 1)}]" for _, hi in ts.dimensions) if ts.is_array else ""
        if bt == "CHAINE":
            sz = (ts.size or 128) + 1
            return f"char {_safe_id(name) if not name.startswith('*') else name}{dims}[{sz}]"
        c_t = self._c_base_type(ts)
        clean = _safe_id(name) if not name.startswith("*") else "*" + _safe_id(name[1:])
        return f"{c_t} {clean}{dims}"

    def _c_stmts(
        self,
        stmts: List[Stmt],
        indent: int,
        fn_name: Optional[str] = None,
        ptr_vars: Optional[Set[str]] = None,
    ) -> List[str]:
        pad = "    " * indent
        ptr_vars = ptr_vars or set()
        out: List[str] = []
        for st in stmts:
            if isinstance(st, AssignStmt):
                if fn_name and isinstance(st.target, VarRef) and norm_key(st.target.name) == norm_key(fn_name):
                    out.append(f"{pad}{_safe_id(fn_name)}_ret = {self._c_expr(st.value, ptr_vars)};")
                else:
                    out.append(f"{pad}{self._c_expr(st.target, ptr_vars)} = {self._c_expr(st.value, ptr_vars)};")
            elif isinstance(st, SaisirStmt):
                if st.prompt:
                    out.append(f'{pad}printf("%s", {self._c_expr(st.prompt, ptr_vars)});')
                for tgt in st.targets:
                    fmt, addr = self._c_scanf_spec(tgt)
                    out.append(f'{pad}scanf("{fmt}", {addr});')
            elif isinstance(st, AfficherStmt):
                parts = []
                args = []
                for it in st.items:
                    if isinstance(it, Literal) and it.lit_type == "CHAINE":
                        parts.append(str(it.value).replace("%", "%%").replace('"', '\\"'))
                    else:
                        parts.append(self._c_printf_fmt(it))
                        args.append(self._c_expr(it, ptr_vars))
                nl = "\\n" if st.newline else ""
                arg_tail = (", " + ", ".join(args)) if args else ""
                out.append(f'{pad}printf("{"".join(parts)}{nl}"{arg_tail});')
            elif isinstance(st, IfStmt):
                for idx, br in enumerate(st.branches):
                    kw = "if" if idx == 0 else "} else if"
                    out.append(f"{pad}{kw} ({self._c_expr(br.condition, ptr_vars)}) {{")
                    out.extend(self._c_stmts(br.body, indent + 1, fn_name, ptr_vars))
                if st.else_body:
                    out.append(f"{pad}}} else {{")
                    out.extend(self._c_stmts(st.else_body, indent + 1, fn_name, ptr_vars))
                out.append(f"{pad}}}")
            elif isinstance(st, PourStmt):
                v = self._c_expr(st.var_target, ptr_vars)
                s_e = self._c_expr(st.start_expr, ptr_vars)
                e_e = self._c_expr(st.end_expr, ptr_vars)
                step_e = self._c_expr(st.step_expr, ptr_vars) if st.step_expr else "1"
                cmp_op = ">=" if step_e.startswith("-") else "<="
                out.append(f"{pad}for ({v} = {s_e}; {v} {cmp_op} {e_e}; {v} += {step_e}) {{")
                out.extend(self._c_stmts(st.body, indent + 1, fn_name, ptr_vars))
                out.append(f"{pad}}}")
            elif isinstance(st, TantQueStmt):
                out.append(f"{pad}while ({self._c_expr(st.condition, ptr_vars)}) {{")
                out.extend(self._c_stmts(st.body, indent + 1, fn_name, ptr_vars))
                out.append(f"{pad}}}")
            elif isinstance(st, RepeterStmt):
                out.append(f"{pad}do {{")
                out.extend(self._c_stmts(st.body, indent + 1, fn_name, ptr_vars))
                out.append(f"{pad}}} while (!({self._c_expr(st.until_condition, ptr_vars)}));")
            elif isinstance(st, IterStmt):
                out.append(f"{pad}while (true) {{")
                out.extend(self._c_stmts(st.body, indent + 1, fn_name, ptr_vars))
                out.append(f"{pad}}}")
            elif isinstance(st, SortirSiStmt):
                out.append(f"{pad}if ({self._c_expr(st.condition, ptr_vars)}) break;")
            elif isinstance(st, SelonStmt):
                out.append(f"{pad}switch ({self._c_expr(st.selector, ptr_vars)}) {{")
                for cb in st.cases:
                    for v in cb.values:
                        out.append(f"{pad}    case {self._c_expr(v, ptr_vars)}:")
                    out.extend(self._c_stmts(cb.body, indent + 2, fn_name, ptr_vars))
                    out.append(f"{pad}        break;")
                if st.else_body:
                    out.append(f"{pad}    default:")
                    out.extend(self._c_stmts(st.else_body, indent + 2, fn_name, ptr_vars))
                    out.append(f"{pad}        break;")
                out.append(f"{pad}}}")
            elif isinstance(st, CallStmt):
                out.append(f"{pad}{_safe_id(st.name)}({', '.join(self._c_expr(a, ptr_vars) for a in st.args)});")
            elif isinstance(st, ReturnStmt):
                out.append(f"{pad}return {self._c_expr(st.value, ptr_vars)};")
        return out

    def _c_scanf_spec(self, target: Expr) -> tuple[str, str]:
        c_e = self._c_expr(target)
        if isinstance(target, VarRef):
            ts = self.var_types.get(norm_key(target.name))
            if ts:
                bt = norm_key(ts.base_type)
                if bt == "CHAINE":
                    return "%s", c_e
                if bt in ("REEL", "DECIMAL"):
                    return "%lf", f"&{c_e}"
                if bt == "CAR":
                    return " %c", f"&{c_e}"
        return "%d", f"&{c_e}"

    def _c_printf_fmt(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "REEL":
                return "%g"
            if expr.lit_type == "CHAINE":
                return "%s"
            return "%d"
        if isinstance(expr, VarRef):
            ts = self.var_types.get(norm_key(expr.name))
            if ts:
                bt = norm_key(ts.base_type)
                if bt == "CHAINE":
                    return "%s"
                if bt in ("REEL", "DECIMAL"):
                    return "%g"
                if bt == "CAR":
                    return "%c"
        return "%g" if isinstance(expr, BinaryOp) and expr.op == "/" else "%d"

    def _c_expr(self, expr: Expr, ptr_vars: Optional[Set[str]] = None) -> str:
        ptr_vars = ptr_vars or set()
        if isinstance(expr, Literal):
            if expr.lit_type == "CHAINE":
                return '"' + str(expr.value).replace('"', '\\"') + '"'
            if expr.lit_type == "BOOLEEN":
                return "true" if expr.value else "false"
            return str(expr.value)
        if isinstance(expr, VarRef):
            sid = _safe_id(expr.name)
            return f"(*{sid})" if sid in ptr_vars else sid
        if isinstance(expr, IndexAccess):
            base = self._c_expr(expr.target, ptr_vars)
            for i in expr.indices:
                base = f"{base}[{self._c_expr(i, ptr_vars)}]"
            return base
        if isinstance(expr, FieldAccess):
            return f"{self._c_expr(expr.target, ptr_vars)}.{_safe_id(expr.field_name)}"
        if isinstance(expr, UnaryOp):
            op = "!" if expr.op == "NON" else expr.op
            return f"({op}{self._c_expr(expr.operand, ptr_vars)})"
        if isinstance(expr, BinaryOp):
            l_s = self._c_expr(expr.left, ptr_vars)
            r_s = self._c_expr(expr.right, ptr_vars)
            if expr.op == "^":
                return f"pow({l_s}, {r_s})"
            op_map = {"=": "==", "<>": "!=", "ET": "&&", "OU": "||", "DIV": "/", "MOD": "%"}
            return f"({l_s} {op_map.get(expr.op, expr.op)} {r_s})"
        if isinstance(expr, CallExpr):
            b = self.profile.resolve_builtin(expr.name)
            a = [self._c_expr(x, ptr_vars) for x in expr.args]
            if b == "RAC2":
                return f"sqrt({a[0]})"
            if b == "ABS":
                return f"fabs({a[0]})"
            if b == "LONG":
                return f"(int)strlen({a[0]})"
            return f"{_safe_id(expr.name)}({', '.join(a)})"
        return "0"

    # ==========================================
    # 3. JAVASCRIPT (ES6 / Node.js)
    # ==========================================

    def _to_javascript(self) -> str:
        lines: List[str] = [
            f"// Généré par Omega Studio Code depuis l'algorithme : {self.program.name}",
            'const fs = require("fs");',
            'const _inputs = fs.existsSync(0) ? fs.readFileSync(0, "utf8").trim().split(/\\s+/) : [];',
            "let _inIdx = 0;",
            "function saisir(promptText = '') {",
            "    if (promptText) process.stdout.write(String(promptText));",
            "    return _inputs[_inIdx++] ?? '';",
            "}",
            "",
        ]

        for c in self.program.consts:
            lines.append(f"const {_safe_id(c.name)} = {self._js_expr(c.value_expr)};")
        if self.program.consts:
            lines.append("")

        for sp in self.program.subprograms:
            p_str = ", ".join(_safe_id(p.name) for p in sp.params)
            lines.append(f"function {_safe_id(sp.name)}({p_str}) {{")
            if sp.kind == "FONCTION":
                lines.append(f"    let {_safe_id(sp.name)}_ret = null;")
            for vd in sp.vars:
                for vn in vd.names:
                    lines.append(f"    let {_safe_id(vn)} = {self._js_default(vd.type_spec)};")
            lines.extend(self._js_stmts(sp.body, 1, sp.name if sp.kind == "FONCTION" else None))
            if sp.kind == "FONCTION":
                lines.append(f"    return {_safe_id(sp.name)}_ret;")
            lines.append("}\n")

        lines.append("function main() {")
        for vd in self.program.vars:
            for vn in vd.names:
                lines.append(f"    let {_safe_id(vn)} = {self._js_default(vd.type_spec)};")
        lines.extend(self._js_stmts(self.program.body, 1))
        lines.append("}\n\nmain();")
        return "\n".join(lines) + "\n"

    def _js_default(self, ts: TypeSpec) -> str:
        if ts.is_array and ts.dimensions:
            inner = "0"
            for _, hi in reversed(ts.dimensions):
                inner = f"Array.from({{ length: {max(1, hi + 1)} }}, () => ({inner}))"
            return inner
        bt = norm_key(ts.base_type)
        if bt in ("ENTIER", "REEL", "DECIMAL"):
            return "0"
        if bt in ("CHAINE", "CAR"):
            return '""'
        if bt == "BOOLEEN":
            return "false"
        return "{}"

    def _js_stmts(self, stmts: List[Stmt], indent: int, fn_name: Optional[str] = None) -> List[str]:
        pad = "    " * indent
        out: List[str] = []
        for st in stmts:
            if isinstance(st, AssignStmt):
                if fn_name and isinstance(st.target, VarRef) and norm_key(st.target.name) == norm_key(fn_name):
                    out.append(f"{pad}{_safe_id(fn_name)}_ret = {self._js_expr(st.value)};")
                else:
                    out.append(f"{pad}{self._js_expr(st.target)} = {self._js_expr(st.value)};")
            elif isinstance(st, SaisirStmt):
                p_code = self._js_expr(st.prompt) if st.prompt else "''"
                for idx, tgt in enumerate(st.targets):
                    pr = p_code if idx == 0 else "''"
                    out.append(f"{pad}{self._js_expr(tgt)} = Number(saisir({pr}));")
            elif isinstance(st, AfficherStmt):
                joined = " + ".join(f"String({self._js_expr(it)})" for it in st.items) or '""'
                if st.newline:
                    out.append(f"{pad}console.log({joined});")
                else:
                    out.append(f"{pad}process.stdout.write({joined});")
            elif isinstance(st, IfStmt):
                for idx, br in enumerate(st.branches):
                    kw = "if" if idx == 0 else "} else if"
                    out.append(f"{pad}{kw} ({self._js_expr(br.condition)}) {{")
                    out.extend(self._js_stmts(br.body, indent + 1, fn_name))
                if st.else_body:
                    out.append(f"{pad}}} else {{")
                    out.extend(self._js_stmts(st.else_body, indent + 1, fn_name))
                out.append(f"{pad}}}")
            elif isinstance(st, PourStmt):
                v = self._js_expr(st.var_target)
                s_e = self._js_expr(st.start_expr)
                e_e = self._js_expr(st.end_expr)
                step_e = self._js_expr(st.step_expr) if st.step_expr else "1"
                cmp_op = ">=" if step_e.startswith("-") else "<="
                out.append(f"{pad}for ({v} = {s_e}; {v} {cmp_op} {e_e}; {v} += {step_e}) {{")
                out.extend(self._js_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}}}")
            elif isinstance(st, TantQueStmt):
                out.append(f"{pad}while ({self._js_expr(st.condition)}) {{")
                out.extend(self._js_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}}}")
            elif isinstance(st, RepeterStmt):
                out.append(f"{pad}do {{")
                out.extend(self._js_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}}} while (!({self._js_expr(st.until_condition)}));")
            elif isinstance(st, IterStmt):
                out.append(f"{pad}while (true) {{")
                out.extend(self._js_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}}}")
            elif isinstance(st, SortirSiStmt):
                out.append(f"{pad}if ({self._js_expr(st.condition)}) break;")
            elif isinstance(st, CallStmt):
                out.append(f"{pad}{_safe_id(st.name)}({', '.join(self._js_expr(a) for a in st.args)});")
            elif isinstance(st, ReturnStmt):
                out.append(f"{pad}return {self._js_expr(st.value)};")
        return out

    def _js_expr(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "CHAINE":
                return repr(str(expr.value))
            if expr.lit_type == "BOOLEEN":
                return "true" if expr.value else "false"
            return str(expr.value)
        if isinstance(expr, VarRef):
            return _safe_id(expr.name)
        if isinstance(expr, IndexAccess):
            base = self._js_expr(expr.target)
            for i in expr.indices:
                base = f"{base}[{self._js_expr(i)}]"
            return base
        if isinstance(expr, FieldAccess):
            return f"{self._js_expr(expr.target)}.{_safe_id(expr.field_name)}"
        if isinstance(expr, UnaryOp):
            op = "!" if expr.op == "NON" else expr.op
            return f"({op}{self._js_expr(expr.operand)})"
        if isinstance(expr, BinaryOp):
            l_s = self._js_expr(expr.left)
            r_s = self._js_expr(expr.right)
            if expr.op == "DIV":
                return f"Math.trunc({l_s} / {r_s})"
            op_map = {"=": "===", "<>": "!==", "ET": "&&", "OU": "||", "MOD": "%", "^": "**"}
            return f"({l_s} {op_map.get(expr.op, expr.op)} {r_s})"
        if isinstance(expr, CallExpr):
            b = self.profile.resolve_builtin(expr.name)
            a = [self._js_expr(x) for x in expr.args]
            if b == "LONG":
                return f"{a[0]}.length"
            if b == "RAC2":
                return f"Math.sqrt({a[0]})"
            if b == "ABS":
                return f"Math.abs({a[0]})"
            if b == "ALEA":
                return "Math.random()"
            if b == "MAJ":
                return f"{a[0]}.toUpperCase()"
            if b == "MIN":
                return f"{a[0]}.toLowerCase()"
            return f"{_safe_id(expr.name)}({', '.join(a)})"
        return "null"

    # ==========================================
    # 4. PASCAL (FreePascal / Delphi)
    # ==========================================

    def _to_pascal(self) -> str:
        lines: List[str] = [f"program {_safe_id(self.program.name)};", "uses SysUtils, Math;", ""]
        if self.program.types:
            lines.append("type")
            for td in self.program.types:
                lines.append(f"  {_safe_id(td.name)} = record")
                for fd in td.fields:
                    lines.append(f"    {', '.join(_safe_id(n) for n in fd.names)}: {self._pas_type(fd.type_spec)};")
                lines.append("  end;")
            lines.append("")

        if self.program.consts:
            lines.append("const")
            for c in self.program.consts:
                lines.append(f"  {_safe_id(c.name)} = {self._pas_expr(c.value_expr)};")
            lines.append("")

        if self.program.vars:
            lines.append("var")
            for vd in self.program.vars:
                lines.append(f"  {', '.join(_safe_id(n) for n in vd.names)}: {self._pas_type(vd.type_spec)};")
            lines.append("")

        for sp in self.program.subprograms:
            p_parts = []
            for p in sp.params:
                prefix = "var " if p.mode in ("OUT", "INOUT") else ""
                p_parts.append(f"{prefix}{_safe_id(p.name)}: {self._pas_type(p.type_spec)}")
            sig_args = f"({'; '.join(p_parts)})" if p_parts else ""
            if sp.kind == "FONCTION":
                lines.append(f"function {_safe_id(sp.name)}{sig_args}: {self._pas_type(sp.return_type)};")
            else:
                lines.append(f"procedure {_safe_id(sp.name)}{sig_args};")
            if sp.vars:
                lines.append("var")
                for vd in sp.vars:
                    lines.append(f"  {', '.join(_safe_id(n) for n in vd.names)}: {self._pas_type(vd.type_spec)};")
            lines.append("begin")
            lines.extend(self._pas_stmts(sp.body, 1, sp.name if sp.kind == "FONCTION" else None))
            lines.append("end;\n")

        lines.append("begin")
        lines.extend(self._pas_stmts(self.program.body, 1))
        lines.append("end.")
        return "\n".join(lines) + "\n"

    def _pas_type(self, ts: Optional[TypeSpec]) -> str:
        if ts is None:
            return "Integer"
        if ts.is_array and ts.dimensions:
            bnds = ", ".join(f"{lo}..{hi}" for lo, hi in ts.dimensions)
            elem = TypeSpec(base_type=ts.base_type)
            return f"array[{bnds}] of {self._pas_type(elem)}"
        bt = norm_key(ts.base_type)
        return {
            "ENTIER": "Integer",
            "REEL": "Double",
            "DECIMAL": "Double",
            "CHAINE": "String",
            "CAR": "Char",
            "BOOLEEN": "Boolean",
        }.get(bt, _safe_id(ts.base_type))

    def _pas_stmts(self, stmts: List[Stmt], indent: int, fn_name: Optional[str] = None) -> List[str]:
        pad = "  " * indent
        out: List[str] = []
        for st in stmts:
            if isinstance(st, AssignStmt):
                out.append(f"{pad}{self._pas_expr(st.target)} := {self._pas_expr(st.value)};")
            elif isinstance(st, SaisirStmt):
                if st.prompt:
                    out.append(f"{pad}Write({self._pas_expr(st.prompt)});")
                out.append(f"{pad}ReadLn({', '.join(self._pas_expr(t) for t in st.targets)});")
            elif isinstance(st, AfficherStmt):
                fn = "WriteLn" if st.newline else "Write"
                out.append(f"{pad}{fn}({', '.join(self._pas_expr(i) for i in st.items)});")
            elif isinstance(st, IfStmt):
                for idx, br in enumerate(st.branches):
                    kw = "if" if idx == 0 else "else if"
                    out.append(f"{pad}{kw} {self._pas_expr(br.condition)} then")
                    out.append(f"{pad}begin")
                    out.extend(self._pas_stmts(br.body, indent + 1, fn_name))
                    out.append(f"{pad}end")
                if st.else_body:
                    out.append(f"{pad}else")
                    out.append(f"{pad}begin")
                    out.extend(self._pas_stmts(st.else_body, indent + 1, fn_name))
                    out.append(f"{pad}end;")
                else:
                    out[-1] += ";"
            elif isinstance(st, PourStmt):
                v = self._pas_expr(st.var_target)
                out.append(f"{pad}for {v} := {self._pas_expr(st.start_expr)} to {self._pas_expr(st.end_expr)} do")
                out.append(f"{pad}begin")
                out.extend(self._pas_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}end;")
            elif isinstance(st, TantQueStmt):
                out.append(f"{pad}while {self._pas_expr(st.condition)} do")
                out.append(f"{pad}begin")
                out.extend(self._pas_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}end;")
            elif isinstance(st, RepeterStmt):
                out.append(f"{pad}repeat")
                out.extend(self._pas_stmts(st.body, indent + 1, fn_name))
                out.append(f"{pad}until {self._pas_expr(st.until_condition)};")
            elif isinstance(st, CallStmt):
                out.append(f"{pad}{_safe_id(st.name)}({', '.join(self._pas_expr(a) for a in st.args)});")
            elif isinstance(st, ReturnStmt):
                target_n = _safe_id(fn_name) if fn_name else "Result"
                out.append(f"{pad}{target_n} := {self._pas_expr(st.value)};")
        return out

    def _pas_expr(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "CHAINE":
                return "'" + str(expr.value).replace("'", "''") + "'"
            if expr.lit_type == "BOOLEEN":
                return "True" if expr.value else "False"
            return str(expr.value)
        if isinstance(expr, VarRef):
            return _safe_id(expr.name)
        if isinstance(expr, IndexAccess):
            idxs = ", ".join(self._pas_expr(i) for i in expr.indices)
            return f"{self._pas_expr(expr.target)}[{idxs}]"
        if isinstance(expr, FieldAccess):
            return f"{self._pas_expr(expr.target)}.{_safe_id(expr.field_name)}"
        if isinstance(expr, UnaryOp):
            op = "not " if expr.op == "NON" else expr.op
            return f"({op}{self._pas_expr(expr.operand)})"
        if isinstance(expr, BinaryOp):
            op_map = {"ET": "and", "OU": "or", "OUX": "xor", "DIV": "div", "MOD": "mod"}
            return f"({self._pas_expr(expr.left)} {op_map.get(expr.op, expr.op)} {self._pas_expr(expr.right)})"
        if isinstance(expr, CallExpr):
            return f"{_safe_id(expr.name)}({', '.join(self._pas_expr(a) for a in expr.args)})"
        return "0"
