#!/usr/bin/env bash

set -euo pipefail

VENV_DIR="${1:-.venv}"
INSTALL_DEV="${INSTALL_DEV:-0}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 was not found in PATH." >&2
  exit 1
fi

echo "Creating virtual environment in ${VENV_DIR}"
if ! "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
  echo >&2
  echo "Failed to create a virtual environment." >&2
  echo "On Ubuntu/WSL, install python3-venv first, for example:" >&2
  echo "  sudo apt install python3-venv" >&2
  exit 1
fi

PYTHON_EXE="${VENV_DIR}/bin/python"

echo "Upgrading pip"
"${PYTHON_EXE}" -m pip install --upgrade pip

if [[ "${INSTALL_DEV}" == "1" ]]; then
  echo "Installing project with dev dependencies"
  "${PYTHON_EXE}" -m pip install -e ".[dev]"
else
  echo "Installing project"
  "${PYTHON_EXE}" -m pip install -e .
fi

echo "Installing Playwright Chromium"
"${PYTHON_EXE}" -m playwright install chromium

echo
echo "Bootstrap complete."
echo "Activate the venv with:"
echo "  source ${VENV_DIR}/bin/activate"
echo "Run one refresh with:"
echo "  himawari-wallpaper --once"
