"""Tests d'intégration de l'interface PyQt6 en mode offscreen."""

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from omega_studio.ui.main_window import OmegaMainWindow


def test_main_window_workflows_offscreen(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    ex = Path(__file__).resolve().parent.parent / "examples" / "04_tri_bulles_et_dichotomie.alg"
    win = OmegaMainWindow(initial_file=str(ex))
    win.show()
    app.processEvents()

    # 1. Vérification statique
    assert win.run_verification() is True

    # 2. Mode Pas-à-Pas (plusieurs étapes)
    win.step_into()
    win.step_over()
    win.step_over()
    app.processEvents()
    assert win._exec_mode == "STEP_PAUSE"
    assert win.debugger_panel.var_tree.topLevelItemCount() >= 1

    # 3. Export PNG de l'organigramme
    out_png = tmp_path / "organigramme_test.png"
    assert win.flowchart_widget.save_png_to_path(str(out_png)) is True
    assert out_png.exists() and out_png.stat().st_size > 1000

    # 4. Changement de thème (Clair Académique -> Omarchy TokyoNight)
    win.apply_theme("academic_light")
    app.processEvents()
    win.apply_theme("omarchy_tokyonight")
    app.processEvents()

    win.stop_execution()
    win.close()
