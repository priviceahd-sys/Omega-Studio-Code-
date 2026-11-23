"""
Panneau de traduction automatique d'algorithmes (Algo -> Python 3, C, JavaScript, Pascal).
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.ast_nodes import Program
from ..core.keywords import KeywordProfile
from ..core.transpiler import MultiTranspiler
from .code_editor import pick_monospace_font
from .themes import StudioTheme


class TranspilerPanel(QWidget):
    """Panneau de conversion multi-langages en direct."""

    def __init__(
        self,
        theme: StudioTheme,
        profile: KeywordProfile,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.profile = profile
        self._program: Optional[Program] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Python 3 (.py)", "python")
        self.lang_combo.addItem("Langage C — C11 (.c)", "c")
        self.lang_combo.addItem("JavaScript ES6 (.js)", "javascript")
        self.lang_combo.addItem("Pascal / FreePascal (.pas)", "pascal")

        self.btn_copy = QPushButton("Copier")
        self.btn_export = QPushButton("Exporter...")

        bar.addWidget(QLabel("Cible :"))
        bar.addWidget(self.lang_combo, 1)
        bar.addWidget(self.btn_copy)
        bar.addWidget(self.btn_export)

        self.code_view = QPlainTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFont(pick_monospace_font(10))

        layout.addLayout(bar)
        layout.addWidget(self.code_view, 1)

        self.lang_combo.currentIndexChanged.connect(self.refresh_translation)
        self.btn_copy.clicked.connect(self._copy_code)
        self.btn_export.clicked.connect(self._export_code)

        self.apply_theme(theme)

    def apply_theme(self, theme: StudioTheme) -> None:
        self.theme = theme
        self.code_view.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {theme.bg_editor};
                color: {theme.fg_primary};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px;
            }}
            """
        )

    def set_program(self, program: Optional[Program], profile: Optional[KeywordProfile] = None) -> None:
        self._program = program
        if profile is not None:
            self.profile = profile
        self.refresh_translation()

    def refresh_translation(self) -> None:
        if self._program is None:
            self.code_view.setPlainText("# Corrigez les éventuelles erreurs de syntaxe pour générer le code cible.")
            return
        target = self.lang_combo.currentData() or "python"
        try:
            transpiler = MultiTranspiler(self._program, profile=self.profile)
            code = transpiler.transpile(target)
            self.code_view.setPlainText(code)
        except Exception as exc:
            self.code_view.setPlainText(f"# Erreur de traduction : {exc}")

    def _copy_code(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.code_view.toPlainText())

    def _export_code(self) -> None:
        target = self.lang_combo.currentData() or "python"
        ext_map = {
            "python": ("Python (*.py)", "algorithme.py"),
            "c": ("Source C (*.c)", "algorithme.c"),
            "javascript": ("JavaScript (*.js)", "algorithme.js"),
            "pascal": ("Pascal (*.pas)", "algorithme.pas"),
        }
        flt, default_name = ext_map.get(target, ("Tous (*.*)", "code.txt"))
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le code traduit", default_name, flt)
        if path:
            from pathlib import Path

            Path(path).write_text(self.code_view.toPlainText(), encoding="utf-8")
