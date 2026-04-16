from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
RELEASE_DIR = ROOT / "release"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "release",
    "build",
    "dist",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".cache"}
EXCLUDE_NAMES = {
    ".env",
    "config.json",
    "wallpaper_current.bmp",
    "last_source_meta.json",
    "web_debug_screenshot.png",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a GitHub-ready source release zip for the repository."
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional release label to use in the output filename, for example v0.1.0",
    )
    parser.add_argument(
        "--output-dir",
        default=str(RELEASE_DIR),
        help="Directory where the zip file should be written",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if path.name.startswith(".env."):
        return True
    if path.name.startswith("wallpaper_") and path.suffix.lower() == ".png":
        return True
    if path.name.startswith("origin_wallpaper_") and path.suffix.lower() == ".png":
        return True
    return False


def read_project_name_and_version() -> tuple[str, str]:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    name_match = re.search(r'^name = "([^"]+)"', text, flags=re.MULTILINE)
    version_match = re.search(r'^version = "([^"]+)"', text, flags=re.MULTILINE)

    if not name_match or not version_match:
        raise RuntimeError("Could not read project name/version from pyproject.toml")

    return name_match.group(1), version_match.group(1)


def build_output_path(output_dir: Path, project_name: str, version: str, label: str | None) -> Path:
    safe_project = project_name.replace("_", "-")
    asset_label = sanitize_label(label) if label else version
    filename = f"{safe_project}-{asset_label}.zip"
    return output_dir / filename


def sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip())
    sanitized = sanitized.strip("-")
    if not sanitized:
        raise ValueError("Release label is empty after sanitization.")
    return sanitized


def create_release_zip(output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    added_files = 0
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in ROOT.rglob("*"):
            if not file.is_file():
                continue
            relative = file.relative_to(ROOT)
            if should_skip(relative):
                continue
            archive.write(file, relative)
            added_files += 1

    return added_files


def main() -> None:
    args = parse_args()
    project_name, version = read_project_name_and_version()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_path = build_output_path(output_dir, project_name, version, args.label)
    added_files = create_release_zip(output_path)

    print(f"Created: {output_path}")
    print(f"Files packed: {added_files}")


if __name__ == "__main__":
    main()
