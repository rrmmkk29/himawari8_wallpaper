#!/usr/bin/env python3

import argparse
import asyncio
import io
import json
import os
import re
import sys
import time
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from PIL import Image

from .autostart import install_startup, remove_startup
from .config import ALLOWED_ZOOMS, AppConfig, build_runtime_config
from .platforms import detect_platform, get_screen_size
from .wallpaper import set_lock_screen, set_wallpaper

CURRENT_WALLPAPER_BMP = "wallpaper_current.bmp"
WALLPAPER_RING_PREFIX = "wallpaper"
ORIGIN_RING_PREFIX = "origin_wallpaper"
LOCK_SCREEN_PREFIX = "lockscreen"

MAX_LOG_BYTES = 1024 * 1024
KEEP_LOG_BYTES = 512 * 1024

SOURCE_META_FILE = "last_source_meta.json"
DISCOVERY_ATTEMPTS = 3
DISCOVERY_RETRY_WAIT_MS = 2000

LIVE_TILE_RE = re.compile(
    r"^https://(?P<host>[^/]+)/himawari/img/(?P<layer>D531106|FULL_24h/B13)/"
    r"(?:(?P<zoom>\d+)d|thumbnail)/(?P<tile>\d+)/"
    r"(?P<yyyy>\d{4})/(?P<mm>\d{2})/(?P<dd>\d{2})/"
    r"(?P<hhmmss>\d{6})_(?P<x>\d+)_(?P<y>\d+)\.png$"
)
HTML_PROBE_TILE_RE = re.compile(
    r"^https://(?P<host>[^/]+)/(?:himawari/)?img/(?P<layer>D531106|FULL_24h/B13)/"
    r"(?:(?P<zoom>\d+)d|thumbnail)/(?P<tile>\d+)/"
    r"(?P<yyyy>\d{4})/(?P<mm>\d{2})/(?P<dd>\d{2})/"
    r"(?P<hhmmss>\d{6})_(?P<x>\d+)_(?P<y>\d+)\.png$"
)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_log_file(out_dir: Path) -> Path:
    return out_dir / "himawari.log"


def get_source_meta_file(out_dir: Path) -> Path:
    return out_dir / SOURCE_META_FILE


def truncate_log_file_if_needed(log_path: Path) -> None:
    try:
        if not log_path.exists():
            return

        size = log_path.stat().st_size
        if size <= MAX_LOG_BYTES:
            return

        with log_path.open("rb") as handle:
            if size > KEEP_LOG_BYTES:
                handle.seek(-KEEP_LOG_BYTES, os.SEEK_END)
            data = handle.read()

        nl = data.find(b"\n")
        if nl != -1 and nl + 1 < len(data):
            data = data[nl + 1 :]

        header = (
            f"[{now_str()}] Log truncated automatically; keeping latest "
            f"{KEEP_LOG_BYTES // 1024} KB\n"
        ).encode("utf-8")

        with log_path.open("wb") as handle:
            handle.write(header)
            handle.write(data)
    except Exception:
        pass


def log(msg: str, out_dir: Path) -> None:
    text = f"[{now_str()}] {msg}"
    print(text)
    try:
        log_path = get_log_file(out_dir)
        truncate_log_file_if_needed(log_path)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except Exception:
        pass


def save_png(img: Image.Image, path: Path) -> Path:
    ensure_dir(path.parent)
    img.save(path, "PNG")
    return path


def save_source_meta(meta: Dict[str, Any], out_dir: Path) -> None:
    data = {
        "host": meta.get("host"),
        "d531106_prefix": meta.get("d531106_prefix"),
        "tile_size": meta.get("tile_size"),
        "layer": meta.get("layer"),
        "yyyy": meta.get("yyyy"),
        "mm": meta.get("mm"),
        "dd": meta.get("dd"),
        "hhmmss": meta.get("hhmmss"),
    }
    path = get_source_meta_file(out_dir)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_source_meta(out_dir: Path) -> Optional[Dict[str, Any]]:
    path = get_source_meta_file(out_dir)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = datetime.strptime(
            f"{data['yyyy']}-{data['mm']}-{data['dd']} {data['hhmmss']}",
            "%Y-%m-%d %H%M%S",
        ).replace(tzinfo=timezone.utc)

        data["timestamp"] = ts
        data.setdefault("prefix", data["d531106_prefix"])
        data.setdefault("zoom", 1)
        data.setdefault("is_thumbnail", False)
        data.setdefault("x", 0)
        data.setdefault("y", 0)
        data.setdefault("url", "")
        return data
    except Exception:
        return None


def round_down_utc(dt: datetime, step_seconds: int) -> datetime:
    epoch = int(dt.timestamp())
    epoch -= epoch % step_seconds
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def get_slot_count(interval_sec: int) -> int:
    return max(1, (24 * 3600 + interval_sec - 1) // interval_sec)


def get_slot_index(ts: datetime, interval_sec: int, slot_count: int) -> int:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return int(ts.timestamp() // interval_sec) % slot_count


def get_slot_paths(out_dir: Path, slot_index: int) -> Tuple[Path, Path]:
    origin_path = out_dir / f"{ORIGIN_RING_PREFIX}_{slot_index:03d}.png"
    wallpaper_path = out_dir / f"{WALLPAPER_RING_PREFIX}_{slot_index:03d}.png"
    return origin_path, wallpaper_path


def cleanup_legacy_wallpapers(out_dir: Path, slot_count: int) -> None:
    keep_names = {"himawari.log", CURRENT_WALLPAPER_BMP, SOURCE_META_FILE}
    for index in range(slot_count):
        keep_names.add(f"{WALLPAPER_RING_PREFIX}_{index:03d}.png")
        keep_names.add(f"{ORIGIN_RING_PREFIX}_{index:03d}.png")

    patterns = [
        "wallpaper_*.png",
        "origin_wallpaper_*.png",
        "wallpaper_*.jpg",
        "wallpaper_current.png",
        "origin_wallpaper_current.png",
        "originwallpaper_current.png",
        "lockscreen_*.png",
        "web_debug_screenshot.png",
    ]

    removed = 0
    for pattern in patterns:
        for path in out_dir.glob(pattern):
            if path.name in keep_names:
                continue
            try:
                path.unlink()
                removed += 1
            except Exception:
                pass

    if removed > 0:
        log(f"Cleaned up {removed} legacy image files.", out_dir)


def choose_zoom_for_screen(
    screen_h: int,
    earth_height_ratio: float = 0.6,
    tile_size: int = 550,
    allowed_zooms: Tuple[int, ...] = ALLOWED_ZOOMS,
    oversample: float = 1.05,
) -> int:
    target = int(screen_h * earth_height_ratio * oversample)
    for zoom in allowed_zooms:
        if tile_size * zoom >= target:
            return zoom
    return allowed_zooms[-1]


def compose_wallpaper(
    earth_img: Image.Image,
    screen_w: int,
    screen_h: int,
    earth_height_ratio: float = 0.6,
    y_offset_ratio: float = 0.0,
) -> Image.Image:
    if not 0.05 <= earth_height_ratio <= 1.0:
        raise ValueError("earth_height_ratio should be between 0.05 and 1.0.")

    bg = Image.new("RGB", (screen_w, screen_h), (0, 0, 0))

    target_earth_h = max(1, int(screen_h * earth_height_ratio))
    target_earth_w = target_earth_h

    earth_resized = earth_img.resize((target_earth_w, target_earth_h), Image.LANCZOS)

    x = (screen_w - target_earth_w) // 2
    y = (screen_h - target_earth_h) // 2 + int(screen_h * y_offset_ratio)

    bg.paste(earth_resized, (x, y))
    return bg


def persist_wallpaper_outputs(
    earth: Image.Image,
    wallpaper: Image.Image,
    origin_png_path: Path,
    wallpaper_png_path: Path,
) -> None:
    save_png(earth, origin_png_path)
    save_png(wallpaper, wallpaper_png_path)


def build_lock_screen_path(out_dir: Path, ts_text: str) -> Path:
    suffix = uuid4().hex
    return out_dir / f"{LOCK_SCREEN_PREFIX}_{ts_text}_{suffix}.png"


def parse_live_meta(url: str) -> Optional[Dict[str, Any]]:
    match = LIVE_TILE_RE.match(url)
    if not match:
        return None

    gd = match.groupdict()
    timestamp = datetime.strptime(
        f"{gd['yyyy']}-{gd['mm']}-{gd['dd']} {gd['hhmmss']}",
        "%Y-%m-%d %H%M%S",
    ).replace(tzinfo=timezone.utc)

    host = gd["host"]
    return {
        "host": host,
        "prefix": f"https://{host}/himawari/img/{gd['layer']}",
        "d531106_prefix": f"https://{host}/himawari/img/D531106",
        "layer": gd["layer"],
        "zoom": int(gd["zoom"]) if gd["zoom"] else 1,
        "tile_size": int(gd["tile"]),
        "yyyy": gd["yyyy"],
        "mm": gd["mm"],
        "dd": gd["dd"],
        "hhmmss": gd["hhmmss"],
        "timestamp": timestamp,
        "x": int(gd["x"]),
        "y": int(gd["y"]),
        "url": url,
        "is_thumbnail": "/thumbnail/" in url,
    }


def extract_probe_meta_from_html(html: str) -> Optional[Dict[str, Any]]:
    urls = re.findall(r"https://[^\s\"'<>]+\.png", html)
    for url in urls:
        meta = parse_live_meta(url)
        if meta is None:
            meta = parse_html_probe_meta(url)
        if meta is not None:
            meta["probe_only"] = True
            return meta
    return None


def parse_html_probe_meta(url: str) -> Optional[Dict[str, Any]]:
    match = HTML_PROBE_TILE_RE.match(url)
    if not match:
        return None

    gd = match.groupdict()
    timestamp = datetime.strptime(
        f"{gd['yyyy']}-{gd['mm']}-{gd['dd']} {gd['hhmmss']}",
        "%Y-%m-%d %H%M%S",
    ).replace(tzinfo=timezone.utc)
    host = gd["host"]

    return {
        "host": host,
        "prefix": f"https://{host}/himawari/img/{gd['layer']}",
        "d531106_prefix": f"https://{host}/himawari/img/D531106",
        "layer": gd["layer"],
        "zoom": int(gd["zoom"]) if gd["zoom"] else 1,
        "tile_size": int(gd["tile"]),
        "yyyy": gd["yyyy"],
        "mm": gd["mm"],
        "dd": gd["dd"],
        "hhmmss": gd["hhmmss"],
        "timestamp": timestamp,
        "x": int(gd["x"]),
        "y": int(gd["y"]),
        "url": url,
        "is_thumbnail": "/thumbnail/" in url,
    }


def is_candidate_url_from_page(url: str) -> bool:
    if "/img/D531106/" not in url and "/img/FULL_24h/B13/" not in url:
        return False

    blocked_markers = [
        "coastline",
        "BlueMarble",
        "/img/logo_",
        "/img/sns_",
        "menu_button",
        "submenu_button",
        "time_controller_knob",
    ]
    if any(marker in url for marker in blocked_markers):
        return False

    return parse_live_meta(url) is not None


def build_tile_url(meta: Dict[str, Any], zoom: int, x: int, y: int) -> str:
    return (
        f"{meta['d531106_prefix']}/{zoom}d/{meta['tile_size']}/"
        f"{meta['yyyy']}/{meta['mm']}/{meta['dd']}/{meta['hhmmss']}_{x}_{y}.png"
    )


def build_latest_json_meta(origin: str, date_text: str) -> Dict[str, Any]:
    ts = datetime.strptime(date_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return {
        "host": urlsplit(origin).netloc,
        "prefix": f"{origin}/img/D531106",
        "d531106_prefix": f"{origin}/img/D531106",
        "layer": "D531106",
        "zoom": 1,
        "tile_size": 550,
        "yyyy": ts.strftime("%Y"),
        "mm": ts.strftime("%m"),
        "dd": ts.strftime("%d"),
        "hhmmss": ts.strftime("%H%M%S"),
        "timestamp": ts,
        "x": 0,
        "y": 0,
        "url": "",
        "is_thumbnail": False,
    }


async def fetch_latest_d531106_from_latest_json(
    request_context,
    target_url: str,
    out_dir: Path,
) -> Tuple[Dict[str, Any], bytes]:
    split = urlsplit(target_url)
    origin = f"{split.scheme}://{split.netloc}"
    latest_json_url = f"{origin}/img/D531106/latest.json"

    log(f"Trying latest.json fallback: {latest_json_url}", out_dir)

    response = await request_context.get(
        latest_json_url,
        timeout=30000,
        fail_on_status_code=True,
    )
    payload = await response.json()

    if not isinstance(payload, dict) or "date" not in payload:
        raise RuntimeError("latest.json fallback returned an unexpected payload.")

    meta = build_latest_json_meta(origin, payload["date"])
    tile_url = build_tile_url(meta, 1, 0, 0)
    meta["url"] = tile_url

    tile_response = await request_context.get(
        tile_url,
        timeout=30000,
        fail_on_status_code=True,
    )
    body = await tile_response.body()
    log(f"latest.json fallback resolved current D531106 tile: {tile_url}", out_dir)
    return meta, body


async def discover_live_source(
    page,
    request_context,
    out_dir: Path,
    target_url: str,
    navigation_timeout_ms: int,
    warmup_wait_ms: int,
) -> Tuple[Dict[str, Any], bytes]:
    last_error: Exception | None = None
    urls: list[str] = []

    for attempt in range(1, DISCOVERY_ATTEMPTS + 1):
        try:
            log(f"Opening source page: {target_url} (attempt {attempt}/{DISCOVERY_ATTEMPTS})", out_dir)

            await page.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=navigation_timeout_ms,
            )
            await page.wait_for_timeout(warmup_wait_ms)

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            await page.wait_for_timeout(3000)

            debug_screenshot = out_dir / "web_debug_screenshot.png"
            await page.screenshot(path=str(debug_screenshot), full_page=True)

            urls = await page.evaluate(
                """
                () => {
                    const perf = performance.getEntriesByType('resource').map(entry => entry.name);
                    const imgs = Array.from(document.images)
                        .map(img => img.currentSrc || img.src)
                        .filter(Boolean);
                    return Array.from(new Set([...perf, ...imgs]));
                }
                """
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt == DISCOVERY_ATTEMPTS:
                raise
            log(
                f"Source page open attempt {attempt} failed, retrying: {exc}",
                out_dir,
            )
            await page.wait_for_timeout(DISCOVERY_RETRY_WAIT_MS)

    if not urls and last_error is not None:
        raise last_error

    candidates: List[Dict[str, Any]] = []
    for url in urls:
        if not is_candidate_url_from_page(url):
            continue
        meta = parse_live_meta(url)
        if meta is not None:
            candidates.append(meta)

    if not candidates:
        html = await page.content()
        probe_meta = extract_probe_meta_from_html(html)
        if probe_meta is not None:
            log(
                f"Falling back to HTML probe seed: {probe_meta['url']}",
                out_dir,
            )
            return probe_meta, b""
        raise RuntimeError("No D531106/B13 candidate images found in page resources.")

    candidates.sort(
        key=lambda meta: (
            2
            if meta["layer"] == "D531106" and not meta["is_thumbnail"]
            else 1
            if meta["layer"] == "D531106" and meta["is_thumbnail"]
            else 0,
            meta["zoom"],
        ),
        reverse=True,
    )

    d531106_found = [meta for meta in candidates if meta["layer"] == "D531106"]
    if d531106_found:
        best_meta = d531106_found[0]
        log(f"Found D531106 directly: {best_meta['url']}", out_dir)
    else:
        b13_found = [meta for meta in candidates if meta["layer"] == "FULL_24h/B13"]
        if not b13_found:
            raise RuntimeError("Candidates found, but neither D531106 nor B13 is available.")
        best_meta = b13_found[0]
        log(f"D531106 not found directly; using B13 probe: {best_meta['url']}", out_dir)

    best_body = b""
    try:
        response = await request_context.get(
            best_meta["url"], timeout=30000, fail_on_status_code=True
        )
        best_body = await response.body()
    except Exception as exc:
        log(f"Failed to fetch baseline image; continuing with tile fallback: {exc}", out_dir)

    return best_meta, best_body


async def probe_latest_d531106_from_cache(
    request_context,
    probe_meta: Dict[str, Any],
    out_dir: Path,
    probe_step_seconds: int,
    probe_lookback_steps: int,
) -> Tuple[Dict[str, Any], bytes]:
    base = round_down_utc(datetime.now(timezone.utc), probe_step_seconds)
    last_error = None

    for step in range(probe_lookback_steps):
        ts = base - timedelta(seconds=probe_step_seconds * step)

        meta = dict(probe_meta)
        meta["prefix"] = meta["d531106_prefix"]
        meta["layer"] = "D531106"
        meta["zoom"] = 1
        meta["is_thumbnail"] = False
        meta["x"] = 0
        meta["y"] = 0
        meta["yyyy"] = ts.strftime("%Y")
        meta["mm"] = ts.strftime("%m")
        meta["dd"] = ts.strftime("%d")
        meta["hhmmss"] = ts.strftime("%H%M%S")
        meta["timestamp"] = ts

        url = build_tile_url(meta, 1, 0, 0)
        meta["url"] = url

        try:
            response = await request_context.get(url, timeout=20000, fail_on_status_code=False)
            if response.status != 200:
                continue

            body = await response.body()
            if len(body) < 20000:
                continue

            log(f"Cache probe hit latest D531106: {url}", out_dir)
            return meta, body
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Cache probe failed: {last_error}")


async def download_tiles_via_browser_request(
    request_context,
    meta: Dict[str, Any],
    desired_zoom: int,
    out_dir: Path,
) -> Tuple[Image.Image, int]:
    zoom_candidates = [zoom for zoom in ALLOWED_ZOOMS if zoom <= desired_zoom]
    zoom_candidates.sort(reverse=True)

    last_error = None
    for zoom in zoom_candidates:
        try:
            tile_size = meta["tile_size"]
            canvas = Image.new("RGB", (tile_size * zoom, tile_size * zoom))
            total = zoom * zoom
            done = 0

            log(f"Trying D531106 tiles at zoom={zoom}", out_dir)

            for y in range(zoom):
                for x in range(zoom):
                    url = build_tile_url(meta, zoom, x, y)
                    response = await request_context.get(
                        url, timeout=30000, fail_on_status_code=True
                    )
                    body = await response.body()

                    tile = Image.open(io.BytesIO(body)).convert("RGB")
                    canvas.paste(tile, (x * tile_size, y * tile_size))

                    done += 1
                    log(f"Downloaded tile {done}/{total}: ({x}, {y})", out_dir)

            return canvas, zoom
        except Exception as exc:
            last_error = exc
            log(f"zoom={zoom} failed; trying smaller zoom: {exc}", out_dir)

    raise RuntimeError(f"All D531106 zoom levels failed: {last_error}")


async def fetch_latest_image_from_web(
    out_dir: Path,
    desired_zoom: int,
    config: AppConfig,
) -> Tuple[datetime, str, Image.Image, int]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run `python -m pip install -e .` and "
            "`python -m playwright install chromium` first."
        ) from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1400, "height": 900},
            service_workers="block",
        )
        page = await context.new_page()
        api_context = await playwright.request.new_context(ignore_https_errors=True)

        try:
            try:
                best_meta, best_body = await discover_live_source(
                    page,
                    api_context,
                    out_dir,
                    target_url=config.target_url,
                    navigation_timeout_ms=config.navigation_timeout_ms,
                    warmup_wait_ms=config.warmup_wait_ms,
                )

                if best_meta.get("probe_only"):
                    log(
                        f"Discovery returned probe seed; trying latest.json fallback: {best_meta['url']}",
                        out_dir,
                    )
                    best_meta, best_body = await fetch_latest_d531106_from_latest_json(
                        api_context,
                        config.target_url,
                        out_dir,
                    )

                log(f"Discovery source: {best_meta['url']}", out_dir)
                save_source_meta(best_meta, out_dir)
            except Exception as exc:
                log(f"Page discovery failed; trying latest.json fallback: {exc}", out_dir)

                try:
                    best_meta, best_body = await fetch_latest_d531106_from_latest_json(
                        api_context,
                        config.target_url,
                        out_dir,
                    )
                    log(f"latest.json fallback source: {best_meta['url']}", out_dir)
                    save_source_meta(best_meta, out_dir)
                except Exception as latest_exc:
                    log(f"latest.json fallback failed; trying cache probe: {latest_exc}", out_dir)

                    cached_meta = load_source_meta(out_dir)
                    if not cached_meta:
                        raise RuntimeError(
                            "Page discovery failed, latest.json fallback failed, and no cached probe data exists."
                        )

                    best_meta, best_body = await probe_latest_d531106_from_cache(
                        api_context,
                        cached_meta,
                        out_dir,
                        probe_step_seconds=config.probe_step_seconds,
                        probe_lookback_steps=config.probe_lookback_steps,
                    )
                    log(f"Cache probe source: {best_meta['url']}", out_dir)
                    save_source_meta(best_meta, out_dir)

            try:
                earth, actual_zoom = await download_tiles_via_browser_request(
                    api_context,
                    best_meta,
                    desired_zoom=desired_zoom,
                    out_dir=out_dir,
                )
            except Exception as exc:
                log(f"High zoom D531106 download failed: {exc}", out_dir)

                if best_meta["layer"] == "D531106" and best_body:
                    log("Falling back to already-loaded D531106 image.", out_dir)
                    earth = Image.open(io.BytesIO(best_body)).convert("RGB")
                    actual_zoom = best_meta["zoom"]
                else:
                    raise RuntimeError(
                        "No usable D531106 baseline image and tile download failed."
                    ) from exc

            return best_meta["timestamp"], best_meta["url"], earth, actual_zoom
        finally:
            await api_context.dispose()
            await browser.close()


def update_once(
    config: AppConfig,
    last_timestamp: Optional[str] = None,
) -> Optional[str]:
    screen_w, screen_h = get_screen_size()
    desired_zoom = min(
        choose_zoom_for_screen(
            screen_h=screen_h,
            earth_height_ratio=config.earth_height_ratio,
        ),
        config.max_zoom,
    )

    ts, source_url, earth, actual_zoom = asyncio.run(
        fetch_latest_image_from_web(
            config.output_dir,
            desired_zoom=desired_zoom,
            config=config,
        )
    )
    ts_text = ts.strftime("%Y%m%d_%H%M%S")

    if last_timestamp == ts_text:
        log(f"Latest image unchanged; skipping update: {ts_text}", config.output_dir)
        return last_timestamp

    log(f"New image discovered: {ts_text}", config.output_dir)
    log(f"Source image: {source_url}", config.output_dir)
    log(f"Target zoom: {desired_zoom}; actual zoom: {actual_zoom}", config.output_dir)
    log(f"Detected screen resolution: {screen_w}x{screen_h}", config.output_dir)

    slot_count = get_slot_count(config.interval_sec)
    slot_index = get_slot_index(ts, config.interval_sec, slot_count)
    log(
        f"Writing 24-hour ring buffer slot: {slot_index + 1}/{slot_count}",
        config.output_dir,
    )

    origin_png_path, png_path = get_slot_paths(config.output_dir, slot_index)

    wallpaper = compose_wallpaper(
        earth_img=earth,
        screen_w=screen_w,
        screen_h=screen_h,
        earth_height_ratio=config.earth_height_ratio,
        y_offset_ratio=config.y_offset_ratio,
    )

    persist_wallpaper_outputs(
        earth=earth,
        wallpaper=wallpaper,
        origin_png_path=origin_png_path,
        wallpaper_png_path=png_path,
    )

    if config.apply_wallpaper:
        set_wallpaper(png_path)
        log(f"Wallpaper updated: {png_path}", config.output_dir)
    else:
        log(f"Wallpaper generated without applying it: {png_path}", config.output_dir)

    if config.sync_lock_screen:
        lock_screen_path = build_lock_screen_path(config.output_dir, ts_text)
        save_png(wallpaper, lock_screen_path)
        try:
            set_lock_screen(lock_screen_path)
            log(f"Lock screen updated: {lock_screen_path}", config.output_dir)
        except Exception as exc:
            log(f"Lock screen sync failed: {exc}", config.output_dir)

    return ts_text


def run_loop(
    config: AppConfig,
) -> None:
    last_timestamp = None

    slot_count = get_slot_count(config.interval_sec)
    cleanup_legacy_wallpapers(config.output_dir, slot_count)

    log("Application started.", config.output_dir)
    log(f"Platform: {detect_platform()}", config.output_dir)
    log(f"Refresh interval: {config.interval_sec} seconds", config.output_dir)
    log(f"24-hour ring buffer slots: {slot_count}", config.output_dir)
    log("Source: himawari.asia page resources + cache probe fallback", config.output_dir)
    log(f"Earth height ratio: {config.earth_height_ratio}", config.output_dir)
    log(f"Vertical offset ratio: {config.y_offset_ratio}", config.output_dir)
    log(f"Maximum zoom: {config.max_zoom}", config.output_dir)
    log(f"Target URL: {config.target_url}", config.output_dir)
    log(f"Navigation timeout: {config.navigation_timeout_ms} ms", config.output_dir)
    log(f"Warmup wait: {config.warmup_wait_ms} ms", config.output_dir)
    log(
        f"Probe cadence: {config.probe_step_seconds}s x {config.probe_lookback_steps}",
        config.output_dir,
    )

    while True:
        try:
            last_timestamp = update_once(
                config=config,
                last_timestamp=last_timestamp,
            )
        except Exception as exc:
            log(f"Update failed: {exc}", config.output_dir)

        time.sleep(config.interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Himawari dynamic wallpaper with auto platform detection."
    )

    parser.add_argument("--run", action="store_true", help="Run the refresh loop continuously")
    parser.add_argument("--once", action="store_true", help="Run a single refresh and exit")
    parser.add_argument(
        "--download-only",
        dest="apply_wallpaper",
        action="store_false",
        default=None,
        help="Fetch and generate wallpaper files but do not apply them to the desktop",
    )
    parser.add_argument(
        "--skip-set-wallpaper",
        dest="apply_wallpaper",
        action="store_false",
        default=None,
        help="Legacy alias for --download-only",
    )
    parser.add_argument(
        "--sync-lock-screen",
        action="store_true",
        default=None,
        help="On Windows, also sync the generated wallpaper image to the lock screen",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the simple desktop GUI for common settings",
    )
    parser.add_argument(
        "--no-sync-lock-screen",
        dest="sync_lock_screen",
        action="store_false",
        default=None,
        help="Disable Windows lock screen sync for this run",
    )
    parser.add_argument("--install-startup", action="store_true", help="Install login auto-start")
    parser.add_argument("--remove-startup", action="store_true", help="Remove login auto-start")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a JSON config file",
    )
    parser.add_argument(
        "--target-url",
        type=str,
        default=None,
        help="Source page URL for Himawari discovery",
    )
    parser.add_argument(
        "--navigation-timeout-ms",
        type=int,
        default=None,
        help="Page navigation timeout in milliseconds for the source website",
    )
    parser.add_argument(
        "--warmup-wait-ms",
        type=int,
        default=None,
        help="Wait time in milliseconds before collecting page resources",
    )
    parser.add_argument(
        "--probe-step-seconds",
        type=int,
        default=None,
        help="Probe step size in seconds when scanning cached timestamps",
    )
    parser.add_argument(
        "--probe-lookback-steps",
        type=int,
        default=None,
        help="Maximum number of probe steps to scan backwards in time",
    )
    parser.add_argument("--interval", type=int, default=None, help="Refresh interval in seconds")
    parser.add_argument("--zoom", type=int, default=0, help="Legacy option kept for compatibility")
    parser.add_argument(
        "--max-zoom",
        type=int,
        default=None,
        help="Maximum auto-selected zoom, one of 1/2/4/8",
    )
    parser.add_argument("--out", type=str, default=None, help="Output directory")
    parser.add_argument(
        "--earth-height-ratio",
        type=float,
        default=None,
        help="Earth height ratio relative to the wallpaper height",
    )
    parser.add_argument(
        "--y-offset-ratio",
        type=float,
        default=None,
        help="Vertical Earth offset ratio relative to the screen height",
    )

    args = parser.parse_args()

    try:
        config = build_runtime_config(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    if args.gui:
        from .gui import main as gui_main

        gui_main(config)
        return

    if args.remove_startup:
        if remove_startup():
            print("Auto-start removed.")
        else:
            print("No auto-start entry found.")
        return

    if args.install_startup:
        startup_path = install_startup(
            interval_sec=config.interval_sec,
            out_dir=config.output_dir,
            earth_height_ratio=config.earth_height_ratio,
            y_offset_ratio=config.y_offset_ratio,
            max_zoom=config.max_zoom,
            apply_wallpaper=config.apply_wallpaper,
            sync_lock_screen=config.sync_lock_screen,
            config_path=config.config_path,
        )
        print(f"Auto-start installed: {startup_path}")
        return

    slot_count = get_slot_count(config.interval_sec)
    cleanup_legacy_wallpapers(config.output_dir, slot_count)

    if args.once:
        update_once(config=config)
        return

    run_loop(config)
