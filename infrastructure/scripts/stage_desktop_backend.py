#!/usr/bin/env python
"""Copy backend into desktop/backend-resource for Tauri bundling (excludes venv, DB, caches)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend"
DEST = ROOT / "desktop" / "backend-resource"

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "venv",
    ".venv",
    "media",
    "staticfiles",
    "dist",
    "build",
}
SKIP_FILES = {".env", "db.sqlite3"}


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    return path.name in SKIP_FILES


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    for item in SRC.rglob("*"):
        rel = item.relative_to(SRC)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if item.name in SKIP_FILES:
            continue
        target = DEST / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)

    print(f"Staged backend for desktop: {DEST}")


if __name__ == "__main__":
    main()
