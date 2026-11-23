"""
Gestionnaire des mots-clefs, fonctions intégrées, aide officielle (alg_exec.ini)
et personnalisation compatible Algpers32.
"""

from __future__ import annotations

import json
import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def strip_accents(text: str) -> str:
    """Supprime les accents tout en préservant la casse de base."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def norm_key(text: str) -> str:
    """Normalise un mot-clef ou identificateur (sans accents, majuscules, espaces simples)."""
    cleaned = strip_accents(text.strip()).upper()
    return " ".join(cleaned.split())


# Catégories canoniques de jetons de mots-clefs Alg_32
STANDARD_KEYWORDS: Dict[str, List[str]] = {
    "ALGO": ["ALGO", "ALGORITHME", "PROGRAMME"],
    "DEBUT": ["DEBUT"],
    "FIN": [
        "FIN",
        "FIN ALGO",
        "FINALGO",
        "FALGO",
        "FIN PROGRAMME",
        "FINPROGRAMME",
        "FPROGRAMME",
    ],
    "FIN_PROC": ["FIN PROCEDURE", "FINPROCEDURE", "FPROCEDURE"],
    "FIN_FONC": ["FIN FONCTION", "FINFONCTION", "FFONCTION"],
    "CONST": ["CONST", "CONSTANTE", "CONSTANTES"],
    "VAR": ["VAR", "VARIABLE", "VARIABLES"],
    "GLOBALE": ["GLOBALE", "GLOBALES"],
    "TYPE": ["TYPE"],
    "FIN_TYPE": ["FIN TYPE", "FINTYPE", "FTYPE"],
    "STRUCTURE": ["STRUCTURE"],
    "FIN_STRUCTURE": ["FIN STRUCTURE", "FINSTRUCTURE", "FSTRUCTURE"],
    "TABLEAU": ["TABLEAU", "TABLEAUX"],
    "DE": ["DE", "DEPUIS"],
    "FICHIER": ["FICHIER", "FICHIERS"],
    "EN": ["EN"],
    "ORGANISATION": ["ORGANISATION"],
    "ACCES": ["ACCES"],
    "CLE": ["CLE", "CLEF"],
    "AVEC_CLE": ["AVEC CLE", "AVEC CLEF"],
    "PRIMAIRE": ["PRIMAIRE"],
    "SECONDAIRE": ["SECONDAIRE"],
    "ENREGISTREMENT": [
        "ENREGISTREMENT",
        "DEBUT ENREGISTREMENT",
        "DEBUT ARTICLE",
        "ARTICLE",
    ],
    "FIN_ENREGISTREMENT": [
        "FINENREGISTREMENT",
        "FIN ENREGISTREMENT",
        "FENREGISTREMENT",
        "FIN ARTICLE",
        "FINARTICLE",
        "FARTICLE",
    ],
    "SI": ["SI"],
    "ALORS": ["ALORS"],
    "SINON": ["SINON"],
    "SINON_SI": ["SINON SI", "SINONSI"],
    "FIN_SI": ["FINSI", "FIN SI", "FSI"],
    "SELON": ["SELON", "SUIVANT"],
    "CAS": ["CAS"],
    "AUTRES": ["AUTRES", "CAS SINON"],
    "FIN_SELON": [
        "FINSELON",
        "FIN SELON",
        "FSELON",
        "FINCAS",
        "FIN CAS",
        "FCAS",
        "FINSUIVANT",
        "FIN SUIVANT",
        "FSUIVANT",
    ],
    "POUR": ["POUR"],
    "A": ["A"],
    "PAS": ["PAS"],
    "FAIRE": ["FAIRE"],
    "FIN_POUR": ["FINPOUR", "FIN POUR", "FPOUR"],
    "TANT_QUE": ["TANT QUE", "TANTQUE", "TQ"],
    "FIN_TQ": [
        "FINTQ",
        "FTQ",
        "FIN TANT QUE",
        "FINTANT QUE",
        "FINTANTQUE",
        "FTANT QUE",
        "FTANTQUE",
        "REFAIRE",
    ],
    "REPETER": ["REPETER"],
    "JUSQUA": ["JUSQU'A", "JUSQUA", "JQA"],
    "ITER": ["ITER"],
    "SORTIRSI": ["SORTIRSI", "SORTIR SI"],
    "FIN_ITER": ["FINITER", "FIN ITER", "FITER"],
    "PROCEDURE": ["PROCEDURE", "PROC"],
    "FONCTION": ["FONCTION", "FONCT"],
    "TRAITER": ["TRAITER", "APPELER"],
    "VALRET": ["VALRET", "DELIVRE", "RETOURNER", "RENVOYER"],
    "PARAM_IN": ["DONNEE", "DONNEES", "VALEUR", "VAL"],
    "PARAM_OUT": ["RESULTAT", "RESULTATS"],
    "PARAM_INOUT": ["DONNEE MODIFIEE", "DONNEES MODIFIEES", "ADRESSE", "ADR"],
    "SAISIR": ["SAISIR", "LIRE_CLAVIER"],
    "AFFICHER": ["AFFICHER", "AFFICHE", "ECRIRE_ECRAN"],
    "IMPRIMER": ["IMPRIMER"],
    "A_LA_LIGNE": ["A_LA_LIGNE", "A LA LIGNE"],
    "EFFACE_ECRAN": ["EFFACE_ECRAN", "EFFACE ECRAN", "CLS"],
    "CURSEUR": ["CURSEUR"],
    "COULEUR": ["COULEUR"],
    "COPIE": ["COPIE"],
    "FIN_COPIE": ["FINCOPIE", "FIN COPIE", "FCOPIE"],
    "OUVRIR": ["OUVRIR"],
    "FERMER": ["FERMER"],
    "LIRE": ["LIRE"],
    "ECRIRE": ["ECRIRE"],
    "REECRIRE": ["REECRIRE"],
    "SUPPRIMER": ["SUPPRIMER"],
    "POSITIONNER": ["POSITIONNER", "POSITIONNEMENT"],
    "EXEC_SQL": ["EXEC SQL"],
    "FIN_SQL": ["FIN EXEC", "FIN SQL"],
    "OP_ET": ["ET"],
    "OP_OU": ["OU"],
    "OP_OUX": ["OUX", "XOR"],
    "OP_NON": ["NON"],
    "OP_DIV": ["DIV"],
    "OP_MOD": ["MOD"],
    "ASSIGN_WORD": ["C'EST"],
}

DATA_TYPES: Dict[str, List[str]] = {
    "ENTIER": ["ENTIER", "ENTIERS", "ENT"],
    "REEL": ["REEL", "REELS"],
    "DECIMAL": ["DECIMAL", "DECIMAUX"],
    "CHAINE": ["CHAINE", "CHAINES"],
    "CAR": ["CAR", "CARACTERE", "CARACTERES"],
    "BOOLEEN": ["BOOLEEN", "BOOLEENS", "BOOL"],
}

BUILTIN_FUNCTIONS: Dict[str, Tuple[List[str], str, str]] = {
    # canon_name: (aliases, signature, short_desc)
    "LONG": (["LONG", "LONGUEUR"], "LONG(chaîne)", "Nombre de caractères d'une chaîne"),
    "GAUCHE": (["GAUCHE"], "GAUCHE(chaîne, n)", "n premiers caractères à gauche"),
    "DROITE": (["DROITE"], "DROITE(chaîne, n)", "n derniers caractères à droite"),
    "MILIEU": (["MILIEU", "SSCHAINE"], "MILIEU(chaîne, pos, n)", "Sous-chaîne de n caractères dès pos (1-indexé)"),
    "RANG": (["RANG"], "RANG(chaîne, sous_ch, [départ])", "Position (1-indexée) de sous_ch dans chaîne (0 sinon)"),
    "SUPPR": (["SUPPR"], "SUPPR(chaîne, pos, n)", "Supprime n caractères à partir de pos"),
    "ESPACE": (["ESPACE"], "ESPACE(n)", "Chaîne composée de n espaces"),
    "REPETECAR": (["REPETECAR"], "RÉPÈTECAR(n, code_ansi)", "Répète n fois le caractère de code ANSI donné"),
    "MAJ": (["MAJ", "MAJUSCULE"], "MAJ(chaîne)", "Convertit en majuscules"),
    "MIN": (["MIN", "MINUSCULE"], "MIN(chaîne)", "Convertit en minuscules"),
    "ESPACEDROITE": (["ESPACEDROITE", "ESPACE_DROIT"], "ESPACEDROITE(chaîne)", "Supprime les espaces à droite"),
    "ESPACEGAUCHE": (["ESPACEGAUCHE", "ESPACE_GAUCHE"], "ESPACEGAUCHE(chaîne)", "Supprime les espaces à gauche"),
    "ANSI": (["ANSI", "CODE", "ORD"], "ANSI(car)", "Code ANSI/Unicode du premier caractère"),
    "CAR": (["CAR"], "CAR(code)", "Caractère associé au code numérique"),
    "CVCHAINE": (["CVCHAINE", "NUMCH"], "CVCHAINE(nombre)", "Convertit un nombre en chaîne"),
    "CHNOMBRE": (["CHNOMBRE", "CVNOMBRE"], "CHNOMBRE(chaîne)", "Convertit une chaîne en nombre"),
    "HEX": (["HEX"], "HEX(entier)", "Représentation hexadécimale d'un entier"),
    "ABS": (["ABS"], "ABS(x)", "Valeur absolue"),
    "ENT": (["ENT", "TRONC", "ENTIER"], "ENT(x)", "Partie entière sans arrondi (troncature)"),
    "DECIMALE": (["DECIMALE"], "DÉCIMALE(x)", "Partie décimale de x"),
    "ARRONDI": (["ARRONDI", "ENTARRONDI"], "ARRONDI(x)", "Arrondi commercial à l'entier le plus proche"),
    "RAC2": (["RAC2", "RACINE"], "RAC2(x)", "Racine carrée d'un nombre positif"),
    "SIN": (["SIN"], "SIN(x)", "Sinus (en radians)"),
    "COS": (["COS"], "COS(x)", "Cosinus (en radians)"),
    "TAN": (["TAN"], "TAN(x)", "Tangente (en radians)"),
    "ATN": (["ATN", "ATAN"], "ATN(x)", "Arc tangente (en radians)"),
    "EXP": (["EXP"], "EXP(x)", "Exponentielle e^x"),
    "LN": (["LN", "LOG"], "LN(x)", "Logarithme népérien"),
    "ALEA": (["ALEA"], "ALEA()", "Nombre réel aléatoire dans [0, 1["),
    "ALEA_ENTIER": (["ALEA_ENTIER", "HASARD"], "ALEA_ENTIER(min, max)", "Entier aléatoire entre min et max inclus"),
    "DATESYST": (["DATESYST"], "DATESYST()", "Date système au format jj/mm/aaaa"),
    "HEURESYST": (["HEURESYST"], "HEURESYST()", "Heure système au format hh:mm:ss"),
    "COLONNE": (["COLONNE", "POS"], "COLONNE()", "Colonne courante du curseur (1..80)"),
    "LIGNE": (["LIGNE"], "LIGNE()", "Ligne courante du curseur (1..24)"),
    "TAB": (["TAB"], "TAB(col)", "Positionne l'affichage à la colonne col"),
    "UNCAR": (["UNCAR"], "UNCAR()", "Lit un caractère au clavier"),
    "UNETOUCHE": (["UNETOUCHE"], "UNETOUCHE()", "Lit une touche pressée (ou chaîne vide)"),
    "FF": (["FF", "FINFICHIER"], "FF(fichier)", "Vrai si la fin du fichier est atteinte"),
    "EXISTE": (["EXISTE", "TROUVE"], "EXISTE(enreg)", "Vrai si l'enregistrement recherché existe"),
    "ERREUR": (["ERREUR", "ERREURCLE", "ERREURCLEF"], "ERREUR(fichier)", "Vrai si la dernière opération fichier a échoué"),
    "ERREUR_SQL": (["ERREUR_SQL"], "ERREUR_SQL()", "Vrai si la dernière requête SQL a produit une erreur"),
}


@dataclass
class HelpEntry:
    id: str
    code: int
    title: str
    category: str
    summary: str
    body: str
    snippet: str = ""
    keyword: str = ""


@dataclass
class KeywordProfile:
    """Profil de mots-clefs (compatible avec la philosophie d'Algpers32)."""

    name: str = "Alg_32 Standard + Omega"
    custom_aliases: Dict[str, str] = field(default_factory=dict)  # alias_norm -> canon_token
    custom_help: Dict[str, str] = field(default_factory=dict)  # keyword -> custom help body

    def build_lookup(self) -> Tuple[Dict[str, str], List[Tuple[List[str], str]]]:
        """Retourne (single_word_map, multi_word_sequences_sorted_longest_first)."""
        single: Dict[str, str] = {}
        multi: List[Tuple[List[str], str]] = []

        for canon, words in STANDARD_KEYWORDS.items():
            for w in words:
                nw = norm_key(w)
                parts = nw.split()
                if len(parts) == 1:
                    single[nw] = canon
                else:
                    multi.append((parts, canon))

        for alias_raw, canon in self.custom_aliases.items():
            nw = norm_key(alias_raw)
            if not nw:
                continue
            parts = nw.split()
            if len(parts) == 1:
                single[nw] = canon
            else:
                multi.append((parts, canon))

        multi.sort(key=lambda item: len(item[0]), reverse=True)
        return single, multi

    def resolve_type(self, word: str) -> Optional[str]:
        nw = norm_key(word)
        for canon, aliases in DATA_TYPES.items():
            if nw in aliases:
                return canon
        return None

    def resolve_builtin(self, word: str) -> Optional[str]:
        nw = norm_key(word)
        for canon, (aliases, _, _) in BUILTIN_FUNCTIONS.items():
            if nw in [norm_key(a) for a in aliases]:
                return canon
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "custom_aliases": self.custom_aliases,
            "custom_help": self.custom_help,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeywordProfile":
        return cls(
            name=data.get("name", "Profil personnalisé"),
            custom_aliases=dict(data.get("custom_aliases", {})),
            custom_help=dict(data.get("custom_help", {})),
        )


class HelpRegistry:
    """Charge et indexe l'aide officielle extraite d'alg_exec.ini."""

    def __init__(self) -> None:
        self.entries: List[HelpEntry] = []
        self._by_norm: Dict[str, HelpEntry] = {}
        self._load_default()

    def _load_default(self) -> None:
        res_path = Path(__file__).resolve().parent.parent / "resources" / "alg32_help.json"
        if not res_path.exists():
            return
        try:
            data = json.loads(res_path.read_text(encoding="utf-8"))
            for item in data.get("entries", []):
                entry = HelpEntry(
                    id=item.get("id", ""),
                    code=int(item.get("code", 0)),
                    title=item.get("title", ""),
                    category=item.get("category", "Général"),
                    summary=item.get("summary", ""),
                    body=item.get("body", ""),
                    snippet=item.get("snippet", ""),
                    keyword=item.get("keyword", ""),
                )
                self.entries.append(entry)
                if entry.keyword:
                    self._by_norm[norm_key(entry.keyword)] = entry
                first_word = entry.title.split("(")[0].split()[0] if entry.title else ""
                if first_word:
                    self._by_norm.setdefault(norm_key(first_word), entry)
        except Exception:
            pass

    def find_for_word(self, word: str) -> Optional[HelpEntry]:
        if not word:
            return None
        nw = norm_key(word)
        if nw in self._by_norm:
            return self._by_norm[nw]
        # Recherche par alias de fonction ou de mot-clef
        for canon, (aliases, _, _) in BUILTIN_FUNCTIONS.items():
            if nw in [norm_key(a) for a in aliases] and canon in self._by_norm:
                return self._by_norm[canon]
        for entry in self.entries:
            if nw in norm_key(entry.title):
                return entry
        return None

    def search(self, query: str) -> List[HelpEntry]:
        q = norm_key(query)
        if not q:
            return list(self.entries)
        results = []
        for e in self.entries:
            hay = norm_key(f"{e.title} {e.summary} {e.category} {e.body}")
            if q in hay:
                results.append(e)
        return results


def import_legacy_alg_exec_ini(path: str | os.PathLike) -> Tuple[KeywordProfile, int]:
    """
    Importe un fichier binaire historique `alg_exec.ini` (220 000 octets, CP1252)
    d'Alg_32 / Algpers32 et extrait les mots-clefs personnalisés éventuels.
    """
    raw = Path(path).read_bytes()
    profile = KeywordProfile(name=f"Import {Path(path).name}")
    # Enregistrements 180..187 : table de 25 octets par entrée (21 car mot + 4 chiffres code)
    code_to_canon = {
        "001": "SAISIR",
        "003": "TANT_QUE",
        "004": "STRUCTURE",
        "005": "JUSQUA",
        "006": "SI",
        "007": "POUR",
        "008": "FIN_STRUCTURE",
        "014": "VALRET",
        "016": "PROCEDURE",
        "017": "FICHIER",
        "019": "FONCTION",
        "020": "TRAITER",
        "023": "CURSEUR",
        "025": "CAS",
        "026": "ITER",
        "028": "SORTIRSI",
        "035": "ENREGISTREMENT",
        "036": "FIN_ENREGISTREMENT",
        "038": "COULEUR",
        "048": "COPIE",
        "049": "FIN_COPIE",
        "050": "OUVRIR",
        "051": "FERMER",
        "052": "ECRIRE",
        "053": "LIRE",
        "054": "REECRIRE",
        "055": "SUPPRIMER",
        "056": "POSITIONNER",
        "058": "TYPE",
        "096": "SELON",
        "098": "AUTRES",
        "102": "AFFICHER",
        "103": "IMPRIMER",
        "104": "REPETER",
        "105": "DEBUT",
        "106": "FIN",
        "108": "FIN_TQ",
        "109": "FIN_SI",
        "110": "ALORS",
        "111": "SINON",
        "112": "FIN_POUR",
        "113": "VAR",
        "114": "CONST",
        "115": "A_LA_LIGNE",
        "120": "EXEC_SQL",
        "121": "FIN_SQL",
        "124": "EFFACE_ECRAN",
        "126": "FIN_SELON",
        "127": "FIN_TYPE",
        "128": "FIN_ITER",
        "198": "ALGO",
    }
    standard_lookup, standard_multi = KeywordProfile().build_lookup()
    known_norms = set(standard_lookup.keys()) | {" ".join(p) for p, _ in standard_multi}
    imported_count = 0

    if len(raw) >= 188 * 1000:
        for rec_idx in range(180, 188):
            chunk = raw[rec_idx * 1000 : (rec_idx + 1) * 1000].decode("cp1252", errors="replace")
            for pos in range(0, len(chunk), 25):
                entry = chunk[pos : pos + 25]
                if len(entry) < 25:
                    continue
                word = entry[:21].strip()
                code3 = entry[21:24]
                if word and code3 in code_to_canon:
                    nw = norm_key(word)
                    if nw and nw not in known_norms and nw.replace("_", "").isalnum():
                        profile.custom_aliases[word] = code_to_canon[code3]
                        imported_count += 1
    return profile, imported_count


def read_alg_file_smart(path: str | os.PathLike) -> str:
    """
    Lit un fichier .alg en détectant intelligemment l'encodage UTF-8 ou CP1252/Latin-1
    (pour ouvrir sans erreur les anciens algorithmes créés sous Alg_32 en 1997-2003).
    """
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            return text.replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
