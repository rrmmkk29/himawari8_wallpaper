from pathlib import Path

from himawari_wallpaper import gui
from himawari_wallpaper.uninstall import CleanupResult


def test_find_latest_generated_wallpaper_returns_newest_file(tmp_path: Path) -> None:
    first = tmp_path / "wallpaper_001.png"
    second = tmp_path / "wallpaper_002.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    result = gui.find_latest_generated_wallpaper(tmp_path)

    assert result == second


def test_find_latest_generated_wallpaper_returns_none_when_missing(tmp_path: Path) -> None:
    assert gui.find_latest_generated_wallpaper(tmp_path) is None


def test_format_latest_wallpaper_status_when_missing(tmp_path: Path) -> None:
    text = gui._format_latest_wallpaper_status(tmp_path)

    assert "none found" in text


def test_format_latest_wallpaper_status_includes_filename(tmp_path: Path) -> None:
    image = tmp_path / "wallpaper_003.png"
    image.write_bytes(b"png")

    text = gui._format_latest_wallpaper_status(tmp_path)

    assert "wallpaper_003.png" in text
    assert "updated" in text


def test_format_startup_hint_windows(monkeypatch) -> None:
    monkeypatch.setattr(gui, "detect_platform", lambda: "windows")

    text = gui._format_startup_hint()

    assert "pythonw.exe" in text


def test_format_startup_hint_macos(monkeypatch) -> None:
    monkeypatch.setattr(gui, "detect_platform", lambda: "macos")

    text = gui._format_startup_hint()

    assert "LaunchAgent" in text


def test_is_lock_screen_supported_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(gui, "detect_platform", lambda: "windows")

    assert gui._is_lock_screen_supported() is True


def test_is_lock_screen_supported_off_windows(monkeypatch) -> None:
    monkeypatch.setattr(gui, "detect_platform", lambda: "linux")

    assert gui._is_lock_screen_supported() is False


def test_format_platform_label_windows() -> None:
    assert gui._format_platform_label("windows") == "Windows"


def test_format_platform_label_macos() -> None:
    assert gui._format_platform_label("macos") == "macOS"


def test_format_platform_label_linux_fallback() -> None:
    assert gui._format_platform_label("linux") == "Linux"


def test_format_browser_fallback_details_mentions_project_extra() -> None:
    text = gui._format_browser_fallback_details()

    assert ".[browser]" in text
    assert "Playwright" in text


def test_format_startup_toggle_details_windows(monkeypatch, tmp_path: Path) -> None:
    startup_path = tmp_path / "Startup" / "HimawariWallpaperAuto.bat"
    monkeypatch.setattr(gui, "detect_platform", lambda: "windows")
    monkeypatch.setattr(gui, "get_startup_entry_path", lambda: startup_path)

    text = gui._format_startup_toggle_details()

    assert str(startup_path) in text
    assert "pythonw.exe" in text


def test_build_cleanup_confirmation_message_mentions_conda_and_targets(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "output"

    text = gui._build_cleanup_confirmation_message(config_path=config_path, output_dir=output_dir)

    assert str(config_path) in text
    assert str(output_dir) in text
    assert "conda environment is not removed" in text


def test_find_project_root_returns_matching_parent(tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    nested = project_root / "src" / "himawari_wallpaper"
    nested.mkdir(parents=True)
    (project_root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    result = gui._find_project_root((nested,))

    assert result == project_root.resolve()


def test_build_browser_fallback_install_steps_prefers_project_extra(tmp_path: Path) -> None:
    steps = gui._build_browser_fallback_install_steps("python", tmp_path)

    assert steps == [
        (["python", "-m", "pip", "install", "-e", ".[browser]"], tmp_path),
        (["python", "-m", "playwright", "install", "chromium"], None),
    ]


def test_build_browser_fallback_install_steps_falls_back_to_direct_package() -> None:
    steps = gui._build_browser_fallback_install_steps("python", None)

    assert steps == [
        (["python", "-m", "pip", "install", "playwright>=1.45.0"], None),
        (["python", "-m", "playwright", "install", "chromium"], None),
    ]


def test_format_subprocess_error_uses_last_output_line() -> None:
    error = gui.subprocess.CalledProcessError(
        1,
        ["python", "-m", "pip", "install", "playwright"],
        stderr="line one\nlast line",
    )

    text = gui._format_subprocess_error(error)

    assert "last line" in text
    assert "python -m pip install playwright" in text


def test_format_cleanup_result_summarizes_removed_items(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    config_path = tmp_path / "config.json"
    result = CleanupResult(
        removed_startup=True,
        removed_output_paths=(output_dir / "wallpaper_001.png", output_dir),
        removed_config=False,
    )

    text = gui._format_cleanup_result(
        result=result,
        output_dir=output_dir,
        config_path=config_path,
        requested_actions=(True, True, True),
    )

    assert "Startup: removed" in text
    assert "output paths removed: 2" in text
    assert "config removed: no" in text


def test_format_cleanup_result_marks_skipped_actions(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    result = CleanupResult(
        removed_startup=False,
        removed_output_paths=(),
        removed_config=False,
    )

    text = gui._format_cleanup_result(
        result=result,
        output_dir=output_dir,
        config_path=None,
        requested_actions=(False, True, False),
    )

    assert "Startup: skipped" in text
    assert "output paths removed: 0" in text
    assert "config cleanup: skipped" in text


class _BoolState:
    def __init__(self, value: bool) -> None:
        self._value = value

    def get(self) -> bool:
        return self._value


class _StartupToggleState:
    def __init__(self, enabled: bool) -> None:
        self.startup_enabled = _BoolState(enabled)
        self.syncing_startup_toggle = False


def test_toggle_startup_calls_install_when_enabled(monkeypatch) -> None:
    state = _StartupToggleState(True)
    calls: list[str] = []

    monkeypatch.setattr(gui, "_install_startup", lambda current_state: calls.append("install") or True)
    monkeypatch.setattr(gui, "_remove_startup", lambda current_state: calls.append("remove") or True)

    gui._toggle_startup(state)

    assert calls == ["install"]


def test_toggle_startup_calls_remove_when_disabled(monkeypatch) -> None:
    state = _StartupToggleState(False)
    calls: list[str] = []

    monkeypatch.setattr(gui, "_install_startup", lambda current_state: calls.append("install") or True)
    monkeypatch.setattr(gui, "_remove_startup", lambda current_state: calls.append("remove") or True)

    gui._toggle_startup(state)

    assert calls == ["remove"]
