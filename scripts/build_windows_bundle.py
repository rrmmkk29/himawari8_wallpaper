from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
RELEASE_DIR = ROOT / "release"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "pyinstaller"
SPEC_DIR = ROOT / "build" / "spec"
WINDOWS_VERSION_FILE = ROOT / "build" / "windows-version-info.txt"
GUI_ENTRYPOINT = ROOT / "src" / "himawari_wallpaper_gui.py"
APP_NAME = "himawari-dynamic-wallpaper-gui"
WINDOWS_ICON_PATH = ROOT / "assets" / "windows" / "app.ico"
SUPPORT_FILES = (
    (Path("README.md"), "README.md"),
    (Path("README.zh-CN.md"), "README.zh-CN.md"),
    (Path("config.example.json"), "config.example.json"),
)
GENERATED_BUNDLE_FILES = ("config.json",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Windows GUI executable bundle for end users."
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


def read_project_metadata() -> dict[str, str]:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    name_match = re.search(r'^name = "([^"]+)"', text, flags=re.MULTILINE)
    version_match = re.search(r'^version = "([^"]+)"', text, flags=re.MULTILINE)
    description_match = re.search(r'^description = "([^"]+)"', text, flags=re.MULTILINE)
    author_match = re.search(r'{ name = "([^"]+)" }', text)

    if not name_match or not version_match or not description_match:
        raise RuntimeError("Could not read project name/version from pyproject.toml")

    return {
        "name": name_match.group(1),
        "version": version_match.group(1),
        "description": description_match.group(1),
        "author": author_match.group(1) if author_match else "Unknown",
    }


def sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip())
    sanitized = sanitized.strip("-")
    if not sanitized:
        raise ValueError("Release label is empty after sanitization.")
    return sanitized


def build_output_path(output_dir: Path, project_name: str, version: str, label: str | None) -> Path:
    safe_project = project_name.replace("_", "-")
    asset_label = sanitize_label(label) if label else version
    filename = f"{safe_project}-windows-{asset_label}.zip"
    return output_dir / filename


def build_pyinstaller_command(version_file: Path) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--version-file",
        str(version_file),
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--paths",
        str(ROOT / "src"),
        str(GUI_ENTRYPOINT),
    ]
    if WINDOWS_ICON_PATH.exists():
        command.extend(["--icon", str(WINDOWS_ICON_PATH)])
    return command


def build_windows_file_version(version: str) -> str:
    parts = [int(part) for part in re.findall(r"\d+", version)]
    while len(parts) < 4:
        parts.append(0)
    return ",".join(str(part) for part in parts[:4])


def build_windows_version_info(metadata: dict[str, str]) -> str:
    file_version = build_windows_file_version(metadata["version"])
    product_version = file_version
    escaped_author = metadata["author"].replace("'", "''")
    escaped_description = metadata["description"].replace("'", "''")
    escaped_name = metadata["name"].replace("'", "''")
    escaped_version = metadata["version"].replace("'", "''")

    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({file_version}),
    prodvers=({product_version}),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{escaped_author}'),
            StringStruct('FileDescription', '{escaped_description}'),
            StringStruct('FileVersion', '{escaped_version}'),
            StringStruct('InternalName', '{escaped_name}'),
            StringStruct('OriginalFilename', '{APP_NAME}.exe'),
            StringStruct('ProductName', '{escaped_name}'),
            StringStruct('ProductVersion', '{escaped_version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)"""


def write_windows_version_file(path: Path, metadata: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_windows_version_info(metadata), encoding="utf-8")
    return path


def run_pyinstaller(version_file: Path) -> Path:
    command = build_pyinstaller_command(version_file)
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise RuntimeError(f"PyInstaller did not create the expected executable: {exe_path}")
    return exe_path


def create_bundle_archive(output_path: Path, exe_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    archive_root = output_path.stem
    added_files = 0
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(exe_path, Path(archive_root) / exe_path.name)
        added_files += 1

        for relative_path, archive_name in SUPPORT_FILES:
            source_path = ROOT / relative_path
            archive.write(source_path, Path(archive_root) / archive_name)
            added_files += 1

        config_source = ROOT / "config.example.json"
        for archive_name in GENERATED_BUNDLE_FILES:
            archive.writestr(
                str(Path(archive_root) / archive_name),
                config_source.read_text(encoding="utf-8"),
            )
            added_files += 1

    return added_files


def main() -> None:
    args = parse_args()
    metadata = read_project_metadata()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_path = build_output_path(output_dir, metadata["name"], metadata["version"], args.label)

    version_file = write_windows_version_file(WINDOWS_VERSION_FILE, metadata)
    exe_path = run_pyinstaller(version_file)
    added_files = create_bundle_archive(output_path, exe_path)

    print(f"Created: {output_path}")
    print(f"Files packed: {added_files}")


if __name__ == "__main__":
    main()
