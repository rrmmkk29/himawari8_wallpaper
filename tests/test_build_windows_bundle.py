import importlib.util
import zipfile
from pathlib import Path


def load_build_windows_bundle_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "build_windows_bundle.py"
    spec = importlib.util.spec_from_file_location("build_windows_bundle", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_output_path_uses_windows_suffix() -> None:
    module = load_build_windows_bundle_module()

    output = module.build_output_path(
        Path("release"),
        "himawari-dynamic-wallpaper",
        "0.1.0",
        "v0.1.1",
    )

    assert output == Path("release") / "himawari-dynamic-wallpaper-windows-v0.1.1.zip"


def test_build_pyinstaller_command_targets_gui_entrypoint() -> None:
    module = load_build_windows_bundle_module()
    version_file = Path("build/windows-version-info.txt")

    command = module.build_pyinstaller_command(version_file)

    assert command[:3] == [module.sys.executable, "-m", "PyInstaller"]
    assert "--windowed" in command
    assert "--onefile" in command
    assert "--version-file" in command
    assert str(version_file) in command
    assert str(module.GUI_ENTRYPOINT) == command[-1]


def test_create_bundle_archive_packs_exe_and_support_files(tmp_path: Path) -> None:
    module = load_build_windows_bundle_module()
    exe_path = tmp_path / "himawari-dynamic-wallpaper-gui.exe"
    exe_path.write_bytes(b"exe")
    output_path = tmp_path / "bundle.zip"

    original_root = module.ROOT
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    (fake_root / "src" / "himawari_wallpaper").mkdir(parents=True)
    (fake_root / "src" / "himawari_wallpaper" / "__init__.py").write_text("", encoding="utf-8")
    for relative, _archive_name in module.SUPPORT_FILES:
        (fake_root / relative).write_text(relative.name, encoding="utf-8")

    try:
        module.ROOT = fake_root
        added = module.create_bundle_archive(output_path, exe_path)
    finally:
        module.ROOT = original_root

    assert added >= 1 + len(module.SUPPORT_FILES) + len(module.GENERATED_BUNDLE_FILES)
    with zipfile.ZipFile(output_path) as archive:
        names = set(archive.namelist())

    archive_root = output_path.stem
    assert f"{archive_root}/{exe_path.name}" in names
    assert f"{archive_root}/src/himawari_wallpaper/__init__.py" in names
    for relative, archive_name in module.SUPPORT_FILES:
        assert f"{archive_root}/{archive_name}" in names
    for archive_name in module.GENERATED_BUNDLE_FILES:
        assert f"{archive_root}/{archive_name}" in names


def test_build_python_launcher_script_imports_cli_main() -> None:
    module = load_build_windows_bundle_module()

    content = module.build_python_launcher_script()

    assert 'SOURCE_DIR = ROOT / "src"' in content
    assert "from himawari_wallpaper.cli import main" in content


def test_build_run_bat_contents_calls_python_runtime() -> None:
    module = load_build_windows_bundle_module()

    content = module.build_run_bat_contents(run_once=False)

    assert "call :resolve_python PYTHON_CMD" in content
    assert "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%run_himawari.py\"" in content
    assert "run_himawari.py" in content
    assert "--run --config" in content
    assert "py.exe py python.exe python" in content
    assert "\\WindowsApps\\" in content


def test_build_windows_file_version_pads_to_four_parts() -> None:
    module = load_build_windows_bundle_module()

    result = module.build_windows_file_version("0.1.2")

    assert result == "0,1,2,0"


def test_build_windows_version_info_contains_metadata() -> None:
    module = load_build_windows_bundle_module()

    content = module.build_windows_version_info(
        {
            "name": "himawari-dynamic-wallpaper",
            "version": "0.1.0",
            "description": "Cross-platform Himawari satellite dynamic wallpaper project",
            "author": "Your Name",
        }
    )

    assert "FileDescription" in content
    assert "ProductVersion" in content
    assert "0.1.0" in content
