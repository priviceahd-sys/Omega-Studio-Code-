#!/usr/bin/env bash
# ==============================================================================
# Installateur dédié Omarchy (Arch Linux + Hyprland + Walker)
# Installe Omega Studio Code dans votre espace utilisateur (~/.local) sans sudo !
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SHARE="$HOME/.local/share/omega-studio-code"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
MIME_DIR="$HOME/.local/share/mime/packages"

echo "+--------------------------------------------------------------+"
echo "|    Installation d'OMEGA STUDIO CODE v2.0 sur Omarchy/Linux   |"
echo "+--------------------------------------------------------------+"

mkdir -p "$APP_SHARE" "$BIN_DIR" "$APPS_DIR" "$ICONS_DIR" "$MIME_DIR"

echo "-> Copie des fichiers de l'application vers $APP_SHARE..."
rm -rf "$APP_SHARE/omega_studio" "$APP_SHARE/examples" "$APP_SHARE/assets"
cp -r "$SCRIPT_DIR/omega_studio" "$APP_SHARE/"
cp -r "$SCRIPT_DIR/examples" "$APP_SHARE/"
cp -r "$SCRIPT_DIR/assets" "$APP_SHARE/"
cp "$SCRIPT_DIR/pyproject.toml" "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/run.sh" "$APP_SHARE/"
chmod +x "$APP_SHARE/run.sh"

echo "-> Configuration de l'environnement Python isolé (PyQt6)..."
if command -v uv >/dev/null 2>&1; then
    if [[ ! -x "$APP_SHARE/.venv/bin/python" ]]; then
        uv venv "$APP_SHARE/.venv"
    fi
    uv pip install --python "$APP_SHARE/.venv/bin/python" -r "$APP_SHARE/requirements.txt"
else
    if [[ ! -x "$APP_SHARE/.venv/bin/python" ]]; then
        python3 -m venv "$APP_SHARE/.venv"
    fi
    "$APP_SHARE/.venv/bin/pip" install --upgrade pip
    "$APP_SHARE/.venv/bin/pip" install -r "$APP_SHARE/requirements.txt"
fi

echo "-> Création de la commande : $BIN_DIR/omega-studio"
cat > "$BIN_DIR/omega-studio" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$APP_SHARE\${PYTHONPATH:+:\$PYTHONPATH}"
if [[ -n "\${WAYLAND_DISPLAY:-}" && -z "\${QT_QPA_PLATFORM:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=1
exec "$APP_SHARE/.venv/bin/python" -m omega_studio "\$@"
EOF
chmod +x "$BIN_DIR/omega-studio"

echo "-> Installation de l'icône SVG et du lanceur Walker / Hyprland..."
cp "$APP_SHARE/assets/omega-studio-code.svg" "$ICONS_DIR/omega-studio-code.svg"

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
Keywords=algo;alg32;algexec;algorithmique;pseudocode;omega;
EOF

# Association des fichiers .alg
cat > "$MIME_DIR/omega-studio-alg.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-alg">
    <comment>Algorithme Alg_32 / Omega Studio Code</comment>
    <glob pattern="*.alg"/>
    <glob pattern="*.ALG"/>
  </mime-type>
</mime-info>
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$HOME/.local/share/mime" || true

"$APP_SHARE/.venv/bin/python" -c "import sys; sys.path.insert(0, '$APP_SHARE'); import omega_studio; print('   [OK] Module Omega Studio Code v' + omega_studio.__version__ + ' vérifié.')"

echo ""
echo "Installation terminée avec succès !"
echo "  1) Depuis Omarchy (Super + Espace / Walker) : tapez « Omega Studio Code »"
if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
    echo "  2) Depuis votre terminal                    : omega-studio"
else
    echo "  2) Depuis votre terminal                    : ~/.local/bin/omega-studio"
fi
