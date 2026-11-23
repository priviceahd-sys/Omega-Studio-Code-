"""
Système de thèmes visuels d'Omega Studio Code.
Inclut des palettes harmonisées pour Omarchy (TokyoNight, Catppuccin Mocha),
VS Code Dark et un mode Clair Académique haute lisibilité.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class StudioTheme:
    id: str
    name: str
    is_dark: bool
    # Surfaces principales
    bg_activity: str
    bg_sidebar: str
    bg_editor: str
    bg_panel: str
    bg_elevated: str
    bg_hover: str
    bg_selection: str
    border: str
    # Typographie
    fg_primary: str
    fg_secondary: str
    fg_muted: str
    # Accents UI
    accent: str
    accent_hover: str
    accent_fg: str
    success: str
    warning: str
    danger: str
    # Coloration syntaxique
    syn_keyword: str
    syn_control: str
    syn_type: str
    syn_builtin: str
    syn_string: str
    syn_number: str
    syn_comment: str
    syn_operator: str
    # Éditeur : lignes spéciales
    line_current: str
    line_debug: str
    line_error: str
    gutter_bg: str
    gutter_fg: str


THEMES: Dict[str, StudioTheme] = {
    "omarchy_tokyonight": StudioTheme(
        id="omarchy_tokyonight",
        name="Omarchy TokyoNight (Sombre)",
        is_dark=True,
        bg_activity="#13141c",
        bg_sidebar="#16161e",
        bg_editor="#1a1b26",
        bg_panel="#16161e",
        bg_elevated="#24283b",
        bg_hover="#292e42",
        bg_selection="#33467c",
        border="#292e42",
        fg_primary="#c0caf5",
        fg_secondary="#a9b1d6",
        fg_muted="#565f89",
        accent="#7aa2f7",
        accent_hover="#89ddff",
        accent_fg="#15161e",
        success="#9ece6a",
        warning="#e0af68",
        danger="#f7768e",
        syn_keyword="#bb9af7",
        syn_control="#7aa2f7",
        syn_type="#2ac3de",
        syn_builtin="#7dcfff",
        syn_string="#9ece6a",
        syn_number="#ff9e64",
        syn_comment="#565f89",
        syn_operator="#89ddff",
        line_current="#202334",
        line_debug="#3d3420",
        line_error="#3f1f29",
        gutter_bg="#16161e",
        gutter_fg="#565f89",
    ),
    "vscode_dark": StudioTheme(
        id="vscode_dark",
        name="Omega Studio Dark (VS Code)",
        is_dark=True,
        bg_activity="#181818",
        bg_sidebar="#202022",
        bg_editor="#1e1e1e",
        bg_panel="#181818",
        bg_elevated="#2d2d30",
        bg_hover="#37373d",
        bg_selection="#264f78",
        border="#323236",
        fg_primary="#d4d4d4",
        fg_secondary="#cccccc",
        fg_muted="#7a7a80",
        accent="#007acc",
        accent_hover="#1f8ad2",
        accent_fg="#ffffff",
        success="#4ec9b0",
        warning="#dcdcaa",
        danger="#f14c4c",
        syn_keyword="#c586c0",
        syn_control="#569cd6",
        syn_type="#4ec9b0",
        syn_builtin="#dcdcaa",
        syn_string="#ce9178",
        syn_number="#b5cea8",
        syn_comment="#6a9955",
        syn_operator="#9cdcfe",
        line_current="#262629",
        line_debug="#42381b",
        line_error="#442022",
        gutter_bg="#1e1e1e",
        gutter_fg="#6e7681",
    ),
    "catppuccin_mocha": StudioTheme(
        id="catppuccin_mocha",
        name="Omarchy Catppuccin Mocha",
        is_dark=True,
        bg_activity="#11111b",
        bg_sidebar="#181825",
        bg_editor="#1e1e2e",
        bg_panel="#181825",
        bg_elevated="#313244",
        bg_hover="#45475a",
        bg_selection="#45475a",
        border="#313244",
        fg_primary="#cdd6f4",
        fg_secondary="#bac2de",
        fg_muted="#6c7086",
        accent="#89b4fa",
        accent_hover="#b4befe",
        accent_fg="#11111b",
        success="#a6e3a1",
        warning="#f9e2af",
        danger="#f38ba8",
        syn_keyword="#cba6f7",
        syn_control="#89b4fa",
        syn_type="#94e2d5",
        syn_builtin="#89dceb",
        syn_string="#a6e3a1",
        syn_number="#fab387",
        syn_comment="#6c7086",
        syn_operator="#94e2d5",
        line_current="#262639",
        line_debug="#423929",
        line_error="#452432",
        gutter_bg="#181825",
        gutter_fg="#6c7086",
    ),
    "academic_light": StudioTheme(
        id="academic_light",
        name="Clair Académique (Cours & TP)",
        is_dark=False,
        bg_activity="#e2e8f0",
        bg_sidebar="#f1f5f9",
        bg_editor="#ffffff",
        bg_panel="#f8fafc",
        bg_elevated="#e2e8f0",
        bg_hover="#cbd5e1",
        bg_selection="#bfdbfe",
        border="#cbd5e1",
        fg_primary="#0f172a",
        fg_secondary="#334155",
        fg_muted="#64748b",
        accent="#2563eb",
        accent_hover="#1d4ed8",
        accent_fg="#ffffff",
        success="#15803d",
        warning="#b45309",
        danger="#dc2626",
        syn_keyword="#7c3aed",
        syn_control="#1d4ed8",
        syn_type="#0f766e",
        syn_builtin="#0369a1",
        syn_string="#15803d",
        syn_number="#c2410c",
        syn_comment="#64748b",
        syn_operator="#334155",
        line_current="#f1f5f9",
        line_debug="#fef3c7",
        line_error="#fee2e2",
        gutter_bg="#f8fafc",
        gutter_fg="#64748b",
    ),
}


def build_stylesheet(t: StudioTheme) -> str:
    """Construit la feuille de style QSS globale pour le thème choisi."""
    return f"""
    QMainWindow, QDialog {{
        background-color: {t.bg_sidebar};
        color: {t.fg_primary};
    }}
    QWidget {{
        color: {t.fg_primary};
        selection-background-color: {t.bg_selection};
        selection-color: {t.fg_primary};
    }}
    QMenuBar {{
        background-color: {t.bg_activity};
        color: {t.fg_primary};
        border-bottom: 1px solid {t.border};
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        padding: 5px 10px;
        border-radius: 4px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {t.bg_hover};
    }}
    QMenu {{
        background-color: {t.bg_elevated};
        color: {t.fg_primary};
        border: 1px solid {t.border};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {t.accent};
        color: {t.accent_fg};
    }}
    QMenu::separator {{
        height: 1px;
        background: {t.border};
        margin: 4px 6px;
    }}
    QToolBar {{
        background-color: {t.bg_sidebar};
        border-bottom: 1px solid {t.border};
        spacing: 6px;
        padding: 4px 8px;
    }}
    QToolButton {{
        background-color: transparent;
        color: {t.fg_primary};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 5px 9px;
        font-weight: 600;
    }}
    QToolButton:hover {{
        background-color: {t.bg_hover};
        border-color: {t.border};
    }}
    QToolButton:checked {{
        background-color: {t.bg_elevated};
        border-color: {t.accent};
        color: {t.accent};
    }}
    QPushButton {{
        background-color: {t.bg_elevated};
        color: {t.fg_primary};
        border: 1px solid {t.border};
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {t.bg_hover};
        border-color: {t.accent};
    }}
    QPushButton[primary="true"] {{
        background-color: {t.accent};
        color: {t.accent_fg};
        border-color: {t.accent};
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {t.accent_hover};
    }}
    QPushButton[danger="true"] {{
        background-color: {t.danger};
        color: #ffffff;
        border-color: {t.danger};
    }}
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {t.bg_editor};
        color: {t.fg_primary};
        border: 1px solid {t.border};
        border-radius: 5px;
        padding: 5px 8px;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {t.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t.bg_elevated};
        color: {t.fg_primary};
        border: 1px solid {t.border};
        selection-background-color: {t.accent};
        selection-color: {t.accent_fg};
    }}
    QTabWidget::pane {{
        border: 1px solid {t.border};
        background-color: {t.bg_editor};
    }}
    QTabBar::tab {{
        background-color: {t.bg_sidebar};
        color: {t.fg_muted};
        border: none;
        border-right: 1px solid {t.border};
        border-bottom: 1px solid {t.border};
        padding: 6px 10px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background-color: {t.bg_editor};
        color: {t.fg_primary};
        border-top: 2px solid {t.accent};
        border-bottom: 1px solid {t.bg_editor};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {t.bg_hover};
        color: {t.fg_secondary};
    }}
    QTreeWidget, QListWidget, QTableWidget {{
        background-color: {t.bg_sidebar};
        color: {t.fg_primary};
        border: 1px solid {t.border};
        alternate-background-color: {t.bg_editor};
        outline: 0;
    }}
    QTreeWidget::item, QListWidget::item {{
        padding: 4px 6px;
        border-radius: 4px;
    }}
    QTreeWidget::item:selected, QListWidget::item:selected {{
        background-color: {t.bg_selection};
        color: {t.fg_primary};
    }}
    QTreeWidget::item:hover:!selected, QListWidget::item:hover:!selected {{
        background-color: {t.bg_hover};
    }}
    QHeaderView::section {{
        background-color: {t.bg_elevated};
        color: {t.fg_secondary};
        border: none;
        border-right: 1px solid {t.border};
        border-bottom: 1px solid {t.border};
        padding: 5px 8px;
        font-weight: 700;
    }}
    QSplitter::handle {{
        background-color: {t.border};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    QSplitter::handle:hover {{
        background-color: {t.accent};
    }}
    QScrollBar:vertical {{
        background: {t.bg_sidebar};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.bg_hover};
        min-height: 24px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t.fg_muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: {t.bg_sidebar};
        height: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t.bg_hover};
        min-width: 24px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QStatusBar {{
        background-color: {t.bg_activity};
        color: {t.fg_secondary};
        border-top: 1px solid {t.border};
        font-size: 12px;
    }}
    QToolTip {{
        background-color: {t.bg_elevated};
        color: {t.fg_primary};
        border: 1px solid {t.accent};
        padding: 5px 8px;
    }}
    """
