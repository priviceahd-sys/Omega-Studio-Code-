"""
Fenêtre principale d'Omega Studio Code (architecture inspirée de VS Code,
optimisée pour Omarchy / Hyprland / Wayland et l'apprentissage de l'algorithmique Alg_32).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..core.interpreter import AlgInterpreter, StepEvent
from ..core.keywords import (
    BUILTIN_FUNCTIONS,
    HelpRegistry,
    KeywordProfile,
    read_alg_file_smart,
)
from ..core.verifier import Diagnostic, format_algorithm_source, verify_source
from .code_editor import EditorWorkspace, pick_monospace_font
from .console_widget import ExecutionConsole
from .debugger_panel import DebuggerPanel
from .flowchart_widget import FlowchartWidget
from .help_and_pers_dialog import AlgpersDialog, HelpBrowserWidget
from .icons import make_app_logo_icon, make_icon
from .themes import THEMES, StudioTheme, build_stylesheet
from .transpiler_panel import TranspilerPanel

SNIPPET_TEMPLATES: List[Tuple[str, str, str]] = [
    (
        "Structure",
        "Squelette complet ALGO ... DEBUT ... FIN",
        'ALGO mon_algorithme\nVAR\n    x : entier\nDEBUT\n    SAISIR "Valeur de x : ", x\n    AFFICHER "Résultat = ", x * 2\nFIN\n',
    ),
    ("Entrées / Sorties", "SAISIR avec invite", 'SAISIR "Entrez une valeur : ", nom_var'),
    ("Entrées / Sorties", "AFFICHER expressions", 'AFFICHER "Résultat : ", resultat'),
    ("Entrées / Sorties", "COULEUR encre, fond (0..15)", "COULEUR 14, 1"),
    ("Entrées / Sorties", "CURSEUR ligne, colonne", "CURSEUR 5, 10"),
    ("Entrées / Sorties", "EFFACE_ECRAN", "EFFACE_ECRAN"),
    (
        "Conditions",
        "SI ... ALORS ... SINON ... FINSI",
        "SI condition ALORS\n    ' actions si vrai\nSINON\n    ' actions si faux\nFINSI",
    ),
    (
        "Conditions",
        "SELON ... CAS ... FINSELON",
        "SELON choix\n    CAS 1 :\n        AFFICHER \"Option 1\"\n    CAS 2 :\n        AFFICHER \"Option 2\"\n    CAS SINON :\n        AFFICHER \"Autre choix\"\nFINSELON",
    ),
    (
        "Boucles",
        "POUR i := 1 A n ... FINPOUR",
        "POUR i := 1 A 10\n    AFFICHER i\nFINPOUR",
    ),
    (
        "Boucles",
        "TANT QUE ... FINTQ",
        "TANT QUE condition\n    ' instructions répétées\nFINTQ",
    ),
    (
        "Boucles",
        "REPETER ... JUSQU'A",
        "REPETER\n    SAISIR \"Entrez un nombre positif : \", n\nJUSQU'A n > 0",
    ),
    (
        "Boucles",
        "ITER ... SORTIRSI ... FINITER",
        "ITER\n    ' instructions\n    SORTIRSI condition_sortie\nFINITER",
    ),
    (
        "Tableaux & Structures",
        "Déclaration TABLEAU 1D",
        "tab[10] : tableau d'entiers",
    ),
    (
        "Tableaux & Structures",
        "STRUCTURE ... FINSTRUCTURE",
        "STRUCTURE etudiant\n    nom : chaîne(30)\n    moyenne : réel\nFINSTRUCTURE",
    ),
    (
        "Sous-programmes",
        "PROCEDURE avec paramètres E / ES",
        "PROCEDURE echanger(es a, b : entiers)\nVAR\n    tmp : entier\nDEBUT\n    tmp := a\n    a := b\n    b := tmp\nFIN",
    ),
    (
        "Sous-programmes",
        "FONCTION avec VALRET",
        "FONCTION carre(e x : réel) : réel\nDEBUT\n    VALRET := x * x\nFIN",
    ),
    (
        "SQL & Fichiers",
        "Bloc EXEC SQL ... FIN EXEC",
        "EXEC SQL\n    SELECT nom, note FROM etudiants ORDER BY note DESC\nFIN EXEC",
    ),
]


def _config_file_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    cfg_dir = base / "omega-studio-code"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "settings.json"


class OmegaMainWindow(QMainWindow):
    """Environnement de développement intégré complet Omega Studio Code."""

    def __init__(self, initial_file: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__} — Studio Algorithmique (Alg_32 Moderne)")
        self.setWindowIcon(make_app_logo_icon())
        self.resize(1440, 880)

        # Chargement de la configuration utilisateur (XDG ~/.config/omega-studio-code/settings.json)
        self.settings = self._load_settings()
        theme_id = self.settings.get("theme", "omarchy_tokyonight")
        self.theme: StudioTheme = THEMES.get(theme_id, THEMES["omarchy_tokyonight"])
        self.profile = KeywordProfile.from_dict(self.settings["profile"]) if "profile" in self.settings else KeywordProfile()
        self.strict_alg32_mode: bool = bool(self.settings.get("strict_alg32", False))
        self.help_registry = HelpRegistry()

        # Répertoire d'exemples intégrés et dossier de travail
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.examples_dir = self.repo_root / "examples"
        self.workspace_dir = Path(self.settings.get("workspace_dir", str(self.examples_dir if self.examples_dir.exists() else Path.cwd())))

        # État d'exécution / débogage
        self._interpreter: Optional[AlgInterpreter] = None
        self._gen = None
        self._exec_mode: str = "IDLE"  # IDLE, RUN_FAST, STEP_PAUSE, AUTO_STEP, WAIT_INPUT
        self._step_target_depth: Optional[int] = None

        self._run_timer = QTimer(self)
        self._run_timer.setInterval(8)
        self._run_timer.timeout.connect(self._on_fast_run_tick)

        self._auto_step_timer = QTimer(self)
        self._auto_step_timer.setInterval(300)
        self._auto_step_timer.timeout.connect(self._on_auto_step_tick)

        self._live_parse_timer = QTimer(self)
        self._live_parse_timer.setSingleShot(True)
        self._live_parse_timer.setInterval(420)
        self._live_parse_timer.timeout.connect(self._refresh_live_views)

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self.apply_theme(self.theme.id)

        # Ouvre le fichier demandé ou l'exemple de bienvenue
        if initial_file and Path(initial_file).exists():
            self.open_file_from_path(Path(initial_file))
        else:
            welcome = self.examples_dir / "01_bienvenue_omega.alg"
            if welcome.exists():
                self.open_file_from_path(welcome)
            else:
                self.new_algorithm()

        self._refresh_live_views()

    # ==========================================
    # Construction de l'interface Studio
    # ==========================================

    def _build_ui(self) -> None:
        central = QWidget(self)
        root_h = QHBoxLayout(central)
        root_h.setContentsMargins(0, 0, 0, 0)
        root_h.setSpacing(0)

        # 1. Barre d'activité verticale à gauche (style VS Code)
        self.activity_bar = QWidget()
        self.activity_bar.setFixedWidth(50)
        act_v = QVBoxLayout(self.activity_bar)
        act_v.setContentsMargins(6, 10, 6, 10)
        act_v.setSpacing(10)

        self.btn_act_explorer = self._make_activity_btn("Explorateur & Exemples .alg (Ctrl+Shift+E)")
        self.btn_act_keywords = self._make_activity_btn("Palette Mots-clefs & Fonctions Alg_32 (Ctrl+Shift+K)")
        self.btn_act_flowchart = self._make_activity_btn("Afficher l'Organigramme")
        self.btn_act_translate = self._make_activity_btn("Afficher le Traducteur Python / C / JS / Pascal")
        self.btn_act_pers = self._make_activity_btn("Atelier Algpers32 — Personnaliser les mots-clefs")
        self.btn_act_help = self._make_activity_btn("Manuel officiel Alg_32 (F1)")

        self.btn_act_explorer.setChecked(True)
        self.btn_act_explorer.clicked.connect(lambda: self._switch_sidebar_page(0))
        self.btn_act_keywords.clicked.connect(lambda: self._switch_sidebar_page(1))
        self.btn_act_flowchart.clicked.connect(lambda: self.right_tabs.setCurrentWidget(self.flowchart_widget))
        self.btn_act_translate.clicked.connect(lambda: self.right_tabs.setCurrentWidget(self.transpiler_panel))
        self.btn_act_pers.clicked.connect(self.open_algpers_dialog)
        self.btn_act_help.clicked.connect(lambda: self.right_tabs.setCurrentWidget(self.help_browser))

        act_v.addWidget(self.btn_act_explorer)
        act_v.addWidget(self.btn_act_keywords)
        act_v.addWidget(self.btn_act_flowchart)
        act_v.addWidget(self.btn_act_translate)
        act_v.addStretch(1)
        act_v.addWidget(self.btn_act_pers)
        act_v.addWidget(self.btn_act_help)

        # 2. Panneau latéral gauche (Explorateur + Palette d'instructions)
        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.setMinimumWidth(230)
        self.sidebar_stack.addWidget(self._build_explorer_page())
        self.sidebar_stack.addWidget(self._build_palette_page())

        # 3. Zone centrale : Éditeur en haut + Console/Diagnostics/Impression/SQL en bas
        self.editor_workspace = EditorWorkspace(self.theme, self.profile, self)
        self.editor_workspace.activeEditorChanged.connect(self._on_active_editor_changed)
        self.editor_workspace.helpRequested.connect(self._show_context_help)
        self.editor_workspace.cursorMoved.connect(self._update_cursor_status)

        self.bottom_tabs = QTabWidget()
        self.console = ExecutionConsole(self.theme, self)
        self.console.inputSubmitted.connect(self._on_user_input_submitted)

        # Onglet Vérification & Diagnostics
        diag_container = QWidget()
        diag_v = QVBoxLayout(diag_container)
        diag_v.setContentsMargins(6, 6, 6, 6)
        self.diag_summary_lbl = QLabel("Aucune vérification exécutée.")
        self.diag_list = QListWidget()
        self.diag_list.itemClicked.connect(self._on_diagnostic_clicked)
        diag_v.addWidget(self.diag_summary_lbl)
        diag_v.addWidget(self.diag_list, 1)

        # Onglet État d'impression (IMPRIMER d'Alg_32)
        print_container = QWidget()
        pr_v = QVBoxLayout(print_container)
        pr_v.setContentsMargins(6, 6, 6, 6)
        pr_bar = QHBoxLayout()
        btn_copy_pr = QPushButton("Copier dans le presse-papier")
        btn_save_pr = QPushButton("Enregistrer l'état (.txt)")
        btn_clear_pr = QPushButton("Effacer l'état")
        pr_bar.addWidget(QLabel("Sortie différée IMPRIMER (compatible Alg_32) :"))
        pr_bar.addStretch(1)
        pr_bar.addWidget(btn_copy_pr)
        pr_bar.addWidget(btn_save_pr)
        pr_bar.addWidget(btn_clear_pr)
        self.printer_view = QPlainTextEdit()
        self.printer_view.setReadOnly(True)
        self.printer_view.setFont(pick_monospace_font(10))
        pr_v.addLayout(pr_bar)
        pr_v.addWidget(self.printer_view, 1)
        btn_clear_pr.clicked.connect(self.printer_view.clear)
        btn_copy_pr.clicked.connect(
            lambda: QApplication.clipboard().setText(self.printer_view.toPlainText()) if QApplication.clipboard() else None
        )
        btn_save_pr.clicked.connect(self._save_printer_report)

        # Onglet Explorateur SQL & Fichiers Alg_32
        sql_container = QWidget()
        sql_v = QVBoxLayout(sql_container)
        sql_v.setContentsMargins(6, 6, 6, 6)
        self.sql_info_lbl = QLabel("Base SQL SQLite3 & Fichiers séquentiels/indexés Alg_32 : prêts.")
        self.sql_table_widget = QTableWidget(0, 0)
        sql_v.addWidget(self.sql_info_lbl)
        sql_v.addWidget(self.sql_table_widget, 1)

        self.bottom_tabs.addTab(self.console, "Console d'Exécution")
        self.bottom_tabs.addTab(diag_container, "Vérification (0)")
        self.bottom_tabs.addTab(print_container, "État d'Impression")
        self.bottom_tabs.addTab(sql_container, "SQL && Fichiers")

        center_v_split = QSplitter(Qt.Orientation.Vertical)
        center_v_split.addWidget(self.editor_workspace)
        center_v_split.addWidget(self.bottom_tabs)
        center_v_split.setStretchFactor(0, 5)
        center_v_split.setStretchFactor(1, 2)
        center_v_split.setSizes([540, 250])

        # 4. Panneau latéral droit : Débogueur + Organigramme + Traducteur + Manuel Alg_32
        self.right_tabs = QTabWidget()
        self.right_tabs.setMinimumWidth(360)

        self.debugger_panel = DebuggerPanel(self.theme, self)
        self.debugger_panel.stepOverRequested.connect(self.step_over)
        self.debugger_panel.stepIntoRequested.connect(self.step_into)
        self.debugger_panel.autoStepToggled.connect(self.toggle_auto_step)
        self.debugger_panel.continueRequested.connect(self.continue_execution)
        self.debugger_panel.stopRequested.connect(self.stop_execution)
        self.debugger_panel.speedChanged.connect(self._auto_step_timer.setInterval)
        self.debugger_panel.frameClicked.connect(self._goto_editor_line)

        self.flowchart_widget = FlowchartWidget(self.theme, self)
        self.transpiler_panel = TranspilerPanel(self.theme, self.profile, self)
        self.help_browser = HelpBrowserWidget(self.help_registry, self.theme, self)
        self.help_browser.snippetInsertRequested.connect(self._insert_snippet_into_editor)

        self.right_tabs.addTab(self.debugger_panel, "Débogueur")
        self.right_tabs.addTab(self.flowchart_widget, "Organigramme")
        self.right_tabs.addTab(self.transpiler_panel, "Traduction")
        self.right_tabs.addTab(self.help_browser, "Aide")

        # Assemblage horizontal global redimensionnable
        self.main_h_split = QSplitter(Qt.Orientation.Horizontal)
        self.main_h_split.addWidget(self.sidebar_stack)
        self.main_h_split.addWidget(center_v_split)
        self.main_h_split.addWidget(self.right_tabs)
        self.main_h_split.setStretchFactor(0, 1)
        self.main_h_split.setStretchFactor(1, 4)
        self.main_h_split.setStretchFactor(2, 2)
        self.main_h_split.setSizes([255, 705, 430])

        root_h.addWidget(self.activity_bar)
        root_h.addWidget(self.main_h_split, 1)
        self.setCentralWidget(central)

        # Barre d'état inférieure (style VS Code)
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.lbl_status_mode = QLabel(f" Ω {__app_name__} • Prêt ")
        self.lbl_status_profile = QLabel(f" Profil : {self.profile.name} ")
        self.lbl_status_pos = QLabel(" Ligne 1, Col 1 ")
        self.lbl_status_enc = QLabel(" UTF-8 • Alg_32 ")
        status.addWidget(self.lbl_status_mode)
        status.addPermanentWidget(self.lbl_status_profile)
        status.addPermanentWidget(self.lbl_status_pos)
        status.addPermanentWidget(self.lbl_status_enc)

    def _make_activity_btn(self, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setCheckable(False)
        btn.setIconSize(QSize(24, 24))
        btn.setFixedSize(38, 38)
        btn.setToolTip(tooltip)
        return btn

    def _build_explorer_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        title = QLabel("EXPLORATEUR")
        title.setStyleSheet("font-weight: 700; letter-spacing: 0.5px;")
        btn_open_dir = QPushButton("Dossier...")
        btn_open_dir.clicked.connect(self.choose_workspace_folder)
        hdr.addWidget(title)
        hdr.addStretch(1)
        hdr.addWidget(btn_open_dir)
        v.addLayout(hdr)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.itemDoubleClicked.connect(self._on_explorer_item_activated)
        self.file_tree.itemActivated.connect(self._on_explorer_item_activated)
        v.addWidget(self.file_tree, 1)

        btn_refresh = QPushButton("↻ Actualiser la liste")
        btn_refresh.clicked.connect(self.refresh_explorer)
        v.addWidget(btn_refresh)

        self.refresh_explorer()
        return page

    def _build_palette_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        lbl = QLabel("MOTS-CLEFS & FONCTIONS")
        lbl.setStyleSheet("font-weight: 700; letter-spacing: 0.5px;")
        v.addWidget(lbl)

        self.palette_filter = QLineEdit()
        self.palette_filter.setPlaceholderText("Filtrer (ex: POUR, RAC2, MILIEU...)")
        v.addWidget(self.palette_filter)

        self.palette_tree = QTreeWidget()
        self.palette_tree.setHeaderHidden(True)
        v.addWidget(self.palette_tree, 1)

        hint = QLabel("Double-cliquez sur un élément pour l'insérer à la position du curseur.")
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.palette_filter.textChanged.connect(self._populate_palette_tree)
        self.palette_tree.itemDoubleClicked.connect(self._on_palette_double_clicked)
        self._populate_palette_tree()
        return page

    def _populate_palette_tree(self) -> None:
        filt = self.palette_filter.text().strip().lower()
        self.palette_tree.clear()

        # 1. Modèles d'instructions
        cat_nodes: Dict[str, QTreeWidgetItem] = {}
        for cat, title, code in SNIPPET_TEMPLATES:
            if filt and filt not in title.lower() and filt not in code.lower():
                continue
            parent = cat_nodes.get(cat)
            if parent is None:
                parent = QTreeWidgetItem([f"▸ {cat}"])
                self.palette_tree.addTopLevelItem(parent)
                cat_nodes[cat] = parent
            child = QTreeWidgetItem([title])
            child.setData(0, Qt.ItemDataRole.UserRole, code)
            child.setToolTip(0, code)
            parent.addChild(child)
            parent.setExpanded(True)

        # 2. Fonctions intégrées Alg_32
        fn_root = QTreeWidgetItem(["▸ Fonctions intégrées Alg_32"])
        for canon, (_, sig, desc) in sorted(BUILTIN_FUNCTIONS.items()):
            if filt and filt not in sig.lower() and filt not in desc.lower():
                continue
            item = QTreeWidgetItem([f"{sig} — {desc}"])
            item.setData(0, Qt.ItemDataRole.UserRole, sig)
            item.setToolTip(0, desc)
            fn_root.addChild(item)
        if fn_root.childCount() > 0:
            self.palette_tree.addTopLevelItem(fn_root)
            fn_root.setExpanded(bool(filt))

    def _switch_sidebar_page(self, index: int) -> None:
        if self.sidebar_stack.isVisible() and self.sidebar_stack.currentIndex() == index:
            self.sidebar_stack.setVisible(False)
        else:
            self.sidebar_stack.setVisible(True)
            self.sidebar_stack.setCurrentIndex(index)

    # ==========================================
    # Barre de menus & Barre d'outils
    # ==========================================

    def _build_menus(self) -> None:
        mb = self.menuBar()
        if mb is None:
            return

        # Menu Fichier (fidèle à Alg_32 + onglets modernes)
        m_file = mb.addMenu("&Fichier")
        act_new = QAction("&Nouvel algorithme", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self.new_algorithm)

        act_open = QAction("&Ouvrir un algorithme (.alg)...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_algorithm_dialog)

        act_merge = QAction("&Fusionner un fichier dans l'éditeur...", self)
        act_merge.triggered.connect(self.merge_algorithm_dialog)

        act_save = QAction("&Enregistrer", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self.save_current_algorithm)

        act_save_as = QAction("Enregistrer &sous...", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self.save_current_algorithm_as)

        act_export_flow = QAction("Exporter l'&organigramme en PNG...", self)
        act_export_flow.triggered.connect(self.flowchart_widget.export_png)

        act_quit = QAction("&Quitter", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)

        for a in (act_new, act_open, act_merge, act_save, act_save_as, act_export_flow, act_quit):
            m_file.addAction(a)  # type: ignore[union-attr]

        # Menu Édition
        m_edit = mb.addMenu("&Édition")
        act_undo = QAction("&Annuler", self)
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(lambda: self._ed_call("undo"))

        act_redo = QAction("&Rétablir", self)
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        act_redo.triggered.connect(lambda: self._ed_call("redo"))

        act_find = QAction("Re&chercher...", self)
        act_find.setShortcut(QKeySequence.StandardKey.Find)
        act_find.triggered.connect(lambda: self.editor_workspace.show_find_bar(False))

        act_replace = QAction("Rem&placer...", self)
        act_replace.setShortcut(QKeySequence("Ctrl+H"))
        act_replace.triggered.connect(lambda: self.editor_workspace.show_find_bar(True))

        act_fmt = QAction("&Formater & Indenter l'algorithme", self)
        act_fmt.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_fmt.triggered.connect(lambda: self.format_current_editor(uppercase=True))

        act_upper = QAction("&Mots-clefs en MAJUSCULES (style Alg_32)", self)
        act_upper.triggered.connect(lambda: self.format_current_editor(uppercase=True))

        act_bp = QAction("Basculer un &point d'arrêt sur la ligne", self)
        act_bp.setShortcut(QKeySequence("F9"))
        act_bp.triggered.connect(self._toggle_current_breakpoint)

        for a in (act_undo, act_redo, act_find, act_replace, act_fmt, act_upper, act_bp):
            m_edit.addAction(a)  # type: ignore[union-attr]

        # Menu Exécution & Vérification
        m_run = mb.addMenu("E&xécution")
        act_verify = QAction("&Vérifier la syntaxe et les types", self)
        act_verify.setShortcut(QKeySequence("F4"))
        act_verify.triggered.connect(self.run_verification)

        act_run = QAction("Exécuter &sans interruption", self)
        act_run.setShortcut(QKeySequence("F5"))
        act_run.triggered.connect(self.run_without_interruption)

        act_step_over = QAction("Pas à Pas — Instruction &suivante", self)
        act_step_over.setShortcut(QKeySequence("F10"))
        act_step_over.triggered.connect(self.step_over)

        act_step_into = QAction("Pas à Pas — &Entrer dans sous-programme", self)
        act_step_into.setShortcut(QKeySequence("F11"))
        act_step_into.triggered.connect(self.step_into)

        act_auto_step = QAction("Pas à Pas &Automatique (Lent/Rapide)", self)
        act_auto_step.setShortcut(QKeySequence("F8"))
        act_auto_step.triggered.connect(lambda: self.toggle_auto_step(self._exec_mode != "AUTO_STEP"))

        act_stop = QAction("&Arrêter l'exécution", self)
        act_stop.setShortcut(QKeySequence("Shift+F5"))
        act_stop.triggered.connect(self.stop_execution)

        for a in (act_verify, act_run, act_step_over, act_step_into, act_auto_step, act_stop):
            m_run.addAction(a)  # type: ignore[union-attr]

        # Menu Affichage & Thèmes
        m_view = mb.addMenu("&Affichage")
        for tid, t_obj in THEMES.items():
            act_t = QAction(f"Thème : {t_obj.name}", self)
            act_t.triggered.connect(lambda _=False, k=tid: self.apply_theme(k))
            m_view.addAction(act_t)  # type: ignore[union-attr]

        m_view.addSeparator()  # type: ignore[union-attr]
        act_zin = QAction("Agrandir la police (Ctrl++)", self)
        act_zin.setShortcut(QKeySequence.StandardKey.ZoomIn)
        act_zin.triggered.connect(lambda: self._zoom_editor(1))

        act_zout = QAction("Réduire la police (Ctrl+-)", self)
        act_zout.setShortcut(QKeySequence.StandardKey.ZoomOut)
        act_zout.triggered.connect(lambda: self._zoom_editor(-1))

        self.act_strict = QAction("Mode strict Alg_32 historique (avertissement > 73 col.)", self)
        self.act_strict.setCheckable(True)
        self.act_strict.setChecked(self.strict_alg32_mode)
        self.act_strict.toggled.connect(self._toggle_strict_mode)

        m_view.addAction(act_zin)  # type: ignore[union-attr]
        m_view.addAction(act_zout)  # type: ignore[union-attr]
        m_view.addAction(self.act_strict)  # type: ignore[union-attr]

        # Menu Outils & Aide
        m_help = mb.addMenu("&Outils && Aide")
        act_pers = QAction("Atelier &Algpers32 (Personnaliser les mots-clefs)...", self)
        act_pers.triggered.connect(self.open_algpers_dialog)

        act_manual = QAction("&Manuel officiel Alg_32 (F1)", self)
        act_manual.triggered.connect(lambda: self.right_tabs.setCurrentWidget(self.help_browser))

        act_about = QAction(f"À &propos d'{__app_name__}", self)
        act_about.triggered.connect(self.show_about_dialog)

        m_help.addAction(act_pers)  # type: ignore[union-attr]
        m_help.addAction(act_manual)  # type: ignore[union-attr]
        m_help.addSeparator()  # type: ignore[union-attr]
        m_help.addAction(act_about)  # type: ignore[union-attr]

    def _build_toolbar(self) -> None:
        tb = QToolBar("Actions principales", self)
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)
        self.main_toolbar = tb

        self.tb_new = QAction("Nouveau", self)
        self.tb_new.setToolTip("Nouvel algorithme (Ctrl+N)")
        self.tb_new.triggered.connect(self.new_algorithm)

        self.tb_open = QAction("Ouvrir", self)
        self.tb_open.setToolTip("Ouvrir un fichier .alg (Ctrl+O)")
        self.tb_open.triggered.connect(self.open_algorithm_dialog)

        self.tb_save = QAction("Enregistrer", self)
        self.tb_save.setToolTip("Enregistrer le fichier courant (Ctrl+S)")
        self.tb_save.triggered.connect(self.save_current_algorithm)

        self.tb_verify = QAction("Vérifier (F4)", self)
        self.tb_verify.setToolTip("Analyser la syntaxe, les déclarations et les types (F4)")
        self.tb_verify.triggered.connect(self.run_verification)

        self.tb_format = QAction("Formater", self)
        self.tb_format.setToolTip("Indenter automatiquement et mettre les mots-clefs en majuscules (Ctrl+Shift+F)")
        self.tb_format.triggered.connect(lambda: self.format_current_editor(uppercase=True))

        self.tb_run = QAction("Exécuter (F5)", self)
        self.tb_run.setToolTip("Exécuter l'algorithme sans interruption (F5)")
        self.tb_run.triggered.connect(self.run_without_interruption)

        self.tb_step = QAction("Pas à Pas (F10)", self)
        self.tb_step.setToolTip("Exécuter l'instruction suivante en mode Pas-à-Pas (F10)")
        self.tb_step.triggered.connect(self.step_over)

        self.tb_step_in = QAction("Entrer (F11)", self)
        self.tb_step_in.setToolTip("Pas-à-Pas détaillé : entrer dans les procédures et fonctions (F11)")
        self.tb_step_in.triggered.connect(self.step_into)

        self.tb_stop = QAction("Arrêter", self)
        self.tb_stop.setToolTip("Interrompre l'exécution en cours (Shift+F5)")
        self.tb_stop.triggered.connect(self.stop_execution)

        tb.addAction(self.tb_new)
        tb.addAction(self.tb_open)
        tb.addAction(self.tb_save)
        tb.addSeparator()
        tb.addAction(self.tb_verify)
        tb.addAction(self.tb_format)
        tb.addSeparator()
        tb.addAction(self.tb_run)
        tb.addAction(self.tb_step)
        tb.addAction(self.tb_step_in)
        tb.addAction(self.tb_stop)
        tb.addSeparator()

        # Sélecteur rapide de thème visuel dans la barre d'outils
        tb.addWidget(QLabel("  Thème : "))
        self.theme_combo = QComboBox()
        for tid, tobj in THEMES.items():
            self.theme_combo.addItem(tobj.name, tid)
        cur_idx = self.theme_combo.findData(self.theme.id)
        if cur_idx >= 0:
            self.theme_combo.setCurrentIndex(cur_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        tb.addWidget(self.theme_combo)

    # ==========================================
    # Gestion des thèmes & préférences
    # ==========================================

    def apply_theme(self, theme_id: str) -> None:
        if theme_id not in THEMES:
            return
        self.theme = THEMES[theme_id]
        t = self.theme
        self.setStyleSheet(build_stylesheet(t))
        self.activity_bar.setStyleSheet(
            f"background-color: {t.bg_activity}; border-right: 1px solid {t.border};"
        )

        # Régénère les icônes vectorielles avec les couleurs exactes du thème
        ic_fg = t.fg_primary
        self.btn_act_explorer.setIcon(make_icon("open_file", ic_fg, 22))
        self.btn_act_keywords.setIcon(make_icon("keywords", ic_fg, 22))
        self.btn_act_flowchart.setIcon(make_icon("flowchart", ic_fg, 22))
        self.btn_act_translate.setIcon(make_icon("translate", ic_fg, 22))
        self.btn_act_pers.setIcon(make_icon("customize", ic_fg, 22))
        self.btn_act_help.setIcon(make_icon("help", ic_fg, 22))

        self.tb_new.setIcon(make_icon("new_file", ic_fg, 18))
        self.tb_open.setIcon(make_icon("open_file", ic_fg, 18))
        self.tb_save.setIcon(make_icon("save", ic_fg, 18))
        self.tb_verify.setIcon(make_icon("verify", t.accent, 18))
        self.tb_format.setIcon(make_icon("format", ic_fg, 18))
        self.tb_run.setIcon(make_icon("play", t.success, 18))
        self.tb_step.setIcon(make_icon("step_over", t.warning, 18))
        self.tb_step_in.setIcon(make_icon("step_into", t.accent, 18))
        self.tb_stop.setIcon(make_icon("stop", t.danger, 18))

        self.right_tabs.setTabIcon(0, make_icon("step_over", t.warning, 16))
        self.right_tabs.setTabIcon(1, make_icon("flowchart", t.accent, 16))
        self.right_tabs.setTabIcon(2, make_icon("translate", t.success, 16))
        self.right_tabs.setTabIcon(3, make_icon("help", ic_fg, 16))

        self.bottom_tabs.setTabIcon(0, make_icon("keywords", t.success, 16))
        self.bottom_tabs.setTabIcon(1, make_icon("verify", t.accent, 16))
        self.bottom_tabs.setTabIcon(2, make_icon("new_file", ic_fg, 16))
        self.bottom_tabs.setTabIcon(3, make_icon("customize", t.warning, 16))

        self.editor_workspace.set_theme_and_profile(t, self.profile)
        self.console.apply_theme(t)
        self.debugger_panel.apply_theme(t)
        self.flowchart_widget.apply_theme(t)
        self.transpiler_panel.apply_theme(t)
        self.help_browser.apply_theme(t)
        self.printer_view.setStyleSheet(
            f"background-color: {t.bg_editor}; color: {t.fg_primary}; border: 1px solid {t.border}; padding: 8px;"
        )

        idx = self.theme_combo.findData(theme_id)
        if idx >= 0 and self.theme_combo.currentIndex() != idx:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)

        self.settings["theme"] = theme_id
        self._save_settings()

    def _on_theme_combo_changed(self) -> None:
        tid = self.theme_combo.currentData()
        if tid:
            self.apply_theme(tid)

    def _load_settings(self) -> dict:
        p = _config_file_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_settings(self) -> None:
        try:
            self.settings["profile"] = self.profile.to_dict()
            self.settings["strict_alg32"] = self.strict_alg32_mode
            self.settings["workspace_dir"] = str(self.workspace_dir)
            _config_file_path().write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # ==========================================
    # Gestion des fichiers & Explorateur
    # ==========================================

    def refresh_explorer(self) -> None:
        self.file_tree.clear()

        if self.examples_dir.exists():
            ex_root = QTreeWidgetItem(["Exemples intégrés (.alg)"])
            ex_root.setIcon(0, make_icon("open_file", self.theme.accent, 16))
            for p in sorted(self.examples_dir.glob("*.alg")):
                it = QTreeWidgetItem([p.name])
                it.setData(0, Qt.ItemDataRole.UserRole, str(p))
                ex_root.addChild(it)
            self.file_tree.addTopLevelItem(ex_root)
            ex_root.setExpanded(True)

        if self.workspace_dir.exists() and self.workspace_dir.resolve() != self.examples_dir.resolve():
            ws_root = QTreeWidgetItem([f"Dossier : {self.workspace_dir.name}"])
            ws_root.setIcon(0, make_icon("open_file", self.theme.warning, 16))
            for p in sorted(self.workspace_dir.glob("*.alg")):
                it = QTreeWidgetItem([p.name])
                it.setData(0, Qt.ItemDataRole.UserRole, str(p))
                ws_root.addChild(it)
            self.file_tree.addTopLevelItem(ws_root)
            ws_root.setExpanded(True)

    def choose_workspace_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier d'algorithmes", str(self.workspace_dir))
        if folder:
            self.workspace_dir = Path(folder)
            self._save_settings()
            self.refresh_explorer()

    def _on_explorer_item_activated(self, item: QTreeWidgetItem) -> None:
        raw_path = item.data(0, Qt.ItemDataRole.UserRole)
        if raw_path:
            self.open_file_from_path(Path(raw_path))

    def new_algorithm(self) -> None:
        template = (
            "ALGO nouvel_algorithme\n"
            "' Écrivez vos déclarations et instructions ci-dessous\n"
            "VAR\n"
            "    n : entier\n"
            "DEBUT\n"
            '    SAISIR "Entrez un entier : ", n\n'
            '    AFFICHER "Le double de ", n, " vaut ", n * 2\n'
            "FIN\n"
        )
        ed = self.editor_workspace.new_tab("sans_nom.alg", template, path=None)
        ed.textChanged.connect(self._schedule_live_parse)
        self._schedule_live_parse()

    def open_file_from_path(self, path: Path) -> None:
        if not path.exists():
            return
        content = read_alg_file_smart(path)
        ed = self.editor_workspace.new_tab(path.name, content, path=path)
        ed.textChanged.connect(self._schedule_live_parse)
        self._refresh_live_views()

    def open_algorithm_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un algorithme Alg_32",
            str(self.workspace_dir),
            "Algorithmes (*.alg);;Tous les fichiers (*.*)",
        )
        if path:
            self.open_file_from_path(Path(path))

    def merge_algorithm_dialog(self) -> None:
        """Fonctionnalité historique `Fusionne...` d'Alg_32 : insère le contenu d'un autre .alg au curseur."""
        ed = self.editor_workspace.current_editor()
        if not ed:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Fusionner un fichier .alg à la position du curseur",
            str(self.workspace_dir),
            "Algorithmes (*.alg);;Tous (*.*)",
        )
        if path:
            ed.insertPlainText("\n" + read_alg_file_smart(path) + "\n")

    def save_current_algorithm(self) -> bool:
        ed = self.editor_workspace.current_editor()
        if not ed:
            return False
        if ed.file_path is None:
            return self.save_current_algorithm_as()
        ed.file_path.write_text(ed.toPlainText(), encoding="utf-8")
        ed.document().setModified(False)
        self.editor_workspace.refresh_tab_title(ed)
        self.lbl_status_mode.setText(f" ✔ Enregistré : {ed.file_path.name} ")
        return True

    def save_current_algorithm_as(self) -> bool:
        ed = self.editor_workspace.current_editor()
        if not ed:
            return False
        default_dir = str(ed.file_path or (self.workspace_dir / "mon_algo.alg"))
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer l'algorithme sous...",
            default_dir,
            "Algorithmes (*.alg);;Tous (*.*)",
        )
        if not path:
            return False
        target = Path(path if path.endswith(".alg") else f"{path}.alg")
        target.write_text(ed.toPlainText(), encoding="utf-8")
        ed.file_path = target
        ed.document().setModified(False)
        self.editor_workspace.refresh_tab_title(ed)
        self.refresh_explorer()
        return True

    def _save_printer_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer l'état d'impression", "etat_impression.txt", "Texte (*.txt)"
        )
        if path:
            Path(path).write_text(self.printer_view.toPlainText(), encoding="utf-8")

    # ==========================================
    # Édition, Formatage & Analyse en direct
    # ==========================================

    def _ed_call(self, method_name: str) -> None:
        ed = self.editor_workspace.current_editor()
        if ed and hasattr(ed, method_name):
            getattr(ed, method_name)()

    def _zoom_editor(self, delta: int) -> None:
        ed = self.editor_workspace.current_editor()
        if ed:
            ed.zoom_font(delta)

    def _toggle_current_breakpoint(self) -> None:
        ed = self.editor_workspace.current_editor()
        if ed:
            ed.toggle_breakpoint()

    def _toggle_strict_mode(self, checked: bool) -> None:
        self.strict_alg32_mode = checked
        self._save_settings()
        self.run_verification()

    def format_current_editor(self, uppercase: bool = True) -> None:
        ed = self.editor_workspace.current_editor()
        if not ed:
            return
        line = ed.textCursor().blockNumber() + 1
        formatted = format_algorithm_source(
            ed.toPlainText(), uppercase_keywords=uppercase, profile=self.profile
        )
        ed.setPlainText(formatted)
        ed.goto_line(line)
        self.lbl_status_mode.setText(" • Algorithme reformaté et indenté ")

    def _insert_snippet_into_editor(self, snippet: str) -> None:
        ed = self.editor_workspace.current_editor()
        if ed:
            ed.insertPlainText(snippet)
            ed.setFocus()

    def _on_palette_double_clicked(self, item: QTreeWidgetItem) -> None:
        code = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(code, str) and code:
            self._insert_snippet_into_editor(code)

    def _show_context_help(self, word: str) -> None:
        self.right_tabs.setCurrentWidget(self.help_browser)
        if word:
            self.help_browser.select_word(word)

    def _update_cursor_status(self, line: int, col: int) -> None:
        self.lbl_status_pos.setText(f" Ligne {line}, Col {col} ")

    def _on_active_editor_changed(self) -> None:
        self.stop_execution()
        self._refresh_live_views()

    def _schedule_live_parse(self) -> None:
        self._live_parse_timer.start()

    def _refresh_live_views(self) -> None:
        ed = self.editor_workspace.current_editor()
        if not ed:
            return
        rep = verify_source(ed.toPlainText(), profile=self.profile, strict_alg32=self.strict_alg32_mode)
        if rep.program is not None:
            self.flowchart_widget.set_program(rep.program)
            self.transpiler_panel.set_program(rep.program, profile=self.profile)
        err_map = {d.line: d.message for d in rep.diagnostics if d.severity == "ERROR"}
        ed.set_error_lines(err_map)
        self._populate_diagnostics_ui(rep.diagnostics, rep.ok, quiet=True)

    # ==========================================
    # Vérification statique (F4)
    # ==========================================

    def run_verification(self) -> bool:
        ed = self.editor_workspace.current_editor()
        if not ed:
            return False
        rep = verify_source(ed.toPlainText(), profile=self.profile, strict_alg32=self.strict_alg32_mode)
        err_map = {d.line: d.message for d in rep.diagnostics if d.severity == "ERROR"}
        ed.set_error_lines(err_map)
        self._populate_diagnostics_ui(rep.diagnostics, rep.ok, quiet=False)
        if rep.program is not None:
            self.flowchart_widget.set_program(rep.program)
            self.transpiler_panel.set_program(rep.program, profile=self.profile)
        return rep.ok

    def _populate_diagnostics_ui(self, diags: List[Diagnostic], ok: bool, quiet: bool = False) -> None:
        self.diag_list.clear()
        err_count = sum(1 for d in diags if d.severity == "ERROR")
        warn_count = sum(1 for d in diags if d.severity == "WARNING")
        self.bottom_tabs.setTabText(1, f"Vérification ({err_count + warn_count})")

        if ok and not diags:
            self.diag_summary_lbl.setText("✔ Vérification terminée : aucune erreur détectée.")
            self.diag_summary_lbl.setStyleSheet(f"color: {self.theme.success}; font-weight: 700;")
        elif ok:
            self.diag_summary_lbl.setText(f"✔ Syntaxe valide ({warn_count} avertissement(s)).")
            self.diag_summary_lbl.setStyleSheet(f"color: {self.theme.warning}; font-weight: 700;")
        else:
            self.diag_summary_lbl.setText(f"✖ {err_count} erreur(s) détectée(s) — cliquez sur une ligne pour y accéder.")
            self.diag_summary_lbl.setStyleSheet(f"color: {self.theme.danger}; font-weight: 700;")

        for d in diags:
            icon = "✖" if d.severity == "ERROR" else "⚠"
            item = QListWidgetItem(f"{icon}  [Ligne {d.line}]  {d.message}")
            item.setData(Qt.ItemDataRole.UserRole, (d.line, d.col))
            col = self.theme.danger if d.severity == "ERROR" else self.theme.warning
            item.setForeground(QColor(col))
            self.diag_list.addItem(item)

        if not quiet:
            self.bottom_tabs.setCurrentIndex(1)

    def _on_diagnostic_clicked(self, item: QListWidgetItem) -> None:
        pos = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(pos, tuple):
            self._goto_editor_line(pos[0], pos[1])

    def _goto_editor_line(self, line: int, col: int = 1) -> None:
        ed = self.editor_workspace.current_editor()
        if ed:
            ed.goto_line(line, col, focus=True)

    # ==========================================
    # Moteur d'exécution & Débogueur Pas-à-Pas
    # ==========================================

    def _prepare_execution(self) -> bool:
        self.stop_execution()
        ed = self.editor_workspace.current_editor()
        if not ed:
            return False

        rep = verify_source(ed.toPlainText(), profile=self.profile, strict_alg32=self.strict_alg32_mode)
        err_map = {d.line: d.message for d in rep.diagnostics if d.severity == "ERROR"}
        ed.set_error_lines(err_map)
        self._populate_diagnostics_ui(rep.diagnostics, rep.ok, quiet=rep.ok)
        if not rep.ok or rep.program is None:
            self.lbl_status_mode.setText(" ✖ Erreur de vérification : exécution annulée ")
            return False

        self.flowchart_widget.set_program(rep.program)
        self.transpiler_panel.set_program(rep.program, profile=self.profile)

        wdir = str(ed.file_path.parent) if ed.file_path else str(self.workspace_dir)
        self._interpreter = AlgInterpreter(rep.program, profile=self.profile, working_dir=wdir)
        self._gen = self._interpreter.run_generator()

        self.console.clear_console()
        self.printer_view.clear()
        self.debugger_panel.reset_snapshot()
        self.debugger_panel.set_debugging_active(True)
        self.bottom_tabs.setCurrentWidget(self.console)
        return True

    def run_without_interruption(self) -> None:
        """Lance l'algorithme à pleine vitesse (ou reprend depuis une pause Pas-à-Pas)."""
        if self._exec_mode == "STEP_PAUSE" and self._gen is not None:
            self.continue_execution()
            return
        if not self._prepare_execution():
            return
        self._exec_mode = "RUN_FAST"
        self.console.set_status("Exécution en cours...", self.theme.accent)
        self.lbl_status_mode.setText(" ▶ Exécution en cours... ")
        self._clear_debug_highlights()
        self._run_timer.start()

    def continue_execution(self) -> None:
        if self._gen is None:
            return
        self._auto_step_timer.stop()
        self._exec_mode = "RUN_FAST"
        self.console.set_status("Exécution en cours...", self.theme.accent)
        self._clear_debug_highlights()
        self._run_timer.start()

    def step_into(self) -> None:
        """Pas-à-Pas détaillé (F11) : entre dans les procédures et fonctions."""
        if self._gen is None:
            if not self._prepare_execution():
                return
            self.right_tabs.setCurrentWidget(self.debugger_panel)
        if self._exec_mode == "WAIT_INPUT":
            return
        self._run_timer.stop()
        self._auto_step_timer.stop()
        self._step_target_depth = None
        self._exec_mode = "STEP_PAUSE"
        self._advance_until_next_step()

    def step_over(self) -> None:
        """Pas-à-Pas standard (F10) : exécute un appel de sous-programme d'un seul tenant."""
        if self._gen is None:
            if not self._prepare_execution():
                return
            self.right_tabs.setCurrentWidget(self.debugger_panel)
            self._step_target_depth = None
        elif self._interpreter is not None:
            self._step_target_depth = len(self._interpreter.call_stack)
        if self._exec_mode == "WAIT_INPUT":
            return
        self._run_timer.stop()
        self._auto_step_timer.stop()
        self._exec_mode = "STEP_PAUSE"
        self._advance_until_next_step()

    def toggle_auto_step(self, enabled: bool) -> None:
        """Pas-à-Pas automatique cadencé (F8)."""
        if enabled:
            if self._gen is None:
                if not self._prepare_execution():
                    self.debugger_panel.btn_auto.setChecked(False)
                    return
                self.right_tabs.setCurrentWidget(self.debugger_panel)
            self._run_timer.stop()
            self._step_target_depth = None
            self._exec_mode = "AUTO_STEP"
            self._auto_step_timer.start()
        else:
            self._auto_step_timer.stop()
            if self._gen is not None and self._exec_mode == "AUTO_STEP":
                self._exec_mode = "STEP_PAUSE"

    def stop_execution(self) -> None:
        self._run_timer.stop()
        self._auto_step_timer.stop()
        if self._gen is not None:
            try:
                self._gen.close()
            except Exception:
                pass
        self._gen = None
        self._interpreter = None
        self._exec_mode = "IDLE"
        self.console.set_waiting_input(False)
        self.console.set_status("Prêt", self.theme.fg_muted)
        self.debugger_panel.set_debugging_active(False)
        self._clear_debug_highlights()
        self.lbl_status_mode.setText(f" Ω {__app_name__} • Prêt ")

    def _clear_debug_highlights(self) -> None:
        ed = self.editor_workspace.current_editor()
        if ed:
            ed.set_debug_line(None)
        self.flowchart_widget.set_active_line(None)

    def _on_fast_run_tick(self) -> None:
        if self._gen is None or self._interpreter is None:
            self._run_timer.stop()
            return
        ed = self.editor_workspace.current_editor()
        bps = ed.breakpoints if ed else set()

        # Exécute un lot d'instructions par tick pour garder l'UI ultra fluide
        for _ in range(450):
            if self._gen is None:
                break
            try:
                ev = next(self._gen)
            except StopIteration:
                self._finish_execution_cleanly()
                return

            if ev.kind == "STEP":
                if ev.line in bps:
                    self._run_timer.stop()
                    self._exec_mode = "STEP_PAUSE"
                    self._sync_debug_ui(ev.line)
                    self.console.set_status(f"Point d'arrêt atteint (L{ev.line})", self.theme.warning)
                    self.lbl_status_mode.setText(f" ⏸ Pause au point d'arrêt ligne {ev.line} ")
                    return
            else:
                if not self._handle_non_step_event(ev):
                    return

    def _on_auto_step_tick(self) -> None:
        if self._exec_mode != "AUTO_STEP" or self._gen is None:
            self._auto_step_timer.stop()
            return
        self._advance_until_next_step()

    def _advance_until_next_step(self, send_val: Optional[str] = None) -> None:
        if self._gen is None or self._interpreter is None:
            return
        first_iter = True
        while self._gen is not None:
            try:
                ev = self._gen.send(send_val) if (first_iter and send_val is not None) else next(self._gen)
                first_iter = False
            except StopIteration:
                self._finish_execution_cleanly()
                return

            if ev.kind == "STEP":
                depth_ok = (
                    self._step_target_depth is None
                    or len(self._interpreter.call_stack) <= self._step_target_depth
                )
                if depth_ok:
                    self._sync_debug_ui(ev.line)
                    self.console.set_status(f"Pas-à-Pas : ligne {ev.line}", self.theme.warning)
                    self.lbl_status_mode.setText(f" ▶ Pas-à-Pas • Ligne {ev.line} ")
                    return
            else:
                if not self._handle_non_step_event(ev):
                    return

    def _handle_non_step_event(self, ev: StepEvent) -> bool:
        """Traite les événements E/S, SQL, fin ou erreur. Retourne False si la boucle doit suspendre."""
        if ev.kind == "OUTPUT":
            self.console.append_text(ev.text, newline=ev.newline)
            if self._interpreter:
                self.console.cursor_label.setText(
                    f"Curseur : L{self._interpreter.cursor_line}, C{self._interpreter.cursor_col}"
                )
            return True

        if ev.kind == "PRINTER":
            c = self.printer_view.textCursor()
            c.movePosition(c.MoveOperation.End)
            c.insertText(ev.text + ("\n" if ev.newline else ""))
            self.printer_view.setTextCursor(c)
            return True

        if ev.kind == "SCREEN_CMD":
            if ev.text == "EFFACE_ECRAN":
                self.console.clear_console()
            elif ev.text == "COULEUR" and ev.fg_color is not None and ev.bg_color is not None:
                self.console.set_vga_colors(ev.fg_color, ev.bg_color)
            elif ev.text == "CURSEUR" and ev.cursor_pos is not None:
                self.console.set_cursor_position(*ev.cursor_pos)
            return True

        if ev.kind == "SQL_RESULT":
            self._display_sql_result(ev.sql_columns, ev.sql_rows)
            return True

        if ev.kind == "INPUT_REQUEST":
            self._run_timer.stop()
            self._auto_step_timer.stop()
            self._prev_mode_before_input = self._exec_mode
            self._exec_mode = "WAIT_INPUT"
            self._sync_debug_ui(ev.line)
            self.bottom_tabs.setCurrentWidget(self.console)
            self.console.set_waiting_input(True, ev.prompt, ev.target_name, ev.target_type)
            self.lbl_status_mode.setText(f" • En attente de saisie clavier ({ev.target_name}) ")
            return False

        if ev.kind == "ERROR":
            self._run_timer.stop()
            self._auto_step_timer.stop()
            self.console.append_text(f"\n[ERREUR LIGNE {ev.line}] {ev.text}", newline=True, color_override=self.theme.danger)
            self.console.set_status(f"Erreur ligne {ev.line}", self.theme.danger)
            ed = self.editor_workspace.current_editor()
            if ed:
                ed.set_error_lines({ev.line: ev.text})
                ed.goto_line(ev.line, focus=False)
            self._finish_after_stop_or_error(is_error=True, msg=f" ✖ Erreur d'exécution L{ev.line} ")
            return False

        if ev.kind == "FINISHED":
            self._finish_execution_cleanly()
            return False

        return True

    def _on_user_input_submitted(self, value: str) -> None:
        if self._gen is None or self._exec_mode != "WAIT_INPUT":
            return
        prev = getattr(self, "_prev_mode_before_input", "RUN_FAST")
        self._exec_mode = prev

        if prev == "RUN_FAST":
            try:
                ev = self._gen.send(value)
            except StopIteration:
                self._finish_execution_cleanly()
                return
            if ev.kind == "STEP" or self._handle_non_step_event(ev):
                self.console.set_status("Exécution en cours...", self.theme.accent)
                self._clear_debug_highlights()
                self._run_timer.start()
        elif prev == "AUTO_STEP":
            self._advance_until_next_step(send_val=value)
            if self._exec_mode == "AUTO_STEP":
                self._auto_step_timer.start()
        else:
            self._advance_until_next_step(send_val=value)

    def _sync_debug_ui(self, line: int) -> None:
        ed = self.editor_workspace.current_editor()
        if ed:
            ed.set_debug_line(line)
        self.flowchart_widget.set_active_line(line)
        if self._interpreter is not None:
            snap = self._interpreter.snapshot_state()
            self.debugger_panel.update_from_snapshot(snap)
            self._refresh_sql_files_tab(snap)

    def _display_sql_result(self, cols: List[str], rows: List[tuple]) -> None:
        self.sql_table_widget.clear()
        self.sql_table_widget.setColumnCount(len(cols))
        self.sql_table_widget.setHorizontalHeaderLabels(cols)
        self.sql_table_widget.setRowCount(len(rows))
        for r_i, row in enumerate(rows):
            for c_i, val in enumerate(row):
                self.sql_table_widget.setItem(r_i, c_i, QTableWidgetItem(str(val)))
        hdr = self.sql_table_widget.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sql_info_lbl.setText(f"Dernier SELECT SQL : {len(rows)} ligne(s) retournée(s).")
        # Affiche aussi un résumé lisible dans la console
        if cols:
            self.console.append_text(" | ".join(cols), newline=True, color_override=self.theme.accent)
            for row in rows:
                self.console.append_text(" | ".join(str(x) for x in row), newline=True)

    def _refresh_sql_files_tab(self, snap: dict) -> None:
        tables = snap.get("sql_tables", {})
        files = snap.get("files", {})
        parts = []
        if snap.get("sql_db"):
            parts.append(f"Base SQL : {snap['sql_db']} ({len(tables)} table(s))")
        if files:
            f_desc = ", ".join(f"{k} ({'ouvert' if v['open'] else 'fermé'}, {v['count']} enr.)" for k, v in files.items())
            parts.append(f"Fichiers : {f_desc}")
        if parts:
            self.sql_info_lbl.setText("  •  ".join(parts))
        if tables and self.sql_table_widget.rowCount() == 0:
            first_t = next(iter(tables.values()))
            self._display_sql_result(first_t[0], first_t[1])

    def _finish_execution_cleanly(self) -> None:
        if self._interpreter is not None:
            snap = self._interpreter.snapshot_state()
            self.debugger_panel.update_from_snapshot(snap)
            self._refresh_sql_files_tab(snap)
        self._run_timer.stop()
        self._auto_step_timer.stop()
        self._gen = None
        self._interpreter = None
        self._exec_mode = "IDLE"
        self.console.set_waiting_input(False)
        self.console.set_status("Exécution terminée", self.theme.success)
        self.debugger_panel.set_debugging_active(False)
        self._clear_debug_highlights()
        self.lbl_status_mode.setText(" ✔ Exécution terminée avec succès ")

    def _finish_after_stop_or_error(self, is_error: bool, msg: str) -> None:
        if self._interpreter is not None:
            self.debugger_panel.update_from_snapshot(self._interpreter.snapshot_state())
        self._gen = None
        self._interpreter = None
        self._exec_mode = "IDLE"
        self.console.set_waiting_input(False)
        self.debugger_panel.set_debugging_active(False)
        self._clear_debug_highlights()
        self.lbl_status_mode.setText(msg)

    # ==========================================
    # Boîtes de dialogue Algpers32 & À propos
    # ==========================================

    def open_algpers_dialog(self) -> None:
        dlg = AlgpersDialog(self.profile, self.theme, self)
        dlg.profileUpdated.connect(self._on_profile_updated)
        dlg.exec()

    def _on_profile_updated(self, new_profile: KeywordProfile) -> None:
        self.profile = new_profile
        self.lbl_status_profile.setText(f" Profil : {self.profile.name} ")
        self.editor_workspace.set_theme_and_profile(self.theme, self.profile)
        self._save_settings()
        self._refresh_live_views()

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            f"À propos d'{__app_name__}",
            f"<h3>Ω {__app_name__} v{__version__}</h3>"
            "<p>Environnement de développement algorithmique moderne en français, "
            "conçu comme évolution complète d'<b>Alg_32 / Alg'exec</b> "
            "(Éducation Nationale / André Guntz) et <b>Algpers32</b>.</p>"
            "<ul>"
            "<li>Optimisé nativement pour <b>Omarchy</b> (Arch Linux + Hyprland / Wayland)</li>"
            "<li>Éditeur multi-onglets avec coloration syntaxique, auto-complétion et points d'arrêt</li>"
            "<li>Débogueur visuel Pas-à-Pas avec espion des variables, tableaux et structures</li>"
            "<li>Génération automatique d'organigrammes normalisés exportables en PNG</li>"
            "<li>Traducteur instantané vers Python 3, C, JavaScript et Pascal</li>"
            "<li>Moteur SQL SQLite3 intégré et manuel officiel Alg_32 complet</li>"
            "</ul>",
        )
