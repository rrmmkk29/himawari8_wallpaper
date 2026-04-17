import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from himawari_wallpaper.config import build_runtime_config


def make_args(**overrides):
    defaults = {
        "interval": None,
        "max_zoom": None,
        "out": None,
        "earth_height_ratio": None,
        "y_offset_ratio": None,
        "config": None,
        "apply_wallpaper": None,
        "sync_lock_screen": None,
        "target_url": None,
        "navigation_timeout_ms": None,
        "warmup_wait_ms": None,
        "probe_step_seconds": None,
        "probe_lookback_steps": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_runtime_config_uses_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    config = build_runtime_config(make_args())

    assert config.interval_sec == 3600
    assert config.max_zoom == 8
    assert config.output_dir.exists()
    assert config.apply_wallpaper is True
    assert config.sync_lock_screen is False
    assert config.target_url == "https://himawari.asia/"
    assert config.navigation_timeout_ms == 120000
    assert config.warmup_wait_ms == 15000
    assert config.probe_step_seconds == 600
    assert config.probe_lookback_steps == 36


def test_build_runtime_config_reads_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HIMAWARI_INTERVAL_SECONDS", "900")
    monkeypatch.setenv("HIMAWARI_MAX_ZOOM", "4")
    monkeypatch.setenv("HIMAWARI_EARTH_HEIGHT_RATIO", "0.5")
    monkeypatch.setenv("HIMAWARI_Y_OFFSET_RATIO", "0.2")
    monkeypatch.setenv("HIMAWARI_OUTPUT_DIR", str(tmp_path / "env-output"))
    monkeypatch.setenv("HIMAWARI_APPLY_WALLPAPER", "false")
    monkeypatch.setenv("HIMAWARI_SYNC_LOCK_SCREEN", "true")

    config = build_runtime_config(make_args())

    assert config.interval_sec == 900
    assert config.max_zoom == 4
    assert config.earth_height_ratio == 0.5
    assert config.y_offset_ratio == 0.2
    assert config.output_dir == (tmp_path / "env-output").resolve()
    assert config.apply_wallpaper is False
    assert config.sync_lock_screen is True


def test_build_runtime_config_prefers_cli_over_environment(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HIMAWARI_INTERVAL_SECONDS", "900")
    monkeypatch.setenv("HIMAWARI_MAX_ZOOM", "4")

    config = build_runtime_config(make_args(interval=1800, max_zoom=2, out="./cli-output"))

    assert config.interval_sec == 1800
    assert config.max_zoom == 2
    assert config.output_dir == (tmp_path / "cli-output").resolve()


def test_build_runtime_config_reads_json_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "interval_sec": 1200,
                "max_zoom": 4,
                "output_dir": "./from-config",
                "earth_height_ratio": 0.55,
                "y_offset_ratio": -0.1,
                "apply_wallpaper": False,
                "sync_lock_screen": True,
                "target_url": "https://example.test/",
                "navigation_timeout_ms": 90000,
                "warmup_wait_ms": 5000,
                "probe_step_seconds": 300,
                "probe_lookback_steps": 12,
            }
        ),
        encoding="utf-8",
    )

    config = build_runtime_config(make_args(config=str(config_path)))

    assert config.interval_sec == 1200
    assert config.max_zoom == 4
    assert config.output_dir == (tmp_path / "from-config").resolve()
    assert config.earth_height_ratio == 0.55
    assert config.y_offset_ratio == -0.1
    assert config.apply_wallpaper is False
    assert config.sync_lock_screen is True
    assert config.target_url == "https://example.test/"
    assert config.navigation_timeout_ms == 90000
    assert config.warmup_wait_ms == 5000
    assert config.probe_step_seconds == 300
    assert config.probe_lookback_steps == 12
    assert config.config_path == config_path.resolve()


def test_build_runtime_config_prefers_cli_over_json_config(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"interval_sec": 1200, "max_zoom": 4}),
        encoding="utf-8",
    )

    config = build_runtime_config(
        make_args(config=str(config_path), interval=2400, max_zoom=2)
    )

    assert config.interval_sec == 2400
    assert config.max_zoom == 2


def test_build_runtime_config_reads_config_path_from_environment(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"interval_sec": 1500}), encoding="utf-8")
    monkeypatch.setenv("HIMAWARI_CONFIG", str(config_path))

    config = build_runtime_config(make_args())

    assert config.interval_sec == 1500
    assert config.config_path == config_path.resolve()


def test_build_runtime_config_rejects_invalid_zoom(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="max-zoom"):
        build_runtime_config(make_args(max_zoom=3))


def test_build_runtime_config_rejects_invalid_interval(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="interval"):
        build_runtime_config(make_args(interval=30))


def test_build_runtime_config_rejects_invalid_probe_step(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="probe-step-seconds"):
        build_runtime_config(make_args(probe_step_seconds=0))


def test_build_runtime_config_rejects_invalid_navigation_timeout(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="navigation-timeout-ms"):
        build_runtime_config(make_args(navigation_timeout_ms=0))


def test_build_runtime_config_rejects_invalid_probe_lookback(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="probe-lookback-steps"):
        build_runtime_config(make_args(probe_lookback_steps=0))


def test_build_runtime_config_rejects_unknown_json_keys(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"bad_key": True}), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported keys"):
        build_runtime_config(make_args(config=str(config_path)))


def test_build_runtime_config_rejects_missing_json_file(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="was not found"):
        build_runtime_config(make_args(config=str(tmp_path / "missing.json")))
