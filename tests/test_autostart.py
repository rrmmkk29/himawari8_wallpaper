from pathlib import Path

from himawari_wallpaper import autostart


def test_get_startup_entry_path_windows(monkeypatch) -> None:
    monkeypatch.setattr(autostart, "detect_platform", lambda: autostart.WINDOWS)
    monkeypatch.setattr(autostart, "_get_windows_startup_folder", lambda: Path("/tmp/startup"))

    result = autostart.get_startup_entry_path()

    assert result == Path("/tmp/startup") / autostart.STARTUP_SHORTCUT_NAME


def test_has_startup_reflects_target_exists(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "auto.bat"
    monkeypatch.setattr(autostart, "get_startup_entry_path", lambda: target)
    monkeypatch.setattr(autostart, "detect_platform", lambda: autostart.LINUX)

    assert autostart.has_startup() is False

    target.write_text("echo test", encoding="utf-8")

    assert autostart.has_startup() is True


def test_has_startup_windows_accepts_legacy_bat(monkeypatch, tmp_path: Path) -> None:
    startup_dir = tmp_path / "Startup"
    startup_dir.mkdir()
    monkeypatch.setattr(autostart, "detect_platform", lambda: autostart.WINDOWS)
    monkeypatch.setattr(autostart, "_get_windows_startup_folder", lambda: startup_dir)

    legacy_target = startup_dir / autostart.LEGACY_STARTUP_BAT_NAME
    legacy_target.write_text("@echo off\n", encoding="utf-8")

    assert autostart.has_startup() is True


def test_remove_startup_windows_removes_shortcut_and_legacy_entries(monkeypatch, tmp_path: Path) -> None:
    startup_dir = tmp_path / "Startup"
    startup_dir.mkdir()
    monkeypatch.setattr(autostart, "detect_platform", lambda: autostart.WINDOWS)
    monkeypatch.setattr(autostart, "_get_windows_startup_folder", lambda: startup_dir)

    current_target = startup_dir / autostart.STARTUP_SHORTCUT_NAME
    legacy_target = startup_dir / autostart.LEGACY_STARTUP_BAT_NAME
    legacy_vbs_target = startup_dir / autostart.LEGACY_STARTUP_VBS_NAME
    current_target.write_text("lnk", encoding="utf-8")
    legacy_target.write_text("bat", encoding="utf-8")
    legacy_vbs_target.write_text("vbs", encoding="utf-8")

    assert autostart.remove_startup() is True
    assert not current_target.exists()
    assert not legacy_target.exists()
    assert not legacy_vbs_target.exists()


def test_install_windows_startup_creates_shortcut_and_removes_legacy_entries(
    monkeypatch,
    tmp_path: Path,
) -> None:
    startup_dir = tmp_path / "Startup"
    startup_dir.mkdir()
    monkeypatch.setattr(autostart, "_get_windows_startup_folder", lambda: startup_dir)
    recorded: dict[str, object] = {}

    def fake_create_windows_shortcut(shortcut_path: Path, command: list[str]) -> None:
        recorded["shortcut_path"] = shortcut_path
        recorded["command"] = command
        shortcut_path.write_text("shortcut", encoding="utf-8")

    monkeypatch.setattr(autostart, "_create_windows_shortcut", fake_create_windows_shortcut)

    legacy_target = startup_dir / autostart.LEGACY_STARTUP_BAT_NAME
    legacy_target.write_text("@echo off\n", encoding="utf-8")

    target = autostart._install_windows_startup(
        ["C:\\demo\\pythonw.exe", "C:\\demo\\run.py", "--run"]
    )

    assert target == startup_dir / autostart.STARTUP_SHORTCUT_NAME
    assert recorded["shortcut_path"] == target
    assert recorded["command"] == ["C:\\demo\\pythonw.exe", "C:\\demo\\run.py", "--run"]
    assert target.exists()
    assert not legacy_target.exists()


def test_build_windows_shortcut_command_targets_pythonw(monkeypatch, tmp_path: Path) -> None:
    shortcut_path = tmp_path / "Startup" / autostart.STARTUP_SHORTCUT_NAME
    monkeypatch.setattr(autostart.subprocess, "list2cmdline", lambda values: " ".join(values))
    monkeypatch.setattr(autostart, "_find_windows_powershell_executable", lambda: "pwsh.exe")

    command = autostart._build_windows_shortcut_command(
        shortcut_path,
        ["C:\\demo\\pythonw.exe", "C:\\demo\\run.py", "--run"],
    )

    assert command[:4] == ["pwsh.exe", "-NoProfile", "-NonInteractive", "-Command"]
    assert "CreateShortcut" in command[4]
    assert "pythonw.exe" in command[4]
    assert "run.py --run" in command[4]


def test_get_windows_startup_folder_falls_back_without_appdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    result = autostart._get_windows_startup_folder()

    assert result == (
        tmp_path
        / "AppData"
        / "Roaming"
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )


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
