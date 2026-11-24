#!/usr/bin/env bash
# ==============================================================================
# Installateur dédié Omarchy (Arch Linux + Hyprland + Walker)
# Installe "Omega Code Studio" (commande `omega-code-studio` + alias `omega-studio`)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SHARE="$HOME/.local/share/omega-code-studio"
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

# Nettoyage automatique de l'ancien dossier/lanceur si une version précédente était présente
rm -rf "$HOME/.local/share/omega-studio-code"
rm -f "$APPS_DIR/omega-studio-code.desktop"
rm -f "$ICONS_DIR/omega-studio-code.svg"

echo "-> Copie des fichiers de l'application vers $APP_SHARE..."
rm -rf "$APP_SHARE/omega_studio" "$APP_SHARE/examples" "$APP_SHARE/assets"
cp -r "$SCRIPT_DIR/omega_studio" "$APP_SHARE/"
cp -r "$SCRIPT_DIR/examples" "$APP_SHARE/"
cp -r "$SCRIPT_DIR/assets" "$APP_SHARE/"
cp "$SCRIPT_DIR/pyproject.toml" "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/run.sh" "$APP_SHARE/"
chmod +x "$APP_SHARE/run.sh"

echo "-> Vérification de PyQt6 sur le système..."
if ! "$SYS_PY" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
    if command -v pacman >/dev/null 2>&1; then
        echo "-> Installation du paquet natif Arch/Omarchy 'python-pyqt6' via pacman..."
        sudo pacman -S --needed python-pyqt6 qt6-wayland || true
    fi
fi

if "$SYS_PY" -c "import PyQt6.QtWidgets" >/dev/null 2>&1; then
    echo "-> PyQt6 système détecté : liaison rapide (.venv --system-site-packages)..."
    "$SYS_PY" -m venv --system-site-packages --without-pip --clear "$APP_SHARE/.venv"
else
    echo "-> Installation de PyQt6 dans l'environnement virtuel (.venv)..."
    "$SYS_PY" -m venv --clear "$APP_SHARE/.venv"
    if ! "$APP_SHARE/.venv/bin/pip" --default-timeout=90 install -r "$APP_SHARE/requirements.txt"; then
        if command -v uv >/dev/null 2>&1; then
            UV_HTTP_TIMEOUT=90 uv pip install --python "$APP_SHARE/.venv/bin/python" -r "$APP_SHARE/requirements.txt"
        else
            echo "[ERREUR] Impossible de télécharger PyQt6 depuis pypi.org."
            echo "Sur Omarchy/Arch, exécutez simplement : sudo pacman -S python-pyqt6 qt6-wayland"
            exit 1
        fi
    fi
fi

echo "-> Création de la commande : $BIN_DIR/omega-code-studio"
cat > "$BIN_DIR/omega-code-studio" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$APP_SHARE\${PYTHONPATH:+:\$PYTHONPATH}"
if [[ -n "\${WAYLAND_DISPLAY:-}" && -z "\${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=1
exec "$APP_SHARE/.venv/bin/python" -m omega_studio "\$@"
EOF
chmod +x "$BIN_DIR/omega-code-studio"
ln -sf "$BIN_DIR/omega-code-studio" "$BIN_DIR/omega-studio"

echo "-> Installation de l'icône SVG et du lanceur Walker « Omega Code Studio »..."
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

"$APP_SHARE/.venv/bin/python" -c "import sys; sys.path.insert(0, '$APP_SHARE'); import omega_studio, PyQt6; print('   [OK] ' + omega_studio.__app_name__ + ' v' + omega_studio.__version__ + ' + PyQt6 prêts !')"

echo ""
echo "Installation terminée avec succès !"
echo "  1) Depuis Omarchy (Super + Espace / Walker) : tapez « Omega Code Studio »"
if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
    echo "  2) Depuis votre terminal                    : omega-code-studio"
else
    echo "  2) Depuis votre terminal                    : ~/.local/bin/omega-code-studio"
fi
