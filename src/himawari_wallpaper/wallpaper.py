import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import Callable
from uuid import uuid4

from PIL import Image

from .platforms import APP_DIR_NAME, LINUX, MACOS, WINDOWS, detect_platform

CURRENT_WALLPAPER_BMP = "wallpaper_current.bmp"
POWERSHELL_THROW_RE = re.compile(r"throw\s+'([^']+)'", re.IGNORECASE)
LOCK_SCREEN_STAGE_DIR_NAME = "lockscreen-stage"
LOCK_SCREEN_STAGE_PREFIX = "lockscreen-source"
KEEP_LOCK_SCREEN_STAGE_FILES = 8


def set_wallpaper(img_path: Path) -> None:
    current_platform = detect_platform()

    if current_platform == WINDOWS:
        _set_wallpaper_windows(img_path)
        return

    if current_platform == MACOS:
        _set_wallpaper_macos(img_path)
        return

    if current_platform == LINUX:
        _set_wallpaper_linux(img_path)
        return

    raise RuntimeError(f"Unsupported platform: {current_platform}")


def set_lock_screen(img_path: Path) -> None:
    current_platform = detect_platform()

    if current_platform != WINDOWS:
        raise RuntimeError("Lock screen sync is currently supported on Windows only.")

    _set_lock_screen_windows(img_path)


def _set_wallpaper_windows(img_path: Path) -> None:
    import ctypes

    bmp_path = img_path.parent / CURRENT_WALLPAPER_BMP
    Image.open(img_path).save(bmp_path, "BMP")

    spi_set_desktop_wallpaper = 20
    spif_update_inifile = 0x01
    spif_sendchange = 0x02

    ok = ctypes.windll.user32.SystemParametersInfoW(
        spi_set_desktop_wallpaper,
        0,
        str(bmp_path),
        spif_update_inifile | spif_sendchange,
    )
    if not ok:
        raise RuntimeError("Failed to set Windows wallpaper.")


def _set_lock_screen_windows(img_path: Path) -> None:
    candidates = _prepare_windows_lock_screen_candidates(img_path)
    errors: list[str] = []

    for candidate in candidates:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _build_lock_screen_script(candidate),
        ]
        try:
            _run_command(command, "Failed to set Windows lock screen.")
            return
        except RuntimeError as exc:
            errors.append(str(exc))

    joined = "; ".join(errors) if errors else "no candidate lock screen image was generated"
    raise RuntimeError(joined)


def _set_wallpaper_macos(img_path: Path) -> None:
    script = (
        'tell application "System Events" to tell every desktop '
        f'to set picture to POSIX file "{img_path.resolve()}"'
    )
    _run_command(["osascript", "-e", script], "Failed to set macOS wallpaper.")


def _set_wallpaper_linux(img_path: Path) -> None:
    wallpaper_uri = img_path.resolve().as_uri()
    attempts: list[Callable[[], None]] = [
        lambda: _run_if_available(
            ["plasma-apply-wallpaperimage", str(img_path.resolve())],
            "plasma-apply-wallpaperimage",
        ),
        lambda: _run_gsettings(wallpaper_uri),
        lambda: _run_xfconf(str(img_path.resolve())),
        lambda: _run_if_available(["feh", "--bg-fill", str(img_path.resolve())], "feh"),
    ]

    errors: list[str] = []
    for attempt in attempts:
        try:
            attempt()
            return
        except Exception as exc:
            errors.append(str(exc))

    joined = "; ".join(errors) if errors else "no wallpaper backend available"
    raise RuntimeError(f"Failed to set Linux wallpaper: {joined}")


def _run_gsettings(wallpaper_uri: str) -> None:
    if not shutil.which("gsettings"):
        raise RuntimeError("gsettings not available")

    _run_command(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", wallpaper_uri],
        "Failed to set Linux wallpaper via gsettings.",
    )

    try:
        _run_command(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                wallpaper_uri,
            ],
            "Failed to set Linux dark wallpaper via gsettings.",
        )
    except RuntimeError:
        pass


def _run_xfconf(img_path: str) -> None:
    if not shutil.which("xfconf-query"):
        raise RuntimeError("xfconf-query not available")

    properties = [
        "/backdrop/screen0/monitor0/workspace0/last-image",
        "/backdrop/screen0/monitor0/image-path",
    ]

    errors: list[str] = []
    for property_name in properties:
        try:
            _run_command(
                ["xfconf-query", "-c", "xfce4-desktop", "-p", property_name, "-s", img_path],
                f"Failed to set XFCE wallpaper property {property_name}.",
            )
            return
        except Exception as exc:
            errors.append(str(exc))

    raise RuntimeError("; ".join(errors))


def _run_if_available(command: list[str], binary_name: str) -> None:
    if not shutil.which(binary_name):
        raise RuntimeError(f"{binary_name} not available")
    _run_command(command, f"Failed to run {binary_name}.")


def _build_lock_screen_script(img_path: Path) -> str:
    escaped_path = str(img_path).replace("'", "''")
    return rf"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.System.UserProfile.LockScreen, Windows.System.UserProfile, ContentType=WindowsRuntime] | Out-Null
[Windows.System.UserProfile.UserProfilePersonalizationSettings, Windows.System.UserProfile, ContentType=WindowsRuntime] | Out-Null

if (-not [Windows.System.UserProfile.UserProfilePersonalizationSettings]::IsSupported()) {{
    throw 'Windows lock screen personalization is not supported on this system.'
}}

function Invoke-WinRtAsyncResult {{
    param(
        [Parameter(Mandatory = $true)]
        $Operation,
        [Parameter(Mandatory = $true)]
        [Type] $ResultType
    )

    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
        $_.Name -eq 'AsTask' -and
        $_.IsGenericMethod -and
        $_.GetParameters().Count -eq 1
    }} | Select-Object -First 1

    if ($null -eq $method) {{
        throw 'Unable to bridge WinRT async operation to a .NET task.'
    }}

    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    return $task.GetAwaiter().GetResult()
}}

function Invoke-WinRtAsyncAction {{
    param(
        [Parameter(Mandatory = $true)]
        $Action
    )

    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
        $_.Name -eq 'AsTask' -and
        -not $_.IsGenericMethod -and
        $_.GetParameters().Count -eq 1
    }} | Select-Object -First 1

    if ($null -eq $method) {{
        throw 'Unable to bridge WinRT async action to a .NET task.'
    }}

    $task = $method.Invoke($null, @($Action))
    $task.GetAwaiter().GetResult() | Out-Null
}}

$file = Invoke-WinRtAsyncResult `
    -Operation ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{escaped_path}')) `
    -ResultType ([Windows.Storage.StorageFile])

$settings = [Windows.System.UserProfile.UserProfilePersonalizationSettings]::Current
$result = Invoke-WinRtAsyncResult `
    -Operation ($settings.TrySetLockScreenImageAsync($file)) `
    -ResultType ([bool])

if ($result) {{
    return
}}

Invoke-WinRtAsyncAction `
    -Action ([Windows.System.UserProfile.LockScreen]::SetImageFileAsync($file))
"""


def _get_windows_lock_screen_stage_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / APP_DIR_NAME / LOCK_SCREEN_STAGE_DIR_NAME


def _prepare_windows_lock_screen_candidates(img_path: Path) -> list[Path]:
    source = img_path.resolve()
    stage_dir = _get_windows_lock_screen_stage_dir()
    stage_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{LOCK_SCREEN_STAGE_PREFIX}_{uuid4().hex}"
    png_path = stage_dir / f"{unique_name}.png"
    jpg_path = stage_dir / f"{unique_name}.jpg"

    image = Image.open(source).convert("RGB")
    image.save(png_path, "PNG")
    image.save(jpg_path, "JPEG", quality=95)

    _cleanup_old_windows_lock_screen_candidates(stage_dir)
    return [png_path.resolve(), jpg_path.resolve()]


def _cleanup_old_windows_lock_screen_candidates(stage_dir: Path) -> None:
    matches = sorted(
        stage_dir.glob(f"{LOCK_SCREEN_STAGE_PREFIX}_*.*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_path in matches[KEEP_LOCK_SCREEN_STAGE_FILES:]:
        try:
            old_path.unlink()
        except Exception:
            pass


def _run_command(command: list[str], error_message: str) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"{error_message} Missing command: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = _format_command_error_output(exc.stderr or exc.stdout or "")
        suffix = f" {stderr}" if stderr else ""
        raise RuntimeError(f"{error_message}{suffix}") from exc


def _format_command_error_output(output: str) -> str:
    text = output.strip()
    if not text:
        return ""

    throw_match = POWERSHELL_THROW_RE.search(text)
    if throw_match:
        return _humanize_powershell_throw(throw_match.group(1))

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1]


def _humanize_powershell_throw(message: str) -> str:
    if message == "Windows rejected the lock screen image update.":
        return (
            "Windows rejected the lock screen image update. "
            "This usually means lock screen personalization is blocked by current "
            "Windows settings, policy, or lock screen mode."
        )

    if message == "Windows lock screen personalization is not supported on this system.":
        return (
            "Windows lock screen personalization is not supported on this system."
        )

    return message
