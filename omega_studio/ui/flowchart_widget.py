"""
Vue interactive d'Organigramme (FlowchartWidget) basée sur QGraphicsView / QGraphicsScene.
Dessine des formes normalisées (Début/Fin, Affectation, Saisie/Affichage, Losange SI/Boucle, Sous-programme),
suit en temps réel la ligne active du débogueur Pas-à-Pas et permet l'export en PNG.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.ast_nodes import Program
from ..core.flowchart import FlowEdge, FlowGraph, FlowNode, FlowchartBuilder
from .themes import StudioTheme


class InteractiveGraphView(QGraphicsView):
    """Vue graphique avec zoom molette fluide et déplacement à la souris (Drag)."""

    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
        self.scale(factor, factor)


class FlowchartWidget(QWidget):
    """Panneau d'organigramme algorithmique automatique synchronisé avec l'éditeur et le débogueur."""

    nodeClickedLine = pyqtSignal(int)

    def __init__(self, theme: StudioTheme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self._program: Optional[Program] = None
        self._graph: Optional[FlowGraph] = None
        self._active_line: Optional[int] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)
        self.sub_combo = QComboBox()
        self.sub_combo.setMinimumWidth(120)
        self.btn_fit = QPushButton("Ajuster")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_in.setFixedWidth(28)
        self.btn_zoom_out.setFixedWidth(28)
        self.btn_export = QPushButton("Export PNG")
        self.btn_export.setToolTip("Exporter l'organigramme complet en image PNG haute définition")

        toolbar.addWidget(QLabel("Vue :"))
        toolbar.addWidget(self.sub_combo, 1)
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_zoom_in)
        toolbar.addWidget(self.btn_fit)
        toolbar.addWidget(self.btn_export)

        self.scene = QGraphicsScene(self)
        self.view = InteractiveGraphView(self.scene, self)

        layout.addLayout(toolbar)
        layout.addWidget(self.view, 1)

        self.sub_combo.currentIndexChanged.connect(self._rebuild_scene)
        self.btn_zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        self.btn_zoom_out.clicked.connect(lambda: self.view.scale(1 / 1.2, 1 / 1.2))
        self.btn_fit.clicked.connect(self.fit_diagram)
        self.btn_export.clicked.connect(self.export_png)

        self.apply_theme(theme)

    def apply_theme(self, theme: StudioTheme) -> None:
        self.theme = theme
        self.view.setBackgroundBrush(QBrush(QColor(theme.bg_editor)))
        self.view.setStyleSheet(f"border: 1px solid {theme.border}; border-radius: 6px;")
        self._render_graph()

    def set_program(self, program: Optional[Program]) -> None:
        self._program = program
        self.sub_combo.blockSignals(True)
        prev_txt = self.sub_combo.currentData()
        self.sub_combo.clear()
        if program is not None:
            self.sub_combo.addItem(f"Principal ({program.name})", None)
            for sp in program.subprograms:
                self.sub_combo.addItem(f"{sp.kind.title()} : {sp.name}", sp.name)
            if prev_txt is not None:
                idx = self.sub_combo.findData(prev_txt)
                if idx >= 0:
                    self.sub_combo.setCurrentIndex(idx)
        self.sub_combo.blockSignals(False)
        self._rebuild_scene()

    def set_active_line(self, line: Optional[int]) -> None:
        if self._active_line != line:
            self._active_line = line
            self._render_graph(center_active=True)

    def _rebuild_scene(self) -> None:
        if self._program is None:
            self._graph = None
            self.scene.clear()
            return
        sub_name = self.sub_combo.currentData()
        builder = FlowchartBuilder()
        self._graph = builder.build_for_program(self._program, subprogram_name=sub_name)
        self._render_graph()

    def _render_graph(self, center_active: bool = False) -> None:
        self.scene.clear()
        if self._graph is None or not self._graph.nodes:
            return

        t = self.theme
        node_map: Dict[int, FlowNode] = {n.id: n for n in self._graph.nodes}

        # 1. Dessine les flèches de liaison en arrière-plan
        for edge in self._graph.edges:
            src = node_map.get(edge.src_id)
            dst = node_map.get(edge.dst_id)
            if not src or not dst:
                continue
            self._draw_edge(src, dst, edge)

        # 2. Dessine les nœuds normalisés
        active_rect: Optional[QRectF] = None
        font = QFont("Sans Serif", 9, QFont.Weight.DemiBold)

        for node in self._graph.nodes:
            left = node.x - node.width / 2.0
            rect = QRectF(left, node.y, node.width, node.height)
            is_active = self._active_line is not None and node.line == self._active_line and node.shape != "JUNCTION"

            if node.shape == "JUNCTION":
                pen = QPen(QColor(t.fg_muted), 1.5)
                brush = QBrush(QColor(t.bg_elevated))
                self.scene.addEllipse(QRectF(node.x - 5, node.y + node.height / 2.0 - 5, 10, 10), pen, brush)
                continue

            border_col, fill_col = self._colors_for_shape(node.shape)
            if is_active:
                border_col = QColor(t.warning)
                fill_col = QColor(t.line_debug)
                active_rect = rect

            pen = QPen(border_col, 2.8 if is_active else 1.8)
            brush = QBrush(fill_col)

            if node.shape == "TERMINAL":
                path = QPainterPath()
                path.addRoundedRect(rect, node.height / 2.0, node.height / 2.0)
                self.scene.addPath(path, pen, brush)

            elif node.shape == "IO":
                skew = 16.0
                poly = QPolygonF(
                    [
                        QPointF(rect.left() + skew, rect.top()),
                        QPointF(rect.right(), rect.top()),
                        QPointF(rect.right() - skew, rect.bottom()),
                        QPointF(rect.left(), rect.bottom()),
                    ]
                )
                self.scene.addPolygon(poly, pen, brush)

            elif node.shape == "DECISION":
                poly = QPolygonF(
                    [
                        QPointF(rect.center().x(), rect.top()),
                        QPointF(rect.right(), rect.center().y()),
                        QPointF(rect.center().x(), rect.bottom()),
                        QPointF(rect.left(), rect.center().y()),
                    ]
                )
                self.scene.addPolygon(poly, pen, brush)

            elif node.shape == "SUBCALL":
                self.scene.addRect(rect, pen, brush)
                inner_pen = QPen(border_col, 1.3)
                self.scene.addLine(rect.left() + 10, rect.top(), rect.left() + 10, rect.bottom(), inner_pen)
                self.scene.addLine(rect.right() - 10, rect.top(), rect.right() - 10, rect.bottom(), inner_pen)

            else:  # PROCESS
                path = QPainterPath()
                path.addRoundedRect(rect, 7.0, 7.0)
                self.scene.addPath(path, pen, brush)

            # Texte centré dans la forme
            txt_item = self.scene.addText(node.label, font)
            if txt_item:
                txt_item.setDefaultTextColor(QColor(t.fg_primary))
                txt_item.setTextWidth(node.width - 24)
                opt = txt_item.document().defaultTextOption()
                opt.setAlignment(Qt.AlignmentFlag.AlignCenter)
                txt_item.document().setDefaultTextOption(opt)
                tb = txt_item.boundingRect()
                txt_item.setPos(node.x - tb.width() / 2.0, node.y + (node.height - tb.height()) / 2.0)

        bounds = self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        self.scene.setSceneRect(bounds)

        if center_active and active_rect is not None:
            self.view.centerOn(active_rect.center())

    def _colors_for_shape(self, shape: str) -> Tuple[QColor, QColor]:
        t = self.theme
        if shape == "TERMINAL":
            return QColor(t.syn_keyword), QColor(t.bg_elevated)
        if shape == "DECISION":
            return QColor(t.accent), QColor(t.bg_sidebar)
        if shape == "IO":
            return QColor(t.success), QColor(t.bg_elevated)
        if shape == "SUBCALL":
            return QColor(t.syn_type), QColor(t.bg_elevated)
        return QColor(t.fg_muted), QColor(t.bg_elevated)

    def _draw_edge(self, src: FlowNode, dst: FlowNode, edge: FlowEdge) -> None:
        t = self.theme
        if edge.kind == "TRUE":
            col = QColor(t.success)
        elif edge.kind == "FALSE":
            col = QColor(t.danger)
        elif edge.kind == "LOOP_BACK":
            col = QColor(t.syn_keyword)
        else:
            col = QColor(t.fg_muted)

        pen = QPen(col, 1.7, Qt.PenStyle.DashLine if edge.kind == "LOOP_BACK" else Qt.PenStyle.SolidLine)

        # Point de départ
        if edge.waypoints:
            first_wp = edge.waypoints[0]
            if src.shape == "DECISION" and abs(first_wp[1] - (src.y + src.height / 2.0)) < 2.0:
                sx = src.x - src.width / 2.0 if first_wp[0] < src.x else src.x + src.width / 2.0
                sy = src.y + src.height / 2.0
            else:
                sx, sy = src.x, src.y + src.height
        else:
            sx, sy = src.x, src.y + (src.height / 2.0 if src.shape == "JUNCTION" else src.height)

        # Point d'arrivée
        if edge.waypoints and edge.kind == "LOOP_BACK":
            ex = dst.x - (dst.width / 2.0 if dst.shape != "JUNCTION" else 5.0)
            ey = dst.y + dst.height / 2.0
        elif edge.waypoints and dst.shape == "JUNCTION":
            last_wp = edge.waypoints[-1]
            ex = dst.x - 5.0 if last_wp[0] < dst.x else dst.x + 5.0
            ey = dst.y + dst.height / 2.0
        else:
            ex, ey = dst.x, dst.y + (dst.height / 2.0 - 5.0 if dst.shape == "JUNCTION" else 0.0)

        pts: List[QPointF] = [QPointF(sx, sy)] + [QPointF(wx, wy) for wx, wy in edge.waypoints] + [QPointF(ex, ey)]

        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        self.scene.addPath(path, pen)

        # Pointe de flèche sur le dernier segment
        p1, p2 = pts[-2], pts[-1]
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arr_len = 8.0
        a1 = QPointF(p2.x() - arr_len * math.cos(angle - 0.45), p2.y() - arr_len * math.sin(angle - 0.45))
        a2 = QPointF(p2.x() - arr_len * math.cos(angle + 0.45), p2.y() - arr_len * math.sin(angle + 0.45))
        self.scene.addPolygon(QPolygonF([p2, a1, a2]), QPen(col, 1.0), QBrush(col))

        if edge.label:
            lbl_item = self.scene.addText(edge.label, QFont("Sans Serif", 8, QFont.Weight.Bold))
            if lbl_item:
                lbl_item.setDefaultTextColor(col)
                mid = pts[1] if len(pts) > 2 else QPointF((sx + ex) / 2.0 + 4, (sy + ey) / 2.0 - 10)
                lbl_item.setPos(mid.x() + 4, mid.y() - 18)

    def fit_diagram(self) -> None:
        rect = self.scene.itemsBoundingRect()
        if not rect.isEmpty():
            self.view.fitInView(rect.adjusted(-25, -25, 25, 25), Qt.AspectRatioMode.KeepAspectRatio)

    def export_png(self) -> None:
        if self.scene.itemsBoundingRect().isEmpty():
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter l'organigramme en PNG",
            "organigramme.png",
            "Images PNG (*.png)",
        )
        if not file_path:
            return
        self.save_png_to_path(file_path)

    def save_png_to_path(self, file_path: str) -> bool:
        rect = self.scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        if rect.isEmpty():
            return False
        img = QImage(int(rect.width() * 2), int(rect.height() * 2), QImage.Format.Format_ARGB32)
        img.fill(QColor(self.theme.bg_editor))
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.scene.render(painter, QRectF(0, 0, img.width(), img.height()), rect)
        painter.end()
        return img.save(file_path)
