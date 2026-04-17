from pathlib import Path

from himawari_wallpaper.autostart import _build_command
from himawari_wallpaper.wallpaper import _build_lock_screen_script


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
    assert "wallpaper''s.png" in script
