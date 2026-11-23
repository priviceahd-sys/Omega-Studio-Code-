"""
Analyseur syntaxique récursif (Parser) complet pour le langage Alg_32 / Omega Studio Code.
Transforme une liste de jetons en un Arbre Syntaxique Abstrait (AST) riche.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from .ast_nodes import (
    AfficherStmt,
    AssignStmt,
    BinaryOp,
    CallExpr,
    CallStmt,
    CaseBranch,
    ConstDecl,
    CopieStmt,
    Expr,
    FieldAccess,
    FileDecl,
    FileOpStmt,
    IfBranch,
    IfStmt,
    IndexAccess,
    IterStmt,
    Literal,
    ParamDecl,
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
from .keywords import KeywordProfile, norm_key
from .lexer import LexError, Token, tokenize


class ParseError(Exception):
    def __init__(self, message: str, line: int, col: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col


class Parser:
    def __init__(self, tokens: List[Token], profile: Optional[KeywordProfile] = None) -> None:
        self.tokens = tokens
        self.pos = 0
        self.profile = profile or KeywordProfile()
        self.declared_files_and_records: Set[str] = set()

    def cur(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        idx = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[idx]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def skip_newlines(self) -> None:
        while self.cur().type in ("NEWLINE", "SEMI"):
            self.advance()

    def match(self, *types: str) -> Optional[Token]:
        if self.cur().type in types:
            return self.advance()
        return None

    def expect(self, *types: str, msg: str = "") -> Token:
        tok = self.cur()
        if tok.type in types:
            return self.advance()
        expected = msg or " ou ".join(types)
        raise ParseError(f"Attendu {expected}, mais trouvé {tok.value or tok.type!r}", tok.line, tok.col)

    CONTEXTUAL_IDENT_TOKENS = {
        "IDENT",
        "CLE",
        "EN",
        "A",
        "DE",
        "PAS",
        "VALRET",
        "ACCES",
        "ORGANISATION",
        "PRIMAIRE",
        "SECONDAIRE",
        "PARAM_IN",
        "PARAM_OUT",
        "PARAM_INOUT",
    }

    def _expect_name_token(self, msg: str = "un identificateur") -> Token:
        """Accepte un identificateur (et tolère certains mots contextuels utilisés comme noms de variables, ex: val, resultat, adresse, cle)."""
        tok = self.cur()
        if tok.type in self.CONTEXTUAL_IDENT_TOKENS:
            return self.advance()
        raise ParseError(f"Attendu {msg}, mais trouvé {tok.value or tok.type!r}", tok.line, tok.col)

    # ==========================================
    # Programme principal & Déclarations
    # ==========================================

    def parse_program(self) -> Program:
        self.skip_newlines()
        start_line = self.cur().line
        has_header = False
        prog_name = "Algorithme"

        if self.cur().type == "ALGO":
            has_header = True
            algo_tok = self.advance()
            start_line = algo_tok.line
            # Le nom d'algo peut comporter tirets/apostrophes ou mots sur la même ligne
            name_parts: List[str] = []
            while self.cur().type not in ("NEWLINE", "EOF", "SEMI"):
                name_parts.append(self.advance().value)
            prog_name = "_".join(name_parts) if name_parts else "Sans_Nom"

        prog = Program(
            line=start_line,
            name=prog_name,
            has_explicit_algo_header=has_header,
        )

        self.skip_newlines()

        # Section déclarative avant DEBUT (types, const, fichiers, var, procédures/fonctions amont)
        while self.cur().type not in ("DEBUT", "EOF"):
            t = self.cur().type
            if t == "TYPE":
                prog.types.append(self.parse_typedef())
            elif t == "CONST":
                prog.consts.extend(self.parse_const_section())
            elif t == "FICHIER":
                fdecl = self.parse_file_decl()
                prog.files.append(fdecl)
            elif t == "VAR":
                prog.vars.extend(self.parse_var_section())
            elif t in ("PROCEDURE", "FONCTION"):
                prog.subprograms.append(self.parse_subprogram())
            elif t == "COPIE":
                cp = self.parse_copie_stmt()
                prog.body.append(cp)
            else:
                break
            self.skip_newlines()

        # Bloc principal DEBUT ... FIN
        if self.cur().type == "DEBUT":
            self.advance()
            self.skip_newlines()
            prog.body.extend(self.parse_stmt_list({"FIN", "EOF"}))
            end_tok = self.expect("FIN", msg="FIN (fin de l'algorithme principal)")
            prog.end_line = end_tok.line
        elif prog.subprograms and self.cur().type == "EOF":
            prog.end_line = self.cur().line
        else:
            tok = self.cur()
            raise ParseError(
                f"Mot-clef DEBUT attendu pour démarrer le corps de l'algorithme (trouvé {tok.value or tok.type!r})",
                tok.line,
                tok.col,
            )

        self.skip_newlines()

        # Procédures et fonctions déclarées après FIN (style Alg_32 classique)
        while self.cur().type != "EOF":
            if self.cur().type in ("PROCEDURE", "FONCTION"):
                prog.subprograms.append(self.parse_subprogram())
                self.skip_newlines()
            else:
                tok = self.cur()
                raise ParseError(
                    f"Instruction ou texte inattendu après FIN : {tok.value!r} (seules PROCEDURE et FONCTION sont attendues après FIN)",
                    tok.line,
                    tok.col,
                )

        return prog

    def parse_typedef(self) -> TypeDefDecl:
        tok = self.expect("TYPE")
        name_tok = self._expect_name_token("le nom du TYPE")
        self.skip_newlines()
        fields: List[VarDecl] = []
        while self.cur().type not in ("FIN_TYPE", "EOF"):
            fields.append(self.parse_single_var_decl())
            self.skip_newlines()
        self.expect("FIN_TYPE", msg="FIN TYPE")
        return TypeDefDecl(line=tok.line, name=name_tok.value, fields=fields)

    def parse_const_section(self) -> List[ConstDecl]:
        self.expect("CONST")
        self.skip_newlines()
        consts: List[ConstDecl] = []
        stop_tokens = {
            "VAR",
            "TYPE",
            "FICHIER",
            "DEBUT",
            "PROCEDURE",
            "FONCTION",
            "CONST",
            "EOF",
        }
        while self.cur().type not in stop_tokens:
            line_no = self.cur().line
            name_tok = self._expect_name_token("un nom de constante")
            if self.cur().type == "COLON":
                # Support optionnel `CONST PI : réel = 3.14`
                self.advance()
                self.parse_type_spec()
            self.expect("EQ", "ASSIGN", msg="'=' ou ':=' pour initialiser la constante")
            val = self.parse_expr()
            consts.append(ConstDecl(line=line_no, name=name_tok.value, value_expr=val))
            self.skip_newlines()
        return consts

    def parse_file_decl(self) -> FileDecl:
        tok = self.expect("FICHIER")
        fname = self._expect_name_token("le nom du fichier").value
        self.declared_files_and_records.add(norm_key(fname))
        org = "SEQUENTIELLE"
        acces = "SEQUENTIEL"
        pkey: Optional[str] = None
        skeys: List[str] = []
        rec_name: Optional[str] = None
        rec_fields: List[VarDecl] = []

        # Syntaxe : FICHIER nom {EN|(} ORGANISATION {séquentielle|relative|indexée|binaire} ...
        has_paren = False
        self.skip_newlines()
        if self.match("EN"):
            pass
        elif self.match("LPAREN"):
            has_paren = True

        self.skip_newlines()
        if self.match("ORGANISATION"):
            org_tok = self._expect_name_token("le mode d'organisation")
            org_norm = norm_key(org_tok.value)
            if "BIN" in org_norm:
                org = "BINAIRE"
            elif "REL" in org_norm:
                org = "RELATIVE"
            elif "IND" in org_norm:
                org = "INDEXEE"
            else:
                org = "SEQUENTIELLE"
            # ex: séquentielle indexée / longueur fixe / variable
            while self.cur().type == "IDENT" and norm_key(self.cur().value) in (
                "INDEXEE",
                "FIXE",
                "VARIABLE",
                "LONGUEUR",
            ):
                extra = norm_key(self.advance().value)
                if extra == "INDEXEE":
                    org = "INDEXEE"

        self.skip_newlines()
        while self.cur().type in ("ACCES", "CLE", "RPAREN"):
            if self.match("RPAREN"):
                has_paren = False
                break
            if self.match("ACCES"):
                acc_tok = self._expect_name_token("le mode d'accès")
                acc_val = norm_key(acc_tok.value)
                if self.cur().type == "SLASH":
                    self.advance()
                    acc_val += "/" + norm_key(self._expect_name_token().value)
                if "DIR" in acc_val and "SEQ" in acc_val:
                    acces = "DYNAMIQUE"
                elif "DYN" in acc_val:
                    acces = "DYNAMIQUE"
                elif "DIR" in acc_val:
                    acces = "DIRECT"
                else:
                    acces = "SEQUENTIEL"
            elif self.match("CLE"):
                is_sec = False
                if self.match("PRIMAIRE"):
                    is_sec = False
                elif self.match("SECONDAIRE"):
                    is_sec = True
                self.match("EQ", "COLON")
                kname = self._expect_name_token("le nom de la clef").value
                if is_sec or pkey is not None:
                    skeys.append(kname)
                else:
                    pkey = kname
            self.skip_newlines()

        if has_paren:
            self.match("RPAREN")
        self.skip_newlines()

        if self.match("ENREGISTREMENT"):
            if self.cur().type not in ("NEWLINE", "EOF"):
                rec_name = self._expect_name_token("le nom d'enregistrement").value
                self.declared_files_and_records.add(norm_key(rec_name))
            self.skip_newlines()
            while self.cur().type not in ("FIN_ENREGISTREMENT", "EOF"):
                rec_fields.append(self.parse_single_var_decl())
                self.skip_newlines()
            self.expect("FIN_ENREGISTREMENT", msg="FINENREGISTREMENT")

        return FileDecl(
            line=tok.line,
            name=fname,
            organisation=org,
            acces=acces,
            primary_key=pkey,
            secondary_keys=skeys,
            record_name=rec_name,
            record_fields=rec_fields,
        )

    def parse_var_section(self) -> List[VarDecl]:
        self.expect("VAR")
        self.skip_newlines()
        decls: List[VarDecl] = []
        stop_tokens = {
            "DEBUT",
            "CONST",
            "TYPE",
            "FICHIER",
            "PROCEDURE",
            "FONCTION",
            "VAR",
            "EOF",
        }
        while self.cur().type not in stop_tokens:
            decls.append(self.parse_single_var_decl())
            self.skip_newlines()
        return decls

    def parse_single_var_decl(self) -> VarDecl:
        line_no = self.cur().line
        is_global = bool(self.match("GLOBALE"))

        # Cas STRUCTURE nom_struct ... FINSTRUCTURE
        if self.match("STRUCTURE"):
            sname = self._expect_name_token("le nom de la structure").value
            self.skip_newlines()
            sfields: List[VarDecl] = []
            while self.cur().type not in ("FIN_STRUCTURE", "EOF"):
                sfields.append(self.parse_single_var_decl())
                self.skip_newlines()
            self.expect("FIN_STRUCTURE", msg="FINSTRUCTURE")
            ts = TypeSpec(line=line_no, base_type="STRUCTURE", struct_fields=sfields)
            return VarDecl(line=line_no, names=[sname], type_spec=ts, is_global=is_global)

        # Cas : a, b, c : entiers   OU   t1[5,6], t2[10] : tableaux de réels
        names: List[str] = []
        inline_dims_map: List[Optional[List[Tuple[int, int]]]] = []

        while True:
            ntok = self._expect_name_token("un nom de variable")
            names.append(ntok.value)
            if self.cur().type == "LBRACKET":
                inline_dims_map.append(self.parse_array_dimensions())
            else:
                inline_dims_map.append(None)
            if not self.match("COMMA"):
                break

        self.expect("COLON", msg="':' avant le type de la variable")
        ts = self.parse_type_spec()

        # Si les dimensions ont été écrites après le nom de variable (Format 1 d'Alg_32 : t[10] : tableau d'entiers)
        first_dims = next((d for d in inline_dims_map if d is not None), None)
        if first_dims is not None and not ts.dimensions:
            ts.is_array = True
            ts.dimensions = first_dims

        return VarDecl(line=line_no, names=names, type_spec=ts, is_global=is_global)

    def parse_array_dimensions(self) -> List[Tuple[int, int]]:
        self.expect("LBRACKET")
        dims: List[Tuple[int, int]] = []
        if self.match("RBRACKET"):
            # ex: paramètre de procédure t[] : tableau d'entiers
            return [(1, 0)]
        while True:
            lo_val = self._parse_const_int_bound()
            if self.match("COLON", "DOTDOT"):
                hi_val = self._parse_const_int_bound()
                dims.append((lo_val, hi_val))
            else:
                # Par défaut en algorithmique française Alg_32 : [N] => 1..N (et l'interpréteur tolère 0..N)
                dims.append((1, lo_val))
            if not self.match("COMMA"):
                break
        self.expect("RBRACKET")
        return dims

    def _parse_const_int_bound(self) -> int:
        sign = 1
        if self.match("MINUS"):
            sign = -1
        elif self.match("PLUS"):
            sign = 1
        tok = self.expect("INT", msg="une borne entière de tableau")
        return sign * int(tok.value)

    def parse_type_spec(self) -> TypeSpec:
        line_no = self.cur().line
        is_arr = False
        dims: List[Tuple[int, int]] = []

        if self.match("TABLEAU"):
            is_arr = True
            if self.cur().type == "LBRACKET":
                dims = self.parse_array_dimensions()
            self.match("DE")

        tok = self._expect_name_token("un type de données (entier, réel, chaîne, booléen, car...)")
        canon = self.profile.resolve_type(tok.value)
        base = canon if canon else tok.value
        size: Optional[int] = None
        decimals: Optional[int] = None

        if self.match("LPAREN"):
            sz_tok = self.expect("INT", msg="la taille entière du type")
            size = int(sz_tok.value)
            if self.match("COMMA"):
                dec_tok = self.expect("INT", msg="le nombre de décimales")
                decimals = int(dec_tok.value)
            self.expect("RPAREN")

        return TypeSpec(
            line=line_no,
            base_type=base,
            size=size,
            decimals=decimals,
            is_array=is_arr,
            dimensions=dims,
        )

    def parse_subprogram(self) -> SubprogramDecl:
        kind_tok = self.advance()  # PROCEDURE ou FONCTION
        kind = "FONCTION" if kind_tok.type == "FONCTION" else "PROCEDURE"
        name_tok = self._expect_name_token(f"le nom de la {kind.lower()}")
        params: List[ParamDecl] = []

        if self.match("LPAREN"):
            if not self.match("RPAREN"):
                params = self.parse_param_list()
                self.expect("RPAREN")

        ret_type: Optional[TypeSpec] = None
        if kind == "FONCTION":
            self.expect("COLON", msg="':' suivi du type de retour de la fonction")
            ret_type = self.parse_type_spec()

        self.skip_newlines()
        consts: List[ConstDecl] = []
        local_vars: List[VarDecl] = []
        while self.cur().type in ("CONST", "VAR"):
            if self.cur().type == "CONST":
                consts.extend(self.parse_const_section())
            elif self.cur().type == "VAR":
                local_vars.extend(self.parse_var_section())
            self.skip_newlines()

        self.expect("DEBUT", msg=f"DEBUT de la {kind.lower()} {name_tok.value}")
        self.skip_newlines()
        end_set = {"FIN", "FIN_PROC", "FIN_FONC", "EOF"}
        body = self.parse_stmt_list(end_set)
        end_tok = self.expect("FIN", "FIN_PROC", "FIN_FONC", msg=f"FIN de la {kind.lower()} {name_tok.value}")

        return SubprogramDecl(
            line=kind_tok.line,
            kind=kind,
            name=name_tok.value,
            params=params,
            return_type=ret_type,
            consts=consts,
            vars=local_vars,
            body=body,
            end_line=end_tok.line,
        )

    def parse_param_list(self) -> List[ParamDecl]:
        params: List[ParamDecl] = []
        current_mode = "INOUT"

        while self.cur().type not in ("RPAREN", "EOF"):
            line_no = self.cur().line
            # Modes : donnée / résultat / donnée modifiée / valeur / adresse / e / s / es
            if self.cur().type in ("PARAM_IN", "PARAM_OUT", "PARAM_INOUT"):
                nxt1 = self.peek(1).type
                nxt3 = self.peek(3).type
                is_mode_prefix = False
                if nxt1 not in ("COLON", "COMMA", "LBRACKET"):
                    is_mode_prefix = True
                elif nxt1 == "COLON" and nxt3 in ("COLON", "COMMA", "LBRACKET"):
                    is_mode_prefix = True
                if is_mode_prefix:
                    m_tok = self.advance().type
                    self.match("COLON")
                    current_mode = {
                        "PARAM_IN": "IN",
                        "PARAM_OUT": "OUT",
                        "PARAM_INOUT": "INOUT",
                    }[m_tok]
            elif self.cur().type == "IDENT" and norm_key(self.cur().value) in ("E", "S", "ES"):
                # Vérifie que ce n'est pas le nom du paramètre lui-même suivi de ':' ou ',' ou '['
                nxt_type = self.peek().type
                if nxt_type not in ("COLON", "COMMA", "LBRACKET"):
                    m_str = norm_key(self.advance().value)
                    self.match("COLON")
                    current_mode = {"E": "IN", "S": "OUT", "ES": "INOUT"}[m_str]

            group_names: List[Tuple[str, bool]] = []
            while True:
                p_tok = self._expect_name_token("un nom de paramètre")
                has_br = False
                if self.cur().type == "LBRACKET":
                    self.parse_array_dimensions()
                    has_br = True
                group_names.append((p_tok.value, has_br))
                if not self.match("COMMA"):
                    break

            self.expect("COLON", msg="':' avant le type du paramètre")
            ts = self.parse_type_spec()
            for pname, has_br in group_names:
                pts = TypeSpec(
                    line=ts.line,
                    base_type=ts.base_type,
                    size=ts.size,
                    decimals=ts.decimals,
                    is_array=ts.is_array or has_br,
                    dimensions=list(ts.dimensions),
                )
                eff_mode = "INOUT" if pts.is_array and current_mode == "IN" else current_mode
                params.append(ParamDecl(line=line_no, name=pname, type_spec=pts, mode=eff_mode))

            if self.match("SEMI"):
                current_mode = "INOUT"
                continue
            elif self.match("COMMA"):
                continue
            else:
                break

        return params

    # ==========================================
    # Instructions (Statements)
    # ==========================================

    def parse_stmt_list(self, stop_tokens: Set[str]) -> List[Stmt]:
        stmts: List[Stmt] = []
        self.skip_newlines()
        while self.cur().type not in stop_tokens and self.cur().type != "EOF":
            # Cas particulier : dans SELON, on s'arrête sur CAS ou AUTRES
            if "CAS" in stop_tokens and self.cur().type in ("CAS", "AUTRES"):
                break
            stmt = self.parse_stmt()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_newlines()
        return stmts

    def parse_stmt(self) -> Optional[Stmt]:
        tok = self.cur()
        t = tok.type

        if t == "SAISIR":
            return self.parse_saisir()
        if t in ("AFFICHER", "IMPRIMER"):
            return self.parse_afficher(to_printer=(t == "IMPRIMER"))
        if t in ("EFFACE_ECRAN", "A_LA_LIGNE"):
            self.advance()
            return ScreenCmdStmt(line=tok.line, cmd=t, args=[])
        if t in ("CURSEUR", "COULEUR"):
            return self.parse_screen_cmd()
        if t == "SI":
            return self.parse_if()
        if t == "SELON":
            return self.parse_selon()
        if t == "POUR":
            return self.parse_pour()
        if t == "TANT_QUE":
            return self.parse_tant_que()
        if t == "REPETER":
            return self.parse_repeter()
        if t == "ITER":
            return self.parse_iter()
        if t == "SORTIRSI":
            self.advance()
            cond = self.parse_expr()
            return SortirSiStmt(line=tok.line, condition=cond)
        if t == "TRAITER":
            self.advance()
            return self.parse_proc_call_stmt()
        if t == "VALRET":
            return self.parse_return_stmt()
        if t == "COPIE":
            return self.parse_copie_stmt()
        if t == "FIN_COPIE":
            self.advance()
            return None
        if t in ("OUVRIR", "FERMER", "LIRE", "ECRIRE", "REECRIRE", "SUPPRIMER", "POSITIONNER"):
            return self.parse_file_or_io_stmt()
        if t == "SQL_BLOCK":
            sql_tok = self.advance()
            return SqlStmt(line=sql_tok.line, raw_sql=sql_tok.value, end_line=self.cur().line)

        # Affectation (x := expr, t[i] <- expr, s.champ := expr) ou appel de procédure proc(a, b)
        if t in self.CONTEXTUAL_IDENT_TOKENS and t != "VALRET":
            lhs = self.parse_postfix_lvalue()
            if isinstance(lhs, CallExpr):
                return CallStmt(line=tok.line, name=lhs.name, args=lhs.args)
            if self.match("ASSIGN", "EQ"):
                rhs = self.parse_expr()
                return AssignStmt(line=tok.line, target=lhs, value=rhs)
            # Appel de procédure sans parenthèses
            if isinstance(lhs, VarRef) and self.cur().type in ("NEWLINE", "SEMI", "EOF"):
                return CallStmt(line=tok.line, name=lhs.name, args=[])
            raise ParseError(
                f"Opérateur d'affectation ':=' ou '<-' attendu après { getattr(lhs, 'name', 'la cible') }",
                self.cur().line,
                self.cur().col,
            )

        raise ParseError(
            f"Instruction non reconnue ou mot-clef mal placé : {tok.value or tok.type!r}",
            tok.line,
            tok.col,
        )

    def parse_saisir(self) -> SaisirStmt:
        tok = self.expect("SAISIR")
        has_paren = bool(self.match("LPAREN"))
        prompt: Optional[Expr] = None
        targets: List[Expr] = []

        # Si le premier argument est une chaîne littérale suivie d'une virgule, c'est l'invite (prompt) d'Alg_32 !
        if self.cur().type == "STRING" and self.peek().type == "COMMA":
            str_tok = self.advance()
            prompt = Literal(line=str_tok.line, value=str_tok.value, lit_type="CHAINE")
            self.expect("COMMA")

        while True:
            target = self.parse_postfix_lvalue()
            if not isinstance(target, (VarRef, IndexAccess, FieldAccess)):
                raise ParseError("SAISIR attend une variable, un élément de tableau ou un champ", tok.line, tok.col)
            targets.append(target)
            if not self.match("COMMA"):
                break

        if has_paren:
            self.expect("RPAREN")
        return SaisirStmt(line=tok.line, prompt=prompt, targets=targets)

    def parse_afficher(self, to_printer: bool = False) -> AfficherStmt:
        tok = self.advance()
        newline = True
        items: List[Expr] = []

        if self.cur().type in ("NEWLINE", "SEMI", "EOF"):
            return AfficherStmt(line=tok.line, items=[], newline=True, to_printer=to_printer)

        # Attention : `AFFICHER (a + b) * 2` commence par '(' sans englober toute l'instruction
        has_outer_paren = False
        if self.cur().type == "LPAREN":
            # Regarde si toute la ligne se termine par ')'
            save_pos = self.pos
            try:
                self.advance()
                if self.cur().type == "RPAREN":
                    self.advance()
                    return AfficherStmt(line=tok.line, items=[], newline=True, to_printer=to_printer)
                first = self.parse_expr()
                temp_items = [first]
                while self.match("COMMA"):
                    temp_items.append(self.parse_expr())
                if self.match("RPAREN") and self.cur().type in ("NEWLINE", "SEMI", "EOF", "AMP"):
                    items = temp_items
                    has_outer_paren = True
                else:
                    self.pos = save_pos
            except ParseError:
                self.pos = save_pos

        if not has_outer_paren:
            while True:
                if self.cur().type == "AMP":
                    break
                items.append(self.parse_expr())
                if not self.match("COMMA"):
                    break

        if self.match("AMP"):
            newline = False

        return AfficherStmt(line=tok.line, items=items, newline=newline, to_printer=to_printer)

    def parse_screen_cmd(self) -> ScreenCmdStmt:
        tok = self.advance()
        has_paren = bool(self.match("LPAREN"))
        e1 = self.parse_expr()
        self.expect("COMMA", msg="',' entre les 2 paramètres")
        e2 = self.parse_expr()
        if has_paren:
            self.expect("RPAREN")
        return ScreenCmdStmt(line=tok.line, cmd=tok.type, args=[e1, e2])

    def parse_if(self) -> IfStmt:
        si_tok = self.expect("SI")
        cond = self.parse_expr()
        self.skip_newlines()
        self.expect("ALORS", msg="ALORS après la condition du SI")
        self.skip_newlines()

        branches: List[IfBranch] = []
        first_body = self.parse_stmt_list({"SINON", "SINON_SI", "FIN_SI"})
        branches.append(IfBranch(condition=cond, body=first_body, line=si_tok.line))

        else_body: List[Stmt] = []
        while self.cur().type == "SINON_SI" or (self.cur().type == "SINON" and self.peek().type == "SI"):
            el_line = self.cur().line
            if self.cur().type == "SINON_SI":
                self.advance()
            else:
                self.advance()
                self.advance()
            el_cond = self.parse_expr()
            self.skip_newlines()
            self.expect("ALORS", msg="ALORS après SINON SI")
            self.skip_newlines()
            el_body = self.parse_stmt_list({"SINON", "SINON_SI", "FIN_SI"})
            branches.append(IfBranch(condition=el_cond, body=el_body, line=el_line))

        if self.match("SINON"):
            self.skip_newlines()
            # Cas où l'étudiant écrit SINON sur une ligne suivi de SI ... FINSI imbriqué ou normal
            else_body = self.parse_stmt_list({"FIN_SI"})

        end_tok = self.expect("FIN_SI", msg="FINSI pour fermer la structure SI")
        return IfStmt(line=si_tok.line, branches=branches, else_body=else_body, end_line=end_tok.line)

    def parse_selon(self) -> SelonStmt:
        tok = self.expect("SELON")
        selector = self.parse_expr()
        self.skip_newlines()
        cases: List[CaseBranch] = []
        else_body: List[Stmt] = []

        while self.cur().type not in ("FIN_SELON", "EOF"):
            if self.match("AUTRES") or (self.cur().type == "CAS" and self.peek().type == "SINON"):
                if self.cur().type == "CAS":
                    self.advance()
                    self.advance()
                self.match("COLON")
                self.skip_newlines()
                else_body = self.parse_stmt_list({"FIN_SELON", "CAS", "AUTRES"})
            elif self.match("CAS"):
                cline = self.tokens[self.pos - 1].line
                if self.match("SINON", "AUTRES"):
                    self.match("COLON")
                    self.skip_newlines()
                    else_body = self.parse_stmt_list({"FIN_SELON", "CAS", "AUTRES"})
                    continue
                vals: List[Expr] = []
                ranges: List[Tuple[Expr, Expr]] = []
                while True:
                    v1 = self.parse_expr()
                    if self.match("DOTDOT"):
                        v2 = self.parse_expr()
                        ranges.append((v1, v2))
                    else:
                        vals.append(v1)
                    if not self.match("COMMA"):
                        break
                self.match("COLON")
                self.skip_newlines()
                cbody = self.parse_stmt_list({"CAS", "AUTRES", "FIN_SELON"})
                cases.append(CaseBranch(values=vals, ranges=ranges, body=cbody, line=cline))
            else:
                raise ParseError("CAS ou FINSELON attendu dans le bloc SELON", self.cur().line, self.cur().col)

        end_tok = self.expect("FIN_SELON", msg="FINSELON")
        return SelonStmt(
            line=tok.line,
            selector=selector,
            cases=cases,
            else_body=else_body,
            end_line=end_tok.line,
        )

    def parse_pour(self) -> PourStmt:
        tok = self.expect("POUR")
        var_target = self.parse_postfix_lvalue()
        if not self.match("ASSIGN", "EQ", "DE"):
            raise ParseError("':=', '<-' ou 'DE' attendu après la variable de boucle POUR", self.cur().line, self.cur().col)
        start_expr = self.parse_expr()
        self.expect("A", "JUSQUA", msg="'A' (ou 'À') attendu dans la boucle POUR")
        end_expr = self.parse_expr()
        step_expr: Optional[Expr] = None
        if self.match("PAS"):
            self.match("ASSIGN", "EQ", "DE")
            step_expr = self.parse_expr()
        self.match("FAIRE")
        self.skip_newlines()
        body = self.parse_stmt_list({"FIN_POUR"})
        end_tok = self.expect("FIN_POUR", msg="FINPOUR")
        return PourStmt(
            line=tok.line,
            var_target=var_target,
            start_expr=start_expr,
            end_expr=end_expr,
            step_expr=step_expr,
            body=body,
            end_line=end_tok.line,
        )

    def parse_tant_que(self) -> TantQueStmt:
        tok = self.expect("TANT_QUE")
        cond = self.parse_expr()
        self.match("FAIRE")
        self.skip_newlines()
        body = self.parse_stmt_list({"FIN_TQ"})
        end_tok = self.expect("FIN_TQ", msg="FINTQ (ou FIN TANT QUE)")
        return TantQueStmt(line=tok.line, condition=cond, body=body, end_line=end_tok.line)

    def parse_repeter(self) -> RepeterStmt:
        tok = self.expect("REPETER")
        self.skip_newlines()
        body = self.parse_stmt_list({"JUSQUA"})
        jq_tok = self.expect("JUSQUA", msg="JUSQU'A à la fin du bloc REPETER")
        cond = self.parse_expr()
        return RepeterStmt(line=tok.line, body=body, until_condition=cond, until_line=jq_tok.line)

    def parse_iter(self) -> IterStmt:
        tok = self.expect("ITER")
        self.skip_newlines()
        body = self.parse_stmt_list({"FIN_ITER"})
        end_tok = self.expect("FIN_ITER", msg="FINITER")
        return IterStmt(line=tok.line, body=body, end_line=end_tok.line)

    def parse_proc_call_stmt(self) -> CallStmt:
        name_tok = self._expect_name_token("le nom de la procédure")
        args: List[Expr] = []
        if self.match("LPAREN"):
            if not self.match("RPAREN"):
                while True:
                    args.append(self.parse_expr())
                    if not self.match("COMMA"):
                        break
                self.expect("RPAREN")
        return CallStmt(line=name_tok.line, name=name_tok.value, args=args)

    def parse_return_stmt(self) -> ReturnStmt:
        tok = self.expect("VALRET")
        # Supporte `VALRET := expr`, `DELIVRE(expr)`, `RETOURNER expr`
        self.match("ASSIGN", "EQ")
        val = self.parse_expr()
        return ReturnStmt(line=tok.line, value=val)

    def parse_copie_stmt(self) -> CopieStmt:
        tok = self.expect("COPIE")
        str_tok = self.expect("STRING", msg='le chemin du module entre guillemets (ex: COPIE "module.alg")')
        return CopieStmt(line=tok.line, module_path=str_tok.value)

    def parse_file_or_io_stmt(self) -> Stmt:
        tok = self.cur()
        op = tok.type

        # Ergonomie étudiante : si ECRIRE ou LIRE est utilisé avec une chaîne ou variable ordinaire
        # qui n'est pas un FICHIER/ENREGISTREMENT déclaré, on l'interprète intelligemment comme AFFICHER / SAISIR !
        if op == "ECRIRE":
            nxt = self.peek()
            first_is_file = nxt.type == "IDENT" and norm_key(nxt.value) in self.declared_files_and_records
            if not first_is_file:
                return self.parse_afficher(to_printer=False)

        if op == "LIRE":
            nxt = self.peek()
            first_is_file = nxt.type == "IDENT" and norm_key(nxt.value) in self.declared_files_and_records
            if not first_is_file:
                self.advance()  # consomme LIRE
                has_paren = bool(self.match("LPAREN"))
                targets: List[Expr] = []
                while True:
                    targets.append(self.parse_postfix_lvalue())
                    if not self.match("COMMA"):
                        break
                if has_paren:
                    self.expect("RPAREN")
                return SaisirStmt(line=tok.line, prompt=None, targets=targets)

        self.advance()

        if op == "OUVRIR":
            fname = self._expect_name_token("le nom du fichier à ouvrir").value
            mode = "LECTURE/ECRITURE"
            if self.match("EN"):
                m_parts = [norm_key(self._expect_name_token("le mode d'ouverture").value)]
                if self.match("SLASH"):
                    m_parts.append(norm_key(self._expect_name_token().value))
                mode = "/".join(m_parts)
            return FileOpStmt(line=tok.line, op="OUVRIR", target_names=[fname], mode=mode)

        if op == "FERMER":
            fnames = [self._expect_name_token("un nom de fichier").value]
            while self.match("COMMA"):
                fnames.append(self._expect_name_token("un nom de fichier").value)
            return FileOpStmt(line=tok.line, op="FERMER", target_names=fnames)

        if op in ("ECRIRE", "REECRIRE", "SUPPRIMER"):
            tname = self._expect_name_token("le nom d'enregistrement ou de fichier").value
            pos_expr: Optional[Expr] = None
            var_target: Optional[Expr] = None
            if self.match("COMMA"):
                first_e = self.parse_expr()
                if self.match("COMMA"):
                    pos_expr = first_e
                    var_target = self.parse_postfix_lvalue()
                else:
                    var_target = first_e
            return FileOpStmt(
                line=tok.line,
                op=op,
                target_names=[tname],
                position_expr=pos_expr,
                var_target=var_target,
            )

        if op == "LIRE":
            tname = self._expect_name_token("le nom d'enregistrement ou de fichier").value
            seq_next = False
            key_expr: Optional[Expr] = None
            pos_expr = None
            var_target = None

            if self.cur().type == "SELON" and norm_key(self.cur().value) == "SUIVANT":
                self.advance()
                seq_next = True
            elif self.match("AVEC_CLE"):
                self.match("EQ", "COLON")
                key_expr = self.parse_expr()
            elif self.match("COMMA"):
                first_e = self.parse_postfix_lvalue()
                if self.match("COMMA"):
                    pos_expr = first_e
                    var_target = self.parse_postfix_lvalue()
                else:
                    var_target = first_e

            return FileOpStmt(
                line=tok.line,
                op="LIRE",
                target_names=[tname],
                sequential_next=seq_next,
                key_expr=key_expr,
                position_expr=pos_expr,
                var_target=var_target,
            )

        if op == "POSITIONNER":
            tname = self._expect_name_token("le nom d'enregistrement ou de fichier").value
            key_expr = None
            pos_expr = None
            if self.match("AVEC_CLE"):
                self.match("EQ", "COLON")
                key_expr = self.parse_expr()
            elif self.match("COMMA"):
                pos_expr = self.parse_expr()
            return FileOpStmt(
                line=tok.line,
                op="POSITIONNER",
                target_names=[tname],
                key_expr=key_expr,
                position_expr=pos_expr,
            )

        raise ParseError(f"Opération fichier inattendue : {op}", tok.line, tok.col)

    # ==========================================
    # Expressions (priorités exactes Alg_32)
    # ==========================================

    def parse_expr(self) -> Expr:
        return self.parse_or()

    def parse_or(self) -> Expr:
        left = self.parse_xor()
        while self.cur().type == "OP_OU":
            op_tok = self.advance()
            right = self.parse_xor()
            left = BinaryOp(line=op_tok.line, op="OU", left=left, right=right)
        return left

    def parse_xor(self) -> Expr:
        left = self.parse_and()
        while self.cur().type == "OP_OUX":
            op_tok = self.advance()
            right = self.parse_and()
            left = BinaryOp(line=op_tok.line, op="OUX", left=left, right=right)
        return left

    def parse_and(self) -> Expr:
        left = self.parse_comparison()
        while self.cur().type == "OP_ET":
            op_tok = self.advance()
            right = self.parse_comparison()
            left = BinaryOp(line=op_tok.line, op="ET", left=left, right=right)
        return left

    def parse_comparison(self) -> Expr:
        left = self.parse_additive()
        while self.cur().type in ("CMP", "EQ"):
            op_tok = self.advance()
            op_str = "=" if op_tok.type == "EQ" else op_tok.value
            right = self.parse_additive()
            left = BinaryOp(line=op_tok.line, op=op_str, left=left, right=right)
        return left

    def parse_additive(self) -> Expr:
        left = self.parse_multiplicative()
        while self.cur().type in ("PLUS", "MINUS"):
            op_tok = self.advance()
            right = self.parse_multiplicative()
            left = BinaryOp(line=op_tok.line, op=op_tok.value, left=left, right=right)
        return left

    def parse_multiplicative(self) -> Expr:
        left = self.parse_power()
        while self.cur().type in ("STAR", "SLASH", "OP_DIV", "OP_MOD", "MOD_SYM"):
            op_tok = self.advance()
            if op_tok.type == "OP_DIV":
                op_str = "DIV"
            elif op_tok.type in ("OP_MOD", "MOD_SYM"):
                op_str = "MOD"
            else:
                op_str = op_tok.value
            right = self.parse_power()
            left = BinaryOp(line=op_tok.line, op=op_str, left=left, right=right)
        return left

    def parse_power(self) -> Expr:
        left = self.parse_unary()
        if self.cur().type == "POW":
            op_tok = self.advance()
            right = self.parse_power()
            return BinaryOp(line=op_tok.line, op="^", left=left, right=right)
        return left

    def parse_unary(self) -> Expr:
        if self.cur().type in ("PLUS", "MINUS", "OP_NON"):
            op_tok = self.advance()
            op_str = "NON" if op_tok.type == "OP_NON" else op_tok.value
            operand = self.parse_unary()
            return UnaryOp(line=op_tok.line, op=op_str, operand=operand)
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        tok = self.cur()
        if tok.type == "INT":
            self.advance()
            return Literal(line=tok.line, value=int(tok.value), lit_type="ENTIER")
        if tok.type == "FLOAT":
            self.advance()
            return Literal(line=tok.line, value=float(tok.value), lit_type="REEL")
        if tok.type == "STRING":
            self.advance()
            return Literal(line=tok.line, value=tok.value, lit_type="CHAINE")
        if tok.type == "BOOL":
            self.advance()
            return Literal(line=tok.line, value=(tok.value == "VRAI"), lit_type="BOOLEEN")
        if tok.type == "LPAREN":
            self.advance()
            inner = self.parse_expr()
            self.expect("RPAREN", msg="')' fermante")
            return inner
        if tok.type in self.CONTEXTUAL_IDENT_TOKENS or tok.type == "ERREUR":
            return self.parse_postfix_lvalue()

        raise ParseError(f"Expression attendue, mais trouvé {tok.value or tok.type!r}", tok.line, tok.col)

    def parse_postfix_lvalue(self) -> Expr:
        name_tok = self._expect_name_token("un identificateur")
        node: Expr = VarRef(line=name_tok.line, name=name_tok.value)

        # Appel de fonction f(a, b)
        if self.match("LPAREN"):
            args: List[Expr] = []
            if not self.match("RPAREN"):
                while True:
                    args.append(self.parse_expr())
                    if not self.match("COMMA"):
                        break
                self.expect("RPAREN", msg="')' après les arguments")
            node = CallExpr(line=name_tok.line, name=name_tok.value, args=args)

        # Chaînage d'accès tableaux t[i, j] ou t[i][j] et champs structure s.nom
        while True:
            if self.match("LBRACKET"):
                indices: List[Expr] = []
                while True:
                    indices.append(self.parse_expr())
                    if not self.match("COMMA"):
                        break
                self.expect("RBRACKET", msg="']' après l'indice de tableau")
                if isinstance(node, IndexAccess):
                    node.indices.extend(indices)
                else:
                    node = IndexAccess(line=node.line, target=node, indices=indices)
            elif self.match("DOT"):
                ftok = self._expect_name_token("un nom de champ après '.'")
                node = FieldAccess(line=ftok.line, target=node, field_name=ftok.value)
            else:
                break

        return node


def parse_source(source: str, profile: Optional[KeywordProfile] = None) -> Program:
    tokens = tokenize(source, profile=profile)
    parser = Parser(tokens, profile=profile)
    return parser.parse_program()
