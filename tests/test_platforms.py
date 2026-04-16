from pathlib import Path

from himawari_wallpaper import platforms


def test_detect_platform_maps_windows(monkeypatch) -> None:
    monkeypatch.setattr(platforms.platform, "system", lambda: "Windows")
    assert platforms.detect_platform() == platforms.WINDOWS


def test_detect_platform_maps_macos(monkeypatch) -> None:
    monkeypatch.setattr(platforms.platform, "system", lambda: "Darwin")
    assert platforms.detect_platform() == platforms.MACOS


def test_detect_platform_maps_linux(monkeypatch) -> None:
    monkeypatch.setattr(platforms.platform, "system", lambda: "Linux")
    assert platforms.detect_platform() == platforms.LINUX


def test_get_default_output_dir_uses_linux_xdg(monkeypatch) -> None:
    monkeypatch.setattr(platforms.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/xdg-data")

    assert platforms.get_default_output_dir() == Path("/tmp/xdg-data/himawari-dynamic-wallpaper")
