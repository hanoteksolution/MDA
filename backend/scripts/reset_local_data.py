#!/usr/bin/env python
"""Delete local MDA SQLite databases so the setup wizard runs on next launch."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

PATHS = [
    BACKEND / "db.sqlite3",
    Path(os.environ.get("APPDATA", "")) / "com.mda.erp",
]

PROCESS_NAMES = ("mda-api", "mda-erp-desktop")


def kill_processes() -> None:
    if sys.platform == "win32":
        for name in PROCESS_NAMES:
            subprocess.run(
                ["taskkill", "/F", "/IM", f"{name}.exe"],
                capture_output=True,
                check=False,
            )
        # Dev backend on port 8000 (python runserver)
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                if ":8000" in line and "LISTENING" in line:
                    pid = line.split()[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, check=False)
        except Exception:
            pass
    else:
        for name in PROCESS_NAMES:
            subprocess.run(["pkill", "-f", name], capture_output=True, check=False)


def wipe(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file():
        path.unlink()
        print(f"Removed {path}")
        return
    shutil.rmtree(path)
    print(f"Removed {path}/")


def main() -> int:
    print("Stopping MDA API / desktop processes...")
    kill_processes()
    print("Wiping local MDA databases and app data...")
    for path in PATHS:
        if path.parts and path.parts[-1] == "com.mda.erp" and not path.parent.exists():
            continue
        wipe(path)
    print()
    print("Done. Next steps:")
    print("  1. If using the INSTALLED desktop app: run make build-desktop and reinstall.")
    print("  2. If using dev mode: run make dev (no rebuild needed).")
    print("  3. Open the app — you should see the setup wizard.")
    print("  4. If you still see the old login, clear browser/app storage (access_token).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
