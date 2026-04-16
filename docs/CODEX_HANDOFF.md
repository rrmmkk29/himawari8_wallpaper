# 给 Codex 的交接说明

下面这段可以直接贴给 Codex：

---

Please inspect this repository and help me refactor it conservatively.

Goals:
1. Preserve current behavior.
2. Split the code into small modules.
3. Add clear configuration points for URLs, cache paths, and timing.
4. Improve error handling, logging, retries, and testability.
5. Prepare the project for reliable GitHub maintenance.

Please do the work in stages:
- Stage 1: explain the current architecture and risks.
- Stage 2: propose a refactor plan.
- Stage 3: implement the smallest safe structural improvements.
- Stage 4: add tests for non-network logic.
- Stage 5: improve README and developer docs.

Important constraints:
- Keep Windows compatibility.
- Avoid unnecessary dependencies.
- Do not rewrite everything at once.
- Prefer small PR-style changes.

Also check for:
- hard-coded paths
- brittle network code
- duplicated logic
- places suitable for CLI/config extraction
- hidden packaging or deployment problems

---

## 第二轮可继续给 Codex 的任务

- Add typed configuration loading.
- Add image stitching unit tests.
- Expand Linux desktop-environment wallpaper backends.
- Move network retry policy into explicit config.
- Add release packaging and smoke-test commands for each OS.
