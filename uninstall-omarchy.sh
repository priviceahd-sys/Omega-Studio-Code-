#!/usr/bin/env bash
# ==============================================================================
# Désinstallateur propre d'Omega Code Studio (ne supprime jamais Omega Studio Code)
# ==============================================================================
set -euo pipefail

rm -rf "$HOME/.local/share/omega-code-studio"
rm -f "$HOME/.local/bin/omega-code-studio"
rm -f "$HOME/.local/share/applications/omega-code-studio.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/omega-code-studio.svg"
rm -f "$HOME/.local/share/mime/packages/omega-code-studio-alg.xml"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true

echo "✔ Omega Code Studio a été désinstallé (Omega Studio Code est conservé intact)."
