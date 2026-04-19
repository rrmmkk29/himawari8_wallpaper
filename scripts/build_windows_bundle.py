from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
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
GENERATED_BUNDLE_FILES = (
    "config.json",
    "run_himawari.py",
    "Run Himawari Wallpaper.bat",
    "Run Himawari Once.bat",
    "Open Himawari Settings.bat",
)
SOURCE_DIR_NAME = "src"
LAUNCHER_SCRIPT_NAME = "run_himawari.py"


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


def collect_bundle_mappings(
    exe_path: Path,
) -> list[tuple[Path, Path]]:
    mappings: list[tuple[Path, Path]] = [
        (exe_path, Path(exe_path.name)),
        (ROOT / SOURCE_DIR_NAME, Path(SOURCE_DIR_NAME)),
    ]

    for relative_path, archive_name in SUPPORT_FILES:
        mappings.append((ROOT / relative_path, Path(archive_name)))

    return mappings


def build_python_launcher_script() -> str:
    return """from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from himawari_wallpaper.cli import main


if __name__ == "__main__":
    main()
"""


def build_run_bat_contents(run_once: bool) -> str:
    mode_flag = "--once" if run_once else "--run"
    return "\n".join(
        [
            "@echo off",
            "setlocal",
            "set SCRIPT_DIR=%~dp0",
            "cd /d \"%SCRIPT_DIR%\"",
            "call :resolve_python PYTHON_CMD",
            "if errorlevel 1 exit /b 1",
            "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%run_himawari.py\" "
            f"{mode_flag} --config \"%SCRIPT_DIR%config.json\"",
            "endlocal",
            "exit /b %errorlevel%",
            "",
            ":resolve_python",
            "set \"%~1=\"",
            "if defined CONDA_PREFIX if exist \"%CONDA_PREFIX%\\python.exe\" (",
            "    set \"%~1=%CONDA_PREFIX%\\python.exe\"",
            "    exit /b 0",
            ")",
            "for %%I in (py.exe py python.exe python) do (",
            "    call :find_candidate \"%%~I\" FOUND_PYTHON",
            "    if defined FOUND_PYTHON (",
            "        set \"%~1=%FOUND_PYTHON%\"",
            "        exit /b 0",
            "    )",
            ")",
            "echo Could not find a usable Python interpreter.",
            "echo Install Python or launch this script from an activated conda environment.",
            "exit /b 1",
            "",
            ":find_candidate",
            "set \"%~2=\"",
            "for /f \"delims=\" %%P in ('where %~1 2^>nul') do (",
            "    echo %%~fP| findstr /i /c:\"\\WindowsApps\\\" >nul",
            "    if errorlevel 1 (",
            "        set \"%~2=%%~fP\"",
            "        exit /b 0",
            "    )",
            ")",
            "exit /b 1",
        ]
    ) + "\n"


def build_gui_bat_contents(exe_name: str) -> str:
    return "\n".join(
        [
            "@echo off",
            "setlocal",
            "set SCRIPT_DIR=%~dp0",
            "cd /d \"%SCRIPT_DIR%\"",
            f"start \"\" \"%SCRIPT_DIR%{exe_name}\"",
            "endlocal",
        ]
    ) + "\n"


def build_generated_bundle_contents(exe_name: str) -> dict[str, str]:
    config_source = ROOT / "config.example.json"
    return {
        "config.json": config_source.read_text(encoding="utf-8"),
        LAUNCHER_SCRIPT_NAME: build_python_launcher_script(),
        "Run Himawari Wallpaper.bat": build_run_bat_contents(run_once=False),
        "Run Himawari Once.bat": build_run_bat_contents(run_once=True),
        "Open Himawari Settings.bat": build_gui_bat_contents(exe_name),
    }


def _ignore_copy_names(_dir: str, entries: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in entries:
        if name == "__pycache__" or name.endswith((".pyc", ".pyo")):
            ignored.add(name)
    return ignored


def build_bundle_directory(
    bundle_dir: Path,
    exe_path: Path,
) -> int:
    bundle_dir.mkdir(parents=True, exist_ok=True)

    for source_path, relative_target in collect_bundle_mappings(exe_path=exe_path):
        destination_path = bundle_dir / relative_target
        if source_path.is_dir():
            shutil.copytree(
                source_path,
                destination_path,
                dirs_exist_ok=True,
                ignore=_ignore_copy_names,
            )
        else:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)

    for relative_target, content in build_generated_bundle_contents(exe_path.name).items():
        destination_path = bundle_dir / relative_target
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(content, encoding="utf-8")

    return sum(1 for path in bundle_dir.rglob("*") if path.is_file())


def create_bundle_archive(
    output_path: Path,
    exe_path: Path,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="himawari-bundle-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        archive_root = temp_dir / output_path.stem
        build_bundle_directory(archive_root, exe_path=exe_path)

        added_files = 0
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source_path in sorted(archive_root.rglob("*")):
                if not source_path.is_file():
                    continue
                archive.write(source_path, source_path.relative_to(temp_dir))
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
