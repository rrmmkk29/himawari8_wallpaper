#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_CONDA_ENV = "himawari-wallpaper"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def get_venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def build_conda_create_command(conda_exe: str, env_name: str, python_version: str) -> list[str]:
    return [conda_exe, "create", "-y", "-n", env_name, f"python={python_version}", "pip"]


def build_conda_run_command(conda_exe: str, env_name: str, command: list[str]) -> list[str]:
    return [conda_exe, "run", "--no-capture-output", "-n", env_name, *command]


def build_install_target(dev: bool, with_playwright: bool) -> str:
    extras: list[str] = []
    if dev:
        extras.append("dev")
    if with_playwright:
        extras.append("browser")
    if not extras:
        return "."
    return f".[{','.join(extras)}]"


def find_conda_executable(custom: str | None = None) -> str:
    if custom:
        return custom

    for candidate in ("conda", "mamba", "micromamba"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise SystemExit(
        "Conda-compatible executable was not found in PATH. "
        "Install conda/mamba/micromamba first, or use `--manager venv` as a fallback."
    )


def conda_env_exists(conda_exe: str, env_name: str) -> bool:
    result = subprocess.run(
        [conda_exe, "env", "list", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    envs = payload.get("envs", [])
    lowered = env_name.lower()
    return any(Path(env_path).name.lower() == lowered for env_path in envs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a venv or conda environment and install Himawari wallpaper dependencies."
    )
    parser.add_argument(
        "--manager",
        choices=("venv", "conda"),
        default="conda",
        help="Environment manager to use, default: conda",
    )
    parser.add_argument(
        "--venv",
        default=".venv",
        help="Virtual environment directory for venv mode, default: .venv",
    )
    parser.add_argument(
        "--conda-env-name",
        default=DEFAULT_CONDA_ENV,
        help=f"Conda environment name for conda mode, default: {DEFAULT_CONDA_ENV}",
    )
    parser.add_argument(
        "--conda-exe",
        default=None,
        help="Optional conda executable path, for example conda or mamba",
    )
    parser.add_argument(
        "--python-version",
        default="3.11",
        help="Python version to create inside the conda environment, default: 3.11",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install development dependencies in addition to runtime dependencies",
    )
    parser.add_argument(
        "--with-playwright",
        action="store_true",
        help="Install optional Playwright browser fallback support",
    )
    parser.add_argument(
        "--skip-playwright",
        action="store_true",
        help="Skip `playwright install chromium` after installing optional browser fallback support",
    )
    return parser.parse_args()


def bootstrap_venv(args: argparse.Namespace, repo_root: Path) -> None:
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

    install_target = build_install_target(args.dev, args.with_playwright)
    print("Installing project")
    run([str(python_exe), "-m", "pip", "install", "-e", install_target])

    if args.with_playwright and not args.skip_playwright:
        print("Installing Playwright Chromium")
        run([str(python_exe), "-m", "playwright", "install", "chromium"])

    if sys.platform.startswith("win"):
        activate_hint = f"{venv_dir.name}\\Scripts\\Activate.ps1"
    else:
        activate_hint = f"source {venv_dir.name}/bin/activate"

    print()
    print("Bootstrap complete.")
    print("Activate the environment with:")
    print(f"  {activate_hint}")
    print("Then run:")
    print("  python -m himawari_wallpaper --once")
    if not args.with_playwright:
        print("Optional browser fallback:")
        print('  python -m pip install -e ".[browser]"')
        print("  python -m playwright install chromium")
    print("Cleanup hint:")
    print("  python scripts/uninstall.py --all")


def bootstrap_conda(args: argparse.Namespace, repo_root: Path) -> None:
    conda_exe = find_conda_executable(args.conda_exe)
    env_name = args.conda_env_name

    if conda_env_exists(conda_exe, env_name):
        print(f"Conda environment already exists: {env_name}")
    else:
        print(f"Creating conda environment: {env_name}")
        run(build_conda_create_command(conda_exe, env_name, args.python_version))

    print("Upgrading pip inside conda environment")
    run(build_conda_run_command(conda_exe, env_name, ["python", "-m", "pip", "install", "--upgrade", "pip"]))

    install_target = build_install_target(args.dev, args.with_playwright)
    print("Installing project inside conda environment")
    run(build_conda_run_command(conda_exe, env_name, ["python", "-m", "pip", "install", "-e", install_target]))

    if args.with_playwright and not args.skip_playwright:
        print("Installing Playwright Chromium inside conda environment")
        run(build_conda_run_command(conda_exe, env_name, ["python", "-m", "playwright", "install", "chromium"]))

    print()
    print("Bootstrap complete.")
    print("Activate the environment with:")
    print(f"  conda activate {env_name}")
    print("Then run:")
    print("  python -m himawari_wallpaper --once")
    if not args.with_playwright:
        print("Optional browser fallback:")
        print('  python -m pip install -e ".[browser]"')
        print("  python -m playwright install chromium")
    print("Cleanup hint:")
    print(f"  python scripts/uninstall.py --all --remove-conda-env {env_name}")


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if args.manager == "conda":
        bootstrap_conda(args, repo_root)
        return

    bootstrap_venv(args, repo_root)


if __name__ == "__main__":
    main()
