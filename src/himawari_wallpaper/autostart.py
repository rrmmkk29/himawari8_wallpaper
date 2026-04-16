import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

from .platforms import LINUX, MACOS, WINDOWS, detect_platform

STARTUP_BAT_NAME = "HimawariWallpaperAuto.bat"
LAUNCH_AGENT_NAME = "com.himawari.dynamic-wallpaper.plist"
AUTOSTART_DESKTOP_NAME = "himawari-dynamic-wallpaper.desktop"


def install_startup(
    interval_sec: int,
    out_dir: Path,
    earth_height_ratio: float,
    y_offset_ratio: float,
    max_zoom: int,
    config_path: Path | None = None,
) -> Path:
    current_platform = detect_platform()
    command = _build_command(
        interval_sec=interval_sec,
        out_dir=out_dir,
        earth_height_ratio=earth_height_ratio,
        y_offset_ratio=y_offset_ratio,
        max_zoom=max_zoom,
        config_path=config_path,
        background=current_platform == WINDOWS,
    )

    if current_platform == WINDOWS:
        return _install_windows_startup(command)

    if current_platform == MACOS:
        return _install_macos_launch_agent(command, out_dir)

    if current_platform == LINUX:
        return _install_linux_autostart(command)

    raise RuntimeError(f"Unsupported platform: {current_platform}")


def remove_startup() -> bool:
    current_platform = detect_platform()
    if current_platform == WINDOWS:
        target = _get_windows_startup_folder() / STARTUP_BAT_NAME
    elif current_platform == MACOS:
        target = _get_launch_agents_dir() / LAUNCH_AGENT_NAME
    elif current_platform == LINUX:
        target = _get_linux_autostart_dir() / AUTOSTART_DESKTOP_NAME
    else:
        raise RuntimeError(f"Unsupported platform: {current_platform}")

    if target.exists():
        target.unlink()
        return True
    return False


def _build_command(
    interval_sec: int,
    out_dir: Path,
    earth_height_ratio: float,
    y_offset_ratio: float,
    max_zoom: int,
    config_path: Path | None,
    background: bool,
) -> list[str]:
    executable = _get_python_background_executable() if background else sys.executable
    command = [
        executable,
        "-m",
        "himawari_wallpaper",
        "--run",
        "--interval",
        str(interval_sec),
        "--out",
        str(out_dir),
        "--earth-height-ratio",
        str(earth_height_ratio),
        "--y-offset-ratio",
        str(y_offset_ratio),
        "--max-zoom",
        str(max_zoom),
    ]
    if config_path is not None:
        command.extend(["--config", str(config_path)])
    return command


def _install_windows_startup(command: list[str]) -> Path:
    startup_folder = _get_windows_startup_folder()
    startup_folder.mkdir(parents=True, exist_ok=True)
    target = startup_folder / STARTUP_BAT_NAME
    content = "@echo off\nstart \"\" " + subprocess.list2cmdline(command) + "\n"
    target.write_text(content, encoding="utf-8")
    return target


def _install_macos_launch_agent(command: list[str], out_dir: Path) -> Path:
    launch_agents = _get_launch_agents_dir()
    launch_agents.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = launch_agents / LAUNCH_AGENT_NAME
    payload = {
        "Label": "com.himawari.dynamic-wallpaper",
        "ProgramArguments": command,
        "RunAtLoad": True,
        "KeepAlive": False,
        "WorkingDirectory": str(out_dir),
        "StandardOutPath": str(out_dir / "launchd.stdout.log"),
        "StandardErrorPath": str(out_dir / "launchd.stderr.log"),
    }
    with target.open("wb") as handle:
        plistlib.dump(payload, handle)
    return target


def _install_linux_autostart(command: list[str]) -> Path:
    autostart_dir = _get_linux_autostart_dir()
    autostart_dir.mkdir(parents=True, exist_ok=True)
    target = autostart_dir / AUTOSTART_DESKTOP_NAME
    exec_line = shlex.join(command)
    content = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            "Name=Himawari Dynamic Wallpaper",
            "Comment=Refresh Himawari wallpaper automatically",
            f"Exec={exec_line}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
        ]
    )
    target.write_text(content + "\n", encoding="utf-8")
    return target


def _get_windows_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _get_launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def _get_linux_autostart_dir() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "autostart"
    return Path.home() / ".config" / "autostart"


def _get_python_background_executable() -> str:
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return str(executable)
