# AGENTS.md

## Project
This repository hosts a Himawari-based dynamic wallpaper project.
The likely responsibilities include image discovery, tile download, image stitching, wallpaper generation, scheduling, and Windows wallpaper application.

## Primary goals
1. Make the project stable and easy to run on Windows.
2. Refactor the codebase into small, testable modules.
3. Preserve the original behavior before making structural changes.
4. Add logging, configuration, retries, and graceful failure paths.
5. Prepare the project for GitHub collaboration and CI.

## High-priority engineering tasks
- Isolate network fetching from image assembly logic.
- Add timeout, retry, and fallback behavior for remote image fetching.
- Move hard-coded URLs, paths, and intervals into config.
- Add a CLI entrypoint.
- Separate platform-specific wallpaper setting logic.
- Add smoke tests for non-network core logic.
- Improve README and setup instructions.

## Constraints
- Keep the first pass conservative: prefer behavior-preserving refactors.
- Avoid introducing heavyweight dependencies unless clearly justified.
- Keep Windows compatibility.
- Never commit secrets, tokens, personal paths, or machine-specific credentials.

## Suggested target structure
- `src/` for source code
- `tests/` for tests
- `assets/` for icons/static resources
- `docs/` for migration notes and technical docs

## Definition of done for a refactor PR
- Code still runs locally
- Main entrypoint documented
- Basic tests added or updated
- README updated if commands changed
- No secrets or binary junk added
