#!/usr/bin/env bash
# ==============================================================================
# Lanceur direct d'Omega Studio Code (optimisé Omarchy / Arch Linux / Wayland)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

VENV_DIR="$SCRIPT_DIR/.venv"

# Création automatique de l'environnement virtuel au premier lancement
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "-> Initialisation de l'environnement Python local (.venv)..."
    if command -v uv >/dev/null 2>&1; then
        uv venv --system-site-packages "$VENV_DIR" 2>/dev/null || uv venv "$VENV_DIR"
        if ! "$VENV_DIR/bin/python" -c "import PyQt6" >/dev/null 2>&1; then
            uv pip install --python "$VENV_DIR/bin/python" -r "$SCRIPT_DIR/requirements.txt"
        fi
    else
        python3 -m venv --system-site-packages "$VENV_DIR"
        if ! "$VENV_DIR/bin/python" -c "import PyQt6" >/dev/null 2>&1; then
            "$VENV_DIR/bin/pip" install --upgrade pip
            "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
        fi
    fi
fi

# Détection Wayland / Hyprland native (Omarchy) avec repli XCB automatique
if [[ -n "${WAYLAND_DISPLAY:-}" && -z "${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=1

exec "$VENV_DIR/bin/python" -m omega_studio "$@"
