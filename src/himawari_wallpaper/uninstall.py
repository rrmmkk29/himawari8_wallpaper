from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .autostart import remove_startup
from .config import load_config_file, resolve_config_path, resolve_output_dir
from .platforms import get_default_output_dir

OUTPUT_CLEANUP_PATTERNS = (
    "himawari.log",
    "last_source_meta.json",
    "wallpaper_current.bmp",
    "wallpaper_*.png",
    "origin_wallpaper_*.png",
    "lockscreen_*.png",
    "web_debug_screenshot.png",
    "launchd.stdout.log",
    "launchd.stderr.log",
)


@dataclass(frozen=True)
class CleanupResult:
    removed_startup: bool
    removed_output_paths: tuple[Path, ...]
    removed_config: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove startup entries and clean Himawari runtime/config data."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove startup entry, runtime output files, and config file",
    )
    parser.add_argument(
        "--remove-startup",
        action="store_true",
        help="Remove login auto-start entry",
    )
    parser.add_argument(
        "--remove-output",
        action="store_true",
        help="Remove generated runtime files from the output directory",
    )
    parser.add_argument(
        "--remove-config",
        action="store_true",
        help="Remove the config file if it exists",
    )
    parser.add_argument(
        "--remove-conda-env",
        default=None,
        help="Remove the named conda environment after local cleanup",
    )
    parser.add_argument(
        "--conda-exe",
        default=None,
        help="Optional conda executable path, for example conda or mamba",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a config file to read or remove",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Explicit output directory to clean instead of the config/default path",
    )
    return parser.parse_args()


def resolve_cleanup_config_path(custom: str | None) -> Path | None:
    raw = custom or os.environ.get("HIMAWARI_CONFIG")
    if raw:
        return resolve_config_path(raw)

    default = (Path.cwd() / "config.json").resolve()
    if default.exists():
        return default
    return None


def resolve_cleanup_output_dir(custom_output: str | None, config_path: Path | None) -> Path:
    if custom_output:
        return resolve_output_dir(custom_output)

    if config_path and config_path.exists():
        try:
            values = load_config_file(config_path)
        except ValueError:
            values = {}
        output_dir = values.get("output_dir")
        if output_dir:
            return resolve_output_dir(str(output_dir))

    return get_default_output_dir()


def collect_output_cleanup_paths(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []

    found: list[Path] = []
    seen: set[Path] = set()
    for pattern in OUTPUT_CLEANUP_PATTERNS:
        for path in output_dir.glob(pattern):
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            found.append(path)

    found.sort(key=lambda path: path.name)
    return found


def cleanup_output_dir(output_dir: Path) -> list[Path]:
    removed: list[Path] = []
    for path in collect_output_cleanup_paths(output_dir):
        path.unlink(missing_ok=True)
        removed.append(path)

    if output_dir.exists():
        try:
            next(output_dir.iterdir())
        except StopIteration:
            output_dir.rmdir()
            removed.append(output_dir)

    return removed


def remove_config_file(config_path: Path | None) -> bool:
    if config_path is None or not config_path.exists():
        return False
    config_path.unlink()
    return True


def cleanup_local_install(config_path: Path | None, output_dir: Path) -> CleanupResult:
    return perform_cleanup_actions(
        remove_startup_flag=True,
        remove_output_flag=True,
        remove_config_flag=True,
        config_path=config_path,
        output_dir=output_dir,
    )


def perform_cleanup_actions(
    remove_startup_flag: bool,
    remove_output_flag: bool,
    remove_config_flag: bool,
    config_path: Path | None,
    output_dir: Path,
) -> CleanupResult:
    removed_startup = remove_startup() if remove_startup_flag else False
    removed_output_paths = tuple(cleanup_output_dir(output_dir)) if remove_output_flag else ()
    removed_config = remove_config_file(config_path) if remove_config_flag else False
    return CleanupResult(
        removed_startup=removed_startup,
        removed_output_paths=removed_output_paths,
        removed_config=removed_config,
    )


def find_conda_executable(custom: str | None = None) -> str:
    if custom:
        return custom

    for candidate in ("conda", "mamba", "micromamba"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise RuntimeError("Conda-compatible executable was not found in PATH.")


def conda_env_exists(conda_exe: str, env_name: str) -> bool:
    result = subprocess.run(
        [conda_exe, "env", "list", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    envs = payload.get("envs", [])
    lowered = env_name.lower()
    return any(Path(env_path).name.lower() == lowered for env_path in envs)


def build_conda_remove_command(conda_exe: str, env_name: str) -> list[str]:
    return [conda_exe, "env", "remove", "-n", env_name, "-y"]


def remove_conda_env(conda_exe: str, env_name: str) -> bool:
    if not conda_env_exists(conda_exe, env_name):
        return False
    subprocess.run(build_conda_remove_command(conda_exe, env_name), check=True)
    return True


def main() -> None:
    args = parse_args()

    remove_startup_flag = args.all or args.remove_startup
    remove_output_flag = args.all or args.remove_output
    remove_config_flag = args.all or args.remove_config

    config_path = resolve_cleanup_config_path(args.config)
    output_dir = resolve_cleanup_output_dir(args.out, config_path)

    actions_taken = 0

    if remove_startup_flag:
        removed = remove_startup()
        actions_taken += 1
        if removed:
            print("Removed startup entry.")
        else:
            print("No startup entry found.")

    if remove_output_flag:
        removed_paths = cleanup_output_dir(output_dir)
        actions_taken += 1
        if removed_paths:
            print(f"Removed {len(removed_paths)} output path(s) from: {output_dir}")
        else:
            print(f"No runtime output files found in: {output_dir}")

    if remove_config_flag:
        removed = remove_config_file(config_path)
        actions_taken += 1
        if removed and config_path is not None:
            print(f"Removed config file: {config_path}")
        else:
            print("No config file found to remove.")

    if args.remove_conda_env:
        conda_exe = find_conda_executable(args.conda_exe)
        removed = remove_conda_env(conda_exe, args.remove_conda_env)
        actions_taken += 1
        if removed:
            print(f"Removed conda environment: {args.remove_conda_env}")
        else:
            print(f"Conda environment was not found: {args.remove_conda_env}")

    if actions_taken == 0:
        print("No cleanup action selected. Use --all or one of the explicit removal flags.")


if __name__ == "__main__":
    main()
