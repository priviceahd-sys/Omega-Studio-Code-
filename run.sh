#!/usr/bin/env bash
# ==============================================================================
# Lanceur direct d'Omega Studio Code (optimisé Omarchy / Arch Linux / Wayland)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

SYS_PY="/usr/bin/python3"
if [[ ! -x "$SYS_PY" ]]; then
    SYS_PY="$(command -v python3)"
fi

# Si le Python système d'Arch/Omarchy possède déjà python-pyqt6, lancement instantané !
if "$SYS_PY" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
    PYTHON_BIN="$SYS_PY"
else
    VENV_DIR="$SCRIPT_DIR/.venv"
    if [[ ! -x "$VENV_DIR/bin/python" ]] || ! "$VENV_DIR/bin/python" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
        echo "-> Initialisation de l'environnement Python local (.venv)..."
        if command -v pacman >/dev/null 2>&1; then
            echo "-> Installation du paquet natif Arch/Omarchy 'python-pyqt6'..."
            if sudo pacman -S --needed python-pyqt6 qt6-wayland && "$SYS_PY" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
                PYTHON_BIN="$SYS_PY"
            fi
        fi
        if [[ -z "${PYTHON_BIN:-}" ]]; then
            "$SYS_PY" -m venv --clear "$VENV_DIR"
            "$VENV_DIR/bin/pip" --default-timeout=90 install -r "$SCRIPT_DIR/requirements.txt"
            PYTHON_BIN="$VENV_DIR/bin/python"
        fi
    else
        PYTHON_BIN="$VENV_DIR/bin/python"
    fi
fi

# Détection Wayland / Hyprland native (Omarchy) avec repli XCB automatique
if [[ -n "${WAYLAND_DISPLAY:-}" && -z "${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=1

exec "$PYTHON_BIN" -m omega_studio "$@"
