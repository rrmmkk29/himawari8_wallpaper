# Himawari Dynamic Wallpaper

English | [简体中文](README.zh-CN.md)

A dynamic wallpaper project based on Himawari satellite imagery, refactored into a GitHub-friendly structure with:

- Automatic Windows / macOS / Linux detection
- Cross-platform wallpaper application and login auto-start
- An installable CLI entry point
- Easier bootstrap scripts
- Baseline tests and CI

## Platform Support

The application detects the current platform automatically:

- Windows: uses `SystemParametersInfoW` and supports Startup-folder auto-start
- macOS: uses `osascript` and supports `LaunchAgents`
- Linux: tries `plasma-apply-wallpaperimage`, `gsettings`, `xfconf-query`, and `feh`, and supports `~/.config/autostart`

Notes:

- Linux desktop environments vary a lot, so the wallpaper backend is implemented as a capability-based fallback chain.
- If the current Linux desktop is unsupported, the program raises a clear error instead of failing silently.

## Quick Start

Recommended universal bootstrap:

```bash
python scripts/bootstrap.py
```

Install development dependencies too:

```bash
python scripts/bootstrap.py --dev
```

Run a repository self-check before pushing:

```bash
python scripts/repo_check.py
```

If you prefer file-based runtime configuration instead of long CLI commands:

```bash
# Copy config.example.json to config.json and edit it first
python -m himawari_wallpaper --config ./config.json --once
```

### Windows Alternative

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1
.\.venv\Scripts\Activate.ps1
himawari-wallpaper --once
```

### macOS / Linux Alternative

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
source .venv/bin/activate
himawari-wallpaper --once
```

If you see `ensurepip is not available` or `python3 -m venv` fails on Ubuntu / WSL, install:

```bash
sudo apt install python3-venv
```

## Manual Installation

If you do not want to use the bootstrap scripts:

```bash
python -m venv .venv
```

After activating the virtual environment:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Environment Variables

Supported runtime overrides:

- `HIMAWARI_CONFIG`
- `HIMAWARI_OUTPUT_DIR`
- `HIMAWARI_INTERVAL_SECONDS`
- `HIMAWARI_MAX_ZOOM`
- `HIMAWARI_EARTH_HEIGHT_RATIO`
- `HIMAWARI_Y_OFFSET_RATIO`
- `HIMAWARI_TARGET_URL`
- `HIMAWARI_NAVIGATION_TIMEOUT_MS`
- `HIMAWARI_WARMUP_WAIT_MS`
- `HIMAWARI_PROBE_STEP_SECONDS`
- `HIMAWARI_PROBE_LOOKBACK_STEPS`

Priority order:

- CLI arguments override environment variables
- Environment variables override config files
- Config files override built-in defaults

See [`config.example.json`](config.example.json) for a sample config.

The config file also supports network-related settings:

- `target_url`
- `navigation_timeout_ms`
- `warmup_wait_ms`
- `probe_step_seconds`
- `probe_lookback_steps`

Those defaults are suitable for the current Himawari site and normally do not need to be changed unless the upstream site behavior changes.

Current first-run discovery fallback order:

1. Browser resource entries and page images
2. Embedded HTML probe image URLs
3. Direct `latest.json` lookup for the latest `D531106` timestamp
4. Local cached probe metadata

This reduces the amount of hard dependency on the site’s frontend implementation details.

## Common Commands

Refresh once:

```bash
himawari-wallpaper --once
```

Linux / WSL smoke test without touching the desktop wallpaper:

```bash
himawari-wallpaper --once --skip-set-wallpaper --out ./smoke-output
```

Run continuously:

```bash
himawari-wallpaper --run --interval 3600
```

Install login auto-start:

```bash
himawari-wallpaper --install-startup --interval 3600
```

Remove login auto-start:

```bash
himawari-wallpaper --remove-startup
```

Use a custom output directory:

```bash
himawari-wallpaper --once --out ./data
```

Use a config file:

```bash
himawari-wallpaper --config ./config.json --once
```

Temporarily override network settings:

```bash
himawari-wallpaper --once --target-url https://himawari.asia/ --navigation-timeout-ms 120000 --warmup-wait-ms 15000
```

## Default Output Directories

If `--out` is not specified, the application uses a writable per-user location instead of writing into the source tree:

- Windows: `%LOCALAPPDATA%\HimawariDynamicWallpaper`
- macOS: `~/Library/Application Support/HimawariDynamicWallpaper`
- Linux: `$XDG_DATA_HOME/himawari-dynamic-wallpaper` or `~/.local/share/himawari-dynamic-wallpaper`

This is safer than writing inside an installed package directory.

## Linux Notes

Linux wallpaper application tries these backends in order:

- KDE Plasma: `plasma-apply-wallpaperimage`
- GNOME: `gsettings`
- XFCE: `xfconf-query`
- Generic fallback: `feh`

If none of these are available, image fetching and composition can still work, but wallpaper application will fail with a clear error.

WSL validation summary:

- `python3 -m pip install --user -e '.[dev]'` works
- `python3 scripts/repo_check.py` passes
- `python3 -m playwright install chromium` works
- Headless Chromium launches successfully inside WSL
- A real `--once --skip-set-wallpaper` smoke test generated `last_source_meta.json`, the original PNG, and the wallpaper PNG
- The `latest.json` fallback successfully resolved the latest `D531106` timestamp in WSL when browser-side discovery failed
- `himawari.asia` can load slowly in WSL Chromium, so the default navigation timeout is now `120000ms`
- Minimal Ubuntu / WSL installations may lack `python3-venv`, which affects the first run of `bootstrap.py` / `bootstrap.sh`
- WSL is not a full Linux desktop session, so the real desktop wallpaper backend itself was not validated there

If you only want to validate installation first, skip browser installation:

```bash
python scripts/bootstrap.py --skip-playwright
```

Then install Chromium manually later:

```bash
python -m playwright install chromium
```

## Legacy Entry Point

The legacy script entry point is still available:

```bash
python src/himawari_wallpaper_webzoom.py --once
```

The installed CLI is still the preferred way to run it:

```bash
himawari-wallpaper --once
```

## Tests

```bash
pytest -q
```

## Release

Local pre-release checks:

```bash
python scripts/repo_check.py
python scripts/pack_release.py --label local
```

GitHub automated releases:

- Pushing a tag like `v0.1.0` triggers the release packaging workflow
- You can also run the `Release Package` workflow manually to build release artifacts only

See [`docs/RELEASING.md`](docs/RELEASING.md) for the detailed release process.

## Before Uploading To GitHub

- Run `himawari-wallpaper --once` at least once
- Run `pytest -q`
- Make sure logs, caches, and generated outputs are not committed
- Follow [`docs/GITHUB_UPLOAD_STEPS.md`](docs/GITHUB_UPLOAD_STEPS.md)
