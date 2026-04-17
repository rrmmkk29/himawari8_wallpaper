# Build Windows EXE

This document covers the Windows-only GUI bundle that is intended for end users who do not want to install Python manually.

## What It Produces

The Windows bundle script creates a zip archive in `release/` that contains:

- `himawari-dynamic-wallpaper-gui.exe`
- `README.md`
- `README.zh-CN.md`
- `config.example.json`
- `config.json`

`config.json` is generated from `config.example.json` so a user can edit it directly after extracting the release package.

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
5. Verify the generated `.exe` manually on a clean Windows machine if possible.
6. Push tag `vX.Y.Z` so GitHub Actions can publish the same artifact in CI.

## Cleanup

To remove local app data, config, and startup entries after testing:

```bash
himawari-wallpaper-cleanup --all
```
