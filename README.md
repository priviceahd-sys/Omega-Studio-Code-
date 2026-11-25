# Ω Omega Code Studio v2.0

**Omega Code Studio** est un environnement de développement intégré (IDE) de bureau en **Python / PyQt6**, conçu comme le successeur moderne complet d'**Alg_32 / Alg'exec** et d'**Algpers32** (Éducation Nationale / André Guntz), optimisé nativement pour **Omarchy** (Arch Linux + Hyprland / Wayland).

---

## ✨ Ce qui a été transformé par rapport à Alg_32 (1997)

| Aspect | Alg_32 / Alg'exec historique (VB5, 1997) | Ω Omega Code Studio v2.0 (PyQt6) |
| :--- | :--- | :--- |
| **Système & Rendu** | Windows 95/98 (`MSVBVM50.dll`, installateur 16/32 bits incompatible Linux) | **Natif Linux / Omarchy (Wayland + Hyprland HiDPI)**, multiplateforme |
| **Interface visuelle** | Fenêtres grises fixes `MS Sans Serif` / `Courier New` | **Studio Visuel complet (`Ctrl+Shift+P`)** : mélanges de couleurs sur mesure, 8 dégradés animés (*Aurore Boréale*, *Cyberpunk Néon*, *Crépuscule*...), galerie multi-images avec diaporama en fondu enchaîné, effet verre dépoli (*Glassmorphism*) + 4 thèmes classiques |
| **Éditeur de code** | Mono-fichier, limité à 73 colonnes (et 25-30 lignes en démo), sans numéros de lignes | **Multi-onglets illimité**, numéros de lignes, coloration syntaxique, auto-indentation, auto-complétion (`Ctrl+Espace`), recherche/remplacement (`Ctrl+F` / `Ctrl+H`), points d'arrêt (`F9`) et formateur automatique (`Ctrl+Shift+F`) |
| **Débogage Pas-à-Pas** | Fenêtre séparée rudimentaire tronquant les valeurs à 35 caractères | **Débogueur visuel intégré** (`F10` Suivant, `F11` Entrer, `F8` Cadence auto réglable), espion complet des variables, tableaux 1D/2D/3D, structures et pile d'appels récursive |
| **Pédagogie visuelle** | Aucune représentation graphique ni export | **Organigramme normalisé automatique** (zoom interactif, suivi en direct du Pas-à-Pas, export PNG haute définition) |
| **Traduction de code** | Aucune | **Transpileur temps réel** vers **Python 3**, **C (C11)**, **JavaScript (ES6)** et **Pascal** |
| **Base SQL (`EXEC SQL`)** | Dépendance obsolète Microsoft Access 2.0 (`DAO350.dll`) | **Moteur SQLite3 embarqué natif** (`START DATABASE`, `SELECT ... INTO :var`, curseurs `DECLARE / OPEN / FETCH / CLOSE`) + explorateur de tables intégré |
| **Personnalisation** | Exécutable séparé `Algpers32.exe` | **Atelier Algpers32 intégré** avec import direct des fichiers historiques `alg_exec.ini` et export JSON |
| **Aide officielle** | Fichier binaire `alg_exec.ini` CP1252 | **77 fiches du manuel officiel Alg_32 intégrées en UTF-8**, consultables via `F1` avec insertion rapide |

---

## 🚀 Installation et lancement sur Omarchy (Arch Linux + Hyprland)

### Option 1 — Installation complète dans Omarchy (Recommandée)
Installe **Omega Code Studio** proprement dans votre session utilisateur (`~/.local`), crée la commande `omega-code-studio` et ajoute l'application avec son icône vectorielle directement dans votre lanceur **Walker (`Super + Espace`)** :

```bash
git clone -b arena/fa8a2c9c-omega-studio-code https://github.com/priviceahd-sys/Omega-Studio-Code-.git
builtin cd ~/Omega-Studio-Code-
./install-omarchy.sh
```

Vous pouvez ensuite lancer le logiciel :
- depuis **Walker (`Super + Espace`)** en tapant **`Omega Code Studio`** ;
- ou depuis votre terminal (**Ghostty / Alacritty**) :
  ```bash
  omega-code-studio
  ```

*(Pour désinstaller proprement à tout moment : `./uninstall-omarchy.sh`)*

### Option 2 — Lancement immédiat sans installation système
Depuis le dossier téléchargé ou cloné :

```bash
./run.sh
```

Le script détecte automatiquement **`uv`** (présent par défaut sur Omarchy) ou `python3 -m venv`, installe `PyQt6` dans `.venv` au premier démarrage et active le support natif Wayland (`QT_QPA_PLATFORM=wayland;xcb`).

---

## ⌨️ Raccourcis clavier principaux

| Raccourci | Action |
| :--- | :--- |
| `F4` | **Vérifier** la syntaxe, les déclarations et la cohérence des types |
| `F5` | **Exécuter** l'algorithme sans interruption (ou continuer jusqu'au prochain point d'arrêt) |
| `F10` | **Pas à Pas** — Instruction suivante (Step Over) |
| `F11` | **Pas à Pas détaillé** — Entrer dans la procédure ou fonction (Step Into) |
| `F8` | **Pas à Pas automatique** (cadence réglable via le curseur en millisecondes) |
| `Shift + F5` | **Arrêter** immédiatement l'exécution |
| `F9` | Poser / retirer un **point d'arrêt** (`●`) sur la ligne courante (ou clic sur le numéro de ligne) |
| `F1` | Ouvrir l'**Aide Alg_32** directement sur le mot-clef ou la fonction sous le curseur |
| `Ctrl + Espace` | Ouvrir l'**auto-complétion** des instructions, fonctions et variables |
| `Ctrl + Shift + F` | **Formater** automatiquement l'indentation et mettre les mots-clefs en MAJUSCULES |
| `Ctrl + F` / `Ctrl + H` | Rechercher / Remplacer dans l'algorithme |
| `Ctrl + +` / `Ctrl + -` | Agrandir / réduire la taille de police de l'éditeur (ou `Ctrl + Molette`) |

---

## 📚 12 Algorithmes d'exemple prêts à l'emploi (`examples/`)

1. `01_bienvenue_omega.alg` — Prise en main, `DATESYST()`, `HEURESYST()`, boucle `POUR`, `RAC2()`
2. `02_facture_tva_conditions.alg` — `SELON ... CAS`, `SI ... ALORS ... SINON`, `IMPRIMER`
3. `03_table_multiplication.alg` — Contrôle de saisie `REPETER ... JUSQU'A` et tabulation `TAB()`
4. `04_tri_bulles_et_dichotomie.alg` — Tableaux, procédures `es` et fonction de recherche dichotomique
5. `05_recursivite_factorielle_fibo.alg` — Récursivité (`VALRET` et `DELIVRE`) et suivi de la pile d'appels
6. `06_structures_et_types.alg` — `TYPE ... FIN TYPE` et `STRUCTURE ... FINSTRUCTURE`
7. `07_procedures_parametres_es.alg` — Paramètres en Entrée (`e`), Sortie (`s`) et Entrée/Sortie (`es`)
8. `08_jeu_plus_ou_moins.alg` — Jeu interactif avec `ALEA_ENTIER` et `ITER ... SORTIRSI ... FINITER`
9. `09_chaines_palindrome_cesar.alg` — Fonctions chaînes (`LONG`, `MILIEU`, `MAJ`, `ANSI`, `CAR`)
10. `10_ecran_couleurs_vga.alg` — Palette historique 16 couleurs `COULEUR`, `CURSEUR` et `EFFACE_ECRAN`
11. `11_fichiers_clients.alg` — Fichiers séquentiels Alg_32 (`FICHIER`, `OUVRIR`, `ECRIRE`, `LIRE`, `FF`)
12. `12_base_sql_etudiants.alg` — Requêtes `EXEC SQL ... FIN EXEC` avec SQLite3 intégré

---

## 🧪 Exécuter la suite de tests automatisés

```bash
.venv/bin/pytest -v
```
