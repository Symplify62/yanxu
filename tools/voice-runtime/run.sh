#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
exec "$PROJECT_DIR/.local-data/voice-runtime/venv/bin/python" "$SCRIPT_DIR/engine.py"
