"""
Générateur d'organigramme algorithmique normalisé (norme AFNOR / ISO)
à partir de l'AST d'un algorithme Alg_32 / Omega Studio Code.
Calcule automatiquement une mise en page hiérarchique propre (x, y, largeur, hauteur)
et les flèches orientées (VRAI, FAUX, retours de boucle).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ast_nodes import (
    AfficherStmt,
    AssignStmt,
    CallStmt,
    FileOpStmt,
    IfStmt,
    IterStmt,
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
)
from .transpiler import expr_to_display


@dataclass
class FlowNode:
    id: int
    shape: str  # "TERMINAL", "PROCESS", "IO", "DECISION", "SUBCALL", "JUNCTION"
    label: str
    line: int
    x: float = 0.0
    y: float = 0.0
    width: float = 210.0
    height: float = 54.0


@dataclass
class FlowEdge:
    src_id: int
    dst_id: int
    label: str = ""  # "", "VRAI", "FAUX", "SUIVANT"
    kind: str = "NORMAL"  # "NORMAL", "TRUE", "FALSE", "LOOP_BACK"
    waypoints: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class FlowGraph:
    title: str
    nodes: List[FlowNode] = field(default_factory=list)
    edges: List[FlowEdge] = field(default_factory=list)


def _short(text: str, max_len: int = 38) -> str:
    s = " ".join(text.split())
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


class FlowchartBuilder:
    """Construit un graphe d'organigramme lisible et équilibré."""

    V_GAP = 42.0
    H_GAP = 64.0
    NODE_W = 216.0
    NODE_H = 52.0
    DECISION_W = 236.0
    DECISION_H = 74.0

    def __init__(self) -> None:
        self._next_id = 1
        self.nodes: List[FlowNode] = []
        self.edges: List[FlowEdge] = []

    def _new_node(
        self,
        shape: str,
        label: str,
        line: int,
        x: float = 0.0,
        y: float = 0.0,
        w: Optional[float] = None,
        h: Optional[float] = None,
    ) -> FlowNode:
        if w is None:
            w = self.DECISION_W if shape == "DECISION" else (20.0 if shape == "JUNCTION" else self.NODE_W)
        if h is None:
            h = self.DECISION_H if shape == "DECISION" else (20.0 if shape == "JUNCTION" else self.NODE_H)
        node = FlowNode(
            id=self._next_id,
            shape=shape,
            label=label,
            line=line,
            x=x,
            y=y,
            width=w,
            height=h,
        )
        self._next_id += 1
        self.nodes.append(node)
        return node

    def build_for_program(self, program: Program, subprogram_name: Optional[str] = None) -> FlowGraph:
        self.nodes = []
        self.edges = []
        self._next_id = 1

        target_stmts: List[Stmt] = program.body
        title = f"ALGO {program.name}"
        start_line = program.line
        end_line = program.end_line

        if subprogram_name:
            sp: Optional[SubprogramDecl] = next(
                (s for s in program.subprograms if s.name == subprogram_name), None
            )
            if sp:
                target_stmts = sp.body
                title = f"{sp.kind} {sp.name}"
                start_line = sp.line
                end_line = sp.end_line

        start_node = self._new_node("TERMINAL", f"DÉBUT\n{_short(title, 28)}", start_line, x=0.0, y=0.0)
        cur_y = start_node.height + self.V_GAP

        if target_stmts:
            first_id, last_id, next_y = self._layout_seq(target_stmts, center_x=0.0, start_y=cur_y)
            self.edges.append(FlowEdge(start_node.id, first_id))
            cur_y = next_y
            prev_id = last_id
        else:
            prev_id = start_node.id

        end_node = self._new_node("TERMINAL", "FIN", end_line, x=0.0, y=cur_y)
        self.edges.append(FlowEdge(prev_id, end_node.id))

        return FlowGraph(title=title, nodes=self.nodes, edges=self.edges)

    def _measure_seq_width(self, stmts: List[Stmt]) -> float:
        w = self.NODE_W
        for st in stmts:
            w = max(w, self._measure_stmt_width(st))
        return w

    def _measure_stmt_width(self, st: Stmt) -> float:
        if isinstance(st, IfStmt):
            total_branches = len(st.branches) + (1 if st.else_body else 1)
            if total_branches <= 2:
                left_w = self._measure_seq_width(st.branches[0].body) if st.branches else self.NODE_W
                right_w = self._measure_seq_width(st.else_body) if st.else_body else (self.NODE_W * 0.6)
                return max(self.DECISION_W, left_w + self.H_GAP + right_w)
            widths = [self._measure_seq_width(b.body) for b in st.branches]
            if st.else_body:
                widths.append(self._measure_seq_width(st.else_body))
            return sum(widths) + self.H_GAP * max(0, len(widths) - 1)
        if isinstance(st, SelonStmt):
            cols = [self._measure_seq_width(cb.body) for cb in st.cases]
            if st.else_body:
                cols.append(self._measure_seq_width(st.else_body))
            if not cols:
                return self.DECISION_W
            return max(self.DECISION_W, sum(cols) + self.H_GAP * (len(cols) - 1))
        if isinstance(st, (PourStmt, TantQueStmt, RepeterStmt, IterStmt)):
            return max(self.DECISION_W, self._measure_seq_width(st.body) + 90.0)
        return self.NODE_W

    def _layout_seq(self, stmts: List[Stmt], center_x: float, start_y: float) -> Tuple[int, int, float]:
        first_id = -1
        prev_id = -1
        cur_y = start_y

        for st in stmts:
            entry_id, exit_id, cur_y = self._layout_stmt(st, center_x, cur_y)
            if first_id == -1:
                first_id = entry_id
            if prev_id != -1:
                self.edges.append(FlowEdge(prev_id, entry_id))
            prev_id = exit_id

        return first_id, prev_id, cur_y

    def _layout_stmt(self, st: Stmt, cx: float, y: float) -> Tuple[int, int, float]:
        if isinstance(st, AssignStmt):
            lbl = _short(f"{expr_to_display(st.target)} ← {expr_to_display(st.value)}")
            n = self._new_node("PROCESS", lbl, st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, SaisirStmt):
            tgts = ", ".join(expr_to_display(t) for t in st.targets)
            n = self._new_node("IO", _short(f"SAISIR {tgts}"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, AfficherStmt):
            prefix = "IMPRIMER" if st.to_printer else "AFFICHER"
            vals = ", ".join(expr_to_display(i) for i in st.items)
            n = self._new_node("IO", _short(f"{prefix} {vals}"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, ScreenCmdStmt):
            args = ", ".join(expr_to_display(a) for a in st.args)
            txt = f"{st.cmd}({args})" if args else st.cmd
            n = self._new_node("IO", _short(txt), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, CallStmt):
            args = ", ".join(expr_to_display(a) for a in st.args)
            n = self._new_node("SUBCALL", _short(f"{st.name}({args})"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, ReturnStmt):
            n = self._new_node("TERMINAL", _short(f"RETOUR {expr_to_display(st.value)}"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, SqlStmt):
            first_l = st.raw_sql.splitlines()[0] if st.raw_sql else "EXEC SQL"
            n = self._new_node("PROCESS", _short(f"SQL: {first_l}"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, FileOpStmt):
            n = self._new_node("IO", _short(f"{st.op} {', '.join(st.target_names)}"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        if isinstance(st, IfStmt):
            return self._layout_if(st, cx, y)

        if isinstance(st, SelonStmt):
            return self._layout_selon(st, cx, y)

        if isinstance(st, (TantQueStmt, PourStmt)):
            return self._layout_pre_loop(st, cx, y)

        if isinstance(st, RepeterStmt):
            return self._layout_repeter(st, cx, y)

        if isinstance(st, IterStmt):
            return self._layout_iter(st, cx, y)

        if isinstance(st, SortirSiStmt):
            n = self._new_node("DECISION", _short(f"SORTIRSI {expr_to_display(st.condition)}"), st.line, x=cx, y=y)
            return n.id, n.id, y + n.height + self.V_GAP

        n = self._new_node("PROCESS", type(st).__name__, st.line, x=cx, y=y)
        return n.id, n.id, y + n.height + self.V_GAP

    def _layout_if(self, st: IfStmt, cx: float, y: float) -> Tuple[int, int, float]:
        # Si simple SI ... ALORS ... [SINON] ... FINSI
        first_br = st.branches[0]
        dec = self._new_node("DECISION", _short(f"{expr_to_display(first_br.condition)} ?"), first_br.line, x=cx, y=y)

        # S'il y a des SINON SI, on les imbrique récursivement dans la branche FAUX
        effective_else: List[Stmt] = list(st.else_body)
        if len(st.branches) > 1:
            nested_if = IfStmt(
                line=st.branches[1].line,
                branches=st.branches[1:],
                else_body=st.else_body,
                end_line=st.end_line,
            )
            effective_else = [nested_if]

        left_w = self._measure_seq_width(first_br.body) if first_br.body else self.NODE_W
        right_w = self._measure_seq_width(effective_else) if effective_else else (self.NODE_W * 0.55)
        span = (left_w + self.H_GAP + right_w) / 2.0
        left_cx = cx - span + left_w / 2.0
        right_cx = cx + span - right_w / 2.0

        branch_y = y + dec.height + self.V_GAP
        max_bottom = branch_y

        if first_br.body:
            l_in, l_out, l_bot = self._layout_seq(first_br.body, left_cx, branch_y)
            self.edges.append(
                FlowEdge(
                    dec.id,
                    l_in,
                    label="VRAI",
                    kind="TRUE",
                    waypoints=[(left_cx, y + dec.height / 2.0)],
                )
            )
            max_bottom = max(max_bottom, l_bot)
        else:
            l_out = -1

        if effective_else:
            r_in, r_out, r_bot = self._layout_seq(effective_else, right_cx, branch_y)
            self.edges.append(
                FlowEdge(
                    dec.id,
                    r_in,
                    label="FAUX",
                    kind="FALSE",
                    waypoints=[(right_cx, y + dec.height / 2.0)],
                )
            )
            max_bottom = max(max_bottom, r_bot)
        else:
            r_out = -1

        join = self._new_node("JUNCTION", "", st.end_line, x=cx, y=max_bottom)
        join_cy = max_bottom + join.height / 2.0

        if l_out != -1:
            self.edges.append(FlowEdge(l_out, join.id, waypoints=[(left_cx, join_cy)]))
        else:
            self.edges.append(
                FlowEdge(
                    dec.id,
                    join.id,
                    label="VRAI",
                    kind="TRUE",
                    waypoints=[(left_cx, y + dec.height / 2.0), (left_cx, join_cy)],
                )
            )

        if r_out != -1:
            self.edges.append(FlowEdge(r_out, join.id, waypoints=[(right_cx, join_cy)]))
        else:
            self.edges.append(
                FlowEdge(
                    dec.id,
                    join.id,
                    label="FAUX",
                    kind="FALSE",
                    waypoints=[(right_cx, y + dec.height / 2.0), (right_cx, join_cy)],
                )
            )

        return dec.id, join.id, max_bottom + join.height + self.V_GAP

    def _layout_selon(self, st: SelonStmt, cx: float, y: float) -> Tuple[int, int, float]:
        dec = self._new_node(
            "DECISION",
            _short(f"SELON {expr_to_display(st.selector)}"),
            st.line,
            x=cx,
            y=y,
        )
        branches: List[Tuple[str, List[Stmt]]] = []
        for cb in st.cases:
            lbls = [expr_to_display(v) for v in cb.values] + [
                f"{expr_to_display(a)}..{expr_to_display(b)}" for a, b in cb.ranges
            ]
            branches.append((", ".join(lbls), cb.body))
        if st.else_body:
            branches.append(("SINON", st.else_body))

        if not branches:
            return dec.id, dec.id, y + dec.height + self.V_GAP

        widths = [self._measure_seq_width(b_stmts) for _, b_stmts in branches]
        total_w = sum(widths) + self.H_GAP * (len(widths) - 1)
        cur_left = cx - total_w / 2.0
        branch_y = y + dec.height + self.V_GAP + 10.0
        max_bot = branch_y
        outs: List[Tuple[int, float]] = []

        for (case_lbl, b_stmts), bw in zip(branches, widths):
            bcx = cur_left + bw / 2.0
            cur_left += bw + self.H_GAP
            if b_stmts:
                b_in, b_out, b_bot = self._layout_seq(b_stmts, bcx, branch_y)
                self.edges.append(
                    FlowEdge(dec.id, b_in, label=_short(case_lbl, 14), waypoints=[(bcx, y + dec.height / 2.0)])
                )
                outs.append((b_out, bcx))
                max_bot = max(max_bot, b_bot)

        join = self._new_node("JUNCTION", "", st.end_line, x=cx, y=max_bot)
        for out_id, bcx in outs:
            self.edges.append(FlowEdge(out_id, join.id, waypoints=[(bcx, max_bot + join.height / 2.0)]))
        return dec.id, join.id, max_bot + join.height + self.V_GAP

    def _layout_pre_loop(self, st: TantQueStmt | PourStmt, cx: float, y: float) -> Tuple[int, int, float]:
        if isinstance(st, TantQueStmt):
            cond_lbl = _short(f"TQ {expr_to_display(st.condition)} ?")
            body = st.body
            end_line = st.end_line
        else:
            step_part = f" PAS {expr_to_display(st.step_expr)}" if st.step_expr else ""
            cond_lbl = _short(
                f"POUR {expr_to_display(st.var_target)} ← {expr_to_display(st.start_expr)} À {expr_to_display(st.end_expr)}{step_part}"
            )
            body = st.body
            end_line = st.end_line

        dec = self._new_node("DECISION", cond_lbl, st.line, x=cx, y=y)
        body_y = y + dec.height + self.V_GAP
        body_w = self._measure_seq_width(body) if body else self.NODE_W

        if body:
            b_in, b_out, b_bot = self._layout_seq(body, cx, body_y)
            self.edges.append(FlowEdge(dec.id, b_in, label="VRAI", kind="TRUE"))
            # Flèche de retour de boucle sur le côté gauche
            left_rail = cx - (body_w / 2.0) - 38.0
            self.edges.append(
                FlowEdge(
                    b_out,
                    dec.id,
                    kind="LOOP_BACK",
                    waypoints=[
                        (cx, b_bot - self.V_GAP / 2.0),
                        (left_rail, b_bot - self.V_GAP / 2.0),
                        (left_rail, y + dec.height / 2.0),
                    ],
                )
            )
        else:
            b_bot = body_y

        join = self._new_node("JUNCTION", "", end_line, x=cx, y=b_bot + 8.0)
        right_rail = cx + (body_w / 2.0) + 42.0
        self.edges.append(
            FlowEdge(
                dec.id,
                join.id,
                label="FAUX",
                kind="FALSE",
                waypoints=[
                    (right_rail, y + dec.height / 2.0),
                    (right_rail, b_bot + 8.0 + join.height / 2.0),
                ],
            )
        )
        return dec.id, join.id, b_bot + 8.0 + join.height + self.V_GAP

    def _layout_repeter(self, st: RepeterStmt, cx: float, y: float) -> Tuple[int, int, float]:
        top_j = self._new_node("JUNCTION", "", st.line, x=cx, y=y)
        cur_y = y + top_j.height + self.V_GAP * 0.7
        body_w = self._measure_seq_width(st.body) if st.body else self.NODE_W

        if st.body:
            b_in, b_out, cur_y = self._layout_seq(st.body, cx, cur_y)
            self.edges.append(FlowEdge(top_j.id, b_in))
            prev = b_out
        else:
            prev = top_j.id

        dec = self._new_node(
            "DECISION",
            _short(f"JUSQU'À {expr_to_display(st.until_condition)} ?"),
            st.until_line,
            x=cx,
            y=cur_y,
        )
        self.edges.append(FlowEdge(prev, dec.id))
        left_rail = cx - (body_w / 2.0) - 38.0
        self.edges.append(
            FlowEdge(
                dec.id,
                top_j.id,
                label="FAUX",
                kind="LOOP_BACK",
                waypoints=[
                    (left_rail, cur_y + dec.height / 2.0),
                    (left_rail, y + top_j.height / 2.0),
                ],
            )
        )
        exit_j = self._new_node("JUNCTION", "", st.until_line, x=cx, y=cur_y + dec.height + self.V_GAP)
        self.edges.append(FlowEdge(dec.id, exit_j.id, label="VRAI", kind="TRUE"))
        return top_j.id, exit_j.id, exit_j.y + exit_j.height + self.V_GAP

    def _layout_iter(self, st: IterStmt, cx: float, y: float) -> Tuple[int, int, float]:
        top_j = self._new_node("JUNCTION", "", st.line, x=cx, y=y)
        cur_y = y + top_j.height + self.V_GAP * 0.7
        body_w = self._measure_seq_width(st.body) if st.body else self.NODE_W
        if st.body:
            b_in, b_out, cur_y = self._layout_seq(st.body, cx, cur_y)
            self.edges.append(FlowEdge(top_j.id, b_in))
            left_rail = cx - (body_w / 2.0) - 38.0
            self.edges.append(
                FlowEdge(
                    b_out,
                    top_j.id,
                    kind="LOOP_BACK",
                    waypoints=[(left_rail, cur_y - self.V_GAP / 2.0), (left_rail, y + top_j.height / 2.0)],
                )
            )
        exit_j = self._new_node("JUNCTION", "", st.end_line, x=cx, y=cur_y)
        self.edges.append(FlowEdge(top_j.id, exit_j.id, label="SORTIE", kind="FALSE"))
        return top_j.id, exit_j.id, cur_y + exit_j.height + self.V_GAP
