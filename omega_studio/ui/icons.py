"""
Générateur d'icônes vectorielles HiDPI nettes via QPainter.
Garantit un rendu impeccable sous Wayland / Hyprland (Omarchy) à n'importe quelle échelle.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


def make_icon(kind: str, color_hex: str = "#c0caf5", size: int = 22) -> QIcon:
    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2.0)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    col = QColor(color_hex)
    pen = QPen(col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    s = float(size)
    m = 3.5

    if kind == "play":
        p.setBrush(col)
        poly = QPolygonF([QPointF(m + 2, m), QPointF(s - m, s / 2), QPointF(m + 2, s - m)])
        p.drawPolygon(poly)

    elif kind == "stop":
        p.setBrush(col)
        p.drawRoundedRect(QRectF(m + 1.5, m + 1.5, s - 2 * m - 3, s - 2 * m - 3), 2.5, 2.5)

    elif kind == "step_over":
        p.drawArc(QRectF(m + 1, m + 2, s - 2 * m - 2, s - 2 * m - 4), 25 * 16, 130 * 16)
        p.drawLine(QPointF(s - m - 1, s / 2), QPointF(s - m - 4.5, s / 2 - 3))
        p.drawLine(QPointF(s - m - 1, s / 2), QPointF(s - m - 2, s / 2 + 3.5))
        p.setBrush(col)
        p.drawEllipse(QPointF(s / 2, s - m - 2), 2.2, 2.2)

    elif kind == "step_into":
        p.drawLine(QPointF(s / 2, m), QPointF(s / 2, s - m - 4))
        p.drawLine(QPointF(s / 2 - 3.5, s - m - 7.5), QPointF(s / 2, s - m - 4))
        p.drawLine(QPointF(s / 2 + 3.5, s - m - 7.5), QPointF(s / 2, s - m - 4))
        p.setBrush(col)
        p.drawEllipse(QPointF(s / 2, s - m - 1), 2.0, 2.0)

    elif kind == "auto_step":
        p.setBrush(col)
        poly1 = QPolygonF([QPointF(m, m + 1), QPointF(s / 2, s / 2), QPointF(m, s - m - 1)])
        poly2 = QPolygonF([QPointF(s / 2, m + 1), QPointF(s - m, s / 2), QPointF(s / 2, s - m - 1)])
        p.drawPolygon(poly1)
        p.drawPolygon(poly2)

    elif kind == "verify":
        p.drawEllipse(QRectF(m, m, s - 2 * m, s - 2 * m))
        p.drawLine(QPointF(m + 3.5, s / 2 + 0.5), QPointF(s / 2 - 1, s - m - 4))
        p.drawLine(QPointF(s / 2 - 1, s - m - 4), QPointF(s - m - 3, m + 4.5))

    elif kind == "format":
        p.drawLine(QPointF(m, m + 2), QPointF(s - m, m + 2))
        p.drawLine(QPointF(m + 4, s / 2), QPointF(s - m, s / 2))
        p.drawLine(QPointF(m + 4, s - m - 2), QPointF(s - m - 3, s - m - 2))

    elif kind == "new_file":
        path = QPainterPath()
        path.moveTo(m + 2, m)
        path.lineTo(s - m - 5, m)
        path.lineTo(s - m - 1, m + 4)
        path.lineTo(s - m - 1, s - m)
        path.lineTo(m + 2, s - m)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(s / 2, s / 2 - 2), QPointF(s / 2, s / 2 + 4))
        p.drawLine(QPointF(s / 2 - 3, s / 2 + 1), QPointF(s / 2 + 3, s / 2 + 1))

    elif kind == "open_file":
        path = QPainterPath()
        path.moveTo(m, m + 3)
        path.lineTo(m + 5, m + 3)
        path.lineTo(m + 7, m + 5.5)
        path.lineTo(s - m, m + 5.5)
        path.lineTo(s - m - 1.5, s - m - 1)
        path.lineTo(m + 1, s - m - 1)
        path.closeSubpath()
        p.drawPath(path)

    elif kind == "save":
        p.drawRoundedRect(QRectF(m + 1, m + 1, s - 2 * m - 2, s - 2 * m - 2), 2.0, 2.0)
        p.drawRect(QRectF(m + 4, m + 1, s - 2 * m - 8, 5))
        p.drawRect(QRectF(m + 3.5, s - m - 6.5, s - 2 * m - 7, 5.5))

    elif kind == "keywords":
        p.drawRoundedRect(QRectF(m, m + 1, s - 2 * m, s - 2 * m - 2), 3.0, 3.0)
        p.drawLine(QPointF(m + 3.5, m + 5.5), QPointF(m + 6.5, s / 2))
        p.drawLine(QPointF(m + 6.5, s / 2), QPointF(m + 3.5, s - m - 5.5))
        p.drawLine(QPointF(s / 2 + 0.5, s - m - 5), QPointF(s - m - 3.5, s - m - 5))

    elif kind == "flowchart":
        p.drawRoundedRect(QRectF(s / 2 - 4.5, m, 9, 4.5), 2.0, 2.0)
        p.drawLine(QPointF(s / 2, m + 4.5), QPointF(s / 2, s / 2 - 2.5))
        dia = QPolygonF(
            [
                QPointF(s / 2, s / 2 - 2.5),
                QPointF(s / 2 + 5, s / 2 + 1.5),
                QPointF(s / 2, s / 2 + 5.5),
                QPointF(s / 2 - 5, s / 2 + 1.5),
            ]
        )
        p.drawPolygon(dia)
        p.drawLine(QPointF(s / 2, s / 2 + 5.5), QPointF(s / 2, s - m))

    elif kind == "translate":
        p.drawLine(QPointF(m, m + 3), QPointF(s / 2 + 1, m + 3))
        p.drawLine(QPointF(m + 4, m + 1), QPointF(m + 4, m + 3))
        p.drawLine(QPointF(m + 2, m + 3), QPointF(m + 7, m + 10))
        p.drawLine(QPointF(m + 7, m + 3), QPointF(m + 2, m + 10))
        p.drawLine(QPointF(s / 2 + 1, s - m), QPointF(s / 2 + 4.5, s / 2 - 1))
        p.drawLine(QPointF(s - m, s - m), QPointF(s / 2 + 4.5, s / 2 - 1))
        p.drawLine(QPointF(s / 2 + 2.2, s - m - 3), QPointF(s - m - 1.2, s - m - 3))

    elif kind == "customize":
        p.drawLine(QPointF(m, m + 3), QPointF(s - m, m + 3))
        p.drawLine(QPointF(m, s / 2), QPointF(s - m, s / 2))
        p.drawLine(QPointF(m, s - m - 3), QPointF(s - m, s - m - 3))
        p.setBrush(col)
        p.drawEllipse(QPointF(m + 4, m + 3), 2.2, 2.2)
        p.drawEllipse(QPointF(s - m - 4, s / 2), 2.2, 2.2)
        p.drawEllipse(QPointF(m + 6, s - m - 3), 2.2, 2.2)

    elif kind == "help":
        p.drawEllipse(QRectF(m, m, s - 2 * m, s - 2 * m))
        f = QFont("Sans Serif", int(s * 0.48), QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "?")

    elif kind == "theme":
        path = QPainterPath()
        path.addEllipse(QRectF(m + 1, m + 1, s - 2 * m - 2, s - 2 * m - 2))
        cut = QPainterPath()
        cut.addEllipse(QRectF(m + 5, m - 1, s - 2 * m - 2, s - 2 * m - 2))
        crescent = path.subtracted(cut)
        p.setBrush(col)
        p.drawPath(crescent)

    p.end()
    return QIcon(pix)


def make_app_logo_icon(size: int = 64) -> QIcon:
    """Icône d'application Omega Studio Code (symbole Ω moderne sur dégradé sombre)."""
    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2.0)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    s = float(size)

    p.setPen(QPen(QColor("#7aa2f7"), 2.5))
    p.setBrush(QColor("#1a1b26"))
    p.drawRoundedRect(QRectF(3, 3, s - 6, s - 6), s * 0.22, s * 0.22)

    font = QFont("Sans Serif", int(s * 0.48), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#7aa2f7"))
    p.drawText(QRectF(0, -2, s, s), Qt.AlignmentFlag.AlignCenter, "Ω")

    p.end()
    return QIcon(pix)
