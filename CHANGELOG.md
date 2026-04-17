# Changelog

## Unreleased
- No unreleased changes yet.

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
