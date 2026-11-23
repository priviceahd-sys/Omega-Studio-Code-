"""
Panneau Débogueur Pas-à-Pas & Espion des Variables / Tableaux / Structures / Pile d'appels.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QSlider,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.interpreter import ArrayValue, StructValue
from .themes import StudioTheme


class DebuggerPanel(QWidget):
    """Panneau latéral d'inspection en direct et de pilotage Pas-à-Pas."""

    stepOverRequested = pyqtSignal()
    stepIntoRequested = pyqtSignal()
    autoStepToggled = pyqtSignal(bool)
    continueRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    speedChanged = pyqtSignal(int)  # délai en ms
    frameClicked = pyqtSignal(int)  # numéro de ligne

    def __init__(self, theme: StudioTheme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self._prev_values: Dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Contrôles Pas-à-Pas rapides (modernisation de f_pap d'Alg_32)
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(4)
        self.btn_step_over = QPushButton("Suivant")
        self.btn_step_over.setToolTip("Exécuter l'instruction suivante sans entrer dans les sous-programmes (F10)")
        self.btn_step_into = QPushButton("Entrer")
        self.btn_step_into.setToolTip("Pas-à-Pas détaillé : entrer dans les procédures et fonctions (F11)")
        self.btn_auto = QPushButton("Auto")
        self.btn_auto.setToolTip("Exécution Pas-à-Pas automatique cadencée (F8)")
        self.btn_auto.setCheckable(True)
        self.btn_cont = QPushButton("Continuer")
        self.btn_cont.setToolTip("Continuer jusqu'au prochain point d'arrêt ou jusqu'à la fin (F5)")
        self.btn_stop = QPushButton("Arrêt")
        self.btn_stop.setToolTip("Interrompre l'exécution (Shift+F5)")
        self.btn_stop.setProperty("danger", True)

        for b in (self.btn_step_over, self.btn_step_into, self.btn_auto, self.btn_cont, self.btn_stop):
            b.setStyleSheet("padding: 5px 8px;")
            ctrl_row.addWidget(b)

        # Curseur de vitesse Pas-à-Pas Automatique (remplace Pas à Pas 0 / 1 / 2 d'Alg_32)
        speed_row = QHBoxLayout()
        self.lbl_speed = QLabel("Cadence Auto : 300 ms / instr.")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(40, 1200)
        self.speed_slider.setValue(300)
        self.speed_slider.setToolTip("Ajuste le délai entre deux instructions en mode Pas-à-Pas automatique")
        speed_row.addWidget(self.lbl_speed)
        speed_row.addWidget(self.speed_slider, 1)

        self.lbl_step_counter = QLabel("État : Aucun débogage actif")

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Arbre d'inspection des variables, constantes, tableaux et structures
        var_box = QWidget()
        vb_layout = QVBoxLayout(var_box)
        vb_layout.setContentsMargins(0, 0, 0, 0)
        vb_layout.setSpacing(4)
        vb_layout.addWidget(QLabel("Variables, Tableaux & Structures en mémoire :"))

        self.var_tree = QTreeWidget()
        self.var_tree.setHeaderLabels(["Nom", "Valeur", "Type"])
        self.var_tree.setAlternatingRowColors(True)
        hdr = self.var_tree.header()
        if hdr:
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.var_tree.setColumnWidth(0, 145)
        self.var_tree.setColumnWidth(2, 125)
        vb_layout.addWidget(self.var_tree, 1)

        # Pile d'appels (Call Stack)
        stack_box = QWidget()
        sb_layout = QVBoxLayout(stack_box)
        sb_layout.setContentsMargins(0, 4, 0, 0)
        sb_layout.setSpacing(4)
        sb_layout.addWidget(QLabel("Pile d'appels (Principal / Procédures / Fonctions) :"))
        self.stack_list = QListWidget()
        self.stack_list.setMaximumHeight(130)
        sb_layout.addWidget(self.stack_list)

        splitter.addWidget(var_box)
        splitter.addWidget(stack_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        layout.addLayout(ctrl_row)
        layout.addLayout(speed_row)
        layout.addWidget(self.lbl_step_counter)
        layout.addWidget(splitter, 1)

        self.btn_step_over.clicked.connect(self.stepOverRequested.emit)
        self.btn_step_into.clicked.connect(self.stepIntoRequested.emit)
        self.btn_auto.toggled.connect(self.autoStepToggled.emit)
        self.btn_cont.clicked.connect(self.continueRequested.emit)
        self.btn_stop.clicked.connect(self.stopRequested.emit)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.stack_list.itemClicked.connect(self._on_stack_clicked)

        self.set_debugging_active(False)

    def _on_speed_changed(self, ms: int) -> None:
        self.lbl_speed.setText(f"Cadence Auto : {ms} ms / instr.")
        self.speedChanged.emit(ms)

    def _on_stack_clicked(self, item) -> None:
        line = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(line, int):
            self.frameClicked.emit(line)

    def apply_theme(self, theme: StudioTheme) -> None:
        self.theme = theme

    def set_debugging_active(self, active: bool) -> None:
        self.btn_step_over.setEnabled(active)
        self.btn_step_into.setEnabled(active)
        self.btn_auto.setEnabled(active)
        self.btn_cont.setEnabled(active)
        self.btn_stop.setEnabled(active)
        if not active:
            self.btn_auto.setChecked(False)

    def reset_snapshot(self) -> None:
        self._prev_values.clear()
        self.var_tree.clear()
        self.stack_list.clear()
        self.lbl_step_counter.setText("État : Prêt")

    def update_from_snapshot(self, snap: Dict[str, Any]) -> None:
        line = snap.get("line", 1)
        steps = snap.get("steps", 0)
        frames = snap.get("frames", [])
        self.lbl_step_counter.setText(f"Ligne active : L{line}   •   Instructions exécutées : {steps:,}")

        # Mise à jour de la pile d'appels (sommet en premier)
        self.stack_list.clear()
        for idx, fr in enumerate(reversed(frames)):
            prefix = "▶ " if idx == 0 else "   "
            from PyQt6.QtWidgets import QListWidgetItem

            it = QListWidgetItem(f"{prefix}{fr['name']}  (ligne {fr['line']})")
            it.setData(Qt.ItemDataRole.UserRole, fr["line"])
            self.stack_list.addItem(it)

        # Mise à jour de l'arbre des variables avec conservation de l'état déplié
        expanded_keys = set()
        for i in range(self.var_tree.topLevelItemCount()):
            top_it = self.var_tree.topLevelItem(i)
            if top_it and top_it.isExpanded():
                expanded_keys.add(top_it.text(0))
                for j in range(top_it.childCount()):
                    ch = top_it.child(j)
                    if ch and ch.isExpanded():
                        expanded_keys.add(f"{top_it.text(0)}/{ch.text(0)}")

        self.var_tree.clear()
        new_values: Dict[str, str] = {}

        for fr in reversed(frames):
            scope_title = f"Portée : {fr['name']}"
            scope_item = QTreeWidgetItem([scope_title, "", f"L{fr['line']}"])
            scope_item.setForeground(0, QColor(self.theme.accent))
            self.var_tree.addTopLevelItem(scope_item)

            for cname, cval in fr["consts"].items():
                val_str = self._fmt_val(cval)
                cit = QTreeWidgetItem([cname, val_str, "CONSTANTE"])
                cit.setForeground(2, QColor(self.theme.fg_muted))
                scope_item.addChild(cit)

            for vname, vval in fr["vars"].items():
                key_id = f"{fr['name']}::{vname}"
                node = self._build_var_item(vname, vval, key_id, new_values)
                scope_item.addChild(node)
                if f"{scope_title}/{vname}" in expanded_keys:
                    node.setExpanded(True)

            scope_item.setExpanded(True)

        self._prev_values = new_values

    def _build_var_item(
        self, name: str, val: Any, key_id: str, new_values: Dict[str, str]
    ) -> QTreeWidgetItem:
        if isinstance(val, ArrayValue):
            dims_s = ", ".join(f"{lo}..{hi}" for lo, hi in val.dimensions)
            summary = f"{len(val.cells)} cellules"
            item = QTreeWidgetItem([name, summary, f"tableau[{dims_s}] de {val.base_type.lower()}"])
            for coords in sorted(val.cells.keys())[:200]:
                c_val = val.cells[coords]
                coord_lbl = f"[{', '.join(str(c) for c in coords)}]"
                sub_key = f"{key_id}{coord_lbl}"
                sub_item = self._build_var_item(coord_lbl, c_val, sub_key, new_values)
                item.addChild(sub_item)
            return item

        if isinstance(val, StructValue):
            item = QTreeWidgetItem([name, "{...}", f"structure {val.type_name}"])
            for fk, fval in val.fields.items():
                disp = val.display_names.get(fk, fk)
                sub_item = self._build_var_item(f".{disp}", fval, f"{key_id}.{fk}", new_values)
                item.addChild(sub_item)
            item.setExpanded(True)
            return item

        val_str = self._fmt_val(val)
        new_values[key_id] = val_str
        type_lbl = self._type_label(val)
        item = QTreeWidgetItem([name, val_str, type_lbl])

        # Surligne en vert/ambre toute variable qui vient de changer à cette étape !
        if key_id in self._prev_values and self._prev_values[key_id] != val_str:
            item.setForeground(0, QColor(self.theme.warning))
            item.setForeground(1, QColor(self.theme.success))
        return item

    def _fmt_val(self, val: Any) -> str:
        if isinstance(val, str):
            return f'"{val}"'
        if isinstance(val, bool):
            return ".VRAI." if val else ".FAUX."
        if isinstance(val, float):
            return str(int(val)) if val.is_integer() else f"{val:.8g}"
        return str(val)

    def _type_label(self, val: Any) -> str:
        if isinstance(val, bool):
            return "booléen"
        if isinstance(val, int):
            return "entier"
        if isinstance(val, float):
            return "réel"
        if isinstance(val, str):
            return f"chaîne ({len(val)})"
        return type(val).__name__
