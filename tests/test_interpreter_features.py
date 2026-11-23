"""Tests complets de l'interpréteur Pas-à-Pas Alg_32 (boucles, tableaux, récursivité, fichiers, SQL)."""

from pathlib import Path
from typing import List

from omega_studio.core.interpreter import AlgInterpreter
from omega_studio.core.parser import parse_source


def _run_to_output(source: str, inputs: List[str] | None = None, working_dir: str | None = None) -> str:
    prog = parse_source(source)
    interp = AlgInterpreter(prog, working_dir=working_dir)
    gen = interp.run_generator()
    in_iter = iter(inputs or [])
    out_parts: List[str] = []

    ev = next(gen)
    while True:
        if ev.kind == "OUTPUT":
            out_parts.append(ev.text + ("\n" if ev.newline else ""))
        elif ev.kind == "ERROR":
            raise AssertionError(f"Erreur d'exécution L{ev.line}: {ev.text}")
        elif ev.kind == "FINISHED":
            break

        try:
            if ev.kind == "INPUT_REQUEST":
                ev = gen.send(next(in_iter))
            else:
                ev = next(gen)
        except StopIteration:
            break

    return "".join(out_parts)


def test_saisir_conditions_and_math() -> None:
    src = """
    ALGO test_io
    VAR
        n : entier
    DEBUT
        SAISIR "Valeur ? ", n
        SI n MOD 2 = 0 ALORS
            AFFICHER "PAIR:", RAC2(16)
        SINON
            AFFICHER "IMPAIR"
        FINSI
    FIN
    """
    out = _run_to_output(src, inputs=["8"])
    assert "PAIR:4" in out


def test_bubble_sort_and_binary_search_example() -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "04_tri_bulles_et_dichotomie.alg"
    out = _run_to_output(ex.read_text(encoding="utf-8"))
    assert "[4] [8] [15] [19] [23] [42] [67] [91]" in out
    assert "Valeur 23 trouvée à l'indice 5" in out


def test_recursion_factorial_and_fibonacci() -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "05_recursivite_factorielle_fibo.alg"
    out = _run_to_output(ex.read_text(encoding="utf-8"))
    assert "7! = 5040" in out
    assert "0 1 1 2 3 5 8 13 21 34 55" in out


def test_procedures_in_out_inout() -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "07_procedures_parametres_es.alg"
    out = _run_to_output(ex.read_text(encoding="utf-8"))
    assert "Après échange : x = 6, y = 47" in out
    assert "quotient = 7, reste = 5" in out


def test_string_functions_alg32() -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "09_chaines_palindrome_cesar.alg"
    out = _run_to_output(ex.read_text(encoding="utf-8"))
    assert "C'est un palindrome !" in out
    assert "UDGDU" in out


def test_sequential_file_operations(tmp_path: Path) -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "11_fichiers_clients.alg"
    out = _run_to_output(ex.read_text(encoding="utf-8"), working_dir=str(tmp_path))
    assert "#101 - Soglo Nadia" in out
    assert "#102 - Kouassi Marc" in out


def test_embedded_sqlite_exec_sql(tmp_path: Path) -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "12_base_sql_etudiants.alg"
    out = _run_to_output(ex.read_text(encoding="utf-8"), working_dir=str(tmp_path))
    assert "Nombre d'étudiants >= 10 : 3" in out
    assert "14.1" in out
