#!/usr/bin/env bash
# ==============================================================================
# Installateur dédié Omarchy (Arch Linux + Hyprland + Walker)
# - Installe "Omega Code Studio" (`omega-code-studio`) avec 100 % des fonctions
# - Préserve intégralement "Omega Studio Code" :
#     * si c'est une autre application système, ne la touche jamais ;
#     * si c'est l'installation précédente d'Alg_32, la met également à jour !
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SHARE="$HOME/.local/share/omega-code-studio"
LEGACY_SHARE="$HOME/.local/share/omega-studio-code"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
MIME_DIR="$HOME/.local/share/mime/packages"

SYS_PY="/usr/bin/python3"
if [[ ! -x "$SYS_PY" ]]; then
    SYS_PY="$(command -v python3)"
fi

echo "+--------------------------------------------------------------+"
echo "|    Installation d'OMEGA CODE STUDIO v2.0 sur Omarchy/Linux   |"
echo "+--------------------------------------------------------------+"

mkdir -p "$APP_SHARE" "$BIN_DIR" "$APPS_DIR" "$ICONS_DIR" "$MIME_DIR"

echo "-> Vérification de PyQt6 sur le système..."
if ! "$SYS_PY" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
    if command -v pacman >/dev/null 2>&1; then
        echo "-> Installation du paquet natif Arch/Omarchy 'python-pyqt6' via pacman..."
        sudo pacman -S --needed python-pyqt6 qt6-wayland || true
    fi
fi

setup_target_dir() {
    local target_dir="$1"
    mkdir -p "$target_dir"
    rm -rf "$target_dir/omega_studio" "$target_dir/examples" "$target_dir/assets"
    cp -r "$SCRIPT_DIR/omega_studio" "$target_dir/"
    cp -r "$SCRIPT_DIR/examples" "$target_dir/"
    cp -r "$SCRIPT_DIR/assets" "$target_dir/"
    cp "$SCRIPT_DIR/pyproject.toml" "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/run.sh" "$target_dir/"
    chmod +x "$target_dir/run.sh"

    if "$SYS_PY" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
        "$SYS_PY" -m venv --system-site-packages --without-pip --clear "$target_dir/.venv"
    else
        "$SYS_PY" -m venv --clear "$target_dir/.venv"
        if ! "$target_dir/.venv/bin/pip" --default-timeout=90 install -r "$target_dir/requirements.txt"; then
            if command -v uv >/dev/null 2>&1; then
                UV_HTTP_TIMEOUT=90 uv pip install --python "$target_dir/.venv/bin/python" -r "$target_dir/requirements.txt"
            else
                echo "[ERREUR] Impossible de télécharger PyQt6."
                echo "Sur Omarchy/Arch, exécutez simplement : sudo pacman -S python-pyqt6 qt6-wayland"
                exit 1
            fi
        fi
    fi
}

echo "-> Installation complète d'Omega Code Studio dans $APP_SHARE..."
setup_target_dir "$APP_SHARE"

cat > "$BIN_DIR/omega-code-studio" <<EOF
#!/usr/bin/env bash
export OMEGA_APP_NAME="Omega Code Studio"
export OMEGA_DESKTOP_ID="omega-code-studio"
export PYTHONPATH="$APP_SHARE\${PYTHONPATH:+:\$PYTHONPATH}"
if [[ -n "\${WAYLAND_DISPLAY:-}" && -z "\${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=1
exec "$APP_SHARE/.venv/bin/python" -m omega_studio "\$@"
EOF
chmod +x "$BIN_DIR/omega-code-studio"

cp "$APP_SHARE/assets/omega-studio-code.svg" "$ICONS_DIR/omega-code-studio.svg"

cat > "$APPS_DIR/omega-code-studio.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Omega Code Studio
GenericName=IDE Algorithmique (Alg_32)
Comment=Environnement moderne de création, débogage Pas-à-Pas et traduction d'algorithmes (.alg)
Exec=$BIN_DIR/omega-code-studio %f
Icon=omega-code-studio
Terminal=false
Categories=Development;IDE;Education;
MimeType=text/x-alg;
StartupWMClass=omega-code-studio
Keywords=omega;code;studio;algo;alg32;algexec;algorithmique;pseudocode;
EOF

# Si une installation précédente d'Omega Studio Code (version Alg_32) existe déjà,
# on la conserve ET on la met à jour avec toutes les fonctionnalités (sans jamais
# supprimer ni écraser une autre application tierce).
if [[ -d "$LEGACY_SHARE/omega_studio" ]]; then
    echo "-> Mise à jour et conservation d'Omega Studio Code dans $LEGACY_SHARE..."
    setup_target_dir "$LEGACY_SHARE"

    cat > "$BIN_DIR/omega-studio" <<EOF
#!/usr/bin/env bash
export OMEGA_APP_NAME="Omega Studio Code"
export OMEGA_DESKTOP_ID="omega-studio-code"
export PYTHONPATH="$LEGACY_SHARE\${PYTHONPATH:+:\$PYTHONPATH}"
if [[ -n "\${WAYLAND_DISPLAY:-}" && -z "\${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=1
exec "$LEGACY_SHARE/.venv/bin/python" -m omega_studio "\$@"
EOF
    chmod +x "$BIN_DIR/omega-studio"

    cp "$LEGACY_SHARE/assets/omega-studio-code.svg" "$ICONS_DIR/omega-studio-code.svg"

    cat > "$APPS_DIR/omega-studio-code.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Omega Studio Code
GenericName=IDE Algorithmique (Alg_32)
Comment=Environnement moderne de création, débogage Pas-à-Pas et traduction d'algorithmes (.alg)
Exec=$BIN_DIR/omega-studio %f
Icon=omega-studio-code
Terminal=false
Categories=Development;IDE;Education;
MimeType=text/x-alg;
StartupWMClass=omega-studio-code
Keywords=omega;studio;code;algo;alg32;algexec;algorithmique;pseudocode;
EOF
fi

# Association des fichiers .alg
cat > "$MIME_DIR/omega-code-studio-alg.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-alg">
    <comment>Algorithme Alg_32 / Omega Code Studio</comment>
    <glob pattern="*.alg"/>
    <glob pattern="*.ALG"/>
  </mime-type>
</mime-info>
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$HOME/.local/share/mime" || true

"$APP_SHARE/.venv/bin/python" -c "import sys; sys.path.insert(0, '$APP_SHARE'); import omega_studio, PyQt6; print('   [OK] Omega Code Studio v' + omega_studio.__version__ + ' prêt (toutes fonctionnalités actives) !')"

echo ""
echo "Installation terminée avec succès !"
echo "  • Nouvelle application : « Omega Code Studio » (commande : ~/.local/bin/omega-code-studio)"
if [[ -d "$LEGACY_SHARE/omega_studio" ]]; then
    echo "  • Ancienne application : « Omega Studio Code » conservée et mise à jour (commande : ~/.local/bin/omega-studio)"
else
    echo "  • Toute autre application « Omega Studio Code » présente sur votre PC a été intégralement préservée."
fi
