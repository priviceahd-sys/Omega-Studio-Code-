"""
Initialisation de QApplication optimisée pour Omarchy (Arch Linux + Hyprland / Wayland)
et l'affichage haute densité (HiDPI).
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

from . import __app_name__, __version__


def configure_wayland_environment() -> None:
    """
    Configure automatiquement Qt6 pour un rendu natif net sur Wayland / Hyprland (Omarchy),
    avec repli transparent sur X11/XWayland si nécessaire.
    """
    if sys.platform.startswith("linux") and "QT_QPA_PLATFORM" not in os.environ:
        if os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
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

    configure_wayland_environment()

    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from .ui.main_window import OmegaMainWindow

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(args)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setDesktopFileName("omega-code-studio")
    app.setApplicationVersion(__version__)

    initial_file = args[1] if len(args) > 1 and not args[1].startswith("-") else None
    win = OmegaMainWindow(initial_file=initial_file)
    win.show()
    return app.exec()
