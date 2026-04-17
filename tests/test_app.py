import asyncio
import os
from pathlib import Path

from datetime import datetime, timezone

from PIL import Image

from himawari_wallpaper.app import (
    MAX_LOCK_SCREEN_FILES,
    build_latest_json_candidates,
    build_latest_json_meta,
    build_lock_screen_path,
    choose_zoom_for_screen,
    compose_wallpaper,
    extract_probe_meta_from_html,
    fetch_latest_image_from_web,
    get_slot_count,
    get_slot_index,
    parse_live_meta,
    persist_wallpaper_outputs,
    prune_lock_screen_outputs,
)
from himawari_wallpaper.config import ALLOWED_ZOOMS, AppConfig


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


def test_build_latest_json_candidates_keeps_direct_and_himawari_paths() -> None:
    candidates = build_latest_json_candidates("https://himawari.asia/")

    assert candidates == [
        ("https://himawari.asia/img/D531106/latest.json", "https://himawari.asia/img/D531106"),
        (
            "https://himawari.asia/himawari/img/D531106/latest.json",
            "https://himawari.asia/himawari/img/D531106",
        ),
    ]


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


def test_prune_lock_screen_outputs_keeps_latest_files(tmp_path: Path) -> None:
    for index in range(MAX_LOCK_SCREEN_FILES + 3):
        path = tmp_path / f"lockscreen_20260416_120000_{index:02d}.png"
        path.write_bytes(b"png")
        os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))

    removed = prune_lock_screen_outputs(tmp_path)
    remaining = sorted(tmp_path.glob("lockscreen_*.png"))

    assert removed == 3
    assert len(remaining) == MAX_LOCK_SCREEN_FILES
    remaining_names = {path.name for path in remaining}
    assert "lockscreen_20260416_120000_00.png" not in remaining_names
    assert f"lockscreen_20260416_120000_{MAX_LOCK_SCREEN_FILES + 2:02d}.png" in remaining_names


def test_fetch_latest_image_from_web_does_not_require_playwright_when_http_succeeds(
    monkeypatch,
    tmp_path: Path,
) -> None:
    meta = build_latest_json_meta("https://himawari.asia", "2026-04-16 12:50:00")
    meta["url"] = "https://himawari.asia/img/D531106/1d/550/2026/04/16/125000_0_0.png"
    earth = Image.new("RGB", (16, 16), (1, 2, 3))

    async def fake_resolve_latest_source_via_http(request_context, out_dir, config):
        return meta, b"baseline"

    async def fake_download_tiles(request_context, source_meta, desired_zoom, out_dir):
        assert source_meta["url"] == meta["url"]
        assert desired_zoom == 1
        return earth, 1

    monkeypatch.setattr(
        "himawari_wallpaper.app.resolve_latest_source_via_http",
        fake_resolve_latest_source_via_http,
    )
    monkeypatch.setattr(
        "himawari_wallpaper.app.download_tiles_via_request_context",
        fake_download_tiles,
    )
    monkeypatch.setattr(
        "himawari_wallpaper.app.save_source_meta",
        lambda *args, **kwargs: None,
    )

    config = AppConfig(
        interval_sec=600,
        output_dir=tmp_path,
        earth_height_ratio=0.6,
        y_offset_ratio=0.0,
        max_zoom=1,
        target_url="https://himawari.asia/",
        navigation_timeout_ms=120000,
        warmup_wait_ms=15000,
        probe_step_seconds=600,
        probe_lookback_steps=12,
        config_path=None,
        apply_wallpaper=False,
        sync_lock_screen=False,
    )

    ts, source_url, image, actual_zoom = asyncio.run(
        fetch_latest_image_from_web(tmp_path, desired_zoom=1, config=config)
    )

    assert ts == meta["timestamp"]
    assert source_url == meta["url"]
    assert image.size == earth.size
    assert actual_zoom == 1
