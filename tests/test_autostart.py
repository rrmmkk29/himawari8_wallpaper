from pathlib import Path

from himawari_wallpaper import autostart


def test_get_startup_entry_path_windows(monkeypatch) -> None:
    monkeypatch.setattr(autostart, "detect_platform", lambda: autostart.WINDOWS)
    monkeypatch.setattr(autostart, "_get_windows_startup_folder", lambda: Path("/tmp/startup"))

    result = autostart.get_startup_entry_path()

    assert result == Path("/tmp/startup") / autostart.STARTUP_BAT_NAME


def test_has_startup_reflects_target_exists(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "auto.bat"
    monkeypatch.setattr(autostart, "get_startup_entry_path", lambda: target)

    assert autostart.has_startup() is False

    target.write_text("echo test", encoding="utf-8")

    assert autostart.has_startup() is True


def test_build_command_uses_explicit_python_and_launcher(tmp_path: Path) -> None:
    python_executable = tmp_path / "runtime" / "python.exe"
    launcher_script = tmp_path / "run_himawari.py"

    command = autostart._build_command(
        interval_sec=3600,
        out_dir=tmp_path / "out",
        earth_height_ratio=0.6,
        y_offset_ratio=0.0,
        max_zoom=4,
        apply_wallpaper=True,
        sync_lock_screen=False,
        config_path=tmp_path / "config.json",
        background=False,
        python_executable=python_executable,
        launcher_script=launcher_script,
    )

    assert command[:2] == [str(python_executable), str(launcher_script)]
    assert "-m" not in command
    assert "--config" in command


def test_build_command_prefers_bundled_runner_executable(monkeypatch, tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir(parents=True)
    gui_executable = bundle_root / "himawari-dynamic-wallpaper-gui.exe"
    gui_executable.write_bytes(b"exe")
    background_runner = bundle_root / autostart.BACKGROUND_RUNNER_EXE_NAME
    background_runner.write_bytes(b"exe")

    monkeypatch.setattr(autostart.sys, "executable", str(gui_executable))

    command = autostart._build_command(
        interval_sec=3600,
        out_dir=tmp_path / "out",
        earth_height_ratio=0.6,
        y_offset_ratio=0.0,
        max_zoom=4,
        apply_wallpaper=True,
        sync_lock_screen=False,
        config_path=None,
        background=True,
    )

    assert command[0] == str(background_runner)
    assert "-m" not in command


def test_build_command_prefers_launcher_next_to_config(monkeypatch, tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir(parents=True)
    launcher_script = bundle_root / "run_himawari.py"
    launcher_script.write_text("print('launcher')\n", encoding="utf-8")
    config_path = bundle_root / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(autostart, "_get_bundled_launcher_script", lambda: None)
    monkeypatch.setattr(
        autostart,
        "_find_system_python_executable",
        lambda background: str(tmp_path / "pythonw.exe"),
    )

    command = autostart._build_command(
        interval_sec=3600,
        out_dir=tmp_path / "out",
        earth_height_ratio=0.6,
        y_offset_ratio=0.0,
        max_zoom=4,
        apply_wallpaper=True,
        sync_lock_screen=False,
        config_path=config_path,
        background=True,
    )

    assert command[:2] == [str(tmp_path / "pythonw.exe"), str(launcher_script)]


def test_get_bundled_runner_executable_prefers_background_binary(monkeypatch, tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir(parents=True)
    gui_executable = bundle_root / autostart.GUI_EXE_NAME
    gui_executable.write_bytes(b"exe")
    runner = bundle_root / autostart.RUNNER_EXE_NAME
    runner.write_bytes(b"exe")
    background_runner = bundle_root / autostart.BACKGROUND_RUNNER_EXE_NAME
    background_runner.write_bytes(b"exe")

    monkeypatch.setattr(autostart.sys, "executable", str(gui_executable))

    assert autostart._get_bundled_runner_executable(background=True) == background_runner
    assert autostart._get_bundled_runner_executable(background=False) == runner


def test_find_system_python_executable_skips_windowsapps_alias(monkeypatch, tmp_path: Path) -> None:
    good_python = tmp_path / "Python312" / "python.exe"
    good_python.parent.mkdir(parents=True)
    good_python.write_text("", encoding="utf-8")

    def fake_which(command_name: str) -> str | None:
        mapping = {
            "py.exe": None,
            "py": None,
            "python.exe": str(Path("C:/Users/demo/AppData/Local/Microsoft/WindowsApps/python.exe")),
            "python": str(good_python),
        }
        return mapping.get(command_name)

    monkeypatch.setattr(autostart.shutil, "which", fake_which)

    result = autostart._find_system_python_executable(background=False)

    assert result == str(good_python)


def test_resolve_python_executable_raises_when_only_gui_exe_is_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    gui_executable = tmp_path / "himawari-dynamic-wallpaper-gui.exe"
    gui_executable.write_bytes(b"exe")

    monkeypatch.setattr(autostart.sys, "executable", str(gui_executable))
    monkeypatch.setattr(autostart, "_find_system_python_executable", lambda background: None)
    monkeypatch.setattr(autostart, "_get_bundled_runtime_dir", lambda: None)

    try:
        autostart._resolve_python_executable(background=False)
    except RuntimeError as exc:
        assert "No usable Python interpreter" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when no usable Python interpreter exists.")
