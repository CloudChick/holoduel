#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-venv}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
AUTO_RELOAD="${AUTO_RELOAD:-true}"
INSTALL_DEPS="${INSTALL_DEPS:-true}"

# Local dev default: do not require hosted HTML game package.
export SKIP_HOSTING_GAME="${SKIP_HOSTING_GAME:-true}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN not found. Install Python 3.10+ first."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[setup] creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if [ "$INSTALL_DEPS" = "true" ]; then
  echo "[setup] installing dependencies"
  python -m pip install -r requirements.txt
fi

UVICORN_ARGS=(server:app --host "$HOST" --port "$PORT")
if [ "$AUTO_RELOAD" = "true" ]; then
  UVICORN_ARGS+=(--reload)
fi

echo "========================================"
echo "  HoloDuel Local Server (macOS)"
echo "========================================"
echo "URL        : http://$HOST:$PORT"
echo "WebSocket  : ws://$HOST:$PORT/ws"
echo "Reload     : $AUTO_RELOAD"
echo "Skip game  : $SKIP_HOSTING_GAME"
echo "Ctrl+C to stop"
echo

exec python -m uvicorn "${UVICORN_ARGS[@]}"
