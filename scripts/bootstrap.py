#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def get_venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a virtual environment and install Himawari wallpaper dependencies."
    )
    parser.add_argument(
        "--venv",
        default=".venv",
        help="Virtual environment directory, default: .venv",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install development dependencies in addition to runtime dependencies",
    )
    parser.add_argument(
        "--skip-playwright",
        action="store_true",
        help="Skip `playwright install chromium`",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    venv_dir = (repo_root / args.venv).resolve()

    if shutil.which("python") is None and shutil.which("python3") is None:
        raise SystemExit("Python 3 was not found in PATH.")

    print(f"Creating virtual environment in {venv_dir}")
    try:
        run([sys.executable, "-m", "venv", str(venv_dir)])
    except subprocess.CalledProcessError as exc:
        if sys.platform.startswith("linux"):
            raise SystemExit(
                "Failed to create a virtual environment. On Ubuntu/WSL, install "
                "`python3-venv` first, for example: `sudo apt install python3-venv`."
            ) from exc
        raise

    python_exe = get_venv_python(venv_dir)

    print("Upgrading pip")
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])

    install_target = ".[dev]" if args.dev else "."
    print("Installing project")
    run([str(python_exe), "-m", "pip", "install", "-e", install_target])

    if not args.skip_playwright:
        print("Installing Playwright Chromium")
        run([str(python_exe), "-m", "playwright", "install", "chromium"])

    if sys.platform.startswith("win"):
        activate_hint = f"{venv_dir.name}\\Scripts\\Activate.ps1"
    else:
        activate_hint = f"source {venv_dir.name}/bin/activate"

    print()
    print("Bootstrap complete.")
    print("Activate the virtual environment with:")
    print(f"  {activate_hint}")
    print("Then run:")
    print("  python -m himawari_wallpaper --once")


if __name__ == "__main__":
    main()
