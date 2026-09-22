#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY=${BOUTIQUE_PYTHON:-/Users/mingqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}
exec "$PY" "$HERE/converter.py" "$@"
