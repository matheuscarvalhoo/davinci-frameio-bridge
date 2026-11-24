#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# install.sh — macOS installer for davinci-frameio-bridge
#
# What it does:
#   1. Creates ~/.resolve_frameio/  (chmod 700)
#   2. Copies frameio_core.py and uploader_gui.py into it.
#   3. Copies the three DaVinci entry-point scripts into the Resolve
#      Scripts folders so they show up in the Workspace > Scripts menu.
#
# What it does NOT do:
#   * Never writes any credential to disk.
#   * Never overwrites your config.json if one already exists.
# ---------------------------------------------------------------------------
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SELF_DIR/src"

CORE_DIR="$HOME/.resolve_frameio"
RESOLVE_SCRIPTS="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts"
DELIVER_DIR="$RESOLVE_SCRIPTS/Deliver"

echo ">> davinci-frameio-bridge installer"
echo ">> source : $SRC"
echo ">> target : $CORE_DIR"
echo ">> resolve: $RESOLVE_SCRIPTS"
echo

if [ ! -d "$SRC" ]; then
  echo "ERROR: src/ not found next to install.sh"
  exit 1
fi

if [ ! -d "$RESOLVE_SCRIPTS" ]; then
  echo "WARNING: DaVinci Resolve scripts folder not found at:"
  echo "         $RESOLVE_SCRIPTS"
  echo "         Install DaVinci Resolve first, open it once, then re-run this script."
  exit 1
fi

# 1. Private config dir
mkdir -p "$CORE_DIR"
chmod 700 "$CORE_DIR"

# 2. Core libs
cp "$SRC/frameio_core.py" "$CORE_DIR/"
cp "$SRC/uploader_gui.py" "$CORE_DIR/"
echo "✓ Copied frameio_core.py and uploader_gui.py to $CORE_DIR"

# 3. Entry-point scripts
mkdir -p "$DELIVER_DIR"

cp "$SRC/Enviar_para_Frame.io.py"         "$DELIVER_DIR/"
cp "$SRC/Importar_comentarios.py"         "$RESOLVE_SCRIPTS/"
cp "$SRC/Enviar_ao_terminar_render.py"    "$RESOLVE_SCRIPTS/"
echo "✓ Copied menu scripts into the Resolve Scripts folder"

# 4. Preserve any existing config; do not overwrite
if [ ! -f "$CORE_DIR/config.json" ]; then
  echo "{}" > "$CORE_DIR/config.json"
  chmod 600 "$CORE_DIR/config.json"
  echo "✓ Created empty config.json (mode 600)"
else
  echo "✓ Existing config.json preserved"
fi

echo
echo "Done! Open DaVinci Resolve → Workspace → Scripts → Deliver → Enviar para Frame.io"
echo "Then click 'Configurar / Login' to enter your Adobe OAuth credentials."
