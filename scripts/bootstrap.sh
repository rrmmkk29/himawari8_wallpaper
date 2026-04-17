#!/usr/bin/env bash

set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 was not found in PATH." >&2
  exit 1
fi

MANAGER="conda"
VENV_DIR=".venv"
CONDA_ENV_NAME="himawari-wallpaper"
PYTHON_VERSION="3.11"
INSTALL_DEV=0
WITH_PLAYWRIGHT=0
SKIP_PLAYWRIGHT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manager)
      MANAGER="$2"
      shift 2
      ;;
    --conda)
      MANAGER="conda"
      shift
      ;;
    --venv-mode)
      MANAGER="venv"
      shift
      ;;
    --env-name)
      CONDA_ENV_NAME="$2"
      shift 2
      ;;
    --python-version)
      PYTHON_VERSION="$2"
      shift 2
      ;;
    --venv)
      VENV_DIR="$2"
      shift 2
      ;;
    --dev)
      INSTALL_DEV=1
      shift
      ;;
    --with-playwright)
      WITH_PLAYWRIGHT=1
      shift
      ;;
    --skip-playwright)
      SKIP_PLAYWRIGHT=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

ARGS=("scripts/bootstrap.py" "--manager" "$MANAGER")

if [[ "$MANAGER" == "conda" ]]; then
  ARGS+=("--conda-env-name" "$CONDA_ENV_NAME" "--python-version" "$PYTHON_VERSION")
else
  ARGS+=("--venv" "$VENV_DIR")
fi

if [[ "$INSTALL_DEV" == "1" ]]; then
  ARGS+=("--dev")
fi

if [[ "$WITH_PLAYWRIGHT" == "1" ]]; then
  ARGS+=("--with-playwright")
fi

if [[ "$SKIP_PLAYWRIGHT" == "1" ]]; then
  ARGS+=("--skip-playwright")
fi

"${PYTHON_BIN}" "${ARGS[@]}"
