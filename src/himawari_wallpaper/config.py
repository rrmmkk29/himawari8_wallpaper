import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .platforms import get_default_output_dir

ALLOWED_ZOOMS = (1, 2, 4, 8)
CONFIG_KEYS = {
    "interval_sec",
    "max_zoom",
    "output_dir",
    "earth_height_ratio",
    "y_offset_ratio",
    "apply_wallpaper",
    "sync_lock_screen",
    "target_url",
    "navigation_timeout_ms",
    "warmup_wait_ms",
    "probe_step_seconds",
    "probe_lookback_steps",
}


@dataclass(frozen=True)
class AppConfig:
    interval_sec: int = 3600
    max_zoom: int = 8
    output_dir: Path = Path(".")
    earth_height_ratio: float = 0.6
    y_offset_ratio: float = 0.0
    apply_wallpaper: bool = True
    sync_lock_screen: bool = False
    target_url: str = "https://himawari.asia/"
    navigation_timeout_ms: int = 120000
    warmup_wait_ms: int = 15000
    probe_step_seconds: int = 600
    probe_lookback_steps: int = 36
    config_path: Path | None = None


def resolve_output_dir(custom: Optional[str]) -> Path:
    if custom:
        output_dir = Path(custom).expanduser()
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        return output_dir.resolve()
    return get_default_output_dir()


def build_runtime_config(args: argparse.Namespace) -> AppConfig:
    config_path = resolve_config_path(
        getattr(args, "config", None) or os.environ.get("HIMAWARI_CONFIG")
    )
    file_values = load_config_file(config_path)

    interval_sec = _get_int_setting(
        args.interval,
        "HIMAWARI_INTERVAL_SECONDS",
        file_values.get("interval_sec"),
        3600,
    )
    max_zoom = _get_int_setting(
        args.max_zoom,
        "HIMAWARI_MAX_ZOOM",
        file_values.get("max_zoom"),
        8,
    )
    earth_height_ratio = _get_float_setting(
        args.earth_height_ratio,
        "HIMAWARI_EARTH_HEIGHT_RATIO",
        file_values.get("earth_height_ratio"),
        0.6,
    )
    y_offset_ratio = _get_float_setting(
        args.y_offset_ratio,
        "HIMAWARI_Y_OFFSET_RATIO",
        file_values.get("y_offset_ratio"),
        0.0,
    )
    apply_wallpaper = _get_bool_setting(
        getattr(args, "apply_wallpaper", None),
        "HIMAWARI_APPLY_WALLPAPER",
        file_values.get("apply_wallpaper"),
        True,
    )
    sync_lock_screen = _get_bool_setting(
        getattr(args, "sync_lock_screen", None),
        "HIMAWARI_SYNC_LOCK_SCREEN",
        file_values.get("sync_lock_screen"),
        False,
    )
    target_url = _get_str_setting(
        getattr(args, "target_url", None),
        "HIMAWARI_TARGET_URL",
        file_values.get("target_url"),
        "https://himawari.asia/",
    )
    navigation_timeout_ms = _get_int_setting(
        getattr(args, "navigation_timeout_ms", None),
        "HIMAWARI_NAVIGATION_TIMEOUT_MS",
        file_values.get("navigation_timeout_ms"),
        120000,
    )
    warmup_wait_ms = _get_int_setting(
        getattr(args, "warmup_wait_ms", None),
        "HIMAWARI_WARMUP_WAIT_MS",
        file_values.get("warmup_wait_ms"),
        15000,
    )
    probe_step_seconds = _get_int_setting(
        getattr(args, "probe_step_seconds", None),
        "HIMAWARI_PROBE_STEP_SECONDS",
        file_values.get("probe_step_seconds"),
        600,
    )
    probe_lookback_steps = _get_int_setting(
        getattr(args, "probe_lookback_steps", None),
        "HIMAWARI_PROBE_LOOKBACK_STEPS",
        file_values.get("probe_lookback_steps"),
        36,
    )
    output_dir = resolve_output_dir(
        args.out
        or os.environ.get("HIMAWARI_OUTPUT_DIR")
        or _coerce_optional_str(file_values.get("output_dir"))
    )

    if interval_sec < 60:
        raise ValueError("--interval should not be smaller than 60 seconds.")

    if max_zoom not in ALLOWED_ZOOMS:
        raise ValueError("--max-zoom must be one of 1 / 2 / 4 / 8.")

    if not 0.05 <= earth_height_ratio <= 1.0:
        raise ValueError("--earth-height-ratio should be between 0.05 and 1.0.")

    if not -1.0 <= y_offset_ratio <= 1.0:
        raise ValueError("--y-offset-ratio should be between -1.0 and 1.0.")

    if not target_url.strip():
        raise ValueError("--target-url should not be empty.")

    if warmup_wait_ms < 0:
        raise ValueError("--warmup-wait-ms should not be negative.")

    if navigation_timeout_ms <= 0:
        raise ValueError("--navigation-timeout-ms should be greater than 0.")

    if probe_step_seconds <= 0:
        raise ValueError("--probe-step-seconds should be greater than 0.")

    if probe_lookback_steps <= 0:
        raise ValueError("--probe-lookback-steps should be greater than 0.")

    output_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        interval_sec=interval_sec,
        max_zoom=max_zoom,
        output_dir=output_dir,
        earth_height_ratio=earth_height_ratio,
        y_offset_ratio=y_offset_ratio,
        apply_wallpaper=apply_wallpaper,
        sync_lock_screen=sync_lock_screen,
        target_url=target_url,
        navigation_timeout_ms=navigation_timeout_ms,
        warmup_wait_ms=warmup_wait_ms,
        probe_step_seconds=probe_step_seconds,
        probe_lookback_steps=probe_lookback_steps,
        config_path=config_path,
    )


def config_to_file_values(config: AppConfig) -> dict[str, Any]:
    return {
        "interval_sec": config.interval_sec,
        "max_zoom": config.max_zoom,
        "output_dir": str(config.output_dir),
        "earth_height_ratio": config.earth_height_ratio,
        "y_offset_ratio": config.y_offset_ratio,
        "apply_wallpaper": config.apply_wallpaper,
        "sync_lock_screen": config.sync_lock_screen,
        "target_url": config.target_url,
        "navigation_timeout_ms": config.navigation_timeout_ms,
        "warmup_wait_ms": config.warmup_wait_ms,
        "probe_step_seconds": config.probe_step_seconds,
        "probe_lookback_steps": config.probe_lookback_steps,
    }


def save_config_file(config_path: Path, values: dict[str, Any]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(values, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resolve_config_path(custom: Optional[str]) -> Path | None:
    if not custom:
        return None
    config_path = Path(custom).expanduser()
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    return config_path.resolve()


def load_config_file(config_path: Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}
    if not config_path.exists():
        raise ValueError(f"--config file was not found: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"--config is not valid JSON: {config_path}") from exc

    if not isinstance(data, dict):
        raise ValueError("--config must contain a JSON object at the top level.")

    unknown_keys = sorted(set(data) - CONFIG_KEYS)
    if unknown_keys:
        joined = ", ".join(unknown_keys)
        raise ValueError(f"--config contains unsupported keys: {joined}")

    return data


def _get_int_setting(
    cli_value: Optional[int],
    env_name: str,
    config_value: Any,
    default: int,
) -> int:
    if cli_value is not None:
        return cli_value
    value = os.environ.get(env_name)
    if value:
        return int(value)
    if config_value is not None:
        return int(config_value)
    return default


def _get_float_setting(
    cli_value: Optional[float],
    env_name: str,
    config_value: Any,
    default: float,
) -> float:
    if cli_value is not None:
        return cli_value
    value = os.environ.get(env_name)
    if value:
        return float(value)
    if config_value is not None:
        return float(config_value)
    return default


def _coerce_optional_str(config_value: Any) -> str | None:
    if config_value is None:
        return None
    return str(config_value)


def _get_str_setting(
    cli_value: Optional[str],
    env_name: str,
    config_value: Any,
    default: str,
) -> str:
    if cli_value is not None:
        return cli_value
    value = os.environ.get(env_name)
    if value:
        return value
    if config_value is not None:
        return str(config_value)
    return default


def _get_bool_setting(
    cli_value: Optional[bool],
    env_name: str,
    config_value: Any,
    default: bool,
) -> bool:
    if cli_value is not None:
        return cli_value

    value = os.environ.get(env_name)
    if value is not None:
        return _parse_bool(value, env_name)

    if config_value is not None:
        return _parse_bool(config_value, "config")

    return default


def _parse_bool(value: Any, source: str) -> bool:
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Invalid boolean value from {source}: {value}")
