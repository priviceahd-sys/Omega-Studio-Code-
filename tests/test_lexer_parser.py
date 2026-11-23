"""Tests unitaires complets du Lexer, Parser, Vérificateur et Formateur Alg_32."""

from pathlib import Path

from omega_studio.core.keywords import KeywordProfile
from omega_studio.core.parser import parse_source
from omega_studio.core.verifier import format_algorithm_source, verify_source


def test_all_builtin_examples_verify_cleanly() -> None:
    examples_dir = Path(__file__).resolve().parent.parent / "examples"
    alg_files = sorted(examples_dir.glob("*.alg"))
    assert len(alg_files) == 12
    for alg_path in alg_files:
        src = alg_path.read_text(encoding="utf-8")
        rep = verify_source(src)
        assert rep.ok, f"Échec de vérification sur {alg_path.name}: {rep.diagnostics}"


def test_undeclared_variable_suggestion() -> None:
    src = """
    ALGO test_faute
    VAR
        montant_ht : réel
    DEBUT
        montnt_ht := 100
    FIN
    """
    rep = verify_source(src)
    assert not rep.ok
    assert any("MONTANT_HT" in d.message for d in rep.diagnostics)


def test_custom_algpers32_keyword_alias() -> None:
    profile = KeywordProfile(name="Perso", custom_aliases={"MONTRER": "AFFICHER"})
    src = """
    ALGO perso_test
    DEBUT
        MONTRER "Bonjour Algpers32 !"
    FIN
    """
    rep = verify_source(src, profile=profile)
    assert rep.ok
    prog = parse_source(src, profile=profile)
    assert len(prog.body) == 1


def test_formatter_indents_and_uppercases_keywords() -> None:
    messy = (
        "algo essai\n"
        "var\n"
        "x : entier\n"
        "debut\n"
        "si x > 0 alors\n"
        'afficher "positif"\n'
        "finsi\n"
        "fin\n"
    )
    formatted = format_algorithm_source(messy, uppercase_keywords=True)
    assert "ALGO essai" in formatted
    assert "    SI x > 0 ALORS" in formatted
    assert '        AFFICHER "positif"' in formatted
    assert '"positif"' in formatted  # ne met pas en majuscules l'intérieur des chaînes !
