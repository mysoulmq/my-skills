#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSHEET_PYTHON="${WORKSHEET_PYTHON:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
if [ ! -x "$WORKSHEET_PYTHON" ]; then
  echo '缺少已验证的文档运行环境；调用 load_workspace_dependencies，并设置 WORKSHEET_PYTHON。' >&2
  exit 1
fi
exec "$WORKSHEET_PYTHON" "$SCRIPT_DIR/worksheet.py" "$@"
