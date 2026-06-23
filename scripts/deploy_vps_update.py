#!/usr/bin/env python3
"""Upload backend + web UI + infrastructure to VPS without overwriting .env secrets.

Windows-safe: remote steps run via a uploaded bash script with ssh -T (no interactive shell).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "safari-server"
REMOTE_ROOT = "/opt/mda"
VPS_HOST = "88.222.220.238"
API_PORT = 8010
WEB_PORT = 8010

SSH_OPTS = ["-T", "-o", "RequestTTY=no", "-o", "LogLevel=ERROR"]

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".git",
    "dist",
    "build",
    "venv",
    ".venv",
    "media",
}
SKIP_FILES = {"db.sqlite3", ".env", ".env.local", ".env.cloud"}


def load_public_urls() -> dict[str, str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from public_url_config import load_config

    return load_config()


def should_skip(rel: Path) -> bool:
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if rel.name in SKIP_FILES:
        return True
    return rel.suffix in {".pyc", ".pyo"}


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None, check: bool = True) -> None:
    """Run a command without shell (safe quoting on Windows)."""
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=check, cwd=cwd, env=env, shell=False)


def build_frontend() -> None:
    print(f"Building web UI (same-origin API: /api/v1)...")
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = "/api/v1"
    cwd = ROOT / "frontend"
    if os.name == "nt":
        # npm is a .cmd shim on Windows — needs shell
        subprocess.run("npm run build", check=True, cwd=cwd, env=env, shell=True)
    else:
        run(["npm", "run", "build"], cwd=cwd, env=env)


def build_archive() -> Path:
    dist = ROOT / "frontend" / "dist"
    if not dist.is_dir() or not any(dist.iterdir()):
        build_frontend()

    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    tmp.close()
    archive_path = Path(tmp.name)
    with tarfile.open(archive_path, "w:gz") as tar:
        for root_name in ("backend", "infrastructure", "scripts"):
            root = ROOT / root_name
            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(ROOT)
                if should_skip(rel):
                    continue
                tar.add(file_path, arcname=str(rel).replace("\\", "/"))

        for file_path in dist.rglob("*"):
            if file_path.is_file():
                rel = file_path.relative_to(ROOT)
                tar.add(file_path, arcname=str(rel).replace("\\", "/"))
    return archive_path


def remote_deploy_commands() -> list[str]:
    compose = (
        "docker compose -f docker-compose.yml -f docker-compose.vps.yml"
    )
    return [
        f"cd {REMOTE_ROOT}",
        "tar -xzf mda-deploy.tar.gz",
        "rm -f mda-deploy.tar.gz",
        f"python3 {REMOTE_ROOT}/infrastructure/scripts/patch_public_url_env.py",
        "cd infrastructure/docker",
        f"{compose} up -d --build",
        f"{compose} exec -T api python manage.py migrate --settings=config.settings.production",
        f"{compose} exec -T api python manage.py bootstrap_system --settings=config.settings.production",
        f"{compose} exec -T api python manage.py bootstrap_platform --settings=config.settings.production",
        f"{compose} restart api",
        f"curl -s -o /dev/null -w 'API HTTP %{{http_code}}\\n' http://127.0.0.1:{WEB_PORT}/api/v1/health/",
        f"curl -s -o /dev/null -w 'WEB HTTP %{{http_code}}\\n' http://127.0.0.1:{WEB_PORT}/",
    ]


def run_remote_script(commands: list[str]) -> None:
    """Upload a bash script and execute it — avoids Windows SSH quoting / interactive TTY issues."""
    script_body = "#!/usr/bin/env bash\nset -euo pipefail\n" + "\n".join(commands) + "\n"
    fd, script_path = tempfile.mkstemp(suffix=".sh", text=True)
    os.close(fd)
    local_script = Path(script_path)
    remote_script = f"{REMOTE_ROOT}/.mda-deploy-run.sh"

    try:
        local_script.write_text(script_body, encoding="utf-8", newline="\n")
        run(["scp", "-q", str(local_script), f"{REMOTE}:{remote_script}"])
        run(["ssh", *SSH_OPTS, REMOTE, f"bash {remote_script}"])
    finally:
        local_script.unlink(missing_ok=True)
        run(["ssh", *SSH_OPTS, REMOTE, f"rm -f {remote_script}"], check=False)


def main() -> None:
    urls = load_public_urls()
    archive = build_archive()
    print(f"Built archive: {archive} ({archive.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"Public URL: {urls['public_url']}")
    try:
        run(["scp", "-q", str(archive), f"{REMOTE}:{REMOTE_ROOT}/mda-deploy.tar.gz"])
        run_remote_script(remote_deploy_commands())
        print("\n=== VPS UPDATE COMPLETE ===")
        print(f"Web app (browser): {urls['public_url']}")
        print(f"API: {urls['api_url']}")
        if urls["host"] != VPS_HOST:
            print(f"\nDNS: point {urls['host']} A record → {VPS_HOST}")
    finally:
        archive.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Deploy failed (exit {exc.returncode}).", file=sys.stderr)
        sys.exit(exc.returncode or 1)
    except OSError as exc:
        print(f"Deploy failed: {exc}", file=sys.stderr)
        sys.exit(1)
