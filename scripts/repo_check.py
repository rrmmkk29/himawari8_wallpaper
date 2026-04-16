#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repository checks before pushing to GitHub."
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip ruff checks",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Skip compileall syntax check",
    )
    parser.add_argument(
        "--skip-cli",
        action="store_true",
        help="Skip CLI help check",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.skip_compile:
        run([sys.executable, "-m", "compileall", "src", "tests", "scripts"])

    if not args.skip_lint:
        run([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"])

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "-q"])

    if not args.skip_cli:
        run([sys.executable, "-m", "himawari_wallpaper", "--help"])

    print("Repository checks passed.")


if __name__ == "__main__":
    main()
