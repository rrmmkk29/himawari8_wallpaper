from __future__ import annotations

import argparse
import os
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
RUNNER_ENTRYPOINT = ROOT / "src" / "himawari_wallpaper_runner.py"
GUI_APP_NAME = "himawari-dynamic-wallpaper-gui"
RUNNER_APP_NAME = "himawari-dynamic-wallpaper"
BACKGROUND_APP_NAME = "himawari-dynamic-wallpaper-background"
WINDOWS_ICON_PATH = ROOT / "assets" / "windows" / "app.ico"
CONDA_RUNTIME_DLLS = (
    "ffi-8.dll",
    "jpeg8.dll",
    "lcms2.dll",
    "libcrypto-3-x64.dll",
    "libexpat.dll",
    "liblzma.dll",
    "libssl-3-x64.dll",
    "libtiff.dll",
    "libwebp.dll",
    "libwebpdecoder.dll",
    "libwebpdemux.dll",
    "libwebpmux.dll",
    "openjp2.dll",
    "tcl86t.dll",
    "tiff.dll",
    "tk86t.dll",
    "turbojpeg.dll",
    "zlib-ng2.dll",
    "zlib.dll",
    "zlib1.dll",
)
SUPPORT_FILES = (
    (Path("README.md"), "README.md"),
    (Path("README.zh-CN.md"), "README.zh-CN.md"),
    (Path("config.example.json"), "config.example.json"),
)
GENERATED_BUNDLE_FILES = (
    "config.json",
    "Run Himawari Wallpaper.bat",
    "Run Himawari Once.bat",
    "Open Himawari Settings.bat",
)
WINDOWS_BUNDLE_EXECUTABLES = (
    f"{GUI_APP_NAME}.exe",
    f"{RUNNER_APP_NAME}.exe",
    f"{BACKGROUND_APP_NAME}.exe",
)


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


def build_pyinstaller_command(
    *,
    version_file: Path,
    app_name: str,
    entrypoint: Path,
    windowed: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed" if windowed else "--console",
        "--name",
        app_name,
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
        str(entrypoint),
    ]
    if WINDOWS_ICON_PATH.exists():
        command.extend(["--icon", str(WINDOWS_ICON_PATH)])
    for binary_path in find_extra_windows_binaries():
        command.extend(["--add-binary", f"{binary_path}{os.pathsep}."])
    return command


def find_extra_windows_binaries() -> list[Path]:
    if sys.platform != "win32":
        return []

    library_bin = Path(sys.prefix) / "Library" / "bin"
    if not library_bin.exists():
        return []

    binaries: list[Path] = []
    for name in CONDA_RUNTIME_DLLS:
        path = library_bin / name
        if path.exists():
            binaries.append(path)
    return binaries


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
            StringStruct('OriginalFilename', '{GUI_APP_NAME}.exe'),
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


def run_pyinstaller(version_file: Path) -> dict[str, Path]:
    targets = (
        (GUI_APP_NAME, GUI_ENTRYPOINT, True),
        (RUNNER_APP_NAME, RUNNER_ENTRYPOINT, False),
        (BACKGROUND_APP_NAME, RUNNER_ENTRYPOINT, True),
    )
    built: dict[str, Path] = {}

    for app_name, entrypoint, windowed in targets:
        command = build_pyinstaller_command(
            version_file=version_file,
            app_name=app_name,
            entrypoint=entrypoint,
            windowed=windowed,
        )
        print("+", " ".join(command))
        subprocess.run(command, cwd=ROOT, check=True)

        exe_path = DIST_DIR / f"{app_name}.exe"
        if not exe_path.exists():
            raise RuntimeError(f"PyInstaller did not create the expected executable: {exe_path}")
        built[app_name] = exe_path

    return built


def collect_bundle_mappings(
    exe_paths: dict[str, Path],
) -> list[tuple[Path, Path]]:
    mappings: list[tuple[Path, Path]] = []

    for exe_path in exe_paths.values():
        mappings.append((exe_path, Path(exe_path.name)))

    for relative_path, archive_name in SUPPORT_FILES:
        mappings.append((ROOT / relative_path, Path(archive_name)))

    return mappings


def build_run_bat_contents(run_once: bool) -> str:
    mode_flag = "--once" if run_once else "--run"
    runner_name = RUNNER_APP_NAME if run_once else BACKGROUND_APP_NAME
    lines = [
        "@echo off",
        "setlocal",
        "set SCRIPT_DIR=%~dp0",
        "cd /d \"%SCRIPT_DIR%\"",
    ]
    if run_once:
        lines.append(
            f"\"%SCRIPT_DIR%{runner_name}.exe\" "
            f"{mode_flag} --config \"%SCRIPT_DIR%config.json\""
        )
        lines.append("endlocal")
        lines.append("exit /b %errorlevel%")
    else:
        lines.append(
            f"start \"\" \"%SCRIPT_DIR%{runner_name}.exe\" "
            f"{mode_flag} --config \"%SCRIPT_DIR%config.json\""
        )
        lines.append("endlocal")
    return "\n".join(lines) + "\n"


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
    exe_paths: dict[str, Path],
) -> int:
    bundle_dir.mkdir(parents=True, exist_ok=True)

    for source_path, relative_target in collect_bundle_mappings(exe_paths=exe_paths):
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

    for relative_target, content in build_generated_bundle_contents(
        exe_paths[GUI_APP_NAME].name
    ).items():
        destination_path = bundle_dir / relative_target
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(content, encoding="utf-8")

    return sum(1 for path in bundle_dir.rglob("*") if path.is_file())


def create_bundle_archive(
    output_path: Path,
    exe_paths: dict[str, Path],
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="himawari-bundle-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        archive_root = temp_dir / output_path.stem
        build_bundle_directory(archive_root, exe_paths=exe_paths)

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
    exe_paths = run_pyinstaller(version_file)
    added_files = create_bundle_archive(output_path, exe_paths)

    print(f"Created: {output_path}")
    print(f"Files packed: {added_files}")


if __name__ == "__main__":
    main()
