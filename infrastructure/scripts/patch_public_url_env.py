#!/usr/bin/env python3
"""Merge domain from infrastructure/public-url.env into backend/.env.cloud on VPS."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from public_url_config import load_config  # noqa: E402

ENV_CLOUD = ROOT / "backend" / ".env.cloud"


def merge_line(text: str, key: str, values: str) -> str:
    parts: set[str] = set()
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.M)
    if match:
        parts.update(v.strip() for v in match.group(1).split(",") if v.strip())
    parts.update(v.strip() for v in values.split(",") if v.strip())
    line = f"{key}={','.join(sorted(parts))}"
    if match:
        return re.sub(rf"^{re.escape(key)}=.*$", line, text, flags=re.M)
    return text.rstrip() + "\n" + line + "\n"


def main() -> None:
    if not ENV_CLOUD.is_file():
        raise SystemExit(f"Missing {ENV_CLOUD}")

    cfg = load_config()
    text = ENV_CLOUD.read_text(encoding="utf-8")
    text = merge_line(text, "ALLOWED_HOSTS", cfg["allowed_hosts"])
    text = merge_line(text, "CORS_ALLOWED_ORIGINS", cfg["cors_origins"])
    ENV_CLOUD.write_text(text, encoding="utf-8")
    print(f"Patched {ENV_CLOUD.name} for host {cfg['host']}")


if __name__ == "__main__":
    main()
