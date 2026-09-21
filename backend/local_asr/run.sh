#!/bin/bash
set -euo pipefail
script_dir="$(cd "$(dirname "$0")" && pwd)"
asr_home="${LOCAL_ASR_HOME:-$HOME/.local/share/pcim-asr}"
if [[ ! -x "$asr_home/venv/bin/python" ]]; then
  echo '本地转写环境不存在，请先按skill说明准备环境。' >&2
  exit 1
fi
# OS-level network denial covers native libraries as well as Python requests.
exec /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  "$asr_home/venv/bin/python" "$script_dir/transcribe.py" "$@"
