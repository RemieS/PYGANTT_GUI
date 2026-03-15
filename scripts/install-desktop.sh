#!/usr/bin/env bash
set -euo pipefail

APP_NAME="pygantt"
PKG_DIR="$(python -c 'import importlib.util, pathlib; spec=importlib.util.find_spec("pygantt"); print(pathlib.Path(spec.origin).parent)')"
ASSET_DIR="$PKG_DIR/assets"

mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"

cp "$ASSET_DIR/pygantt.desktop" "$HOME/.local/share/applications/pygantt.desktop"
cp "$ASSET_DIR/pygantt.png" "$HOME/.local/share/icons/hicolor/256x256/apps/pygantt.png"

chmod +x "$HOME/.local/share/applications/pygantt.desktop"

echo "Installed desktop launcher for PyGantt."