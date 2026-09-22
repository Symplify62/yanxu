#!/bin/sh
# This isolated environment is not the existing pcim-asr/Qwen environment.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
RUNTIME_DIR="$PROJECT_DIR/.local-data/voice-runtime"
mkdir -p "$RUNTIME_DIR/models"
if [ ! -x "$RUNTIME_DIR/venv/bin/python" ]; then
  uv venv --python 3.12 "$RUNTIME_DIR/venv"
fi
uv pip sync --python "$RUNTIME_DIR/venv/bin/python" "$SCRIPT_DIR/requirements.txt"
"$RUNTIME_DIR/venv/bin/python" "$SCRIPT_DIR/download_model.py"
