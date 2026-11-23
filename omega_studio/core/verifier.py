"""
Vérificateur statique & Formateur automatique pour Alg_32 / Omega Studio Code.
Fournit des diagnostics précis (erreurs, avertissements, suggestions orthographiques)
et un formateur d'indentation / mise en majuscules des mots-clefs.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

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
    UnaryOp,
    VarDecl,
    VarRef,
)
from .keywords import BUILTIN_FUNCTIONS, DATA_TYPES, KeywordProfile, norm_key
from .lexer import LexError, tokenize
from .parser import ParseError, parse_source


@dataclass
class Diagnostic:
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    line: int
    col: int = 1


@dataclass
class VerificationReport:
    ok: bool
    diagnostics: List[Diagnostic]
    program: Optional[Program] = None
    stats: Dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.stats is None:
            self.stats = {}


BUILTIN_ARITY: Dict[str, Tuple[int, int]] = {
    "LONG": (1, 1),
    "GAUCHE": (2, 2),
    "DROITE": (2, 2),
    "MILIEU": (3, 3),
    "RANG": (2, 3),
    "SUPPR": (3, 3),
    "ESPACE": (1, 1),
    "REPETECAR": (2, 2),
    "MAJ": (1, 1),
    "MIN": (1, 1),
    "ESPACEDROITE": (1, 1),
    "ESPACEGAUCHE": (1, 1),
    "ANSI": (1, 1),
    "CAR": (1, 1),
    "CVCHAINE": (1, 1),
    "CHNOMBRE": (1, 1),
    "HEX": (1, 1),
    "ABS": (1, 1),
    "ENT": (1, 1),
    "DECIMALE": (1, 1),
    "ARRONDI": (1, 1),
    "RAC2": (1, 1),
    "SIN": (1, 1),
    "COS": (1, 1),
    "TAN": (1, 1),
    "ATN": (1, 1),
    "EXP": (1, 1),
    "LN": (1, 1),
    "ALEA": (0, 0),
    "ALEA_ENTIER": (2, 2),
    "DATESYST": (0, 0),
    "HEURESYST": (0, 0),
    "COLONNE": (0, 0),
    "LIGNE": (0, 0),
    "TAB": (1, 1),
    "UNCAR": (0, 0),
    "UNETOUCHE": (0, 0),
    "FF": (0, 1),
    "EXISTE": (1, 1),
    "ERREUR": (1, 1),
    "ERREUR_SQL": (0, 0),
}


def verify_source(
    source: str,
    profile: Optional[KeywordProfile] = None,
    strict_alg32: bool = False,
) -> VerificationReport:
    profile = profile or KeywordProfile()
    diags: List[Diagnostic] = []

    if not source.strip():
        diags.append(Diagnostic("ERROR", "L'éditeur est vide : écrivez un algorithme (ALGO ... DEBUT ... FIN).", 1, 1))
        return VerificationReport(ok=False, diagnostics=diags)

    try:
        prog = parse_source(source, profile=profile)
    except LexError as e:
        diags.append(Diagnostic("ERROR", f"Erreur lexicale : {e.message}", e.line, e.col))
        return VerificationReport(ok=False, diagnostics=diags)
    except ParseError as e:
        diags.append(Diagnostic("ERROR", f"Erreur de syntaxe : {e.message}", e.line, e.col))
        return VerificationReport(ok=False, diagnostics=diags)

    if not prog.has_explicit_algo_header:
        diags.append(
            Diagnostic(
                "WARNING",
                "En-tête 'ALGO nom_algo' absent en première ligne (recommandé en norme Alg_32).",
                prog.line,
            )
        )

    if strict_alg32:
        for idx, raw_line in enumerate(source.splitlines(), start=1):
            if len(raw_line) > 73:
                diags.append(
                    Diagnostic(
                        "WARNING",
                        f"Mode strict Alg_32 : ligne de {len(raw_line)} caractères (> 73 max historique).",
                        idx,
                    )
                )

    # Construction des tables des symboles
    user_types: Set[str] = {norm_key(td.name) for td in prog.types}
    global_consts: Dict[str, int] = {}
    global_vars: Dict[str, VarDecl] = {}
    all_main_vars: Dict[str, VarDecl] = {}
    files_and_records: Set[str] = set()

    for fdecl in prog.files:
        files_and_records.add(norm_key(fdecl.name))
        if fdecl.record_name:
            files_and_records.add(norm_key(fdecl.record_name))
        for rf in fdecl.record_fields:
            for rname in rf.names:
                all_main_vars[norm_key(rname)] = rf
                global_vars[norm_key(rname)] = rf

    for c in prog.consts:
        ck = norm_key(c.name)
        if ck in global_consts:
            diags.append(Diagnostic("ERROR", f"Constante '{c.name}' déclarée en double.", c.line))
        global_consts[ck] = c.line

    for vd in prog.vars:
        bt = norm_key(vd.type_spec.base_type)
        if bt != "STRUCTURE" and profile.resolve_type(bt) is None and bt not in user_types:
            diags.append(
                Diagnostic("ERROR", f"Type de données inconnu : '{vd.type_spec.base_type}'.", vd.line)
            )
        for vname in vd.names:
            vk = norm_key(vname)
            if vk in all_main_vars or vk in global_consts:
                diags.append(Diagnostic("ERROR", f"Identificateur '{vname}' déjà déclaré.", vd.line))
            all_main_vars[vk] = vd
            if vd.is_global:
                global_vars[vk] = vd

    subprogs: Dict[str, SubprogramDecl] = {}
    for sp in prog.subprograms:
        spk = norm_key(sp.name)
        if spk in subprogs:
            diags.append(
                Diagnostic("ERROR", f"Sous-programme '{sp.name}' déclaré plusieurs fois.", sp.line)
            )
        subprogs[spk] = sp

    def suggest_name(unknown: str, scope: Set[str]) -> str:
        matches = difflib.get_close_matches(norm_key(unknown), list(scope), n=1, cutoff=0.72)
        if matches:
            return f" (vouliez-vous écrire '{matches[0]}' ?)"
        return ""

    def check_expr(
        expr: Expr,
        scope_vars: Set[str],
        scope_consts: Set[str],
        current_fn: Optional[str] = None,
    ) -> None:
        if isinstance(expr, Literal):
            return
        if isinstance(expr, VarRef):
            nk = norm_key(expr.name)
            if (
                nk not in scope_vars
                and nk not in scope_consts
                and nk not in files_and_records
                and nk != (norm_key(current_fn) if current_fn else "")
            ):
                # Vérifie s'il s'agit d'une fonction sans parenthèses (ex: ALEA, DATESYST)
                if profile.resolve_builtin(expr.name) in ("ALEA", "DATESYST", "HEURESYST", "COLONNE", "LIGNE", "UNCAR", "UNETOUCHE", "ERREUR_SQL"):
                    return
                hint = suggest_name(expr.name, scope_vars | scope_consts)
                diags.append(
                    Diagnostic(
                        "ERROR",
                        f"Identificateur '{expr.name}' non déclaré{hint}.",
                        expr.line,
                    )
                )
            return
        if isinstance(expr, IndexAccess):
            check_expr(expr.target, scope_vars, scope_consts, current_fn)
            for idx_e in expr.indices:
                check_expr(idx_e, scope_vars, scope_consts, current_fn)
            return
        if isinstance(expr, FieldAccess):
            check_expr(expr.target, scope_vars, scope_consts, current_fn)
            return
        if isinstance(expr, UnaryOp):
            check_expr(expr.operand, scope_vars, scope_consts, current_fn)
            return
        if isinstance(expr, BinaryOp):
            check_expr(expr.left, scope_vars, scope_consts, current_fn)
            check_expr(expr.right, scope_vars, scope_consts, current_fn)
            return
        if isinstance(expr, CallExpr):
            ck = norm_key(expr.name)
            b_canon = profile.resolve_builtin(expr.name)
            if ck in scope_vars and b_canon is None and ck not in subprogs:
                # Tableau accédé avec parenthèses par habitude VB : avertissement pédagogique
                diags.append(
                    Diagnostic(
                        "ERROR",
                        f"'{expr.name}' est une variable : utilisez des crochets {expr.name}[...] pour indicer un tableau.",
                        expr.line,
                    )
                )
            elif b_canon is not None:
                min_a, max_a = BUILTIN_ARITY.get(b_canon, (0, 99))
                if not (min_a <= len(expr.args) <= max_a):
                    diags.append(
                        Diagnostic(
                            "ERROR",
                            f"La fonction '{expr.name}' attend {min_a if min_a == max_a else f'{min_a} à {max_a}'} argument(s), {len(expr.args)} fourni(s).",
                            expr.line,
                        )
                    )
            elif ck in subprogs:
                sp = subprogs[ck]
                if sp.kind != "FONCTION":
                    diags.append(
                        Diagnostic(
                            "ERROR",
                            f"'{sp.name}' est une PROCEDURE et ne retourne pas de valeur dans une expression.",
                            expr.line,
                        )
                    )
                if len(expr.args) != len(sp.params):
                    diags.append(
                        Diagnostic(
                            "ERROR",
                            f"La fonction '{sp.name}' attend {len(sp.params)} paramètre(s), {len(expr.args)} fourni(s).",
                            expr.line,
                        )
                    )
            else:
                hint = suggest_name(expr.name, set( subprogs.keys() ) | set(BUILTIN_FUNCTIONS.keys()))
                diags.append(
                    Diagnostic("ERROR", f"Fonction '{expr.name}' inconnue{hint}.", expr.line)
                )

            for arg in expr.args:
                check_expr(arg, scope_vars, scope_consts, current_fn)

    def check_stmts(
        stmts: List[Stmt],
        scope_vars: Set[str],
        scope_consts: Set[str],
        in_iter: bool = False,
        current_fn: Optional[str] = None,
    ) -> bool:
        has_return = False
        for st in stmts:
            if isinstance(st, AssignStmt):
                if isinstance(st.target, VarRef):
                    tk = norm_key(st.target.name)
                    if tk in scope_consts:
                        diags.append(
                            Diagnostic(
                                "ERROR",
                                f"Impossible de modifier la constante '{st.target.name}'.",
                                st.line,
                            )
                        )
                    if current_fn and tk == norm_key(current_fn):
                        has_return = True
                check_expr(st.target, scope_vars, scope_consts, current_fn)
                check_expr(st.value, scope_vars, scope_consts, current_fn)
            elif isinstance(st, SaisirStmt):
                if st.prompt:
                    check_expr(st.prompt, scope_vars, scope_consts, current_fn)
                for tgt in st.targets:
                    if isinstance(tgt, VarRef) and norm_key(tgt.name) in scope_consts:
                        diags.append(
                            Diagnostic("ERROR", f"Impossible de SAISIR dans la constante '{tgt.name}'.", st.line)
                        )
                    check_expr(tgt, scope_vars, scope_consts, current_fn)
            elif isinstance(st, AfficherStmt):
                for it in st.items:
                    check_expr(it, scope_vars, scope_consts, current_fn)
            elif isinstance(st, ScreenCmdStmt):
                for a in st.args:
                    check_expr(a, scope_vars, scope_consts, current_fn)
            elif isinstance(st, IfStmt):
                for br in st.branches:
                    check_expr(br.condition, scope_vars, scope_consts, current_fn)
                    if check_stmts(br.body, scope_vars, scope_consts, in_iter, current_fn):
                        has_return = True
                if check_stmts(st.else_body, scope_vars, scope_consts, in_iter, current_fn):
                    has_return = True
            elif isinstance(st, SelonStmt):
                check_expr(st.selector, scope_vars, scope_consts, current_fn)
                for cb in st.cases:
                    for v in cb.values:
                        check_expr(v, scope_vars, scope_consts, current_fn)
                    for r1, r2 in cb.ranges:
                        check_expr(r1, scope_vars, scope_consts, current_fn)
                        check_expr(r2, scope_vars, scope_consts, current_fn)
                    if check_stmts(cb.body, scope_vars, scope_consts, in_iter, current_fn):
                        has_return = True
                if check_stmts(st.else_body, scope_vars, scope_consts, in_iter, current_fn):
                    has_return = True
            elif isinstance(st, PourStmt):
                check_expr(st.var_target, scope_vars, scope_consts, current_fn)
                check_expr(st.start_expr, scope_vars, scope_consts, current_fn)
                check_expr(st.end_expr, scope_vars, scope_consts, current_fn)
                if st.step_expr:
                    check_expr(st.step_expr, scope_vars, scope_consts, current_fn)
                if check_stmts(st.body, scope_vars, scope_consts, in_iter, current_fn):
                    has_return = True
            elif isinstance(st, TantQueStmt):
                check_expr(st.condition, scope_vars, scope_consts, current_fn)
                if check_stmts(st.body, scope_vars, scope_consts, in_iter, current_fn):
                    has_return = True
            elif isinstance(st, RepeterStmt):
                if check_stmts(st.body, scope_vars, scope_consts, in_iter, current_fn):
                    has_return = True
                check_expr(st.until_condition, scope_vars, scope_consts, current_fn)
            elif isinstance(st, IterStmt):
                if check_stmts(st.body, scope_vars, scope_consts, True, current_fn):
                    has_return = True
            elif isinstance(st, SortirSiStmt):
                if not in_iter:
                    diags.append(
                        Diagnostic("WARNING", "SORTIRSI utilisé hors d'une boucle ITER ... FINITER.", st.line)
                    )
                check_expr(st.condition, scope_vars, scope_consts, current_fn)
            elif isinstance(st, CallStmt):
                ck = norm_key(st.name)
                if ck not in subprogs:
                    hint = suggest_name(st.name, set(subprogs.keys()))
                    diags.append(
                        Diagnostic("ERROR", f"Procédure '{st.name}' non déclarée{hint}.", st.line)
                    )
                else:
                    sp = subprogs[ck]
                    if len(st.args) != len(sp.params):
                        diags.append(
                            Diagnostic(
                                "ERROR",
                                f"Appel à '{sp.name}' : {len(sp.params)} paramètre(s) attendu(s), {len(st.args)} fourni(s).",
                                st.line,
                            )
                        )
                    for arg, pdecl in zip(st.args, sp.params):
                        if pdecl.mode in ("OUT", "INOUT") and not isinstance(
                            arg, (VarRef, IndexAccess, FieldAccess)
                        ):
                            diags.append(
                                Diagnostic(
                                    "ERROR",
                                    f"Le paramètre '{pdecl.name}' ({pdecl.mode}) de '{sp.name}' exige une variable modifiable.",
                                    st.line,
                                )
                            )
                for arg in st.args:
                    check_expr(arg, scope_vars, scope_consts, current_fn)
            elif isinstance(st, ReturnStmt):
                has_return = True
                if current_fn is None:
                    diags.append(
                        Diagnostic(
                            "ERROR",
                            "VALRET / DELIVRE ne peut être utilisé qu'à l'intérieur d'une FONCTION.",
                            st.line,
                        )
                    )
                check_expr(st.value, scope_vars, scope_consts, current_fn)
            elif isinstance(st, FileOpStmt):
                for tname in st.target_names:
                    if norm_key(tname) not in files_and_records:
                        diags.append(
                            Diagnostic(
                                "ERROR",
                                f"Fichier ou enregistrement '{tname}' non déclaré dans la section FICHIER.",
                                st.line,
                            )
                        )
                if st.key_expr:
                    check_expr(st.key_expr, scope_vars, scope_consts, current_fn)
                if st.position_expr:
                    check_expr(st.position_expr, scope_vars, scope_consts, current_fn)
                if st.var_target:
                    check_expr(st.var_target, scope_vars, scope_consts, current_fn)
            elif isinstance(st, (CopieStmt, SqlStmt)):
                pass
        return has_return

    # Vérifie le programme principal
    main_scope_vars = set(all_main_vars.keys())
    main_scope_consts = set(global_consts.keys())
    for c in prog.consts:
        check_expr(c.value_expr, main_scope_vars, main_scope_consts)
    check_stmts(prog.body, main_scope_vars, main_scope_consts)

    # Vérifie chaque procédure / fonction
    for sp in prog.subprograms:
        sp_vars = set(global_vars.keys())
        sp_consts = set(global_consts.keys())
        for p in sp.params:
            sp_vars.add(norm_key(p.name))
        for c in sp.consts:
            sp_consts.add(norm_key(c.name))
            check_expr(c.value_expr, sp_vars, sp_consts)
        for vd in sp.vars:
            if vd.is_global:
                diags.append(
                    Diagnostic(
                        "ERROR",
                        "Les variables GLOBALES doivent être déclarées dans l'algorithme principal uniquement.",
                        vd.line,
                    )
                )
            for vname in vd.names:
                sp_vars.add(norm_key(vname))

        fn_name = sp.name if sp.kind == "FONCTION" else None
        returned = check_stmts(sp.body, sp_vars, sp_consts, False, fn_name)
        if sp.kind == "FONCTION" and not returned:
            diags.append(
                Diagnostic(
                    "WARNING",
                    f"La fonction '{sp.name}' ne contient aucune instruction de retour (VALRET := ..., DELIVRE(...) ou {sp.name} := ...).",
                    sp.line,
                )
            )

    has_err = any(d.severity == "ERROR" for d in diags)
    stats = {
        "lines": len(source.splitlines()),
        "variables": sum(len(v.names) for v in prog.vars),
        "constants": len(prog.consts),
        "subprograms": len(prog.subprograms),
        "errors": sum(1 for d in diags if d.severity == "ERROR"),
        "warnings": sum(1 for d in diags if d.severity == "WARNING"),
    }
    return VerificationReport(ok=not has_err, diagnostics=diags, program=prog, stats=stats)


def format_algorithm_source(
    source: str,
    uppercase_keywords: bool = True,
    indent_size: int = 4,
    profile: Optional[KeywordProfile] = None,
) -> str:
    """
    Reformate proprement l'indentation d'un algorithme Alg_32 et met éventuellement
    les mots-clefs et fonctions standards en MAJUSCULES (sans altérer les chaînes ni commentaires).
    """
    profile = profile or KeywordProfile()
    single_kw, multi_kw = profile.build_lookup()
    builtin_norms = {
        norm_key(alias): alias.upper()
        for _, (aliases, _, _) in BUILTIN_FUNCTIONS.items()
        for alias in aliases
    }
    type_norms = {norm_key(a): a.lower() for aliases in DATA_TYPES.values() for a in aliases}

    # Mots qui diminuent l'indentation avant la ligne courante
    dedent_before = {
        "DEBUT",
        "FIN",
        "FIN_PROC",
        "FIN_FONC",
        "SINON",
        "SINON_SI",
        "FIN_SI",
        "CAS",
        "AUTRES",
        "FIN_SELON",
        "FIN_POUR",
        "FIN_TQ",
        "JUSQUA",
        "FIN_ITER",
        "FIN_TYPE",
        "FIN_STRUCTURE",
        "FIN_ENREGISTREMENT",
        "VAR",
        "CONST",
        "TYPE",
        "FICHIER",
    }
    indent_after = {
        "DEBUT",
        "ALORS",
        "SINON",
        "SINON_SI",
        "POUR",
        "TANT_QUE",
        "REPETER",
        "ITER",
        "SELON",
        "CAS",
        "AUTRES",
        "TYPE",
        "STRUCTURE",
        "ENREGISTREMENT",
        "VAR",
        "CONST",
        "FICHIER",
    }

    formatted_lines: List[str] = []
    level = 0
    in_case_body = False
    in_decl_section = False

    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            formatted_lines.append("")
            continue

        # Détecte le premier jeton logique de la ligne
        first_canon: Optional[str] = None
        last_canon: Optional[str] = None
        try:
            line_toks = [t for t in tokenize(stripped, profile=profile) if t.type not in ("NEWLINE", "EOF")]
            if line_toks:
                first_canon = line_toks[0].type
                last_canon = line_toks[-1].type
        except LexError:
            line_toks = []

        # Gestion fine des sections déclaratives VAR / CONST / FICHIER
        if first_canon in ("VAR", "CONST", "FICHIER", "DEBUT", "PROCEDURE", "FONCTION", "ALGO"):
            if in_decl_section:
                level = max(0, level - 1)
                in_decl_section = False

        if first_canon in ("CAS", "AUTRES", "FIN_SELON") and in_case_body:
            level = max(0, level - 1)
            in_case_body = False

        if first_canon in dedent_before and first_canon not in ("VAR", "CONST", "FICHIER", "DEBUT"):
            level = max(0, level - 1)

        out_line = _uppercase_line_keywords(stripped, single_kw, multi_kw, builtin_norms, type_norms) if uppercase_keywords else stripped
        formatted_lines.append((" " * (level * indent_size)) + out_line)

        # Calcul de l'indentation de la ligne suivante
        if first_canon in ("VAR", "CONST", "FICHIER") and len(line_toks) == 1:
            level += 1
            in_decl_section = True
        elif first_canon in ("SI", "SINON_SI"):
            # Indente si FINSI n'est pas sur la même ligne
            if not any(t.type == "FIN_SI" for t in line_toks):
                level += 1
        elif first_canon in ("CAS", "AUTRES"):
            # Si le corps du CAS n'est pas déjà sur la même ligne après ':'
            colon_idx = next((idx for idx, t in enumerate(line_toks) if t.type == "COLON"), -1)
            if colon_idx == -1 or colon_idx == len(line_toks) - 1:
                level += 1
                in_case_body = True
        elif first_canon in indent_after or last_canon == "ALORS":
            level += 1

    return "\n".join(formatted_lines) + "\n"


def _uppercase_line_keywords(
    line: str,
    single_kw: Dict[str, str],
    multi_kw: List[Tuple[List[str], str]],
    builtin_norms: Dict[str, str],
    type_norms: Dict[str, str],
) -> str:
    """Met en majuscules les mots-clefs hors chaînes et hors commentaires."""
    out: List[str] = []
    i = 0
    n = len(line)
    multi_first_words = {seq[0] for seq, _ in multi_kw}

    while i < n:
        ch = line[i]
        # Commentaires : on copie tel quel le reste de la ligne
        if ch in ("'", "’") or (ch == "/" and i + 1 < n and line[i + 1] in ("/", "*")):
            out.append(line[i:])
            break
        # Chaînes : on copie tel quel
        if ch == '"':
            j = i + 1
            while j < n:
                if line[j] == '"' and (j + 1 >= n or line[j + 1] != '"'):
                    j += 1
                    break
                if line[j] == '"' and j + 1 < n and line[j + 1] == '"':
                    j += 2
                    continue
                j += 1
            out.append(line[i:j])
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            nw = norm_key(word)
            # Cas JUSQU'A / C'EST
            if nw in ("JUSQU", "C") and j < n and line[j] in ("'", "’"):
                k = j + 1
                while k < n and (line[k].isalnum() or line[k] == "_"):
                    k += 1
                comb = norm_key(line[i:k])
                if comb in ("JUSQU'A", "C'EST"):
                    out.append(line[i:k].upper())
                    i = k
                    continue

            # Cas multi-mots
            if nw in multi_first_words:
                matched_multi = False
                for seq, _ in multi_kw:
                    if seq[0] != nw:
                        continue
                    cur_p = j
                    ok = True
                    for expected in seq[1:]:
                        while cur_p < n and line[cur_p] in (" ", "\t"):
                            cur_p += 1
                        w_s = cur_p
                        while cur_p < n and (line[cur_p].isalnum() or line[cur_p] == "_"):
                            cur_p += 1
                        if norm_key(line[w_s:cur_p]) != expected:
                            ok = False
                            break
                    if ok:
                        out.append(" ".join(line[i:cur_p].split()).upper())
                        i = cur_p
                        matched_multi = True
                        break
                if matched_multi:
                    continue

            if nw in single_kw or nw in ("VRAI", "FAUX"):
                out.append(word.upper())
            elif nw in builtin_norms and j < n and line[j] == "(":
                out.append(word.upper())
            elif nw in type_norms:
                out.append(word.lower())
            else:
                out.append(word)
            i = j
            continue

        out.append(ch)
        i += 1

    return "".join(out)
