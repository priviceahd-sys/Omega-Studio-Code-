"""
Éditeur de code multi-onglets Omega Studio Code :
- Coloration syntaxique complète Alg_32 (mots-clefs, types, fonctions, chaînes, commentaires)
- Marge de numéros de lignes avec points d'arrêt cliquables (●) et flèche Pas-à-Pas (▶)
- Surlignage de la ligne courante, de la ligne d'exécution Pas-à-Pas et des erreurs
- Auto-indentation intelligente et auto-complétion contextuelle (Ctrl+Espace)
- Barre de Recherche & Remplacement intégrée (Ctrl+F / Ctrl+H)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import QRect, QSize, QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPolygon,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.keywords import BUILTIN_FUNCTIONS, DATA_TYPES, STANDARD_KEYWORDS, KeywordProfile
from .themes import StudioTheme, qss_rgba


def pick_monospace_font(point_size: int = 11) -> QFont:
    """Sélectionne la meilleure police monospace installée (idéal sur Omarchy : JetBrainsMono / CaskaydiaMono / FiraCode)."""
    preferred = [
        "JetBrainsMono Nerd Font",
        "JetBrains Mono",
        "CaskaydiaMono Nerd Font",
        "Cascadia Code",
        "Cascadia Mono",
        "Consolas",
        "Fira Code",
        "Hack",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Monospace",
    ]
    available = set(QFontDatabase.families())
    for fam in preferred:
        if fam in available:
            f = QFont(fam, point_size)
            f.setStyleHint(QFont.StyleHint.Monospace)
            return f
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    f.setPointSize(point_size)
    return f


class AlgSyntaxHighlighter(QSyntaxHighlighter):
    """Coloration syntaxique riche pour le langage Alg_32 / Omega Studio Code."""

    def __init__(self, document: QTextDocument, theme: StudioTheme, profile: Optional[KeywordProfile] = None) -> None:
        super().__init__(document)
        self.theme = theme
        self.profile = profile or KeywordProfile()
        self._rules: List[tuple[re.Pattern[str], QTextCharFormat]] = []
        self._comment_fmt = QTextCharFormat()
        self._build_rules()

    def set_theme_and_profile(self, theme: StudioTheme, profile: Optional[KeywordProfile] = None) -> None:
        self.theme = theme
        if profile is not None:
            self.profile = profile
        self._build_rules()
        self.rehighlight()

    def _build_rules(self) -> None:
        t = self.theme
        self._rules = []

        def fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
            cf = QTextCharFormat()
            cf.setForeground(QColor(color))
            if bold:
                cf.setFontWeight(QFont.Weight.Bold)
            if italic:
                cf.setFontItalic(True)
            return cf

        kw_decl_fmt = fmt(t.syn_keyword, bold=True)
        kw_ctrl_fmt = fmt(t.syn_control, bold=True)
        type_fmt = fmt(t.syn_type, italic=True)
        builtin_fmt = fmt(t.syn_builtin)
        num_fmt = fmt(t.syn_number)
        bool_fmt = fmt(t.syn_number, bold=True)
        op_fmt = fmt(t.syn_operator, bold=True)
        str_fmt = fmt(t.syn_string)
        self._comment_fmt = fmt(t.syn_comment, italic=True)

        decl_groups = {
            "ALGO",
            "DEBUT",
            "FIN",
            "FIN_PROC",
            "FIN_FONC",
            "CONST",
            "VAR",
            "GLOBALE",
            "TYPE",
            "FIN_TYPE",
            "STRUCTURE",
            "FIN_STRUCTURE",
            "FICHIER",
            "ENREGISTREMENT",
            "FIN_ENREGISTREMENT",
            "PROCEDURE",
            "FONCTION",
            "VALRET",
            "EXEC_SQL",
            "FIN_SQL",
        }

        decl_words: List[str] = []
        ctrl_words: List[str] = []
        for canon, words in STANDARD_KEYWORDS.items():
            target_list = decl_words if canon in decl_groups else ctrl_words
            target_list.extend(words)
            # Ajoute aussi les variantes accentuées courantes
            for w in words:
                if "E" in w or "A" in w:
                    target_list.append(
                        w.replace("DEBUT", "DÉBUT")
                        .replace("PROCEDURE", "PROCÉDURE")
                        .replace("REPETER", "RÉPÉTER")
                        .replace("JUSQU'A", "JUSQU'À")
                        .replace("A_LA_LIGNE", "À_LA_LIGNE")
                        .replace("EFFACE_ECRAN", "EFFACE_ÉCRAN")
                        .replace("ECRIRE", "ÉCRIRE")
                        .replace("REECRIRE", "RÉÉCRIRE")
                        .replace("DELIVRE", "DÉLIVRE")
                        .replace("DONNEE", "DONNÉE")
                        .replace("RESULTAT", "RÉSULTAT")
                    )

        for alias, canon in self.profile.custom_aliases.items():
            (decl_words if canon in decl_groups else ctrl_words).append(alias)

        def compile_word_list(words: List[str]) -> re.Pattern[str]:
            escaped = sorted({re.escape(w) for w in words if w.strip()}, key=len, reverse=True)
            pattern = r"(?<![A-Za-z0-9_À-ÿ])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9_À-ÿ])"
            return re.compile(pattern, re.IGNORECASE)

        if decl_words:
            self._rules.append((compile_word_list(decl_words), kw_decl_fmt))
        if ctrl_words:
            self._rules.append((compile_word_list(ctrl_words), kw_ctrl_fmt))

        type_words = [
            "entier",
            "entiers",
            "ent",
            "réel",
            "réels",
            "reel",
            "reels",
            "décimal",
            "decimal",
            "chaîne",
            "chaînes",
            "chaine",
            "chaines",
            "car",
            "caractère",
            "caractères",
            "caractere",
            "booléen",
            "booléens",
            "booleen",
            "bool",
            "tableau",
            "tableaux",
        ]
        self._rules.append((compile_word_list(type_words), type_fmt))

        fn_words = [alias for _, (aliases, _, _) in BUILTIN_FUNCTIONS.items() for alias in aliases] + [
            "DÉCIMALE",
            "RÉPÈTECAR",
            "ALÉA",
            "CVCHAÎNE",
            "SSCHAÎNE",
            "TROUVÉ",
        ]
        fn_escaped = sorted({re.escape(w) for w in fn_words}, key=len, reverse=True)
        self._rules.append(
            (
                re.compile(r"(?<![A-Za-z0-9_À-ÿ])(?:" + "|".join(fn_escaped) + r")(?=\s*\()", re.IGNORECASE),
                builtin_fmt,
            )
        )

        # Booléens et nombres
        self._rules.append((re.compile(r"\.(?:VRAI|FAUX)\.|(?<![A-Za-z0-9_])(?:VRAI|FAUX)(?![A-Za-z0-9_])", re.IGNORECASE), bool_fmt))
        self._rules.append((re.compile(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), num_fmt))
        self._rules.append((re.compile(r":=|<--|<-|←|<>|<=|>="), op_fmt))
        self._rules.append((re.compile(r'"(?:""|\\.|[^"\\])*"'), str_fmt))

    def highlightBlock(self, text: Optional[str]) -> None:
        if text is None:
            return

        for pattern, char_fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), char_fmt)

        # Commentaires de ligne (' ou //) hors chaînes et hors élisions d' / jusqu'a / c'est
        in_str = False
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == '"':
                in_str = not in_str
                i += 1
                continue
            if not in_str:
                if ch == "/" and i + 1 < n and text[i + 1] == "/":
                    self.setFormat(i, n - i, self._comment_fmt)
                    break
                if ch in ("'", "’"):
                    prev_word = text[:i].rstrip()
                    tail_alpha = re.search(r"([A-Za-zÀ-ÿ]+)$", text[:i])
                    elision = tail_alpha and tail_alpha.group(1).upper() in ("D", "JUSQU", "C", "L", "QU", "N", "S")
                    if not elision or not prev_word or text[i - 1].isspace():
                        self.setFormat(i, n - i, self._comment_fmt)
                        break
            i += 1

        # Commentaires multi-lignes /* ... */ (état 1)
        self.setCurrentBlockState(0)
        start_idx = 0
        if self.previousBlockState() != 1:
            start_idx = text.find("/*")
        while start_idx >= 0:
            end_idx = text.find("*/", start_idx + 2)
            if end_idx == -1:
                self.setCurrentBlockState(1)
                length = len(text) - start_idx
            else:
                length = end_idx - start_idx + 2
            self.setFormat(start_idx, length, self._comment_fmt)
            start_idx = text.find("/*", start_idx + length)


class LineNumberArea(QWidget):
    """Marge latérale affichant les numéros de lignes, les points d'arrêt (●) et le pointeur Pas-à-Pas (▶)."""

    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Cliquez sur un numéro de ligne pour poser/retirer un point d'arrêt (F9)")

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            line = self.editor.line_at_y(int(event.position().y()))
            if line >= 1:
                self.editor.toggle_breakpoint(line)


class CodeEditor(QPlainTextEdit):
    """Éditeur algorithmique enrichi pour Omega Studio Code."""

    helpRequested = pyqtSignal(str)
    breakpointsChanged = pyqtSignal()
    cursorPosChangedInfo = pyqtSignal(int, int)

    def __init__(
        self,
        theme: StudioTheme,
        profile: Optional[KeywordProfile] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.profile = profile or KeywordProfile()
        self.file_path: Optional[Path] = None
        self.breakpoints: Set[int] = set()
        self.debug_line: Optional[int] = None
        self.error_lines: Dict[int, str] = {}
        self.glass_alpha_pct: int = 100
        self._pulse_phase: float = 0.0

        from PyQt6.QtCore import QTimer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(50)
        self._pulse_timer.timeout.connect(self._on_debug_pulse_tick)

        self.setFont(pick_monospace_font(11))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.line_number_area = LineNumberArea(self)
        self.highlighter = AlgSyntaxHighlighter(self.document(), self.theme, self.profile)

        # Auto-complétion
        self._completer_model = QStringListModel(self._build_completion_words(), self)
        self.completer = QCompleter(self._completer_model, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_changed)

        self._apply_editor_colors()
        self._update_line_number_area_width(0)
        self._refresh_extra_selections()

    def _build_completion_words(self) -> List[str]:
        words = set()
        for wlist in STANDARD_KEYWORDS.values():
            for w in wlist:
                words.add(w.upper())
        for wlist in DATA_TYPES.values():
            for w in wlist:
                words.add(w.lower())
        for _, (aliases, sig, _) in BUILTIN_FUNCTIONS.items():
            for a in aliases:
                words.add(a.upper() + "(")
        # Mots déjà présents dans le document
        doc_words = re.findall(r"[A-Za-z_À-ÿ][A-Za-z0-9_À-ÿ]{2,}", self.toPlainText())
        words.update(doc_words)
        return sorted(words)

    def _apply_editor_colors(self) -> None:
        t = self.theme
        bg_val = qss_rgba(t.bg_editor, self.glass_alpha_pct) if self.glass_alpha_pct < 100 else t.bg_editor
        self.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {bg_val};
                color: {t.fg_primary};
                border: none;
                selection-background-color: {t.bg_selection};
                selection-color: {t.fg_primary};
            }}
            """
        )

    def set_theme_and_profile(
        self,
        theme: StudioTheme,
        profile: Optional[KeywordProfile] = None,
        glass_alpha_pct: int = 100,
    ) -> None:
        self.theme = theme
        self.glass_alpha_pct = glass_alpha_pct
        if profile is not None:
            self.profile = profile
        self._apply_editor_colors()
        self.highlighter.set_theme_and_profile(theme, self.profile)
        self._refresh_extra_selections()
        self.line_number_area.update()

    def line_number_area_width(self) -> int:
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 26 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_at_y(self, y: int) -> int:
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= y:
            if block.isVisible() and bottom >= y:
                return block.blockNumber() + 1
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
        return -1

    def toggle_breakpoint(self, line: Optional[int] = None) -> None:
        if line is None:
            line = self.textCursor().blockNumber() + 1
        if line in self.breakpoints:
            self.breakpoints.remove(line)
        else:
            self.breakpoints.add(line)
        self.line_number_area.update()
        self.breakpointsChanged.emit()

    def set_debug_line(self, line: Optional[int], animate_pulse: bool = True) -> None:
        self.debug_line = line
        if line is not None and line >= 1:
            self.goto_line(line, focus=False)
            if animate_pulse and not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
        self._refresh_extra_selections()
        self.line_number_area.update()

    def _on_debug_pulse_tick(self) -> None:
        if self.debug_line is None:
            self._pulse_timer.stop()
            return
        import math
        self._pulse_phase = (self._pulse_phase + 0.22) % (math.pi * 2.0)
        self._refresh_extra_selections()

    def set_error_lines(self, errors: Dict[int, str]) -> None:
        self.error_lines = dict(errors)
        self._refresh_extra_selections()
        self.line_number_area.update()

    def goto_line(self, line: int, col: int = 1, focus: bool = True) -> None:
        block = self.document().findBlockByNumber(max(0, line - 1))
        if block.isValid():
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, max(0, col - 1))
            self.setTextCursor(cursor)
            self.centerCursor()
            if focus:
                self.setFocus()

    def _on_cursor_changed(self) -> None:
        c = self.textCursor()
        self.cursorPosChangedInfo.emit(c.blockNumber() + 1, c.columnNumber() + 1)
        self._refresh_extra_selections()

    def _refresh_extra_selections(self) -> None:
        selections: List[QTextEdit.ExtraSelection] = []
        t = self.theme

        # 1. Ligne courante
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(t.line_current))
            sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)

        # 2. Lignes en erreur
        for eline in self.error_lines:
            blk = self.document().findBlockByNumber(eline - 1)
            if blk.isValid():
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(QColor(t.line_error))
                sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                sel.cursor = QTextCursor(blk)
                selections.append(sel)

        # 3. Ligne active Pas-à-Pas (prioritaire, avec pulsation douce)
        if self.debug_line is not None:
            blk = self.document().findBlockByNumber(self.debug_line - 1)
            if blk.isValid():
                import math
                sel = QTextEdit.ExtraSelection()
                dbg_col = QColor(t.line_debug)
                pulse_alpha = int(175 + 65 * math.sin(self._pulse_phase))
                dbg_col.setAlpha(max(110, min(250, pulse_alpha)))
                sel.format.setBackground(dbg_col)
                sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                sel.cursor = QTextCursor(blk)
                selections.append(sel)

        self.setExtraSelections(selections)

    def line_number_area_paint_event(self, event: QPaintEvent) -> None:
        painter = QPainter(self.line_number_area)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self.theme
        gutter_col = QColor(t.gutter_bg)
        gutter_col.setAlpha(max(90, min(255, int(self.glass_alpha_pct * 2.55))))
        painter.fillRect(event.rect(), gutter_col)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        cur_line = self.textCursor().blockNumber() + 1
        w = self.line_number_area.width()
        line_h = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_no = block_number + 1
                cy = top + line_h // 2

                # Point d'arrêt rouge ●
                if line_no in self.breakpoints:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(t.danger))
                    painter.drawEllipse(5, cy - 5, 10, 10)

                # Flèche Pas-à-Pas ▶
                if self.debug_line == line_no:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(t.warning))
                    tri = QPolygon(
                        [
                            self.line_number_area.rect().topLeft() + self.line_number_area.rect().topLeft(),
                        ]
                    )
                    from PyQt6.QtCore import QPoint

                    arrow = QPolygon([QPoint(5, cy - 5), QPoint(14, cy), QPoint(5, cy + 5)])
                    painter.drawPolygon(arrow)

                # Numéro de ligne
                if line_no == cur_line:
                    painter.setPen(QColor(t.accent))
                elif line_no in self.error_lines:
                    painter.setPen(QColor(t.danger))
                else:
                    painter.setPen(QColor(t.gutter_fg))

                painter.drawText(0, top, w - 6, line_h, Qt.AlignmentFlag.AlignRight, str(line_no))

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def word_under_cursor(self) -> str:
        c = self.textCursor()
        c.select(QTextCursor.SelectionType.WordUnderCursor)
        return c.selectedText().strip()

    def _insert_completion(self, completion: str) -> None:
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:] if extra > 0 else "")
        self.setTextCursor(tc)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Si le popup d'auto-complétion est ouvert
        if self.completer.popup().isVisible():
            if event.key() in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
            ):
                event.ignore()
                return

        # F1 : Aide contextuelle Alg_32 sur le mot sous le curseur
        if event.key() == Qt.Key.Key_F1:
            self.helpRequested.emit(self.word_under_cursor())
            return

        # Ctrl+Espace : déclenche l'auto-complétion
        if event.key() == Qt.Key.Key_Space and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._show_completer(force=True)
            return

        # Tab => 4 espaces
        if event.key() == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.insertPlainText("    ")
            return

        # Entrée => auto-indentation intelligente
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            line_text = cursor.block().text()
            indent_match = re.match(r"^(\s*)", line_text)
            indent = indent_match.group(1) if indent_match else ""
            up_stripped = line_text.strip().upper()
            indent_triggers = (
                "DEBUT",
                "DÉBUT",
                "ALORS",
                "SINON",
                "REPETER",
                "RÉPÉTER",
                "ITER",
                "VAR",
                "CONST",
            )
            if (
                up_stripped in indent_triggers
                or up_stripped.endswith("ALORS")
                or up_stripped.startswith(("POUR ", "TANT QUE ", "TANTQUE ", "TQ ", "SELON ", "CAS ", "STRUCTURE ", "TYPE "))
            ):
                indent += "    "
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return

        super().keyPressEvent(event)

        # Auto-complétion fluide à partir de 2 lettres
        if event.text() and (event.text().isalnum() or event.text() == "_"):
            self._show_completer(force=False)
        else:
            self.completer.popup().hide()

    def _show_completer(self, force: bool = False) -> None:
        prefix = self.word_under_cursor()
        if not force and len(prefix) < 2:
            self.completer.popup().hide()
            return
        self._completer_model.setStringList(self._build_completion_words())
        self.completer.setCompletionPrefix(prefix)
        popup = self.completer.popup()
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        cr = self.cursorRect()
        cr.setWidth(240)
        self.completer.complete(cr)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_font(1)
            elif delta < 0:
                self.zoom_font(-1)
            event.accept()
            return
        super().wheelEvent(event)

    def zoom_font(self, delta: int) -> None:
        f = self.font()
        new_sz = max(8, min(28, f.pointSize() + delta))
        f.setPointSize(new_sz)
        self.setFont(f)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self._update_line_number_area_width(0)


class FindReplaceBar(QWidget):
    """Barre compacte de Recherche & Remplacement (Ctrl+F / Ctrl+H)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Rechercher dans l'algorithme...")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Remplacer par...")

        self.btn_next = QPushButton("Suivant")
        self.btn_prev = QPushButton("Précédent")
        self.btn_replace = QPushButton("Remplacer")
        self.btn_replace_all = QPushButton("Tout remplacer")
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedWidth(30)

        layout.addWidget(QLabel("Rechercher :"))
        layout.addWidget(self.find_input, 2)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.replace_input, 2)
        layout.addWidget(self.btn_replace)
        layout.addWidget(self.btn_replace_all)
        layout.addWidget(self.btn_close)

        self.btn_close.clicked.connect(self.hide)
        self.hide()


class EditorWorkspace(QWidget):
    """Conteneur central multi-onglets d'éditeurs .alg avec barre de recherche intégrée."""

    activeEditorChanged = pyqtSignal()
    helpRequested = pyqtSignal(str)
    cursorMoved = pyqtSignal(int, int)

    def __init__(self, theme: StudioTheme, profile: KeywordProfile, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.profile = profile

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(lambda _: self.activeEditorChanged.emit())

        self.find_bar = FindReplaceBar(self)
        self.find_bar.find_input.returnPressed.connect(self.find_next)
        self.find_bar.btn_next.clicked.connect(self.find_next)
        self.find_bar.btn_prev.clicked.connect(self.find_prev)
        self.find_bar.btn_replace.clicked.connect(self.replace_one)
        self.find_bar.btn_replace_all.clicked.connect(self.replace_all)

        vbox.addWidget(self.tabs, 1)
        vbox.addWidget(self.find_bar)

    def current_editor(self) -> Optional[CodeEditor]:
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def new_tab(self, title: str = "sans_nom.alg", content: str = "", path: Optional[Path] = None) -> CodeEditor:
        # Si le fichier est déjà ouvert dans un onglet, on l'active simplement
        if path is not None:
            resolved = path.resolve()
            for i in range(self.tabs.count()):
                ed = self.tabs.widget(i)
                if isinstance(ed, CodeEditor) and ed.file_path and ed.file_path.resolve() == resolved:
                    self.tabs.setCurrentIndex(i)
                    return ed

        ed = CodeEditor(self.theme, self.profile, self)
        ed.set_theme_and_profile(self.theme, self.profile, getattr(self, "_glass_alpha_pct", 100))
        ed.file_path = path
        ed.setPlainText(content)
        ed.document().setModified(False)
        ed.helpRequested.connect(self.helpRequested.emit)
        ed.cursorPosChangedInfo.connect(self.cursorMoved.emit)
        ed.document().modificationChanged.connect(lambda mod, e=ed: self._update_tab_title(e, mod))

        idx = self.tabs.addTab(ed, title)
        self.tabs.setCurrentIndex(idx)
        return ed

    def _update_tab_title(self, editor: CodeEditor, modified: bool) -> None:
        idx = self.tabs.indexOf(editor)
        if idx >= 0:
            base = editor.file_path.name if editor.file_path else "sans_nom.alg"
            self.tabs.setTabText(idx, f"● {base}" if modified else base)

    def refresh_tab_title(self, editor: CodeEditor) -> None:
        self._update_tab_title(editor, editor.document().isModified())

    def close_tab(self, index: int) -> None:
        if self.tabs.count() <= 1:
            ed = self.current_editor()
            if ed:
                ed.clear()
                ed.file_path = None
                self.tabs.setTabText(0, "sans_nom.alg")
            return
        w = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if w:
            w.deleteLater()

    def set_theme_and_profile(
        self,
        theme: StudioTheme,
        profile: KeywordProfile,
        glass_alpha_pct: int = 100,
    ) -> None:
        self.theme = theme
        self.profile = profile
        self._glass_alpha_pct = glass_alpha_pct
        for i in range(self.tabs.count()):
            ed = self.tabs.widget(i)
            if isinstance(ed, CodeEditor):
                ed.set_theme_and_profile(theme, profile, glass_alpha_pct)

    def show_find_bar(self, with_replace: bool = False) -> None:
        self.find_bar.replace_input.setVisible(with_replace)
        self.find_bar.btn_replace.setVisible(with_replace)
        self.find_bar.btn_replace_all.setVisible(with_replace)
        self.find_bar.show()
        ed = self.current_editor()
        if ed and ed.textCursor().hasSelection():
            self.find_bar.find_input.setText(ed.textCursor().selectedText())
        self.find_bar.find_input.setFocus()
        self.find_bar.find_input.selectAll()

    def find_next(self) -> None:
        ed = self.current_editor()
        q = self.find_bar.find_input.text()
        if ed and q:
            if not ed.find(q):
                # Reboucle depuis le début
                c = ed.textCursor()
                c.movePosition(QTextCursor.MoveOperation.Start)
                ed.setTextCursor(c)
                ed.find(q)

    def find_prev(self) -> None:
        ed = self.current_editor()
        q = self.find_bar.find_input.text()
        if ed and q:
            ed.find(q, QTextDocument.FindFlag.FindBackward)

    def replace_one(self) -> None:
        ed = self.current_editor()
        q = self.find_bar.find_input.text()
        rep = self.find_bar.replace_input.text()
        if ed and q:
            c = ed.textCursor()
            if c.hasSelection() and c.selectedText().lower() == q.lower():
                c.insertText(rep)
            self.find_next()

    def replace_all(self) -> None:
        ed = self.current_editor()
        q = self.find_bar.find_input.text()
        rep = self.find_bar.replace_input.text()
        if ed and q:
            text = ed.toPlainText()
            new_text = re.sub(re.escape(q), rep, text, flags=re.IGNORECASE)
            if new_text != text:
                ed.setPlainText(new_text)
