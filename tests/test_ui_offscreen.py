"""Tests d'intégration de l'interface PyQt6 en mode offscreen."""

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from omega_studio.ui.appearance_studio import AppearanceStudioDialog
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


def test_appearance_studio_gradients_images_and_animations() -> None:
    app = QApplication.instance() or QApplication([])
    win = OmegaMainWindow()
    win.resize(1280, 800)
    win.show()
    app.processEvents()

    # Applique un préréglage de dégradé & mélange de couleurs
    win.apply_gradient_preset("cyber_neon")
    assert win.appearance.custom_colors_enabled is True
    assert win.theme.id == "custom_mixed"

    # Ouvre le Studio Visuel, ajoute plusieurs fonds, teste le diaporama et le mélange aléatoire
    dlg = AppearanceStudioDialog(win.appearance, win.theme, win.backdrop, win)
    dlg.appearanceChanged.connect(win._on_live_appearance_updated)
    dlg.show()
    app.processEvents()

    dlg._add_builtin_wallpapers()
    assert len(win.appearance.background_images) == 4
    win.backdrop.next_image()
    win.backdrop._on_anim_tick()
    app.processEvents()
    assert win.appearance.active_image_index == 1

    dlg._randomize_harmony()
    app.processEvents()
    assert win.appearance.custom_colors_enabled is True

    dlg.close()
    win.close()
