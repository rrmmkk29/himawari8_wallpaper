from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "possible_api_key": re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    "windows_user_path": re.compile(r"[A-Za-z]:\\Users\\[^\\]+\\"),
}

for file in ROOT.rglob("*"):
    if not file.is_file():
        continue
    if file.suffix.lower() in {".png", ".jpg", ".jpeg", ".zip", ".ico", ".exe"}:
        continue
    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for name, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            print(f"[{name}] {file}: {m.group(0)[:120]}")
