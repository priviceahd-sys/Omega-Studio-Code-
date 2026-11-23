"""
Arbre Syntaxique Abstrait (AST) complet du langage Alg_32 / Omega Studio Code.
Chaque nœud conserve son numéro de ligne source (`line`) pour le débogueur pas-à-pas,
la vérification statique et la synchronisation en temps réel de l'organigramme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class ASTNode:
    line: int = 1


# =========================
# Types & Déclarations
# =========================


@dataclass
class TypeSpec(ASTNode):
    base_type: str = "ENTIER"  # ENTIER, REEL, DECIMAL, CHAINE, CAR, BOOLEEN, ou nom de TYPE utilisateur / STRUCTURE
    size: Optional[int] = None  # ex: chaine(20)
    decimals: Optional[int] = None  # ex: decimal(8, 2)
    is_array: bool = False
    dimensions: List[Tuple[int, int]] = field(default_factory=list)  # [(min_idx, max_idx), ...]
    struct_fields: List["VarDecl"] = field(default_factory=list)  # si STRUCTURE inline


@dataclass
class ConstDecl(ASTNode):
    name: str = ""
    value_expr: "Expr" = None  # type: ignore[assignment]


@dataclass
class VarDecl(ASTNode):
    names: List[str] = field(default_factory=list)
    type_spec: TypeSpec = field(default_factory=lambda: TypeSpec(base_type="ENTIER"))
    is_global: bool = False


@dataclass
class TypeDefDecl(ASTNode):
    name: str = ""
    fields: List[VarDecl] = field(default_factory=list)


@dataclass
class FileDecl(ASTNode):
    name: str = ""
    organisation: str = "SEQUENTIELLE"  # SEQUENTIELLE, RELATIVE, INDEXEE, BINAIRE
    acces: str = "SEQUENTIEL"  # SEQUENTIEL, DIRECT, DYNAMIQUE
    primary_key: Optional[str] = None
    secondary_keys: List[str] = field(default_factory=list)
    record_name: Optional[str] = None
    record_fields: List[VarDecl] = field(default_factory=list)


@dataclass
class ParamDecl(ASTNode):
    name: str = ""
    type_spec: TypeSpec = field(default_factory=lambda: TypeSpec(base_type="ENTIER"))
    mode: str = "IN"  # IN (e/donnée/valeur), OUT (s/résultat), INOUT (es/donnée modifiée/adresse)


@dataclass
class SubprogramDecl(ASTNode):
    kind: str = "PROCEDURE"  # PROCEDURE ou FONCTION
    name: str = ""
    params: List[ParamDecl] = field(default_factory=list)
    return_type: Optional[TypeSpec] = None
    consts: List[ConstDecl] = field(default_factory=list)
    vars: List[VarDecl] = field(default_factory=list)
    body: List["Stmt"] = field(default_factory=list)
    end_line: int = 1


@dataclass
class Program(ASTNode):
    name: str = "Sans_Nom"
    has_explicit_algo_header: bool = True
    types: List[TypeDefDecl] = field(default_factory=list)
    consts: List[ConstDecl] = field(default_factory=list)
    files: List[FileDecl] = field(default_factory=list)
    vars: List[VarDecl] = field(default_factory=list)
    subprograms: List[SubprogramDecl] = field(default_factory=list)
    body: List["Stmt"] = field(default_factory=list)
    end_line: int = 1


# =========================
# Expressions
# =========================


@dataclass
class Expr(ASTNode):
    pass


@dataclass
class Literal(Expr):
    value: Any = None
    lit_type: str = "ENTIER"  # ENTIER, REEL, CHAINE, BOOLEEN


@dataclass
class VarRef(Expr):
    name: str = ""


@dataclass
class IndexAccess(Expr):
    target: Expr = field(default_factory=Expr)
    indices: List[Expr] = field(default_factory=list)


@dataclass
class FieldAccess(Expr):
    target: Expr = field(default_factory=Expr)
    field_name: str = ""


@dataclass
class UnaryOp(Expr):
    op: str = "-"  # +, -, NON
    operand: Expr = field(default_factory=Expr)


@dataclass
class BinaryOp(Expr):
    op: str = "+"
    left: Expr = field(default_factory=Expr)
    right: Expr = field(default_factory=Expr)


@dataclass
class CallExpr(Expr):
    name: str = ""
    args: List[Expr] = field(default_factory=list)


# =========================
# Instructions (Statements)
# =========================


@dataclass
class Stmt(ASTNode):
    pass


@dataclass
class AssignStmt(Stmt):
    target: Expr = field(default_factory=Expr)
    value: Expr = field(default_factory=Expr)


@dataclass
class SaisirStmt(Stmt):
    prompt: Optional[Expr] = None
    targets: List[Expr] = field(default_factory=list)


@dataclass
class AfficherStmt(Stmt):
    items: List[Expr] = field(default_factory=list)
    newline: bool = True
    to_printer: bool = False  # True => IMPRIMER


@dataclass
class ScreenCmdStmt(Stmt):
    cmd: str = "EFFACE_ECRAN"  # EFFACE_ECRAN, A_LA_LIGNE, CURSEUR, COULEUR
    args: List[Expr] = field(default_factory=list)


@dataclass
class IfBranch:
    condition: Expr
    body: List[Stmt]
    line: int


@dataclass
class IfStmt(Stmt):
    branches: List[IfBranch] = field(default_factory=list)  # SI + SINON SI éventuels
    else_body: List[Stmt] = field(default_factory=list)
    end_line: int = 1


@dataclass
class CaseBranch:
    values: List[Expr] = field(default_factory=list)  # expressions ou comparaisons
    ranges: List[Tuple[Expr, Expr]] = field(default_factory=list)
    body: List[Stmt] = field(default_factory=list)
    line: int = 1


@dataclass
class SelonStmt(Stmt):
    selector: Expr = field(default_factory=Expr)
    cases: List[CaseBranch] = field(default_factory=list)
    else_body: List[Stmt] = field(default_factory=list)
    end_line: int = 1


@dataclass
class PourStmt(Stmt):
    var_target: Expr = field(default_factory=Expr)
    start_expr: Expr = field(default_factory=Expr)
    end_expr: Expr = field(default_factory=Expr)
    step_expr: Optional[Expr] = None
    body: List[Stmt] = field(default_factory=list)
    end_line: int = 1


@dataclass
class TantQueStmt(Stmt):
    condition: Expr = field(default_factory=Expr)
    body: List[Stmt] = field(default_factory=list)
    end_line: int = 1


@dataclass
class RepeterStmt(Stmt):
    body: List[Stmt] = field(default_factory=list)
    until_condition: Expr = field(default_factory=Expr)
    until_line: int = 1


@dataclass
class IterStmt(Stmt):
    body: List[Stmt] = field(default_factory=list)
    end_line: int = 1


@dataclass
class SortirSiStmt(Stmt):
    condition: Expr = field(default_factory=Expr)


@dataclass
class CallStmt(Stmt):
    name: str = ""
    args: List[Expr] = field(default_factory=list)


@dataclass
class ReturnStmt(Stmt):
    value: Expr = field(default_factory=Expr)


@dataclass
class CopieStmt(Stmt):
    module_path: str = ""


@dataclass
class FileOpStmt(Stmt):
    op: str = "OUVRIR"  # OUVRIR, FERMER, LIRE, ECRIRE, REECRIRE, SUPPRIMER, POSITIONNER
    target_names: List[str] = field(default_factory=list)
    mode: str = "LECTURE/ECRITURE"
    sequential_next: bool = False  # LIRE enr SUIVANT
    key_expr: Optional[Expr] = None  # AVEC CLEF = expr
    position_expr: Optional[Expr] = None  # binaire
    var_target: Optional[Expr] = None  # binaire


@dataclass
class SqlStmt(Stmt):
    raw_sql: str = ""
    end_line: int = 1
