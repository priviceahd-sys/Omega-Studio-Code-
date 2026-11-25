"""
Centre d'Aide Officielle Alg_32 (alg_exec.ini) & Atelier de Personnalisation Algpers32 intégré.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.keywords import (
    STANDARD_KEYWORDS,
    HelpEntry,
    HelpRegistry,
    KeywordProfile,
    import_legacy_alg_exec_ini,
)
from .code_editor import pick_monospace_font
from .themes import StudioTheme, qss_rgba


class HelpBrowserWidget(QWidget):
    """Manuel interactif complet d'Alg_32 (extrait d'alg_exec.ini) avec insertion d'extraits."""

    snippetInsertRequested = pyqtSignal(str)

    def __init__(self, registry: HelpRegistry, theme: StudioTheme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.theme = theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher dans le manuel Alg_32 (ex: POUR, TABLEAU, MILIEU, SQL...)")
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("Toutes les rubriques", "")
        cats = sorted({e.category for e in registry.entries})
        for c in cats:
            self.cat_combo.addItem(c, c)
        search_row.addWidget(self.search_input, 2)
        search_row.addWidget(self.cat_combo, 1)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.topic_list = QListWidget()
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setFont(pick_monospace_font(10))

        splitter.addWidget(self.topic_list)
        splitter.addWidget(self.detail_view)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        btn_row = QHBoxLayout()
        self.btn_insert = QPushButton("+ Insérer l'instruction dans l'éditeur")
        self.btn_insert.setProperty("primary", True)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_insert)

        layout.addLayout(search_row)
        layout.addWidget(splitter, 1)
        layout.addLayout(btn_row)

        self.search_input.textChanged.connect(self._refresh_list)
        self.cat_combo.currentIndexChanged.connect(self._refresh_list)
        self.topic_list.currentItemChanged.connect(self._on_topic_selected)
        self.topic_list.itemDoubleClicked.connect(lambda _: self._emit_snippet())
        self.btn_insert.clicked.connect(self._emit_snippet)

        self._refresh_list()

    def apply_theme(self, theme: StudioTheme, glass_alpha_pct: int = 100) -> None:
        self.theme = theme
        bg_val = qss_rgba(theme.bg_editor, glass_alpha_pct) if glass_alpha_pct < 100 else theme.bg_editor
        self.detail_view.setStyleSheet(
            f"background-color: {bg_val}; color: {theme.fg_primary}; border: 1px solid {theme.border}; padding: 8px;"
        )

    def _refresh_list(self) -> None:
        q = self.search_input.text()
        cat = self.cat_combo.currentData() or ""
        entries = self.registry.search(q)
        if cat:
            entries = [e for e in entries if e.category == cat]

        self.topic_list.clear()
        for entry in entries:
            it = QListWidgetItem(f"[{entry.category}]  {entry.title}")
            it.setData(Qt.ItemDataRole.UserRole, entry)
            self.topic_list.addItem(it)

        if self.topic_list.count() > 0:
            self.topic_list.setCurrentRow(0)

    def _on_topic_selected(self, current: Optional[QListWidgetItem], _: Optional[QListWidgetItem]) -> None:
        if not current:
            self.detail_view.clear()
            return
        entry: HelpEntry = current.data(Qt.ItemDataRole.UserRole)
        header = f"═══ {entry.title} ({entry.category}) ═══\n"
        if entry.snippet:
            header += f"Syntaxe rapide : {entry.snippet}\n"
        header += "─" * 52 + "\n\n"
        self.detail_view.setPlainText(header + entry.body)

    def select_word(self, word: str) -> bool:
        entry = self.registry.find_for_word(word)
        if not entry:
            return False
        self.search_input.clear()
        self.cat_combo.setCurrentIndex(0)
        for i in range(self.topic_list.count()):
            it = self.topic_list.item(i)
            if it and it.data(Qt.ItemDataRole.UserRole).id == entry.id:
                self.topic_list.setCurrentRow(i)
                return True
        return False

    def _emit_snippet(self) -> None:
        it = self.topic_list.currentItem()
        if not it:
            return
        entry: HelpEntry = it.data(Qt.ItemDataRole.UserRole)
        text = entry.snippet or entry.keyword or entry.title.split()[0]
        if text:
            self.snippetInsertRequested.emit(text)


class AlgpersDialog(QDialog):
    """
    Atelier moderne remplaçant `Algpers32.exe` :
    Permet de personnaliser les synonymes de mots-clefs, d'importer un fichier
    historique `alg_exec.ini` ou d'exporter un profil JSON partageable entre étudiants.
    """

    profileUpdated = pyqtSignal(KeywordProfile)

    def __init__(self, profile: KeywordProfile, theme: StudioTheme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Atelier Algpers32 — Personnalisation des mots-clefs")
        self.resize(720, 500)
        self.profile = KeywordProfile(
            name=profile.name,
            custom_aliases=dict(profile.custom_aliases),
            custom_help=dict(profile.custom_help),
        )
        self.theme = theme

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QLabel(
            "Ajoutez vos propres synonymes d'instructions (comme dans Algpers32) ou importez un fichier alg_exec.ini existant."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Nom du profil :"))
        self.name_edit = QLineEdit(self.profile.name)
        self.btn_import_ini = QPushButton("Importer alg_exec.ini")
        self.btn_import_json = QPushButton("Importer .json")
        self.btn_export_json = QPushButton("Exporter .json")
        top_row.addWidget(self.name_edit, 1)
        top_row.addWidget(self.btn_import_ini)
        top_row.addWidget(self.btn_import_json)
        top_row.addWidget(self.btn_export_json)
        layout.addLayout(top_row)

        # Ajout d'un nouvel alias
        add_row = QHBoxLayout()
        self.alias_input = QLineEdit()
        self.alias_input.setPlaceholderText("Nouveau mot-clef personnalisé (ex: MONTRER, TANT_QUE...)")
        self.canon_combo = QComboBox()
        for canon in sorted(STANDARD_KEYWORDS.keys()):
            sample = ", ".join(STANDARD_KEYWORDS[canon][:2])
            self.canon_combo.addItem(f"{canon}  ({sample})", canon)
        self.btn_add = QPushButton("+ Ajouter l'alias")
        self.btn_add.setProperty("primary", True)
        add_row.addWidget(self.alias_input, 2)
        add_row.addWidget(QLabel("→ Instruction :"))
        add_row.addWidget(self.canon_combo, 2)
        add_row.addWidget(self.btn_add)
        layout.addLayout(add_row)

        # Table des alias actifs
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Mot-clef personnalisé", "Instruction Alg_32 cible"])
        hdr = self.table.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        bottom_row = QHBoxLayout()
        self.btn_remove = QPushButton("Supprimer la sélection")
        self.btn_reset = QPushButton("Réinitialiser aux mots-clefs standards")
        self.btn_apply = QPushButton("✔ Enregistrer et appliquer")
        self.btn_apply.setProperty("primary", True)
        self.btn_cancel = QPushButton("Annuler")

        bottom_row.addWidget(self.btn_remove)
        bottom_row.addWidget(self.btn_reset)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.btn_cancel)
        bottom_row.addWidget(self.btn_apply)
        layout.addLayout(bottom_row)

        self.btn_add.clicked.connect(self._add_alias)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_reset.clicked.connect(self._reset_defaults)
        self.btn_import_ini.clicked.connect(self._import_ini)
        self.btn_import_json.clicked.connect(self._import_json)
        self.btn_export_json.clicked.connect(self._export_json)
        self.btn_apply.clicked.connect(self._save_and_close)
        self.btn_cancel.clicked.connect(self.reject)

        self._reload_table()

    def _reload_table(self) -> None:
        self.table.setRowCount(0)
        for alias, canon in sorted(self.profile.custom_aliases.items()):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(alias))
            self.table.setItem(r, 1, QTableWidgetItem(canon))

    def _add_alias(self) -> None:
        alias = self.alias_input.text().strip()
        canon = self.canon_combo.currentData()
        if not alias:
            return
        self.profile.custom_aliases[alias] = canon
        self.alias_input.clear()
        self._reload_table()

    def _remove_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                self.profile.custom_aliases.pop(item.text(), None)
                self._reload_table()

    def _reset_defaults(self) -> None:
        self.profile.custom_aliases.clear()
        self.name_edit.setText("Alg_32 Standard + Omega")
        self._reload_table()

    def _import_ini(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un fichier alg_exec.ini d'Alg_32 / Algpers32",
            "",
            "Fichiers INI Alg_32 (*.ini algperso.*);;Tous (*.*)",
        )
        if not path:
            return
        try:
            imported, count = import_legacy_alg_exec_ini(path)
            self.profile.custom_aliases.update(imported.custom_aliases)
            self.name_edit.setText(imported.name)
            self._reload_table()
            QMessageBox.information(
                self,
                "Import Alg_32 réussi",
                f"Fichier chargé avec succès ({count} alias personnalisés supplémentaires détectés).",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Erreur d'import", str(exc))

    def _import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importer un profil JSON", "", "Profil JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.profile = KeywordProfile.from_dict(data)
            self.name_edit.setText(self.profile.name)
            self._reload_table()
        except Exception as exc:
            QMessageBox.warning(self, "Erreur", str(exc))

    def _export_json(self) -> None:
        self.profile.name = self.name_edit.text().strip() or "Profil personnalisé"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le profil de mots-clefs", "profil_algpers.json", "Profil JSON (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _save_and_close(self) -> None:
        self.profile.name = self.name_edit.text().strip() or "Alg_32 Standard + Omega"
        self.profileUpdated.emit(self.profile)
        self.accept()
