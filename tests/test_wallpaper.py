from pathlib import Path

from PIL import Image

from himawari_wallpaper.autostart import _build_command
from himawari_wallpaper.wallpaper import (
    _build_lock_screen_script,
    _cleanup_old_windows_lock_screen_candidates,
    _format_command_error_output,
    _get_windows_lock_screen_stage_dir,
    _humanize_powershell_throw,
    _prepare_windows_lock_screen_candidates,
    _set_lock_screen_windows,
)


def test_build_command_can_disable_desktop_apply_and_enable_lock_screen() -> None:
    command = _build_command(
        interval_sec=3600,
        out_dir=Path("/tmp/out"),
        earth_height_ratio=0.6,
        y_offset_ratio=0.0,
        max_zoom=4,
        apply_wallpaper=False,
        sync_lock_screen=True,
        config_path=Path("/tmp/config.json"),
        background=False,
    )

    assert "--download-only" in command
    assert "--sync-lock-screen" in command
    assert "--config" in command


def test_build_lock_screen_script_includes_expected_winrt_calls() -> None:
    script = _build_lock_screen_script(Path(r"C:\tmp\wallpaper's.png"))

    assert "UserProfilePersonalizationSettings" in script
    assert "TrySetLockScreenImageAsync" in script
    assert "LockScreen" in script
    assert "SetImageFileAsync" in script
    assert "wallpaper''s.png" in script


def test_format_command_error_output_extracts_powershell_throw_message() -> None:
    output = """
    所在位置 行:43 字符: 5
    +     throw 'Windows rejected the lock screen image update.'
    +     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationStopped: (Windows rejecte...n image update.:String) [], RuntimeException
    + FullyQualifiedErrorId : Windows rejected the lock screen image update.
    """

    text = _format_command_error_output(output)

    assert "Windows rejected the lock screen image update." in text
    assert "policy" in text
    assert "FullyQualifiedErrorId" not in text


def test_humanize_powershell_throw_returns_clean_windows_hint() -> None:
    text = _humanize_powershell_throw("Windows rejected the lock screen image update.")

    assert "Windows rejected the lock screen image update." in text
    assert "Windows settings" in text


def test_get_windows_lock_screen_stage_dir_uses_localappdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    path = _get_windows_lock_screen_stage_dir()

    assert path == tmp_path / "HimawariDynamicWallpaper" / "lockscreen-stage"


def test_prepare_windows_lock_screen_candidates_creates_png_and_jpg(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    source = tmp_path / "wallpaper.png"
    Image.new("RGB", (16, 16), (1, 2, 3)).save(source, "PNG")

    candidates = _prepare_windows_lock_screen_candidates(source)

    assert len(candidates) == 2
    assert candidates[0].suffix == ".png"
    assert candidates[1].suffix == ".jpg"
    assert all(path.exists() for path in candidates)
    assert all("lockscreen-source_" in path.name for path in candidates)


def test_cleanup_old_windows_lock_screen_candidates_keeps_latest_files(tmp_path: Path) -> None:
    for index in range(12):
        path = tmp_path / f"lockscreen-source_{index:02d}.png"
        path.write_bytes(b"png")

    _cleanup_old_windows_lock_screen_candidates(tmp_path)

    remaining = sorted(tmp_path.glob("lockscreen-source_*"))
    assert len(remaining) == 8


def test_set_lock_screen_windows_retries_with_second_candidate(monkeypatch, tmp_path: Path) -> None:
    first = tmp_path / "candidate1.png"
    second = tmp_path / "candidate2.jpg"
    calls: list[str] = []

    monkeypatch.setattr(
        "himawari_wallpaper.wallpaper._prepare_windows_lock_screen_candidates",
        lambda img_path: [first, second],
    )

    def fake_run_command(command: list[str], error_message: str) -> None:
        if "candidate1.png" in command[-1]:
            raise RuntimeError("Failed to set Windows lock screen. first attempt failed.")
        calls.append(command[-1])

    monkeypatch.setattr("himawari_wallpaper.wallpaper._run_command", fake_run_command)

    _set_lock_screen_windows(tmp_path / "source.png")

    assert len(calls) == 1
    assert "candidate2.jpg" in calls[0]
