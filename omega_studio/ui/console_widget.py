"""
Console d'exécution interactive Alg_32 / Omega Studio Code.
Gère les 16 couleurs historiques VGA d'Alg_32 (codes 0 à 15 de COULEUR encre, fond),
EFFACE_ECRAN, CURSEUR, et une barre de saisie clavier fluide en direct pour SAISIR.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .code_editor import pick_monospace_font
from .themes import StudioTheme, qss_rgba

# Palette officielle des codes COULEUR 0..15 d'Alg_32 (alg_exec.ini enregistrement 037)
VGA_PALETTE: Dict[int, str] = {
    0: "#15161e",   # 0 = noir
    1: "#1d4ed8",   # 1 = bleu
    2: "#15803d",   # 2 = vert
    3: "#0e7490",   # 3 = cyan
    4: "#b91c1c",   # 4 = rouge
    5: "#7e22ce",   # 5 = violet
    6: "#92400e",   # 6 = marron
    7: "#cbd5e1",   # 7 = blanc standard
    8: "#64748b",   # 8 = gris
    9: "#60a5fa",   # 9 = bleu clair
    10: "#4ade80",  # 10 = vert clair
    11: "#22d3ee",  # 11 = cyan clair
    12: "#f87171",  # 12 = rouge clair
    13: "#c084fc",  # 13 = violet clair
    14: "#facc15",  # 14 = jaune
    15: "#ffffff",  # 15 = blanc brillant
}


class HistoryLineEdit(QLineEdit):
    """Champ de saisie avec historique des entrées précédentes (Flèches Haut/Bas)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.history: List[str] = []
        self._hist_idx: int = -1

    def record_entry(self, text: str) -> None:
        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self._hist_idx = len(self.history)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up and self.history:
            self._hist_idx = max(0, self._hist_idx - 1)
            self.setText(self.history[self._hist_idx])
            return
        if event.key() == Qt.Key.Key_Down and self.history:
            self._hist_idx = min(len(self.history), self._hist_idx + 1)
            self.setText(self.history[self._hist_idx] if self._hist_idx < len(self.history) else "")
            return
        super().keyPressEvent(event)


class ExecutionConsole(QWidget):
    """Écran d'exécution interactif moderne compatible Alg_32."""

    inputSubmitted = pyqtSignal(str)

    def __init__(self, theme: StudioTheme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.fg_code: Optional[int] = None
        self.bg_code: Optional[int] = None
        self._waiting_input = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barre d'état supérieure de la console
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 4, 10, 4)
        h_layout.setSpacing(8)

        self.status_badge = QLabel("● Prêt")
        self.cursor_label = QLabel("Curseur : L1, C1")
        self.btn_clear = QPushButton("Effacer l'écran")
        self.btn_copy = QPushButton("Copier la sortie")

        h_layout.addWidget(self.status_badge)
        h_layout.addStretch(1)
        h_layout.addWidget(self.cursor_label)
        h_layout.addWidget(self.btn_copy)
        h_layout.addWidget(self.btn_clear)

        # Zone d'affichage terminal
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(pick_monospace_font(11))

        # Barre de saisie clavier interactive (affichée/activée lors d'un SAISIR)
        self.input_container = QWidget()
        in_layout = QHBoxLayout(self.input_container)
        in_layout.setContentsMargins(10, 6, 10, 6)
        in_layout.setSpacing(8)

        self.prompt_label = QLabel("⌨ Saisie attendue :")
        self.input_edit = HistoryLineEdit()
        self.input_edit.setFont(pick_monospace_font(11))
        self.input_edit.setPlaceholderText("Entrez une valeur puis appuyez sur Entrée...")
        self.btn_send = QPushButton("Valider (Entrée)")
        self.btn_send.setProperty("primary", True)

        in_layout.addWidget(self.prompt_label)
        in_layout.addWidget(self.input_edit, 1)
        in_layout.addWidget(self.btn_send)

        layout.addWidget(header)
        layout.addWidget(self.output, 1)
        layout.addWidget(self.input_container)

        self.btn_clear.clicked.connect(self.clear_console)
        self.btn_copy.clicked.connect(self._copy_all)
        self.input_edit.returnPressed.connect(self._submit_input)
        self.btn_send.clicked.connect(self._submit_input)

        self.set_waiting_input(False)
        self.apply_theme(theme)

    def apply_theme(self, theme: StudioTheme, glass_alpha_pct: int = 100) -> None:
        self.theme = theme
        self._glass_alpha_pct = glass_alpha_pct
        if self.bg_code is not None:
            bg_hex = VGA_PALETTE[self.bg_code]
        else:
            bg_hex = qss_rgba(theme.bg_editor, glass_alpha_pct) if glass_alpha_pct < 100 else theme.bg_editor
        fg_hex = VGA_PALETTE[self.fg_code] if self.fg_code is not None else theme.fg_primary
        elev_bg = qss_rgba(theme.bg_elevated, min(100, glass_alpha_pct + 6)) if glass_alpha_pct < 100 else theme.bg_elevated
        self.output.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {bg_hex};
                color: {fg_hex};
                border: none;
                border-top: 1px solid {theme.border};
                padding: 8px;
            }}
            """
        )
        self.input_container.setStyleSheet(
            f"background-color: {elev_bg}; border-top: 1px solid {theme.border};"
        )

    def set_status(self, label: str, color_hex: str) -> None:
        self.status_badge.setText(f"● {label}")
        self.status_badge.setStyleSheet(f"color: {color_hex}; font-weight: 700;")

    def clear_console(self) -> None:
        self.fg_code = None
        self.bg_code = None
        self.output.clear()
        self.cursor_label.setText("Curseur : L1, C1")
        self.apply_theme(self.theme, getattr(self, "_glass_alpha_pct", 100))

    def _copy_all(self) -> None:
        from PyQt6.QtWidgets import QApplication

        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.output.toPlainText())

    def set_vga_colors(self, fg: int, bg: int) -> None:
        self.fg_code = fg
        self.bg_code = bg
        self.apply_theme(self.theme)

    def set_cursor_position(self, line: int, col: int) -> None:
        self.cursor_label.setText(f"Curseur : L{line}, C{col}")
        # Assure au moins `line` lignes dans la console pour simuler fidèlement CURSEUR l, c
        doc_lines = self.output.document().blockCount()
        if line > doc_lines:
            c = self.output.textCursor()
            c.movePosition(QTextCursor.MoveOperation.End)
            c.insertText("\n" * (line - doc_lines))
        blk = self.output.document().findBlockByNumber(line - 1)
        if blk.isValid():
            cur_len = len(blk.text())
            c = QTextCursor(blk)
            if col - 1 > cur_len:
                c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                c.insertText(" " * (col - 1 - cur_len))
            else:
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, max(0, col - 1))
            self.output.setTextCursor(c)

    def append_text(self, text: str, newline: bool = True, color_override: Optional[str] = None) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        if color_override:
            fmt.setForeground(QColor(color_override))
        elif self.fg_code is not None:
            fmt.setForeground(QColor(VGA_PALETTE.get(self.fg_code, self.theme.fg_primary)))
        else:
            fmt.setForeground(QColor(self.theme.fg_primary))

        if self.bg_code is not None:
            fmt.setBackground(QColor(VGA_PALETTE.get(self.bg_code, self.theme.bg_editor)))

        cursor.insertText(text + ("\n" if newline else ""), fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def set_waiting_input(self, waiting: bool, prompt: str = "", target_name: str = "", target_type: str = "") -> None:
        self._waiting_input = waiting
        self.input_edit.setEnabled(waiting)
        self.btn_send.setEnabled(waiting)
        if waiting:
            type_badge = f" [{target_type.lower()}]" if target_type and target_type != "AUTO" else ""
            self.prompt_label.setText(f"▶ SAISIR {target_name}{type_badge} :")
            self.prompt_label.setStyleSheet(f"color: {self.theme.warning}; font-weight: 700;")
            self.input_edit.clear()
            self.input_edit.setFocus()
            self.set_status(f"En attente de saisie ({target_name})", self.theme.warning)
        else:
            self.prompt_label.setText("Clavier inactif :")
            self.prompt_label.setStyleSheet(f"color: {self.theme.fg_muted};")

    def _submit_input(self) -> None:
        if not self._waiting_input:
            return
        val = self.input_edit.text()
        self.input_edit.record_entry(val)
        # Écho visuel de la saisie dans le terminal
        self.append_text(val, newline=True, color_override=self.theme.accent)
        self.set_waiting_input(False)
        self.inputSubmitted.emit(val)
