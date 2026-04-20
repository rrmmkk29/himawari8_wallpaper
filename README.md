# Himawari Dynamic Wallpaper

English | [简体中文](README.zh-CN.md)

Dynamic wallpaper based on Himawari satellite imagery.

## Start Here

If you just want to use it and do not care about Python details, follow this section first.

### Windows: easiest install

1. Open the GitHub `Releases` page.
2. Download the latest Windows zip package.
3. Extract the zip to any normal folder, for example `D:\HimawariWallpaper`.
4. Double-click `Open Himawari Settings.bat`.
5. In the GUI, check `Config` and `Output`, then click `Run now`.
6. If you want it to update automatically after every login, enable `Enable startup at login`.

What the main files do:

- `Open Himawari Settings.bat`: opens the settings GUI
- `Run Himawari Once.bat`: downloads and generates once
- `Run Himawari Wallpaper.bat`: starts the continuous background updater
- `config.json`: stores your saved settings

Notes:

- The GUI saves to `config.json`, and the next launch reloads the same settings automatically.
- You can turn off `Apply wallpaper` if you only want the PNG files and prefer to set the wallpaper manually.
- On Windows, `Sync lock screen` is optional and may still depend on local Windows policy support.

### macOS / Linux: current situation

There is no self-contained macOS or Linux bundle yet.

If you are on macOS or Linux, use the Python setup in the `Developer / Python Setup` section below.

## For End Users

### What This Project Does

- Automatic Windows / macOS / Linux detection
- Cross-platform wallpaper application and login auto-start
- Optional download-only mode so users can decide whether to apply images manually
- Optional Windows lock-screen sync
- A simple GUI for common settings
- An installable CLI entry point
- Easier bootstrap scripts
- Baseline tests and CI

### Platform Support

The application detects the current platform automatically:

- Windows: uses `SystemParametersInfoW` and supports Startup-folder auto-start
- Windows lock screen sync: uses `UserProfilePersonalizationSettings` as an optional best-effort feature
- macOS: uses `osascript` and supports `LaunchAgents`
- Linux: tries `plasma-apply-wallpaperimage`, `gsettings`, `xfconf-query`, and `feh`, and supports `~/.config/autostart`

Notes:

- Linux desktop environments vary a lot, so the wallpaper backend is implemented as a capability-based fallback chain.
- If the current Linux desktop is unsupported, the program raises a clear error instead of failing silently.

### Common Commands

Refresh once:

```bash
himawari-wallpaper --once
```

Generate the PNG files only and let the user decide whether to apply them:

```bash
himawari-wallpaper --once --download-only
```

On Windows, sync the lock screen together with the wallpaper:

```bash
himawari-wallpaper --once --sync-lock-screen
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

Clean local app data, config, and startup entry:

```bash
himawari-wallpaper-cleanup --all
```

Use a custom output directory:

```bash
himawari-wallpaper --once --out ./data
```

Use a config file:

```bash
himawari-wallpaper --config ./config.json --once
```

Open the simple settings GUI:

```bash
himawari-wallpaper --gui
# or
himawari-wallpaper-gui
```

The GUI can save common settings, run one update, install or remove startup,
open the output folder, preview the latest generated wallpaper, show current startup status,
show the latest generated wallpaper file, run selectable local cleanup / uninstall actions,
install the optional browser fallback into the current environment, and test Windows lock-screen sync.
The layout is now compacted into a two-column screen with a more prominent `Run now`
primary action so common tasks fit on a normal desktop window more easily.
The action area is grouped into `Run` and `Environment` sections to keep everyday
actions separated from system-level tasks.
Startup is controlled with an `Enable startup at login` toggle in the GUI.
Windows-only lock-screen controls are disabled automatically on macOS and Linux.
The GUI also shows the detected current platform near the top of the window.
When the Windows release bundle is used, the GUI automatically reloads the bundled
`config.json` on the next launch instead of resetting to built-in defaults.
When the project root is available, the browser fallback button installs `.[browser]`;
otherwise it falls back to a direct Playwright package install for ordinary users.

## For Developers

### Python Setup

Conda is the recommended setup for source installs and development.

Recommended bootstrap:

```bash
python scripts/bootstrap.py
conda activate himawari-wallpaper
```

Create a conda environment explicitly with a custom name:

```bash
python scripts/bootstrap.py --manager conda --conda-env-name himawari-wallpaper
conda activate himawari-wallpaper
```

Create directly from the provided conda environment file:

```bash
conda env create -f environment.yml
conda activate himawari-wallpaper
```

### Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1
conda activate himawari-wallpaper
himawari-wallpaper --once
```

Windows venv fallback:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1 -UseVenv -VenvDir .venv
.\.venv\Scripts\Activate.ps1
himawari-wallpaper --once
```

### macOS / Linux

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
conda activate himawari-wallpaper
himawari-wallpaper --once
```

macOS / Linux venv fallback:

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh --venv-mode --venv .venv
source .venv/bin/activate
himawari-wallpaper --once
```

If you explicitly choose the venv fallback and see `ensurepip is not available` or `python3 -m venv` fails on Ubuntu / WSL, install:

```bash
sudo apt install python3-venv
```

Optional browser fallback setup, only if the pure HTTP path stops working upstream:

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

### Environment Variables

Supported runtime overrides:

- `HIMAWARI_CONFIG`
- `HIMAWARI_OUTPUT_DIR`
- `HIMAWARI_INTERVAL_SECONDS`
- `HIMAWARI_MAX_ZOOM`
- `HIMAWARI_EARTH_HEIGHT_RATIO`
- `HIMAWARI_Y_OFFSET_RATIO`
- `HIMAWARI_APPLY_WALLPAPER`
- `HIMAWARI_SYNC_LOCK_SCREEN`
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

The config file also supports behavior flags:

- `apply_wallpaper`
- `sync_lock_screen`

Current discovery fallback order:

1. Direct `latest.json` lookup for the latest `D531106` timestamp
2. Embedded HTML probe image URLs fetched over plain HTTP
3. Local cached probe metadata
4. Optional Playwright browser discovery

This keeps the default install lightweight while still preserving a browser-level recovery path when the upstream site changes.

Temporarily override network settings:

```bash
himawari-wallpaper --once --target-url https://himawari.asia/ --navigation-timeout-ms 120000 --warmup-wait-ms 15000
```

### Default Output Directories

If `--out` is not specified, the application uses a writable per-user location instead of writing into the source tree:

- Windows: `%LOCALAPPDATA%\HimawariDynamicWallpaper`
- macOS: `~/Library/Application Support/HimawariDynamicWallpaper`
- Linux: `$XDG_DATA_HOME/himawari-dynamic-wallpaper` or `~/.local/share/himawari-dynamic-wallpaper`

This is safer than writing inside an installed package directory.

### Linux Notes

Linux wallpaper application tries these backends in order:

- KDE Plasma: `plasma-apply-wallpaperimage`
- GNOME: `gsettings`
- XFCE: `xfconf-query`
- Generic fallback: `feh`

If none of these are available, image fetching and composition can still work, but wallpaper application will fail with a clear error.

WSL validation summary:

- A real `--once --download-only` smoke test generated `last_source_meta.json`, the original PNG, and the wallpaper PNG
- The HTTP-based `latest.json` path successfully resolved the latest `D531106` timestamp in WSL
- Optional Playwright fallback can still be installed later when browser-level discovery is needed
- `himawari.asia` can load slowly in WSL Chromium, so the default navigation timeout remains `120000ms` for the optional browser fallback
- Minimal Ubuntu / WSL installations may lack `python3-venv`, which affects the first run of `bootstrap.py` / `bootstrap.sh`
- WSL is not a full Linux desktop session, so the real desktop wallpaper backend itself was not validated there

If you want to add the optional browser fallback later:

```bash
python scripts/bootstrap.py --with-playwright
```

Or install it manually inside the active environment:

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

Linux / WSL smoke test without touching the desktop wallpaper:

```bash
himawari-wallpaper --once --download-only --out ./smoke-output
```

If you used conda, also remove the conda environment:

```bash
python scripts/uninstall.py --all --remove-conda-env himawari-wallpaper
```

### Legacy Entry Point

The legacy script entry point is still available:

```bash
python src/himawari_wallpaper_webzoom.py --once
```

The installed CLI is still the preferred way to run it:

```bash
himawari-wallpaper --once
```

### Windows Release Bundle

The Windows release bundle includes:

- `himawari-dynamic-wallpaper-gui.exe`
- `himawari-dynamic-wallpaper.exe`
- `himawari-dynamic-wallpaper-background.exe`
- `Run Himawari Wallpaper.bat` for continuous runs
- `Run Himawari Once.bat` for a one-shot refresh
- `Open Himawari Settings.bat` for reopening the GUI
- `config.example.json` and a ready-to-edit `config.json`
- `README.md` and `README.zh-CN.md`

This bundle is intended to be self-contained for ordinary Windows users.
The GUI is only the settings helper. The actual update logic runs through the bundled
runner executables, not through the GUI executable itself.
The `.bat` launchers call the packaged runner `.exe` files directly, so target machines
do not need a separate Python installation just to use the release bundle.

For Windows executable details, see [`docs/BUILD_WINDOWS_EXE.md`](docs/BUILD_WINDOWS_EXE.md).
