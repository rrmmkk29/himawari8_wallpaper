from pathlib import Path

from datetime import datetime, timezone

from PIL import Image

from himawari_wallpaper.app import (
    build_latest_json_meta,
    build_lock_screen_path,
    choose_zoom_for_screen,
    compose_wallpaper,
    extract_probe_meta_from_html,
    get_slot_count,
    get_slot_index,
    parse_live_meta,
    persist_wallpaper_outputs,
)
from himawari_wallpaper.config import ALLOWED_ZOOMS


def test_choose_zoom_for_screen_returns_allowed_zoom() -> None:
    assert choose_zoom_for_screen(screen_h=1080, earth_height_ratio=0.6) == 2
    assert choose_zoom_for_screen(screen_h=4320, earth_height_ratio=0.6) in ALLOWED_ZOOMS


def test_compose_wallpaper_keeps_canvas_size() -> None:
    earth = Image.new("RGB", (10, 10), (255, 255, 255))
    wallpaper = compose_wallpaper(earth_img=earth, screen_w=100, screen_h=80)

    assert wallpaper.size == (100, 80)
    assert wallpaper.getpixel((50, 40)) == (255, 255, 255)


def test_slot_count_and_index_are_stable() -> None:
    slot_count = get_slot_count(3600)
    ts = datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)

    assert slot_count == 24
    assert get_slot_index(ts, 3600, slot_count) == 12


def test_parse_live_meta_extracts_fields() -> None:
    meta = parse_live_meta(
        "https://himawari8-dl.nict.go.jp/himawari/img/D531106/4d/550/"
        "2026/04/16/120000_1_2.png"
    )

    assert meta is not None
    assert meta["host"] == "himawari8-dl.nict.go.jp"
    assert meta["zoom"] == 4
    assert meta["tile_size"] == 550
    assert meta["x"] == 1
    assert meta["y"] == 2


def test_extract_probe_meta_from_html_uses_embedded_png_url() -> None:
    html = """
    <html>
      <head>
        <meta property="og:image"
              content="https://himawari.asia/img/D531106/1d/550/2015/07/07/015000_0_0.png">
      </head>
    </html>
    """

    meta = extract_probe_meta_from_html(html)

    assert meta is not None
    assert meta["layer"] == "D531106"
    assert meta["d531106_prefix"] == "https://himawari.asia/himawari/img/D531106"
    assert meta["probe_only"] is True


def test_build_latest_json_meta_uses_origin_and_date() -> None:
    meta = build_latest_json_meta("https://himawari.asia", "2026-04-16 12:50:00")

    assert meta["d531106_prefix"] == "https://himawari.asia/img/D531106"
    assert meta["yyyy"] == "2026"
    assert meta["mm"] == "04"
    assert meta["dd"] == "16"
    assert meta["hhmmss"] == "125000"


def test_persist_wallpaper_outputs_only_writes_files(tmp_path: Path) -> None:
    earth = Image.new("RGB", (10, 10), (255, 255, 255))
    wallpaper = Image.new("RGB", (20, 20), (0, 0, 0))
    origin_path = tmp_path / "origin.png"
    wallpaper_path = tmp_path / "wallpaper.png"

    persist_wallpaper_outputs(
        earth=earth,
        wallpaper=wallpaper,
        origin_png_path=origin_path,
        wallpaper_png_path=wallpaper_path,
    )

    assert origin_path.exists()
    assert wallpaper_path.exists()


def test_build_lock_screen_path_is_unique(tmp_path: Path) -> None:
    first = build_lock_screen_path(tmp_path, "20260416_120000")
    second = build_lock_screen_path(tmp_path, "20260416_120000")

    assert first.parent == tmp_path
    assert first.name.startswith("lockscreen_20260416_120000_")
    assert second.name.startswith("lockscreen_20260416_120000_")
    assert first != second
