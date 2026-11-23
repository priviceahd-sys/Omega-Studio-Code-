"""
Analyseur lexical (Lexer) pour le langage algorithmique Alg_32 / Omega Studio Code.
Gère les élisions françaises (JUSQU'À, C'EST, tableau d'entiers), les commentaires
(', //, /* */, (* *)), les littéraux booléens (.VRAI. / .FAUX.), les blocs EXEC SQL
et les mots-clefs multi-mots personnalisables (Algpers32).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .keywords import KeywordProfile, norm_key, strip_accents


@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_part(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def tokenize(source: str, profile: Optional[KeywordProfile] = None) -> List[Token]:
    profile = profile or KeywordProfile()
    single_kw, multi_kw = profile.build_lookup()

    raw_tokens: List[Token] = []
    n = len(source)
    i = 0
    line = 1
    col = 1

    def advance(count: int = 1) -> None:
        nonlocal i, line, col
        for _ in range(count):
            if i < n:
                if source[i] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1

    while i < n:
        ch = source[i]

        # Retour à la ligne
        if ch == "\n":
            if not raw_tokens or raw_tokens[-1].type != "NEWLINE":
                raw_tokens.append(Token("NEWLINE", "\n", line, col))
            advance()
            continue

        # Espaces horizontaux
        if ch in (" ", "\t", "\r", "\xa0"):
            advance()
            continue

        # Commentaire ligne //
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                advance()
            continue

        # Commentaire bloc /* ... */
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            start_line, start_col = line, col
            advance(2)
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == "/"):
                advance()
            if i >= n:
                raise LexError("Commentaire /* non fermé en fin de fichier", start_line, start_col)
            advance(2)
            continue

        # Commentaire bloc (* ... *)
        if ch == "(" and i + 1 < n and source[i + 1] == "*":
            start_line, start_col = line, col
            advance(2)
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == ")"):
                advance()
            if i >= n:
                raise LexError("Commentaire (* non fermé en fin de fichier", start_line, start_col)
            advance(2)
            continue

        # Commentaire apostrophe Alg_32 : ' jusqu'à la fin de ligne
        if ch in ("'", "’"):
            while i < n and source[i] != "\n":
                advance()
            continue

        # Littéral booléen Alg_32 .VRAI. / .FAUX.
        if ch == ".":
            rest = source[i : i + 8]
            up_rest = strip_accents(rest).upper()
            if up_rest.startswith(".VRAI."):
                raw_tokens.append(Token("BOOL", "VRAI", line, col))
                advance(6)
                continue
            if up_rest.startswith(".FAUX."):
                raw_tokens.append(Token("BOOL", "FAUX", line, col))
                advance(6)
                continue
            if i + 1 < n and source[i + 1] == ".":
                raw_tokens.append(Token("DOTDOT", "..", line, col))
                advance(2)
                continue
            raw_tokens.append(Token("DOT", ".", line, col))
            advance()
            continue

        # Chaîne de caractères "..."
        if ch == '"':
            start_line, start_col = line, col
            advance()  # ouvre "
            buf: List[str] = []
            while i < n and source[i] not in ('"', "\n"):
                if source[i] == "\\" and i + 1 < n and source[i + 1] in ('"', "\\", "n", "t"):
                    esc = source[i + 1]
                    buf.append({"n": "\n", "t": "\t"}.get(esc, esc))
                    advance(2)
                elif source[i] == '"' and i + 1 < n and source[i + 1] == '"':
                    buf.append('"')
                    advance(2)
                else:
                    buf.append(source[i])
                    advance()
            if i >= n or source[i] != '"':
                raise LexError('Guillemet fermant (") attendu sur la ligne', start_line, start_col)
            advance()  # ferme "
            raw_tokens.append(Token("STRING", "".join(buf), start_line, start_col))
            continue

        # Nombres (entiers ou réels, notation scientifique incluse)
        if ch.isdigit():
            start_line, start_col = line, col
            num_start = i
            is_float = False
            while i < n and source[i].isdigit():
                advance()
            if i < n and source[i] == "." and not (i + 1 < n and source[i + 1] == "."):
                # Vérifie que ce n'est pas .VRAI. ou similaire
                if i + 1 < n and source[i + 1].isdigit():
                    is_float = True
                    advance()
                    while i < n and source[i].isdigit():
                        advance()
            if i < n and source[i] in ("e", "E"):
                nxt = i + 1
                if nxt < n and source[nxt] in ("+", "-"):
                    nxt += 1
                if nxt < n and source[nxt].isdigit():
                    is_float = True
                    advance()
                    if source[i] in ("+", "-"):
                        advance()
                    while i < n and source[i].isdigit():
                        advance()
            raw_val = source[num_start:i]
            raw_tokens.append(Token("FLOAT" if is_float else "INT", raw_val, start_line, start_col))
            continue

        # Identificateurs, mots-clefs et élisions françaises
        if _is_ident_start(ch):
            start_line, start_col = line, col
            w_start = i
            while i < n and _is_ident_part(source[i]):
                advance()

            word = source[w_start:i]
            nw = norm_key(word)

            # Cas d'élision française : d'entiers -> DE + entiers
            if nw == "D" and i < n and source[i] in ("'", "’"):
                advance()  # consomme l'apostrophe
                raw_tokens.append(Token("DE", "d'", start_line, start_col))
                continue

            # Cas JUSQU'A / JUSQU'À ou C'EST
            if nw in ("JUSQU", "C") and i < n and source[i] in ("'", "’"):
                save_i, save_line, save_col = i, line, col
                advance()
                sub_start = i
                while i < n and _is_ident_part(source[i]):
                    advance()
                sub_word = norm_key(source[sub_start:i])
                combined = f"{nw}'{sub_word}"
                if combined == "JUSQU'A":
                    raw_tokens.append(Token("JUSQUA", source[w_start:i], start_line, start_col))
                    continue
                if combined == "C'EST":
                    raw_tokens.append(Token("ASSIGN", source[w_start:i], start_line, start_col))
                    continue
                i, line, col = save_i, save_line, save_col

            # Bloc EXEC SQL ... FIN EXEC / FIN SQL
            if nw == "EXEC":
                save_i, save_line, save_col = i, line, col
                while i < n and source[i] in (" ", "\t"):
                    advance()
                sql_kw_start = i
                while i < n and _is_ident_part(source[i]):
                    advance()
                if norm_key(source[sql_kw_start:i]) == "SQL":
                    # Capture tout jusqu'à FIN EXEC ou FIN SQL
                    sql_body_start = i
                    end_found = False
                    sql_body_end = i
                    while i < n:
                        # Cherche FIN EXEC / FIN SQL insensible à la casse
                        rem = strip_accents(source[i : i + 12]).upper()
                        if rem.startswith("FIN EXEC") or rem.startswith("FIN SQL"):
                            prev_ok = i == 0 or not _is_ident_part(source[i - 1])
                            end_len = 8 if rem.startswith("FIN EXEC") else 7
                            after_idx = i + end_len
                            next_ok = after_idx >= n or not _is_ident_part(source[after_idx])
                            if prev_ok and next_ok:
                                sql_body_end = i
                                advance(end_len)
                                end_found = True
                                break
                        advance()
                    if not end_found:
                        raise LexError("Bloc EXEC SQL sans FIN EXEC ou FIN SQL", start_line, start_col)
                    sql_text = source[sql_body_start:sql_body_end].strip()
                    raw_tokens.append(Token("SQL_BLOCK", sql_text, start_line, start_col))
                    continue
                else:
                    i, line, col = save_i, save_line, save_col

            if nw in ("VRAI", "TRUE"):
                raw_tokens.append(Token("BOOL", "VRAI", start_line, start_col))
            elif nw in ("FAUX", "FALSE"):
                raw_tokens.append(Token("BOOL", "FAUX", start_line, start_col))
            else:
                raw_tokens.append(Token("WORD", word, start_line, start_col))
            continue

        # Opérateurs multi-caractères
        two = source[i : i + 2]
        three = source[i : i + 3]
        if three == "<--":
            raw_tokens.append(Token("ASSIGN", "<--", line, col))
            advance(3)
            continue
        if three == "-->":
            raw_tokens.append(Token("COLON", "-->", line, col))
            advance(3)
            continue
        if two in (":=", "<-"):
            raw_tokens.append(Token("ASSIGN", two, line, col))
            advance(2)
            continue
        if ch == "←":
            raw_tokens.append(Token("ASSIGN", ch, line, col))
            advance()
            continue
        if two == "**":
            raw_tokens.append(Token("POW", "**", line, col))
            advance(2)
            continue
        if two in ("<=", ">=", "<>", "!="):
            op_val = "<>" if two == "!=" else two
            raw_tokens.append(Token("CMP", op_val, line, col))
            advance(2)
            continue
        if ch in ("<", ">"):
            raw_tokens.append(Token("CMP", ch, line, col))
            advance()
            continue
        if ch == "=":
            raw_tokens.append(Token("EQ", "=", line, col))
            advance()
            continue

        single_punct = {
            "+": "PLUS",
            "-": "MINUS",
            "*": "STAR",
            "/": "SLASH",
            "%": "MOD_SYM",
            "^": "POW",
            "(": "LPAREN",
            ")": "RPAREN",
            "[": "LBRACKET",
            "]": "RBRACKET",
            ",": "COMMA",
            ":": "COLON",
            ";": "SEMI",
            "&": "AMP",
        }
        if ch in single_punct:
            raw_tokens.append(Token(single_punct[ch], ch, line, col))
            advance()
            continue

        raise LexError(f"Caractère non reconnu : {ch!r}", line, col)

    # Passe 2 : fusion des mots-clefs multi-mots (ex: FIN TANT QUE, TANT QUE, DONNEE MODIFIEE)
    merged: List[Token] = []
    idx = 0
    total = len(raw_tokens)
    while idx < total:
        tok = raw_tokens[idx]
        if tok.type == "WORD":
            matched = False
            for seq_words, canon in multi_kw:
                seq_len = len(seq_words)
                if idx + seq_len <= total:
                    ok = True
                    for offset, expected_w in enumerate(seq_words):
                        cand = raw_tokens[idx + offset]
                        if cand.type != "WORD" or cand.line != tok.line or norm_key(cand.value) != expected_w:
                            ok = False
                            break
                    if ok:
                        combined_val = " ".join(raw_tokens[idx + k].value for k in range(seq_len))
                        tok_type = "ASSIGN" if canon == "ASSIGN_WORD" else canon
                        merged.append(Token(tok_type, combined_val, tok.line, tok.col))
                        idx += seq_len
                        matched = True
                        break
            if matched:
                continue

            nw = norm_key(tok.value)
            if nw in single_kw:
                canon = single_kw[nw]
                tok_type = "ASSIGN" if canon == "ASSIGN_WORD" else canon
                merged.append(Token(tok_type, tok.value, tok.line, tok.col))
            else:
                merged.append(Token("IDENT", tok.value, tok.line, tok.col))
        else:
            merged.append(tok)
        idx += 1

    merged.append(Token("EOF", "", line, col))
    return merged
