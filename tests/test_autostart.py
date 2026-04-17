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
