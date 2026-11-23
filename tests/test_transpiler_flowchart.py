"""Tests du transpileur multi-langages (Python, C, JS, Pascal) et du générateur d'organigrammes."""

import subprocess
import sys
from pathlib import Path

from omega_studio.core.flowchart import FlowchartBuilder
from omega_studio.core.parser import parse_source
from omega_studio.core.transpiler import MultiTranspiler


def test_transpile_to_all_four_languages() -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "04_tri_bulles_et_dichotomie.alg"
    prog = parse_source(ex.read_text(encoding="utf-8"))
    tr = MultiTranspiler(prog)

    py_code = tr.transpile("python")
    c_code = tr.transpile("c")
    js_code = tr.transpile("javascript")
    pas_code = tr.transpile("pascal")

    assert "def trier_bulles(" in py_code
    assert "int main(void)" in c_code
    assert "function trier_bulles(" in js_code
    assert "procedure trier_bulles(" in pas_code

    # Vérifie que le code Python généré s'exécute réellement et donne le bon résultat !
    proc = subprocess.run([sys.executable, "-c", py_code], capture_output=True, text=True, check=True)
    assert "Valeur 23 trouvée à l'indice 5" in proc.stdout


def test_flowchart_builder_generates_nodes_and_edges() -> None:
    ex = Path(__file__).resolve().parent.parent / "examples" / "02_facture_tva_conditions.alg"
    prog = parse_source(ex.read_text(encoding="utf-8"))
    graph = FlowchartBuilder().build_for_program(prog)
    assert len(graph.nodes) >= 8
    assert len(graph.edges) >= 8
    shapes = {n.shape for n in graph.nodes}
    assert "TERMINAL" in shapes
    assert "DECISION" in shapes
    assert "IO" in shapes
    assert "PROCESS" in shapes
