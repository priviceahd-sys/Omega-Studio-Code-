#!/usr/bin/env bash
# ==============================================================================
# Désinstallateur propre d'Omega Studio Code sur Omarchy / Linux
# ==============================================================================
set -euo pipefail

rm -rf "$HOME/.local/share/omega-studio-code"
rm -f "$HOME/.local/bin/omega-studio"
rm -f "$HOME/.local/share/applications/omega-studio-code.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/omega-studio-code.svg"
rm -f "$HOME/.local/share/mime/packages/omega-studio-alg.xml"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true

echo "✔ Omega Studio Code a été désinstallé de ~/.local."
