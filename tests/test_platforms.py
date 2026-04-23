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


def test_enable_windows_dpi_awareness_is_noop_off_windows(monkeypatch) -> None:
    monkeypatch.setattr(platforms.platform, "system", lambda: "Linux")
    monkeypatch.setattr(platforms, "_WINDOWS_DPI_AWARENESS_ENABLED", False)

    assert platforms.enable_windows_dpi_awareness() is False


def test_enable_windows_dpi_awareness_sets_flag_once(monkeypatch) -> None:
    class _User32:
        def __init__(self) -> None:
            self.calls = 0

        def SetProcessDPIAware(self) -> None:
            self.calls += 1

    class _Windll:
        def __init__(self, user32) -> None:
            self.user32 = user32

    class _Ctypes:
        def __init__(self, user32) -> None:
            self.windll = _Windll(user32)

    monkeypatch.setattr(platforms.platform, "system", lambda: "Windows")
    monkeypatch.setattr(platforms, "_WINDOWS_DPI_AWARENESS_ENABLED", False)
    user32 = _User32()
    monkeypatch.setitem(__import__("sys").modules, "ctypes", _Ctypes(user32))

    assert platforms.enable_windows_dpi_awareness() is True
    assert platforms.enable_windows_dpi_awareness() is True
    assert user32.calls == 1
