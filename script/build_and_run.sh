#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/apps/desktop"
RUNTIME_DIR="$ROOT_DIR/.tino-runtime"
TINO_HOME="$RUNTIME_DIR/home"
TINO_USER_DATA="$RUNTIME_DIR/user-data"
DEFAULT_PYTHON_VENV="$(cd "$ROOT_DIR/.." && pwd)/.hermes-runtime/venv"
PYTHON_VENV="${TINO_PYTHON_VENV:-$DEFAULT_PYTHON_VENV}"

export PATH="$PYTHON_VENV/bin:$PATH"
export TINO_HOME="$TINO_HOME"
export TINO_DESKTOP_USER_DATA_DIR="$TINO_USER_DATA"
export TINO_DESKTOP_ROOT="$ROOT_DIR"
export TINO_DESKTOP_HERMES="$PYTHON_VENV/bin/hermes"
export TINO_AGENT_BRANDED=1
export CSC_IDENTITY_AUTO_DISCOVERY=false

# agent-browser keeps its managed Chrome under this per-user cache on macOS.
# Pass the executable explicitly: Tino' availability check otherwise only
# scans Playwright caches and hides the browser tools despite a valid install.
TINO_CHROME_PATH="$(find "$HOME/.agent-browser/browsers" -type f -path '*/Contents/MacOS/Google Chrome for Testing' -print -quit 2>/dev/null || true)"
if [[ -n "$TINO_CHROME_PATH" ]]; then
  export AGENT_BROWSER_EXECUTABLE_PATH="$TINO_CHROME_PATH"
fi

mkdir -p "$TINO_HOME" "$TINO_USER_DATA"

if [[ ! -x "$PYTHON_VENV/bin/python" ]]; then
  echo "Python runtime not found at $PYTHON_VENV" >&2
  echo "Set TINO_PYTHON_VENV to a Python 3.10+ Tino virtual environment." >&2
  exit 1
fi

# Desktop's source-runtime resolver intentionally prefers a checkout-local
# environment. Keep dependencies outside the checkout, but expose that existing
# isolated environment through the conventional ignored .venv path.
if [[ ! -e "$ROOT_DIR/.venv" && ! -L "$ROOT_DIR/.venv" ]]; then
  ln -s "$PYTHON_VENV" "$ROOT_DIR/.venv"
fi

build_app() {
  cd "$DESKTOP_DIR"
  npm run pack
}

resolve_app_bundle() {
  local candidate

  candidate="$(find "$DESKTOP_DIR/release" -maxdepth 2 -type d -name 'Tino Agent.app' -print -quit 2>/dev/null || true)"
  if [[ -z "$candidate" ]]; then
    echo "Tino Agent.app was not found. Run with --build-only first." >&2
    exit 1
  fi
  printf '%s\n' "$candidate"
}

launch_app() {
  local app_bundle="$1"

  local -a browser_env=()
  if [[ -n "${AGENT_BROWSER_EXECUTABLE_PATH:-}" ]]; then
    browser_env=(--env "AGENT_BROWSER_EXECUTABLE_PATH=$AGENT_BROWSER_EXECUTABLE_PATH")
  fi

  /usr/bin/open -n "$app_bundle" \
    --env "PATH=$PATH" \
    --env "TINO_HOME=$TINO_HOME" \
    --env "TINO_DESKTOP_USER_DATA_DIR=$TINO_DESKTOP_USER_DATA_DIR" \
    --env "TINO_DESKTOP_ROOT=$TINO_DESKTOP_ROOT" \
    --env "TINO_DESKTOP_HERMES=$TINO_DESKTOP_HERMES" \
    --env "TINO_AGENT_BRANDED=1" \
    "${browser_env[@]}" \
    --env "TINO_ISOLATED_CREDENTIALS=1"
}

mode="${1:---run}"

case "$mode" in
  --run)
    build_app
    launch_app "$(resolve_app_bundle)"
    ;;
  --launch)
    launch_app "$(resolve_app_bundle)"
    ;;
  --build-only)
    build_app
    ;;
  --debug)
    build_app
    app_bundle="$(resolve_app_bundle)"
    exec lldb -- "$app_bundle/Contents/MacOS/Tino Agent"
    ;;
  --logs)
    mkdir -p "$TINO_HOME/logs"
    touch "$TINO_HOME/logs/desktop.log"
    exec tail -F "$TINO_HOME/logs/desktop.log"
    ;;
  --verify)
    launch_app "$(resolve_app_bundle)"
    for _ in {1..45}; do
      backend_port="$(awk -F= '/TINO_BACKEND_READY port=/{port=$NF} END{gsub(/[^0-9]/, "", port); print port}' "$TINO_HOME/logs/desktop.log" 2>/dev/null || true)"
      if pgrep -x 'Tino Agent' >/dev/null 2>&1 && [[ "$backend_port" =~ ^[0-9]+$ ]] && \
        curl --fail --silent "http://127.0.0.1:$backend_port/api/health" >/dev/null; then
        echo "Tino Agent launched successfully."
        echo "Backend healthy on 127.0.0.1:$backend_port."
        echo "Isolated data: $RUNTIME_DIR"
        exit 0
      fi
      sleep 1
    done
    echo "Tino Agent did not stay running; inspect $TINO_HOME/logs/desktop.log" >&2
    exit 1
    ;;
  *)
    echo "Usage: $0 [--run|--launch|--build-only|--debug|--logs|--verify]" >&2
    exit 2
    ;;
esac
