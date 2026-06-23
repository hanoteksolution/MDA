#!/usr/bin/env python3
"""Read MDA_PUBLIC_URL from infrastructure/public-url.env."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "infrastructure" / "public-url.env"
DEFAULT_HOST = "88.222.220.238"
DEFAULT_PORT = 8010
DEFAULT_SCHEME = "http"


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_config() -> dict[str, str]:
    env = _parse_env_file(ENV_FILE)
    raw = (env.get("MDA_PUBLIC_URL") or "").strip().rstrip("/")
    if not raw:
        raw = f"{DEFAULT_SCHEME}://{DEFAULT_HOST}:{DEFAULT_PORT}"

    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname or DEFAULT_HOST
    scheme = parsed.scheme or DEFAULT_SCHEME

    if parsed.port:
        public_url = f"{scheme}://{host}:{parsed.port}".rstrip("/")
    elif host == DEFAULT_HOST:
        public_url = f"{scheme}://{host}:{DEFAULT_PORT}".rstrip("/")
    else:
        public_url = f"{scheme}://{host}".rstrip("/")
    api_url = f"{public_url}/api/v1"

    hosts = {host, DEFAULT_HOST, "localhost", "127.0.0.1"}
    cors = {
        public_url,
        f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://tauri.localhost",
        "http://tauri.localhost",
    }
    if host != DEFAULT_HOST:
        cors.add(f"http://{host}:{DEFAULT_PORT}")
        cors.add(f"https://{host}")

    return {
        "public_url": public_url,
        "api_url": api_url,
        "host": host,
        "allowed_hosts": ",".join(sorted(hosts)),
        "cors_origins": ",".join(sorted(cors)),
    }


def main() -> None:
    cfg = load_config()
    if len(sys.argv) < 2:
        print(cfg["public_url"])
        return
    flag = sys.argv[1]
    mapping = {
        "--public-url": "public_url",
        "--api-url": "api_url",
        "--host": "host",
        "--allowed-hosts": "allowed_hosts",
        "--cors-origins": "cors_origins",
    }
    key = mapping.get(flag)
    if not key:
        print(f"Unknown flag: {flag}", file=sys.stderr)
        sys.exit(1)
    print(cfg[key])


if __name__ == "__main__":
    main()
