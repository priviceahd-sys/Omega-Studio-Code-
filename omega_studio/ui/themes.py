"""
Système de thèmes visuels, mélangeur de couleurs, dégradés et transparence
(Glassmorphism) d'Omega Code Studio.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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


@dataclass
class AppearanceConfig:
    """Configuration complète des couleurs mélangées, dégradés, images multiples et animations."""

    custom_colors_enabled: bool = False
    preset_id: str = "aurora_omarchy"
    color_primary: str = "#0f172a"
    color_secondary: str = "#261447"
    color_accent1: str = "#38bdf8"
    color_accent2: str = "#c084fc"
    mix_ratio: int = 45  # 0..100 : dosage du mélange de couleurs

    # Dégradés & transparence (Glassmorphism)
    gradient_enabled: bool = True
    gradient_style: str = "aurora"  # diagonal, horizontal, vertical, radial, aurora
    gradient_angle: int = 135  # 0..360°
    glass_opacity: int = 84  # 35..100 (%)

    # Galerie multi-images & diaporama
    background_images: List[str] = field(default_factory=list)
    active_image_index: int = 0
    slideshow_enabled: bool = True
    slideshow_interval_sec: int = 12  # 4..120 s
    image_opacity: int = 38  # 5..90 (%)

    # Animations fluides
    animations_enabled: bool = True
    anim_gradient_flow: bool = True
    anim_ambient_orbs: bool = True
    anim_ui_transitions: bool = True
    anim_speed: int = 50  # 10..100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppearanceConfig":
        cfg = cls()
        if not isinstance(data, dict):
            return cfg
        for k in cfg.__dataclass_fields__:
            if k in data:
                setattr(cfg, k, data[k])
        if not isinstance(cfg.background_images, list):
            cfg.background_images = []
        cfg.mix_ratio = max(0, min(100, int(cfg.mix_ratio)))
        cfg.gradient_angle = max(0, min(360, int(cfg.gradient_angle)))
        cfg.glass_opacity = max(35, min(100, int(cfg.glass_opacity)))
        cfg.slideshow_interval_sec = max(4, min(120, int(cfg.slideshow_interval_sec)))
        cfg.image_opacity = max(5, min(90, int(cfg.image_opacity)))
        cfg.anim_speed = max(10, min(100, int(cfg.anim_speed)))
        return cfg


@dataclass(frozen=True)
class GradientPreset:
    id: str
    name: str
    color_primary: str
    color_secondary: str
    color_accent1: str
    color_accent2: str
    gradient_style: str = "aurora"
    gradient_angle: int = 135
    mix_ratio: int = 45


GRADIENT_PRESETS: List[GradientPreset] = [
    GradientPreset(
        id="aurora_omarchy",
        name="Aurore Boréale (Omarchy)",
        color_primary="#0f172a",
        color_secondary="#1e1b4b",
        color_accent1="#38bdf8",
        color_accent2="#c084fc",
        gradient_style="aurora",
        gradient_angle=135,
        mix_ratio=45,
    ),
    GradientPreset(
        id="cyber_neon",
        name="Cyberpunk Néon",
        color_primary="#100924",
        color_secondary="#2b0a3d",
        color_accent1="#00f5d4",
        color_accent2="#f72585",
        gradient_style="diagonal",
        gradient_angle=125,
        mix_ratio=50,
    ),
    GradientPreset(
        id="sunset_fusion",
        name="Crépuscule Solaire",
        color_primary="#1c1022",
        color_secondary="#3d1628",
        color_accent1="#ff6b6b",
        color_accent2="#feca57",
        gradient_style="diagonal",
        gradient_angle=145,
        mix_ratio=48,
    ),
    GradientPreset(
        id="abyssal_ocean",
        name="Océan Abyssal",
        color_primary="#061826",
        color_secondary="#0e344d",
        color_accent1="#00bbf9",
        color_accent2="#2ec4b6",
        gradient_style="radial",
        gradient_angle=120,
        mix_ratio=42,
    ),
    GradientPreset(
        id="emerald_gold",
        name="Émeraude & Or",
        color_primary="#091d17",
        color_secondary="#17382b",
        color_accent1="#10b981",
        color_accent2="#f59e0b",
        gradient_style="diagonal",
        gradient_angle=135,
        mix_ratio=40,
    ),
    GradientPreset(
        id="sakura_night",
        name="Sakura Cosmique",
        color_primary="#181226",
        color_secondary="#321b42",
        color_accent1="#ff7eb3",
        color_accent2="#8b5cf6",
        gradient_style="aurora",
        gradient_angle=150,
        mix_ratio=52,
    ),
    GradientPreset(
        id="volcanic_ember",
        name="Magma Volcanique",
        color_primary="#1a0d10",
        color_secondary="#38161a",
        color_accent1="#fb5607",
        color_accent2="#ffbe0b",
        gradient_style="radial",
        gradient_angle=135,
        mix_ratio=45,
    ),
    GradientPreset(
        id="pastel_crystal",
        name="Cristal Pastel (Clair)",
        color_primary="#eef2ff",
        color_secondary="#fce7f3",
        color_accent1="#4f46e5",
        color_accent2="#ec4899",
        gradient_style="diagonal",
        gradient_angle=135,
        mix_ratio=50,
    ),
]


# ==========================================
# Utilitaires de mélange et d'harmonie RVB
# ==========================================


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) < 6:
        return (26, 27, 38)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return (26, 27, 38)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    ri = max(0, min(255, int(round(r))))
    gi = max(0, min(255, int(round(g))))
    bi = max(0, min(255, int(round(b))))
    return f"#{ri:02x}{gi:02x}{bi:02x}"


def blend_hex(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def lighten_hex(c: str, amount: float) -> str:
    return blend_hex(c, "#ffffff", amount)


def darken_hex(c: str, amount: float) -> str:
    return blend_hex(c, "#000000", amount)


def perceived_luminance(c: str) -> float:
    r, g, b = hex_to_rgb(c)
    return 0.299 * r + 0.587 * g + 0.114 * b


def qss_rgba(hex_color: str, alpha_pct: int) -> str:
    r, g, b = hex_to_rgb(hex_color)
    a = max(0, min(255, int(round(alpha_pct * 255 / 100.0))))
    return f"rgba({r}, {g}, {b}, {a})"


def synthesize_mixed_theme(base_theme: StudioTheme, cfg: AppearanceConfig) -> StudioTheme:
    """
    Génère dynamiquement un StudioTheme complet à partir du mélange de couleurs
    choisi par l'utilisateur (Fond 1, Fond 2, Accent 1, Accent 2 et ratio de fusion).
    """
    if not cfg.custom_colors_enabled:
        return base_theme

    t = cfg.mix_ratio / 100.0
    c1 = cfg.color_primary
    c2 = cfg.color_secondary
    a1 = cfg.color_accent1
    a2 = cfg.color_accent2

    bg_mix = blend_hex(c1, c2, t)
    is_dark = perceived_luminance(bg_mix) < 145.0

    accent = blend_hex(a1, a2, t * 0.45)
    accent_hover = blend_hex(a1, a2, min(1.0, t * 0.45 + 0.40))
    accent_fg = "#0f172a" if perceived_luminance(accent) > 155.0 else "#ffffff"

    if is_dark:
        bg_activity = darken_hex(blend_hex(c1, c2, t * 0.35), 0.22)
        bg_sidebar = blend_hex(c1, c2, t * 0.55)
        bg_editor = blend_hex(c1, c2, t * 0.30)
        bg_panel = blend_hex(c1, c2, t * 0.50)
        bg_elevated = lighten_hex(bg_mix, 0.12)
        bg_hover = lighten_hex(bg_mix, 0.20)
        bg_selection = blend_hex(bg_editor, a1, 0.38)
        border = blend_hex(lighten_hex(bg_mix, 0.16), accent, 0.28)
        fg_primary = "#eef2ff"
        fg_secondary = "#cbd5e1"
        fg_muted = blend_hex(bg_mix, "#94a3b8", 0.65)
        line_current = blend_hex(bg_editor, accent, 0.14)
        line_debug = blend_hex(bg_editor, "#f59e0b", 0.30)
        line_error = blend_hex(bg_editor, "#ef4444", 0.30)
        syn_keyword = lighten_hex(a2, 0.18)
        syn_control = lighten_hex(a1, 0.14)
        syn_type = blend_hex(a1, "#2dd4bf", 0.55)
        syn_builtin = lighten_hex(blend_hex(a1, a2, 0.5), 0.25)
        syn_string = "#a6e3a1"
        syn_number = "#fbbf24"
        syn_comment = fg_muted
        syn_operator = lighten_hex(a1, 0.22)
        success = "#34d399"
        warning = "#fbbf24"
        danger = "#fb7185"
    else:
        bg_activity = darken_hex(blend_hex(c1, c2, t * 0.5), 0.07)
        bg_sidebar = blend_hex(c1, c2, t * 0.45)
        bg_editor = lighten_hex(bg_mix, 0.48)
        bg_panel = lighten_hex(bg_mix, 0.25)
        bg_elevated = darken_hex(bg_mix, 0.05)
        bg_hover = darken_hex(bg_mix, 0.11)
        bg_selection = blend_hex("#ffffff", a1, 0.26)
        border = blend_hex(darken_hex(bg_mix, 0.12), accent, 0.28)
        fg_primary = "#0f172a"
        fg_secondary = "#334155"
        fg_muted = "#64748b"
        line_current = blend_hex(bg_editor, accent, 0.10)
        line_debug = "#fef3c7"
        line_error = "#fee2e2"
        syn_keyword = darken_hex(a2, 0.18)
        syn_control = darken_hex(a1, 0.18)
        syn_type = "#0f766e"
        syn_builtin = darken_hex(blend_hex(a1, a2, 0.5), 0.22)
        syn_string = "#15803d"
        syn_number = "#c2410c"
        syn_comment = "#64748b"
        syn_operator = "#334155"
        success = "#15803d"
        warning = "#b45309"
        danger = "#dc2626"

    return StudioTheme(
        id="custom_mixed",
        name="Mélange Personnalisé",
        is_dark=is_dark,
        bg_activity=bg_activity,
        bg_sidebar=bg_sidebar,
        bg_editor=bg_editor,
        bg_panel=bg_panel,
        bg_elevated=bg_elevated,
        bg_hover=bg_hover,
        bg_selection=bg_selection,
        border=border,
        fg_primary=fg_primary,
        fg_secondary=fg_secondary,
        fg_muted=fg_muted,
        accent=accent,
        accent_hover=accent_hover,
        accent_fg=accent_fg,
        success=success,
        warning=warning,
        danger=danger,
        syn_keyword=syn_keyword,
        syn_control=syn_control,
        syn_type=syn_type,
        syn_builtin=syn_builtin,
        syn_string=syn_string,
        syn_number=syn_number,
        syn_comment=syn_comment,
        syn_operator=syn_operator,
        line_current=line_current,
        line_debug=line_debug,
        line_error=line_error,
        gutter_bg=bg_sidebar,
        gutter_fg=fg_muted,
    )


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


def build_stylesheet(t: StudioTheme, cfg: Optional[AppearanceConfig] = None) -> str:
    """
    Construit la feuille de style QSS globale, avec support des dégradés de couleurs
    et de la transparence Glassmorphism lorsque des images ou dégradés sont actifs.
    """
    has_backdrop = bool(
        cfg is not None
        and (cfg.custom_colors_enabled or cfg.gradient_enabled or len(cfg.background_images) > 0)
    )
    alpha = cfg.glass_opacity if (cfg is not None and has_backdrop) else 100

    surf_editor = qss_rgba(t.bg_editor, alpha) if alpha < 100 else t.bg_editor
    surf_sidebar = qss_rgba(t.bg_sidebar, max(35, alpha - 4)) if alpha < 100 else t.bg_sidebar
    surf_elevated = qss_rgba(t.bg_elevated, min(100, alpha + 8)) if alpha < 100 else t.bg_elevated

    use_grad = bool(cfg is not None and cfg.gradient_enabled)
    a1 = cfg.color_accent1 if (cfg and cfg.custom_colors_enabled) else t.accent
    a2 = cfg.color_accent2 if (cfg and cfg.custom_colors_enabled) else t.accent_hover

    if use_grad:
        tb_bg = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {qss_rgba(t.bg_activity, min(100, alpha + 6))}, "
            f"stop:0.55 {qss_rgba(t.bg_sidebar, min(100, alpha + 4))}, "
            f"stop:1 {qss_rgba(blend_hex(t.bg_sidebar, a2, 0.22), min(100, alpha + 6))})"
        )
        status_bg = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {qss_rgba(blend_hex(t.bg_activity, a1, 0.20), 94)}, "
            f"stop:1 {qss_rgba(blend_hex(t.bg_activity, a2, 0.20), 94)})"
        )
        btn_primary_bg = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {a1}, stop:1 {a2})"
        tab_sel_bg = (
            f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {qss_rgba(blend_hex(t.bg_editor, a1, 0.18), min(100, alpha + 8))}, "
            f"stop:1 {surf_editor})"
        )
    else:
        tb_bg = surf_sidebar
        status_bg = t.bg_activity
        btn_primary_bg = t.accent
        tab_sel_bg = surf_editor

    return f"""
    QMainWindow {{
        background-color: {t.bg_sidebar};
        color: {t.fg_primary};
    }}
    QDialog {{
        background-color: {t.bg_sidebar};
        color: {t.fg_primary};
    }}
    QWidget#AnimatedBackdrop {{
        background: transparent;
    }}
    QWidget {{
        color: {t.fg_primary};
        selection-background-color: {t.bg_selection};
        selection-color: {t.fg_primary};
    }}
    QMenuBar {{
        background: {tb_bg};
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
        background: {tb_bg};
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
        border-color: {t.accent};
    }}
    QToolButton:checked {{
        background-color: {surf_elevated};
        border-color: {t.accent};
        color: {t.accent};
    }}
    QPushButton {{
        background-color: {surf_elevated};
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
        background: {btn_primary_bg};
        color: {t.accent_fg};
        border-color: {a1};
    }}
    QPushButton[primary="true"]:hover {{
        border-color: {a2};
    }}
    QPushButton[danger="true"] {{
        background-color: {t.danger};
        color: #ffffff;
        border-color: {t.danger};
    }}
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {surf_editor};
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
        background-color: {surf_editor};
    }}
    QTabBar::tab {{
        background-color: {surf_sidebar};
        color: {t.fg_muted};
        border: none;
        border-right: 1px solid {t.border};
        border-bottom: 1px solid {t.border};
        padding: 6px 10px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {tab_sel_bg};
        color: {t.fg_primary};
        border-top: 2px solid {a1};
        border-bottom: 1px solid transparent;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {t.bg_hover};
        color: {t.fg_secondary};
    }}
    QTreeWidget, QListWidget, QTableWidget {{
        background-color: {surf_sidebar};
        color: {t.fg_primary};
        border: 1px solid {t.border};
        alternate-background-color: {surf_editor};
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
        background-color: {surf_elevated};
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
        background: transparent;
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
        background: {t.accent};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
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
        background: {status_bg};
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
