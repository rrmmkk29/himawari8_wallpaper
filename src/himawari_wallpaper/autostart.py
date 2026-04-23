import os
import plistlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .platforms import LINUX, MACOS, WINDOWS, detect_platform

STARTUP_SHORTCUT_NAME = "HimawariWallpaperAuto.lnk"
LEGACY_STARTUP_BAT_NAME = "HimawariWallpaperAuto.bat"
LEGACY_STARTUP_VBS_NAME = "HimawariWallpaperAuto.vbs"
LAUNCH_AGENT_NAME = "com.himawari.dynamic-wallpaper.plist"
AUTOSTART_DESKTOP_NAME = "himawari-dynamic-wallpaper.desktop"
GUI_EXE_NAME = "himawari-dynamic-wallpaper-gui.exe"
RUNNER_EXE_NAME = "himawari-dynamic-wallpaper.exe"
BACKGROUND_RUNNER_EXE_NAME = "himawari-dynamic-wallpaper-background.exe"
BUNDLE_MARKERS = (
    GUI_EXE_NAME,
    RUNNER_EXE_NAME,
    BACKGROUND_RUNNER_EXE_NAME,
    "config.json",
    "run_himawari.py",
)
PYTHON_EXECUTABLE_NAMES = {
    "python",
    "python.exe",
    "pythonw",
    "pythonw.exe",
    "py",
    "py.exe",
}


def install_startup(
    interval_sec: int,
    out_dir: Path,
    earth_height_ratio: float,
    y_offset_ratio: float,
    max_zoom: int,
    apply_wallpaper: bool,
    sync_lock_screen: bool,
    config_path: Path | None = None,
    python_executable: Path | None = None,
    launcher_script: Path | None = None,
) -> Path:
    current_platform = detect_platform()
    command = _build_command(
        interval_sec=interval_sec,
        out_dir=out_dir,
        earth_height_ratio=earth_height_ratio,
        y_offset_ratio=y_offset_ratio,
        max_zoom=max_zoom,
        apply_wallpaper=apply_wallpaper,
        sync_lock_screen=sync_lock_screen,
        config_path=config_path,
        background=current_platform == WINDOWS,
        python_executable=python_executable,
        launcher_script=launcher_script,
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
        removed = False
        for target in _get_windows_startup_candidates():
            if target.exists():
                target.unlink()
                removed = True
        return removed

    target = get_startup_entry_path()
    if target.exists():
        target.unlink()
        return True
    return False


def has_startup() -> bool:
    if detect_platform() == WINDOWS:
        return any(target.exists() for target in _get_windows_startup_candidates())
    return get_startup_entry_path().exists()


def get_startup_entry_path() -> Path:
    current_platform = detect_platform()
    if current_platform == WINDOWS:
        return _get_windows_startup_folder() / STARTUP_SHORTCUT_NAME
    if current_platform == MACOS:
        return _get_launch_agents_dir() / LAUNCH_AGENT_NAME
    if current_platform == LINUX:
        return _get_linux_autostart_dir() / AUTOSTART_DESKTOP_NAME
    raise RuntimeError(f"Unsupported platform: {current_platform}")


def _build_command(
    interval_sec: int,
    out_dir: Path,
    earth_height_ratio: float,
    y_offset_ratio: float,
    max_zoom: int,
    apply_wallpaper: bool,
    sync_lock_screen: bool,
    config_path: Path | None,
    background: bool,
    python_executable: Path | None = None,
    launcher_script: Path | None = None,
) -> list[str]:
    bundled_runner = _get_bundled_runner_executable(background=background)
    if bundled_runner is not None:
        command = [str(bundled_runner)]
    else:
        executable = _resolve_python_executable(
            background=background,
            python_executable=python_executable,
        )
        command = [executable]

        effective_launcher = (
            launcher_script
            or _get_bundled_launcher_script()
            or _get_config_relative_launcher_script(config_path)
        )
        if effective_launcher is not None:
            command.append(str(effective_launcher))
        else:
            command.extend(["-m", "himawari_wallpaper"])

    command.extend(
        [
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
    )
    if not apply_wallpaper:
        command.append("--download-only")
    if sync_lock_screen:
        command.append("--sync-lock-screen")
    if config_path is not None:
        command.extend(["--config", str(config_path)])
    return command


def _install_windows_startup(command: list[str]) -> Path:
    startup_folder = _get_windows_startup_folder()
    startup_folder.mkdir(parents=True, exist_ok=True)
    target = startup_folder / STARTUP_SHORTCUT_NAME
    _create_windows_shortcut(target, command)
    for legacy_target in _get_windows_legacy_startup_candidates():
        legacy_target.unlink(missing_ok=True)
    return target


def _create_windows_shortcut(shortcut_path: Path, command: list[str]) -> None:
    shortcut_path.unlink(missing_ok=True)
    command_line = _build_windows_shortcut_command(shortcut_path, command)
    result = subprocess.run(
        command_line,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        details = _decode_subprocess_output(result.stderr or result.stdout or b"").strip()
        if details:
            raise RuntimeError(f"Failed to create Windows startup shortcut: {details}")
        raise RuntimeError("Failed to create Windows startup shortcut.")


def _get_windows_startup_candidates() -> tuple[Path, ...]:
    startup_folder = _get_windows_startup_folder()
    return (
        startup_folder / STARTUP_SHORTCUT_NAME,
        * _get_windows_legacy_startup_candidates(),
    )


def _get_windows_legacy_startup_candidates() -> tuple[Path, ...]:
    startup_folder = _get_windows_startup_folder()
    return (
        startup_folder / LEGACY_STARTUP_BAT_NAME,
        startup_folder / LEGACY_STARTUP_VBS_NAME,
    )


def _build_windows_shortcut_command(shortcut_path: Path, command: list[str]) -> list[str]:
    if not command:
        raise ValueError("command must not be empty.")

    target_path = command[0]
    arguments = subprocess.list2cmdline(command[1:]) if len(command) > 1 else ""
    working_directory = str(Path(target_path).resolve().parent)

    script = "\n".join(
        [
            "$WshShell = New-Object -ComObject WScript.Shell",
            f"$Shortcut = $WshShell.CreateShortcut('{_powershell_single_quote(shortcut_path)}')",
            f"$Shortcut.TargetPath = '{_powershell_single_quote(target_path)}'",
            f"$Shortcut.Arguments = '{_powershell_single_quote(arguments)}'",
            f"$Shortcut.WorkingDirectory = '{_powershell_single_quote(working_directory)}'",
            "$Shortcut.Save()",
        ]
    )
    shell_executable = _find_windows_powershell_executable()
    return [shell_executable, "-NoProfile", "-NonInteractive", "-Command", script]


def _powershell_single_quote(value: str | os.PathLike[str]) -> str:
    return str(value).replace("'", "''")


def _find_windows_powershell_executable() -> str:
    for candidate in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return "powershell"


def _decode_subprocess_output(payload: bytes | str) -> str:
    if isinstance(payload, str):
        return payload

    for encoding in ("utf-8", "utf-16", "gbk", "cp1252"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


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
    if appdata:
        roaming_dir = Path(appdata)
    else:
        userprofile = os.environ.get("USERPROFILE")
        roaming_dir = (
            Path(userprofile) / "AppData" / "Roaming"
            if userprofile
            else Path.home() / "AppData" / "Roaming"
        )
    return roaming_dir / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


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


def _resolve_python_executable(
    background: bool,
    python_executable: Path | None = None,
) -> str:
    if python_executable is not None:
        return str(python_executable)

    bundled_runtime = _get_bundled_runtime_dir()
    if bundled_runtime is not None:
        if background:
            bundled_pythonw = bundled_runtime / "pythonw.exe"
            if bundled_pythonw.exists():
                return str(bundled_pythonw)
        bundled_python = bundled_runtime / "python.exe"
        if bundled_python.exists():
            return str(bundled_python)

    system_python = _find_system_python_executable(background=background)
    if system_python is not None:
        return system_python

    fallback = _get_python_background_executable() if background else str(sys.executable)
    if _is_usable_python_executable(fallback):
        return fallback

    raise RuntimeError(
        "No usable Python interpreter was found. Install Python or launch the app from an "
        "activated conda environment before enabling startup or running bundled scripts."
    )


def _get_bundled_runtime_dir() -> Path | None:
    bundle_root = _get_bundle_root()
    if bundle_root is None:
        return None

    runtime_dir = bundle_root / "runtime"
    if runtime_dir.exists():
        return runtime_dir
    return None


def _get_bundled_runner_executable(background: bool) -> Path | None:
    bundle_root = _get_bundle_root()
    if bundle_root is None:
        return None

    if background:
        background_runner = bundle_root / BACKGROUND_RUNNER_EXE_NAME
        if background_runner.exists():
            return background_runner

    runner = bundle_root / RUNNER_EXE_NAME
    if runner.exists():
        return runner
    return None


def _get_bundled_launcher_script() -> Path | None:
    bundle_root = _get_bundle_root()
    if bundle_root is None:
        return None

    launcher_script = bundle_root / "run_himawari.py"
    if launcher_script.exists():
        return launcher_script
    return None


def _get_config_relative_launcher_script(config_path: Path | None) -> Path | None:
    if config_path is None:
        return None

    launcher_script = config_path.expanduser().resolve().parent / "run_himawari.py"
    if launcher_script.exists():
        return launcher_script
    return None


def _get_bundle_root() -> Path | None:
    executable = Path(sys.executable).resolve()
    candidates = (executable.parent, executable.parent.parent)

    for candidate in candidates:
        if any((candidate / marker).exists() for marker in BUNDLE_MARKERS):
            return candidate

    return None


def _find_system_python_executable(background: bool) -> str | None:
    command_names = (
        ("pythonw.exe", "python.exe", "pythonw", "python", "py.exe", "py")
        if background
        else ("py.exe", "py", "python.exe", "python")
    )

    for command_name in command_names:
        resolved = shutil.which(command_name)
        if resolved and _is_usable_python_executable(resolved):
            return resolved

    return None


def _is_usable_python_executable(value: str | os.PathLike[str]) -> bool:
    path = Path(value)
    if path.name.lower() not in PYTHON_EXECUTABLE_NAMES:
        return False
    if _is_windowsapps_alias(path):
        return False
    if path.is_absolute() and not path.exists():
        return False
    return True


def _is_windowsapps_alias(path: str | os.PathLike[str]) -> bool:
    lowered_parts = {part.lower() for part in Path(path).parts}
    return "windowsapps" in lowered_parts
