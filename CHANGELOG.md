# Changelog

## Unreleased
- No unreleased changes yet.

## 0.2.5
- Switched the Windows release bundle to a self-contained layout with bundled runner executables for the real update workflow.
- Kept the GUI as a settings helper while routing bundled `.bat` launchers and startup entries to runner executables instead of relying on a target-machine Python install.
- Updated the Windows bundle build documentation to match the new self-contained release structure.
- Reorganized both READMEs so ordinary end users see simplified install and usage instructions first, with Python and conda setup moved into developer-focused sections.

## 0.2.4
- Reworked the desktop GUI into a more compact two-column layout with a clearer primary `Run now` action.
- Added bundled-config auto-loading so the Windows GUI reopens with the saved `config.json` instead of resetting to defaults.
- Changed the Windows bundle layout so the GUI is only a settings helper while packaged Python source files, launcher scripts, and `.bat` entrypoints run the real updater logic.

## 0.2.3
- Added vertical scrolling support to the desktop GUI so smaller windows can still access the full settings form.
- Limited generated `lockscreen_*.png` files to the latest 24 items, matching the wallpaper retention model more closely.

## 0.2.2
- Improved Windows lock screen sync by staging normalized local image files and adding an official `LockScreen.SetImageFileAsync(...)` fallback when `UserProfilePersonalizationSettings` is rejected.

## 0.2.1
- Fixed package metadata so editable installs and local release builds work with newer `setuptools`.

## 0.2.0
- Switched the primary image discovery path to pure HTTP with `latest.json`, HTML probe, and cached probe fallbacks.
- Kept Playwright as an optional browser fallback instead of a required default dependency.
- Moved Playwright into the optional `.[browser]` extra and simplified default conda/bootstrap setup.
- Added a GUI button to install the optional browser fallback for ordinary users.
- Updated English and Chinese documentation to match the new install and fallback behavior.
- Expanded tests for HTTP discovery, bootstrap extras, and GUI install helpers.

## 0.1.0
- Refactored the original script into a package with a documented CLI entrypoint.
- Added automatic Windows / macOS / Linux platform detection and wallpaper backends.
- Added login auto-start support for Windows, macOS, and Linux.
- Added JSON config support, environment-variable overrides, and safer per-user output paths.
- Added download-only mode for users who want images without automatic wallpaper changes.
- Added optional Windows lock-screen sync.
- Added a simple GUI for common settings, one-shot runs, startup management, preview, and testing.
- Improved first-run discovery with retries, HTML probe fallback, `latest.json` fallback, and cache probing.
- Added repository self-checks, test coverage, CI, source release packaging, and Windows GUI bundle packaging.
