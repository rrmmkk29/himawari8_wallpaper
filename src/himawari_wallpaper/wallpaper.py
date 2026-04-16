import shutil
import subprocess
from pathlib import Path
from typing import Callable

from PIL import Image

from .platforms import LINUX, MACOS, WINDOWS, detect_platform

CURRENT_WALLPAPER_BMP = "wallpaper_current.bmp"


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


def _run_command(command: list[str], error_message: str) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"{error_message} Missing command: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        suffix = f" {stderr}" if stderr else ""
        raise RuntimeError(f"{error_message}{suffix}") from exc
