"""
Studio d'Apparence, Mélanges de Couleurs, Dégradés, Galerie Multi-Images
et Moteur d'Animations Fluides pour Omega Code Studio.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .themes import (
    GRADIENT_PRESETS,
    AppearanceConfig,
    GradientPreset,
    StudioTheme,
    blend_hex,
    hex_to_rgb,
    rgb_to_hex,
)

BUILTIN_WALLPAPERS: List[Tuple[str, str]] = [
    ("builtin:aurora_waves", "Aurore Boréale Polaire (Intégré)"),
    ("builtin:nebula", "Nébuleuse Cosmique (Intégré)"),
    ("builtin:cyber_grid", "Horizon Synthwave Néon (Intégré)"),
    ("builtin:sunset_peaks", "Montagnes Crépusculaires (Intégré)"),
]


def render_builtin_wallpaper(key: str, width: int = 1280, height: int = 720) -> QPixmap:
    """Génère un fond d'écran vectoriel haute résolution sans alourdir le dépôt Git."""
    img = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    w = float(width)
    h = float(height)

    if key == "builtin:nebula":
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor("#090514"))
        bg.setColorAt(0.5, QColor("#1d1038"))
        bg.setColorAt(1.0, QColor("#0b192c"))
        p.fillRect(0, 0, width, height, bg)

        # Nébuleuses lumineuses
        for cx, cy, rad, col in [
            (0.28 * w, 0.35 * h, 0.45 * w, QColor(168, 85, 247, 130)),
            (0.72 * w, 0.62 * h, 0.48 * w, QColor(56, 189, 248, 120)),
            (0.52 * w, 0.45 * h, 0.32 * w, QColor(244, 114, 182, 105)),
        ]:
            rg = QRadialGradient(cx, cy, rad)
            rg.setColorAt(0.0, col)
            rg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(0, 0, width, height, rg)

        # Étoiles déterministes
        rng = random.Random(42)
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(140):
            sx = rng.uniform(0, w)
            sy = rng.uniform(0, h)
            sr = rng.uniform(0.8, 2.4)
            alpha = rng.randint(90, 230)
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawEllipse(QPointF(sx, sy), sr, sr)

    elif key == "builtin:cyber_grid":
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor("#0c0620"))
        bg.setColorAt(0.55, QColor("#2c0b3f"))
        bg.setColorAt(0.58, QColor("#ff2a85"))
        bg.setColorAt(1.0, QColor("#090418"))
        p.fillRect(0, 0, width, height, bg)

        # Soleil rétro
        sun_y = h * 0.46
        sun_r = h * 0.22
        sg = QLinearGradient(0, sun_y - sun_r, 0, sun_y + sun_r)
        sg.setColorAt(0.0, QColor("#ffbe0b"))
        sg.setColorAt(0.5, QColor("#fb5607"))
        sg.setColorAt(1.0, QColor("#ff006e"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(sg))
        p.drawEllipse(QPointF(w * 0.5, sun_y), sun_r, sun_r)

        # Grille perspective néon
        horizon = h * 0.57
        p.fillRect(QRectF(0, horizon, w, h - horizon), QColor(12, 6, 28, 225))
        pen = QPen(QColor(0, 245, 212, 130), 1.4)
        p.setPen(pen)
        for i in range(-12, 13):
            x_top = w * 0.5 + i * (w * 0.025)
            x_bot = w * 0.5 + i * (w * 0.14)
            p.drawLine(QPointF(x_top, horizon), QPointF(x_bot, h))
        for j in range(1, 12):
            t = (j / 11.0) ** 1.8
            yy = horizon + t * (h - horizon)
            p.drawLine(QPointF(0, yy), QPointF(w, yy))

    elif key == "builtin:sunset_peaks":
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor("#1a102b"))
        bg.setColorAt(0.45, QColor("#5c2246"))
        bg.setColorAt(0.80, QColor("#e85d75"))
        bg.setColorAt(1.0, QColor("#fcca46"))
        p.fillRect(0, 0, width, height, bg)

        # Couches de montagnes
        layers = [
            (0.58, "#391938", 45.0, 1.3),
            (0.68, "#28122b", 38.0, 2.1),
            (0.79, "#160a1c", 28.0, 3.4),
        ]
        for base_ratio, col_hex, amp, freq in layers:
            path = QPainterPath()
            path.moveTo(0, h)
            steps = 80
            for s in range(steps + 1):
                x = (s / steps) * w
                y = (
                    h * base_ratio
                    - math.sin(s * 0.14 * freq) * amp
                    - math.cos(s * 0.07 * freq + 1.2) * (amp * 0.6)
                )
                path.lineTo(x, y)
            path.lineTo(w, h)
            path.closeSubpath()
            p.fillPath(path, QColor(col_hex))

    else:  # builtin:aurora_waves
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor("#061320"))
        bg.setColorAt(0.5, QColor("#0d2238"))
        bg.setColorAt(1.0, QColor("#171332"))
        p.fillRect(0, 0, width, height, bg)

        ribbons = [
            (0.32, "#2dd4bf", "#38bdf8", 70.0, 0.9),
            (0.48, "#818cf8", "#c084fc", 85.0, 1.4),
            (0.64, "#34d399", "#22d3ee", 60.0, 1.9),
        ]
        for y_ratio, c_start, c_end, amp, phase in ribbons:
            path = QPainterPath()
            path.moveTo(0, h)
            for s in range(91):
                x = (s / 90.0) * w
                y = h * y_ratio + math.sin((s / 90.0) * math.pi * 2.5 + phase) * amp
                if s == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            for s in range(90, -1, -1):
                x = (s / 90.0) * w
                y = h * y_ratio + 120.0 + math.sin((s / 90.0) * math.pi * 2.5 + phase + 0.5) * (amp * 0.8)
                path.lineTo(x, y)
            path.closeSubpath()
            lg = QLinearGradient(0, 0, w, 0)
            c1 = QColor(c_start)
            c1.setAlpha(115)
            c2 = QColor(c_end)
            c2.setAlpha(115)
            lg.setColorAt(0.0, c1)
            lg.setColorAt(1.0, c2)
            p.fillPath(path, lg)

    p.end()
    return QPixmap.fromImage(img)


def discover_omarchy_wallpapers(max_count: int = 20) -> List[str]:
    """Détecte automatiquement les fonds d'écran Omarchy / Hyprland / Images de l'utilisateur."""
    home = Path.home()
    candidates_dirs = [
        home / ".config" / "omarchy" / "current" / "backgrounds",
        home / ".config" / "omarchy" / "backgrounds",
        home / ".local" / "share" / "omarchy" / "themes",
        home / "Pictures" / "Wallpapers",
        home / "Pictures",
        home / "Images",
        Path("C:/Windows/Web/Wallpaper"),
    ]
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    found: List[str] = []
    seen = set()

    for d in candidates_dirs:
        if not d.exists():
            continue
        try:
            iterator = d.rglob("*") if "themes" in d.name else d.glob("*")
            for f in sorted(iterator):
                if f.is_file() and f.suffix.lower() in exts:
                    rp = str(f.resolve())
                    if rp not in seen:
                        seen.add(rp)
                        found.append(rp)
                        if len(found) >= max_count:
                            return found
        except Exception:
            continue
    return found


class AnimatedBackdropWidget(QWidget):
    """
    Surface centrale d'Omega Code Studio :
    - Peint les mélanges de couleurs et dégradés multi-angles animés
    - Affiche une ou plusieurs images d'arrière-plan avec diaporama en fondu enchaîné (crossfade)
    - Anime des halos lumineux flottants (Aurore) et un ruban supérieur dynamique
    """

    activeImageChanged = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("AnimatedBackdrop")
        self.cfg = AppearanceConfig()
        self.theme: Optional[StudioTheme] = None

        self._phase: float = 0.0
        self._raw_cache: Dict[str, QPixmap] = {}
        self._scaled_cache: Dict[Tuple[str, int, int], QPixmap] = {}

        # État du fondu enchaîné entre plusieurs images
        self._current_img_key: Optional[str] = None
        self._prev_img_key: Optional[str] = None
        self._crossfade: float = 1.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(36)  # ~28 FPS fluide et économe en CPU
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.timeout.connect(self.next_image)

    def set_theme_and_config(self, theme: StudioTheme, cfg: AppearanceConfig) -> None:
        self.theme = theme
        self.cfg = cfg

        # Synchronise l'image active
        if cfg.background_images:
            idx = max(0, min(len(cfg.background_images) - 1, cfg.active_image_index))
            cfg.active_image_index = idx
            new_key = cfg.background_images[idx]
            if new_key != self._current_img_key:
                if self._current_img_key is not None and cfg.animations_enabled:
                    self._prev_img_key = self._current_img_key
                    self._crossfade = 0.0
                else:
                    self._prev_img_key = None
                    self._crossfade = 1.0
                self._current_img_key = new_key
        else:
            self._current_img_key = None
            self._prev_img_key = None
            self._crossfade = 1.0

        # Gestion des timers d'animation et de diaporama
        need_anim = cfg.animations_enabled and (
            cfg.anim_gradient_flow or cfg.anim_ambient_orbs or self._crossfade < 1.0
        )
        if need_anim:
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            self._anim_timer.stop()

        if cfg.slideshow_enabled and len(cfg.background_images) >= 2:
            self._slideshow_timer.setInterval(max(4, cfg.slideshow_interval_sec) * 1000)
            if not self._slideshow_timer.isActive():
                self._slideshow_timer.start()
        else:
            self._slideshow_timer.stop()

        self.update()

    def next_image(self) -> None:
        imgs = self.cfg.background_images
        if len(imgs) < 2:
            return
        self.select_image_index((self.cfg.active_image_index + 1) % len(imgs))

    def prev_image(self) -> None:
        imgs = self.cfg.background_images
        if len(imgs) < 2:
            return
        self.select_image_index((self.cfg.active_image_index - 1) % len(imgs))

    def select_image_index(self, idx: int) -> None:
        imgs = self.cfg.background_images
        if not imgs:
            return
        idx = idx % len(imgs)
        new_key = imgs[idx]
        if new_key == self._current_img_key:
            return
        self.cfg.active_image_index = idx
        if self._current_img_key is not None and self.cfg.animations_enabled:
            self._prev_img_key = self._current_img_key
            self._crossfade = 0.0
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            self._prev_img_key = None
            self._crossfade = 1.0
        self._current_img_key = new_key
        self.activeImageChanged.emit(idx)
        self.update()

    def _on_anim_tick(self) -> None:
        speed_factor = 0.012 + (self.cfg.anim_speed / 100.0) * 0.048
        self._phase = (self._phase + speed_factor) % (math.pi * 200.0)
        if self._crossfade < 1.0:
            self._crossfade = min(1.0, self._crossfade + 0.055)
            if self._crossfade >= 1.0:
                self._prev_img_key = None
                if not (self.cfg.animations_enabled and (self.cfg.anim_gradient_flow or self.cfg.anim_ambient_orbs)):
                    self._anim_timer.stop()
        self.update()

    def _load_pixmap(self, key: str) -> Optional[QPixmap]:
        if key in self._raw_cache:
            return self._raw_cache[key]
        if key.startswith("builtin:"):
            pm = render_builtin_wallpaper(key, 1280, 720)
            self._raw_cache[key] = pm
            return pm
        p = Path(key)
        if p.exists():
            pm = QPixmap(str(p))
            if not pm.isNull():
                self._raw_cache[key] = pm
                return pm
        return None

    def _get_cover_pixmap(self, key: str, w: int, h: int) -> Optional[QPixmap]:
        if w <= 4 or h <= 4:
            return None
        # Arrondit la taille de cache pour éviter de recalculer à chaque pixel de redimensionnement
        cw = max(64, ((w + 31) // 32) * 32)
        ch = max(64, ((h + 31) // 32) * 32)
        ckey = (key, cw, ch)
        if ckey in self._scaled_cache:
            return self._scaled_cache[ckey]
        raw = self._load_pixmap(key)
        if raw is None or raw.isNull():
            return None
        scaled = raw.scaled(
            cw,
            ch,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        if len(self._scaled_cache) > 24:
            self._scaled_cache.clear()
        self._scaled_cache[ckey] = scaled
        return scaled

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._scaled_cache.clear()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 2 or h <= 2:
            p.end()
            return

        cfg = self.cfg
        t = self.theme

        c1_hex = cfg.color_primary if cfg.custom_colors_enabled else (t.bg_activity if t else "#0f172a")
        c2_hex = cfg.color_secondary if cfg.custom_colors_enabled else (t.bg_elevated if t else "#1e1b4b")
        a1_hex = cfg.color_accent1 if cfg.custom_colors_enabled else (t.accent if t else "#38bdf8")
        a2_hex = cfg.color_accent2 if cfg.custom_colors_enabled else (t.syn_keyword if t else "#c084fc")
        mix = cfg.mix_ratio / 100.0

        # 1. Fond en dégradé riche ou mélange de couleurs
        if cfg.gradient_enabled:
            drift = math.sin(self._phase * 0.7) * 18.0 if (cfg.animations_enabled and cfg.anim_gradient_flow) else 0.0
            angle_rad = math.radians(cfg.gradient_angle + drift)

            if cfg.gradient_style == "radial":
                cx = w * (0.5 + 0.12 * math.cos(self._phase * 0.5) if cfg.animations_enabled else 0.5)
                cy = h * (0.45 + 0.12 * math.sin(self._phase * 0.4) if cfg.animations_enabled else 0.45)
                rg = QRadialGradient(cx, cy, max(w, h) * 0.78)
                rg.setColorAt(0.0, QColor(blend_hex(c2_hex, a1_hex, 0.28 * mix)))
                rg.setColorAt(0.55, QColor(blend_hex(c1_hex, c2_hex, mix)))
                rg.setColorAt(1.0, QColor(c1_hex))
                p.fillRect(self.rect(), rg)
            elif cfg.gradient_style == "horizontal":
                lg = QLinearGradient(0, 0, w, 0)
                lg.setColorAt(0.0, QColor(c1_hex))
                lg.setColorAt(0.5, QColor(blend_hex(c1_hex, c2_hex, mix)))
                lg.setColorAt(1.0, QColor(blend_hex(c2_hex, a2_hex, 0.22)))
                p.fillRect(self.rect(), lg)
            elif cfg.gradient_style == "vertical":
                lg = QLinearGradient(0, 0, 0, h)
                lg.setColorAt(0.0, QColor(c1_hex))
                lg.setColorAt(0.55, QColor(blend_hex(c1_hex, c2_hex, mix)))
                lg.setColorAt(1.0, QColor(blend_hex(c2_hex, a1_hex, 0.22)))
                p.fillRect(self.rect(), lg)
            else:
                # Diagonal ou Aurore multi-couleurs
                dx = math.cos(angle_rad) * w * 0.55
                dy = math.sin(angle_rad) * h * 0.55
                lg = QLinearGradient(w * 0.5 - dx, h * 0.5 - dy, w * 0.5 + dx, h * 0.5 + dy)
                lg.setColorAt(0.0, QColor(c1_hex))
                lg.setColorAt(0.45, QColor(blend_hex(c1_hex, c2_hex, mix)))
                if cfg.gradient_style == "aurora":
                    lg.setColorAt(0.78, QColor(blend_hex(c2_hex, a1_hex, 0.26)))
                    lg.setColorAt(1.0, QColor(blend_hex(c2_hex, a2_hex, 0.30)))
                else:
                    lg.setColorAt(1.0, QColor(c2_hex))
                p.fillRect(self.rect(), lg)
        else:
            p.fillRect(self.rect(), QColor(blend_hex(c1_hex, c2_hex, mix)))

        # 2. Images d'arrière-plan multiples avec fondu enchaîné (crossfade)
        img_alpha_base = cfg.image_opacity / 100.0
        if self._prev_img_key and self._crossfade < 1.0:
            pm_prev = self._get_cover_pixmap(self._prev_img_key, int(w), int(h))
            if pm_prev is not None:
                p.save()
                p.setOpacity(img_alpha_base * (1.0 - self._crossfade))
                ox = int((w - pm_prev.width()) * 0.5)
                oy = int((h - pm_prev.height()) * 0.5)
                p.drawPixmap(ox, oy, pm_prev)
                p.restore()

        if self._current_img_key:
            pm_cur = self._get_cover_pixmap(self._current_img_key, int(w), int(h))
            if pm_cur is not None:
                p.save()
                p.setOpacity(img_alpha_base * self._crossfade)
                ox = int((w - pm_cur.width()) * 0.5)
                oy = int((h - pm_cur.height()) * 0.5)
                p.drawPixmap(ox, oy, pm_cur)
                p.restore()

        # 3. Halos lumineux flottants (mélange animé d'Accent 1 & Accent 2)
        if cfg.animations_enabled and cfg.anim_ambient_orbs:
            orb1_x = w * (0.25 + 0.18 * math.cos(self._phase * 0.45))
            orb1_y = h * (0.30 + 0.16 * math.sin(self._phase * 0.35))
            r1 = max(w, h) * 0.36
            g1 = QRadialGradient(orb1_x, orb1_y, r1)
            ca1 = QColor(a1_hex)
            ca1.setAlpha(48)
            g1.setColorAt(0.0, ca1)
            g1.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), g1)

            orb2_x = w * (0.76 + 0.16 * math.sin(self._phase * 0.38 + 1.4))
            orb2_y = h * (0.68 + 0.16 * math.cos(self._phase * 0.42 + 0.8))
            r2 = max(w, h) * 0.38
            g2 = QRadialGradient(orb2_x, orb2_y, r2)
            ca2 = QColor(a2_hex)
            ca2.setAlpha(44)
            g2.setColorAt(0.0, ca2)
            g2.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), g2)

        # 4. Ruban lumineux supérieur animé en dégradé fluide (3 px)
        if cfg.gradient_enabled or cfg.animations_enabled:
            shift = (math.sin(self._phase * 1.1) + 1.0) * 0.5 if (cfg.animations_enabled and cfg.anim_gradient_flow) else 0.5
            rib = QLinearGradient(0, 0, w, 0)
            rib.setColorAt(0.0, QColor(blend_hex(a1_hex, a2_hex, shift)))
            rib.setColorAt(0.5, QColor(blend_hex(a2_hex, a1_hex, shift)))
            rib.setColorAt(1.0, QColor(blend_hex(a1_hex, a2_hex, 1.0 - shift)))
            p.fillRect(QRectF(0, 0, w, 3.0), rib)

        p.end()


# ==========================================
# Transitions fluides des panneaux & onglets
# ==========================================


def animate_widget_fade_in(widget: QWidget, duration_ms: int = 190) -> None:
    """Applique une animation douce d'apparition en fondu sur un widget (changement d'onglet)."""
    if widget is None:
        return
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.35)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    # Retire l'effet à la fin pour préserver la netteté maximale du rendu sous Wayland
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._omega_fade_anim = anim  # type: ignore[attr-defined]
    anim.start()


def animate_sidebar_width(widget: QWidget, show: bool, target_width: int = 230, duration_ms: int = 210) -> None:
    """Anime l'ouverture ou la fermeture fluide du panneau latéral d'explorateur."""
    start_w = widget.width() if widget.isVisible() else 0
    end_w = target_width if show else 0
    if show:
        widget.setMaximumWidth(start_w)
        widget.setVisible(True)

    anim = QPropertyAnimation(widget, b"maximumWidth", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(start_w)
    anim.setEndValue(end_w)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _on_done() -> None:
        if show:
            widget.setMaximumWidth(16777215)
        else:
            widget.setVisible(False)
            widget.setMaximumWidth(16777215)

    anim.finished.connect(_on_done)
    widget._omega_slide_anim = anim  # type: ignore[attr-defined]
    anim.start()


# ==========================================
# Aperçu en direct dans l'atelier Studio Visuel
# ==========================================


class LiveGradientPreview(QWidget):
    """Bannière d'aperçu animée montrant en direct le mélange de couleurs, dégradés et images."""

    def __init__(self, cfg: AppearanceConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(86)
        self._backdrop = AnimatedBackdropWidget(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._backdrop)

        overlay = QVBoxLayout(self._backdrop)
        overlay.setContentsMargins(16, 12, 16, 12)
        self.lbl_title = QLabel("Aperçu en direct — Mélange de Couleurs, Dégradés & Images")
        self.lbl_title.setStyleSheet(
            "font-size: 14px; font-weight: 800; color: #ffffff; background: rgba(15, 23, 42, 120);"
            "padding: 6px 12px; border-radius: 6px;"
        )
        overlay.addWidget(self.lbl_title, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.update_preview(cfg)

    def update_preview(self, cfg: AppearanceConfig) -> None:
        self._backdrop.set_theme_and_config(None, cfg)  # type: ignore[arg-type]
        nb_img = len(cfg.background_images)
        img_txt = f"{nb_img} image(s) active(s)" if nb_img else "Dégradé pur"
        self.lbl_title.setText(
            f"Aperçu en direct • Mélange {cfg.mix_ratio}% • Dégradé {cfg.gradient_style} ({cfg.gradient_angle}°) • {img_txt}"
        )


# ==========================================
# Boîte de dialogue Studio Visuel Complet
# ==========================================


class AppearanceStudioDialog(QDialog):
    """
    Atelier interactif permettant de personnaliser :
    1) Les couleurs de l'interface, mélanges de couleurs et dégradés
    2) Une sélection de plusieurs images d'arrière-plan + diaporama fondu
    3) Les animations fluides de l'application
    """

    appearanceChanged = pyqtSignal(AppearanceConfig)

    def __init__(
        self,
        cfg: AppearanceConfig,
        theme: StudioTheme,
        backdrop: AnimatedBackdropWidget,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Studio Visuel — Couleurs, Mélanges, Dégradés, Images & Animations")
        self.resize(820, 650)
        self.cfg = AppearanceConfig.from_dict(cfg.to_dict())
        self.theme = theme
        self._main_backdrop = backdrop

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Bannière d'aperçu animée
        self.preview = LiveGradientPreview(self.cfg, self)
        root.addWidget(self.preview)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._build_colors_tab(), "Couleurs, Mélanges && Dégradés")
        self.tabs.addTab(self._build_images_tab(), "Plusieurs Images && Diaporama")
        self.tabs.addTab(self._build_animations_tab(), "Animations Fluides")
        root.addWidget(self.tabs, 1)

        # Barre inférieure d'actions
        footer = QHBoxLayout()
        btn_reset = QPushButton("Réinitialiser au thème classique")
        btn_reset.clicked.connect(self._reset_classic)
        btn_close = QPushButton("Valider && Fermer")
        btn_close.setProperty("primary", True)
        btn_close.clicked.connect(self.accept)

        footer.addWidget(btn_reset)
        footer.addStretch(1)
        footer.addWidget(btn_close)
        root.addLayout(footer)

        self._sync_ui_from_cfg()

    # ------------------------------------------
    # Onglet 1 : Couleurs, Mélanges & Dégradés
    # ------------------------------------------

    def _build_colors_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(10)

        # Activation + Préréglages de mélanges
        grp_presets = QGroupBox("Harmonies && Dégradés Prêts à l'Emploi (1 clic)")
        gp_lay = QGridLayout(grp_presets)
        gp_lay.setSpacing(6)
        for idx, preset in enumerate(GRADIENT_PRESETS):
            btn = QPushButton(preset.name.replace("&", "&&"))
            btn.setStyleSheet(
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {preset.color_primary}, stop:0.55 {preset.color_secondary}, stop:1 {preset.color_accent1});"
                f"color: {'#0f172a' if preset.id == 'pastel_crystal' else '#ffffff'};"
                f"border: 1px solid {preset.color_accent2}; border-radius: 6px; padding: 7px 10px; font-weight: 700;"
            )
            btn.clicked.connect(lambda _, pr=preset: self._apply_preset(pr))
            gp_lay.addWidget(btn, idx // 4, idx % 4)
        v.addWidget(grp_presets)

        # Sélecteurs de couleurs + Mélangeur
        grp_mix = QGroupBox("Mélangeur de Couleurs sur Mesure")
        gm = QVBoxLayout(grp_mix)

        self.chk_custom_colors = QCheckBox("Activer la palette de couleurs mélangées sur toute l'interface")
        self.chk_custom_colors.toggled.connect(self._on_controls_edited)
        gm.addWidget(self.chk_custom_colors)

        swatches = QHBoxLayout()
        self.btn_col_p1 = QPushButton()
        self.btn_col_p2 = QPushButton()
        self.btn_col_a1 = QPushButton()
        self.btn_col_a2 = QPushButton()
        for label_txt, btn, attr in [
            ("Fond 1", self.btn_col_p1, "color_primary"),
            ("Fond 2", self.btn_col_p2, "color_secondary"),
            ("Accent 1", self.btn_col_a1, "color_accent1"),
            ("Accent 2", self.btn_col_a2, "color_accent2"),
        ]:
            col_box = QVBoxLayout()
            col_box.addWidget(QLabel(label_txt))
            btn.setMinimumHeight(34)
            btn.clicked.connect(lambda _, a=attr: self._pick_color(a))
            col_box.addWidget(btn)
            swatches.addLayout(col_box, 1)

        btn_random = QPushButton("Mélange Aléatoire")
        btn_random.setMinimumHeight(34)
        btn_random.clicked.connect(self._randomize_harmony)
        swatches.addWidget(btn_random)
        gm.addLayout(swatches)

        mix_row = QHBoxLayout()
        self.lbl_mix = QLabel("Dosage du mélange : 45%")
        self.slider_mix = QSlider(Qt.Orientation.Horizontal)
        self.slider_mix.setRange(0, 100)
        self.slider_mix.valueChanged.connect(self._on_controls_edited)
        mix_row.addWidget(self.lbl_mix)
        mix_row.addWidget(self.slider_mix, 1)
        gm.addLayout(mix_row)
        v.addWidget(grp_mix)

        # Paramètres des dégradés & effet verre
        grp_grad = QGroupBox("Style de Dégradé && Transparence Verre (Glassmorphism)")
        gg = QGridLayout(grp_grad)

        self.chk_gradient = QCheckBox("Activer les dégradés sur le fond, les barres et les boutons")
        self.chk_gradient.toggled.connect(self._on_controls_edited)
        gg.addWidget(self.chk_gradient, 0, 0, 1, 3)

        gg.addWidget(QLabel("Type de dégradé :"), 1, 0)
        self.combo_grad_style = QComboBox()
        self.combo_grad_style.addItem("Aurore Multi-Couleurs (4 teintes)", "aurora")
        self.combo_grad_style.addItem("Linéaire Diagonal", "diagonal")
        self.combo_grad_style.addItem("Linéaire Horizontal", "horizontal")
        self.combo_grad_style.addItem("Linéaire Vertical", "vertical")
        self.combo_grad_style.addItem("Radial Lumineux", "radial")
        self.combo_grad_style.currentIndexChanged.connect(self._on_controls_edited)
        gg.addWidget(self.combo_grad_style, 1, 1, 1, 2)

        self.lbl_angle = QLabel("Angle du dégradé : 135°")
        self.slider_angle = QSlider(Qt.Orientation.Horizontal)
        self.slider_angle.setRange(0, 360)
        self.slider_angle.valueChanged.connect(self._on_controls_edited)
        gg.addWidget(self.lbl_angle, 2, 0)
        gg.addWidget(self.slider_angle, 2, 1, 1, 2)

        self.lbl_glass = QLabel("Opacité des panneaux (Verre) : 84%")
        self.slider_glass = QSlider(Qt.Orientation.Horizontal)
        self.slider_glass.setRange(40, 100)
        self.slider_glass.valueChanged.connect(self._on_controls_edited)
        gg.addWidget(self.lbl_glass, 3, 0)
        gg.addWidget(self.slider_glass, 3, 1, 1, 2)

        v.addWidget(grp_grad)
        v.addStretch(1)
        return page

    # ------------------------------------------
    # Onglet 2 : Plusieurs Images & Diaporama
    # ------------------------------------------

    def _build_images_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(10)

        top_btns = QHBoxLayout()
        btn_add_files = QPushButton("+ Choisir plusieurs images...")
        btn_add_files.setProperty("primary", True)
        btn_add_files.clicked.connect(self._choose_multiple_images)

        btn_add_omarchy = QPushButton("+ Importer fonds Omarchy / Images")
        btn_add_omarchy.clicked.connect(self._import_omarchy_images)

        btn_add_builtin = QPushButton("+ Fonds artistiques intégrés")
        btn_add_builtin.clicked.connect(self._add_builtin_wallpapers)

        top_btns.addWidget(btn_add_files)
        top_btns.addWidget(btn_add_omarchy)
        top_btns.addWidget(btn_add_builtin)
        v.addLayout(top_btns)

        self.img_list = QListWidget()
        self.img_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.img_list.setIconSize(QSize(136, 80))
        self.img_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.img_list.setSpacing(8)
        self.img_list.setMovement(QListWidget.Movement.Static)
        self.img_list.itemClicked.connect(self._on_gallery_item_clicked)
        v.addWidget(self.img_list, 1)

        nav_row = QHBoxLayout()
        btn_prev = QPushButton("◀ Image précédente")
        btn_prev.clicked.connect(self._prev_gallery_image)
        btn_next = QPushButton("Image suivante ▶")
        btn_next.clicked.connect(self._next_gallery_image)
        btn_remove = QPushButton("Retirer la sélection")
        btn_remove.clicked.connect(self._remove_selected_image)
        btn_clear = QPushButton("Vider la galerie")
        btn_clear.setProperty("danger", True)
        btn_clear.clicked.connect(self._clear_images)

        nav_row.addWidget(btn_prev)
        nav_row.addWidget(btn_next)
        nav_row.addStretch(1)
        nav_row.addWidget(btn_remove)
        nav_row.addWidget(btn_clear)
        v.addLayout(nav_row)

        grp_slide = QGroupBox("Diaporama Animé && Intensité des Images")
        gs = QGridLayout(grp_slide)

        self.chk_slideshow = QCheckBox("Alterner automatiquement entre les images choisies (fondu enchaîné)")
        self.chk_slideshow.toggled.connect(self._on_controls_edited)
        gs.addWidget(self.chk_slideshow, 0, 0, 1, 2)

        gs.addWidget(QLabel("Intervalle du diaporama (secondes) :"), 0, 2)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(4, 120)
        self.spin_interval.setSuffix(" s")
        self.spin_interval.valueChanged.connect(self._on_controls_edited)
        gs.addWidget(self.spin_interval, 0, 3)

        self.lbl_img_opacity = QLabel("Visibilité des images sous le dégradé : 38%")
        self.slider_img_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_img_opacity.setRange(5, 90)
        self.slider_img_opacity.valueChanged.connect(self._on_controls_edited)
        gs.addWidget(self.lbl_img_opacity, 1, 0, 1, 2)
        gs.addWidget(self.slider_img_opacity, 1, 2, 1, 2)

        v.addWidget(grp_slide)
        return page

    # ------------------------------------------
    # Onglet 3 : Animations Fluides
    # ------------------------------------------

    def _build_animations_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(12)

        grp = QGroupBox("Moteur d'Animations && Effets Visuels")
        gl = QVBoxLayout(grp)
        gl.setSpacing(10)

        self.chk_anim_master = QCheckBox("Activer les animations globales de l'interface")
        self.chk_anim_gradient = QCheckBox("Mouvement vivant du dégradé && ruban lumineux supérieur")
        self.chk_anim_orbs = QCheckBox("Halos lumineux flottants (mélange doux d'Accent 1 && Accent 2)")
        self.chk_anim_ui = QCheckBox(
            "Transitions fluides des panneaux, fondu d'onglets, fondu d'images && pulsation Pas-à-Pas"
        )

        for cb in (self.chk_anim_master, self.chk_anim_gradient, self.chk_anim_orbs, self.chk_anim_ui):
            cb.toggled.connect(self._on_controls_edited)
            gl.addWidget(cb)

        sp_row = QHBoxLayout()
        self.lbl_speed = QLabel("Vitesse des animations : 50%")
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(10, 100)
        self.slider_speed.valueChanged.connect(self._on_controls_edited)
        sp_row.addWidget(self.lbl_speed)
        sp_row.addWidget(self.slider_speed, 1)
        gl.addLayout(sp_row)

        v.addWidget(grp)

        info = QFrame()
        il = QVBoxLayout(info)
        lbl_note = QLabel(
            "Astuce : combinez un dégradé Aurore, 3 ou 4 images en diaporama et une opacité "
            "de panneaux autour de 78–85% pour obtenir un rendu verre dépoli fluide tout en "
            "conservant une lisibilité parfaite du code algorithmique."
        )
        lbl_note.setWordWrap(True)
        il.addWidget(lbl_note)
        v.addWidget(info)
        v.addStretch(1)
        return page

    # ------------------------------------------
    # Synchronisation & Événements
    # ------------------------------------------

    def _sync_ui_from_cfg(self) -> None:
        self._updating_ui = True
        c = self.cfg

        self.chk_custom_colors.setChecked(c.custom_colors_enabled)
        self._refresh_swatch_buttons()
        self.slider_mix.setValue(c.mix_ratio)
        self.lbl_mix.setText(f"Dosage du mélange : {c.mix_ratio}%")

        self.chk_gradient.setChecked(c.gradient_enabled)
        idx = self.combo_grad_style.findData(c.gradient_style)
        if idx >= 0:
            self.combo_grad_style.setCurrentIndex(idx)
        self.slider_angle.setValue(c.gradient_angle)
        self.lbl_angle.setText(f"Angle du dégradé : {c.gradient_angle}°")
        self.slider_glass.setValue(c.glass_opacity)
        self.lbl_glass.setText(f"Opacité des panneaux (Verre) : {c.glass_opacity}%")

        self.chk_slideshow.setChecked(c.slideshow_enabled)
        self.spin_interval.setValue(c.slideshow_interval_sec)
        self.slider_img_opacity.setValue(c.image_opacity)
        self.lbl_img_opacity.setText(f"Visibilité des images sous le dégradé : {c.image_opacity}%")

        self.chk_anim_master.setChecked(c.animations_enabled)
        self.chk_anim_gradient.setChecked(c.anim_gradient_flow)
        self.chk_anim_orbs.setChecked(c.anim_ambient_orbs)
        self.chk_anim_ui.setChecked(c.anim_ui_transitions)
        self.slider_speed.setValue(c.anim_speed)
        self.lbl_speed.setText(f"Vitesse des animations : {c.anim_speed}%")

        self._rebuild_gallery_list()
        self._updating_ui = False
        self.preview.update_preview(self.cfg)

    def _refresh_swatch_buttons(self) -> None:
        for btn, hex_val in [
            (self.btn_col_p1, self.cfg.color_primary),
            (self.btn_col_p2, self.cfg.color_secondary),
            (self.btn_col_a1, self.cfg.color_accent1),
            (self.btn_col_a2, self.cfg.color_accent2),
        ]:
            r, g, b = hex_to_rgb(hex_val)
            fg = "#0f172a" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#ffffff"
            btn.setText(hex_val.upper())
            btn.setStyleSheet(
                f"background-color: {hex_val}; color: {fg}; border: 1px solid #94a3b8;"
                "border-radius: 6px; font-weight: 700; padding: 5px;"
            )

    def _rebuild_gallery_list(self) -> None:
        self.img_list.clear()
        builtin_names = dict(BUILTIN_WALLPAPERS)
        for idx, key in enumerate(self.cfg.background_images):
            title = builtin_names.get(key, Path(key).name)
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(key)
            pm = self._make_thumbnail(key)
            if pm is not None:
                item.setIcon(QIcon(pm))
            self.img_list.addItem(item)
            if idx == self.cfg.active_image_index:
                self.img_list.setCurrentItem(item)

    def _make_thumbnail(self, key: str) -> Optional[QPixmap]:
        if key.startswith("builtin:"):
            return render_builtin_wallpaper(key, 272, 160)
        p = Path(key)
        if p.exists():
            pm = QPixmap(str(p))
            if not pm.isNull():
                return pm.scaled(
                    272,
                    160,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
        return None

    def _apply_preset(self, preset: GradientPreset) -> None:
        self.cfg.custom_colors_enabled = True
        self.cfg.preset_id = preset.id
        self.cfg.color_primary = preset.color_primary
        self.cfg.color_secondary = preset.color_secondary
        self.cfg.color_accent1 = preset.color_accent1
        self.cfg.color_accent2 = preset.color_accent2
        self.cfg.gradient_enabled = True
        self.cfg.gradient_style = preset.gradient_style
        self.cfg.gradient_angle = preset.gradient_angle
        self.cfg.mix_ratio = preset.mix_ratio
        self._sync_ui_from_cfg()
        self._emit_live()

    def _pick_color(self, attr_name: str) -> None:
        cur_hex = getattr(self.cfg, attr_name)
        chosen = QColorDialog.getColor(QColor(cur_hex), self, "Choisir une couleur")
        if chosen.isValid():
            setattr(self.cfg, attr_name, chosen.name())
            self.cfg.custom_colors_enabled = True
            self._sync_ui_from_cfg()
            self._emit_live()

    def _randomize_harmony(self) -> None:
        hue = random.randint(0, 359)
        hue2 = (hue + random.choice([35, 55, 140, 200])) % 360
        c1 = QColor.fromHsl(hue, 140, 26).name()
        c2 = QColor.fromHsl(hue2, 165, 44).name()
        a1 = QColor.fromHsl(hue, 230, 155).name()
        a2 = QColor.fromHsl(hue2, 230, 165).name()
        self.cfg.custom_colors_enabled = True
        self.cfg.gradient_enabled = True
        self.cfg.color_primary = c1
        self.cfg.color_secondary = c2
        self.cfg.color_accent1 = a1
        self.cfg.color_accent2 = a2
        self.cfg.mix_ratio = random.randint(35, 65)
        self.cfg.gradient_angle = random.choice([45, 120, 135, 160, 215])
        self._sync_ui_from_cfg()
        self._emit_live()

    def _choose_multiple_images(self) -> None:
        start_dir = str(Path.home() / "Pictures") if (Path.home() / "Pictures").exists() else str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Choisir une ou plusieurs images d'arrière-plan",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;Tous les fichiers (*)",
        )
        if files:
            for f in files:
                if f not in self.cfg.background_images:
                    self.cfg.background_images.append(f)
            self.cfg.active_image_index = max(0, len(self.cfg.background_images) - len(files))
            if self.cfg.glass_opacity > 90:
                self.cfg.glass_opacity = 82
            self._sync_ui_from_cfg()
            self._emit_live()

    def _import_omarchy_images(self) -> None:
        found = discover_omarchy_wallpapers(max_count=16)
        if not found:
            # Si aucun dossier Omarchy standard n'est trouvé, ouvre le sélecteur multi-images
            self._choose_multiple_images()
            return
        added = 0
        for f in found:
            if f not in self.cfg.background_images:
                self.cfg.background_images.append(f)
                added += 1
        if added > 0 and self.cfg.glass_opacity > 90:
            self.cfg.glass_opacity = 82
        self._sync_ui_from_cfg()
        self._emit_live()

    def _add_builtin_wallpapers(self) -> None:
        for key, _ in BUILTIN_WALLPAPERS:
            if key not in self.cfg.background_images:
                self.cfg.background_images.append(key)
        if self.cfg.glass_opacity > 90:
            self.cfg.glass_opacity = 80
        self._sync_ui_from_cfg()
        self._emit_live()

    def _on_gallery_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.img_list.row(item)
        if 0 <= row < len(self.cfg.background_images):
            self.cfg.active_image_index = row
            self._emit_live()

    def _prev_gallery_image(self) -> None:
        if self.cfg.background_images:
            self.cfg.active_image_index = (self.cfg.active_image_index - 1) % len(self.cfg.background_images)
            self._sync_ui_from_cfg()
            self._emit_live()

    def _next_gallery_image(self) -> None:
        if self.cfg.background_images:
            self.cfg.active_image_index = (self.cfg.active_image_index + 1) % len(self.cfg.background_images)
            self._sync_ui_from_cfg()
            self._emit_live()

    def _remove_selected_image(self) -> None:
        row = self.img_list.currentRow()
        if 0 <= row < len(self.cfg.background_images):
            self.cfg.background_images.pop(row)
            self.cfg.active_image_index = max(0, min(self.cfg.active_image_index, len(self.cfg.background_images) - 1))
            self._sync_ui_from_cfg()
            self._emit_live()

    def _clear_images(self) -> None:
        self.cfg.background_images.clear()
        self.cfg.active_image_index = 0
        self._sync_ui_from_cfg()
        self._emit_live()

    def _reset_classic(self) -> None:
        self.cfg = AppearanceConfig(
            custom_colors_enabled=False,
            gradient_enabled=False,
            glass_opacity=100,
            background_images=[],
            animations_enabled=True,
            anim_gradient_flow=False,
            anim_ambient_orbs=False,
            anim_ui_transitions=True,
        )
        self._sync_ui_from_cfg()
        self._emit_live()

    def _on_controls_edited(self) -> None:
        if getattr(self, "_updating_ui", False):
            return
        c = self.cfg
        c.custom_colors_enabled = self.chk_custom_colors.isChecked()
        c.mix_ratio = self.slider_mix.value()
        c.gradient_enabled = self.chk_gradient.isChecked()
        c.gradient_style = str(self.combo_grad_style.currentData())
        c.gradient_angle = self.slider_angle.value()
        c.glass_opacity = self.slider_glass.value()

        c.slideshow_enabled = self.chk_slideshow.isChecked()
        c.slideshow_interval_sec = self.spin_interval.value()
        c.image_opacity = self.slider_img_opacity.value()

        c.animations_enabled = self.chk_anim_master.isChecked()
        c.anim_gradient_flow = self.chk_anim_gradient.isChecked()
        c.anim_ambient_orbs = self.chk_anim_orbs.isChecked()
        c.anim_ui_transitions = self.chk_anim_ui.isChecked()
        c.anim_speed = self.slider_speed.value()

        self.lbl_mix.setText(f"Dosage du mélange : {c.mix_ratio}%")
        self.lbl_angle.setText(f"Angle du dégradé : {c.gradient_angle}°")
        self.lbl_glass.setText(f"Opacité des panneaux (Verre) : {c.glass_opacity}%")
        self.lbl_img_opacity.setText(f"Visibilité des images sous le dégradé : {c.image_opacity}%")
        self.lbl_speed.setText(f"Vitesse des animations : {c.anim_speed}%")

        self.preview.update_preview(c)
        self._emit_live()

    def _emit_live(self) -> None:
        self.appearanceChanged.emit(AppearanceConfig.from_dict(self.cfg.to_dict()))
