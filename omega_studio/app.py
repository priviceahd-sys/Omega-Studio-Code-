"""
Initialisation de QApplication optimisée pour Omarchy (Arch Linux + Hyprland / Wayland)
et l'affichage haute densité (HiDPI).
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

from . import __app_name__, __version__


def configure_platform_environment() -> None:
    """
    Configure automatiquement Qt6 :
    - Sur Linux / Omarchy : rendu natif Wayland / Hyprland (repli X11/XWayland)
    - Sur Windows 10/11 : identifiant AppUserModelID pour l'icône de barre des tâches
    """
    if sys.platform.startswith("linux") and "QT_QPA_PLATFORM" not in os.environ:
        if os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    elif sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OmegaCodeStudio.IDE.2.0")
        except Exception:
            pass
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


def run_app(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv if argv is None else argv)

    if any(flag in args[1:] for flag in ("--version", "-v")):
        print(f"{__app_name__} v{__version__}")
        return 0

    if any(flag in args[1:] for flag in ("--help", "-h")):
        print(f"{__app_name__} v{__version__} — IDE Algorithmique Moderne (Alg_32)")
        print("Utilisation : omega-code-studio [fichier.alg]")
        return 0

    configure_platform_environment()

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from pathlib import Path
    from PyQt6.QtGui import QIcon
    from .ui.main_window import OmegaMainWindow

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    desktop_id = os.environ.get("OMEGA_DESKTOP_ID", "omega-code-studio")
    app = QApplication(args)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setDesktopFileName(desktop_id)
    app.setApplicationVersion(__version__)

    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    icon_candidates = (
        [assets_dir / "omega-code-studio.ico", assets_dir / "omega-studio-code.svg"]
        if sys.platform == "win32"
        else [assets_dir / "omega-studio-code.svg", assets_dir / "omega-code-studio.ico"]
    )
    for icon_file in icon_candidates:
        if icon_file.exists():
            app.setWindowIcon(QIcon(str(icon_file)))
            break

    initial_file = args[1] if len(args) > 1 and not args[1].startswith("-") else None
    win = OmegaMainWindow(initial_file=initial_file)
    win.show()
    return app.exec()
