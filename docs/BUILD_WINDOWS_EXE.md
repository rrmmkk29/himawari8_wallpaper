# Build Windows EXE

This document covers the Windows-only bundle that is intended for end users who want
the GUI and the Python application files packaged together.
The GUI executable is only the settings front end. The actual updater runs through
the packaged Python source files and launcher scripts included in the same archive.

## What It Produces

The Windows bundle script creates a zip archive in `release/` that contains:

- `himawari-dynamic-wallpaper-gui.exe`
- `src/`
- `run_himawari.py`
- `Run Himawari Wallpaper.bat`
- `Run Himawari Once.bat`
- `Open Himawari Settings.bat`
- `README.md`
- `README.zh-CN.md`
- `config.example.json`
- `config.json`

`config.json` is generated from `config.example.json` so a user can edit it directly after extracting the release package.
When the GUI is reopened from the release bundle, it automatically reloads that
same `config.json`.

`Run Himawari Wallpaper.bat` and the generated startup entry call `python` or
`pythonw.exe` and then execute `run_himawari.py`. They do not route the actual
update logic through the GUI executable.

## Local Build

From the repository root:

```bash
python -m pip install -e ".[release]"
python scripts/build_windows_bundle.py --label local
```

The resulting archive will be written into `release/`.

Conda is the preferred environment manager for this repository. Create and
activate the conda environment first, then run the same commands.

## Optional Icon

If you want the executable to use a custom icon, place an `.ico` file here:

`assets/windows/app.ico`

The build script detects that file automatically and passes it to PyInstaller.

## Version Metadata

The build script generates a Windows version-info resource from `pyproject.toml` and injects it into the executable.

It currently uses:

- project `name`
- project `version`
- project `description`
- the first author `name`

If you want cleaner Windows file properties, update the metadata in [`pyproject.toml`](../pyproject.toml) before publishing.

## Recommended Release Flow

1. Update `pyproject.toml` version.
2. Update `CHANGELOG.md`.
3. Run `python scripts/repo_check.py`.
4. Run `python scripts/build_windows_bundle.py --label vX.Y.Z`.
5. Verify the generated GUI, bundled `config.json`, and `.bat` launchers manually on a clean Windows machine if possible.
6. Push tag `vX.Y.Z` so GitHub Actions can publish the same artifact in CI.

## Cleanup

To remove local app data, config, and startup entries after testing:

```bash
himawari-wallpaper-cleanup --all
```
