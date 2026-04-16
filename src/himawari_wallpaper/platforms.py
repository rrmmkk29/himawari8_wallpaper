import os
import platform
from pathlib import Path
from typing import Tuple


WINDOWS = "windows"
MACOS = "macos"
LINUX = "linux"

DEFAULT_SCREEN_SIZE = (1920, 1080)
APP_DIR_NAME = "HimawariDynamicWallpaper"


def detect_platform() -> str:
    system = platform.system().lower()
    if system == "windows":
        return WINDOWS
    if system == "darwin":
        return MACOS
    if system == "linux":
        return LINUX
    raise RuntimeError(f"Unsupported platform: {platform.system()}")


def get_default_output_dir() -> Path:
    current_platform = detect_platform()

    if current_platform == WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / APP_DIR_NAME

    if current_platform == MACOS:
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "himawari-dynamic-wallpaper"
    return Path.home() / ".local" / "share" / "himawari-dynamic-wallpaper"


def get_screen_size(default: Tuple[int, int] = DEFAULT_SCREEN_SIZE) -> Tuple[int, int]:
    current_platform = detect_platform()

    if current_platform == WINDOWS:
        return _get_screen_size_windows(default)

    size = _get_screen_size_tk()
    if size:
        return size

    return _get_screen_size_from_env(default)


def _get_screen_size_windows(default: Tuple[int, int]) -> Tuple[int, int]:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass

    return _get_screen_size_from_env(default)


def _get_screen_size_tk() -> Tuple[int, int] | None:
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        if width > 0 and height > 0:
            return width, height
    except Exception:
        return None
    return None


def _get_screen_size_from_env(default: Tuple[int, int]) -> Tuple[int, int]:
    width = os.environ.get("HIMAWARI_SCREEN_WIDTH")
    height = os.environ.get("HIMAWARI_SCREEN_HEIGHT")
    if width and height:
        try:
            parsed_width = int(width)
            parsed_height = int(height)
            if parsed_width > 0 and parsed_height > 0:
                return parsed_width, parsed_height
        except ValueError:
            pass
    return default
