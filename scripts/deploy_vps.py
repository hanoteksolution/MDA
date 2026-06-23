#!/usr/bin/env python3
"""One-shot deploy of MDA ERP API to Hostinger VPS via SFTP + SSH."""
from __future__ import annotations

import os
import secrets
import sys
import tarfile
import tempfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
REMOTE_ROOT = "/opt/mda"
API_PORT = 8010
DB_TUNNEL_PORT = 5437

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
SKIP_FILES = {
    "db.sqlite3",
    ".env",
    ".env.local",
}


def should_skip(rel: Path) -> bool:
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if rel.name in SKIP_FILES:
        return True
    if rel.suffix in {".pyc", ".pyo"}:
        return True
    return False


def build_archive() -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    tmp.close()
    archive_path = Path(tmp.name)
    include_roots = ["backend", "infrastructure"]
    with tarfile.open(archive_path, "w:gz") as tar:
        for root_name in include_roots:
            root = ROOT / root_name
            if not root.is_dir():
                continue
            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(ROOT)
                if should_skip(rel):
                    continue
                tar.add(file_path, arcname=str(rel).replace("\\", "/"))
    return archive_path


def run_remote(ssh: paramiko.SSHClient, command: str, check: bool = True) -> str:
    print(f"$ {command}")
    _, stdout, stderr = ssh.exec_command(command, get_pty=True)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if out.strip():
        print(out.rstrip().encode("ascii", errors="replace").decode("ascii"))
    if err.strip():
        print(err.rstrip().encode("ascii", errors="replace").decode("ascii"), file=sys.stderr)
    exit_code = stdout.channel.recv_exit_status()
    if check and exit_code != 0:
        raise RuntimeError(f"Command failed ({exit_code}): {command}")
    return out


def main() -> None:
    password = os.environ.get("MDA_VPS_PASSWORD")
    if not password:
        print("Set MDA_VPS_PASSWORD environment variable.", file=sys.stderr)
        sys.exit(1)

    secret_key = secrets.token_urlsafe(48)
    db_password = secrets.token_urlsafe(24)

    env_cloud = f"""SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS=88.222.220.238,localhost,127.0.0.1
DB_NAME=mda_erp
DB_USER=mda
DB_PASSWORD={db_password}
DB_HOST=db
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://88.222.220.238:{API_PORT},http://localhost:5173,https://tauri.localhost,http://tauri.localhost
"""

    archive = build_archive()
    print(f"Built archive: {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MB)")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("88.222.220.238", username="root", password=password, timeout=60)

    try:
        run_remote(ssh, f"mkdir -p {REMOTE_ROOT}")
        sftp = ssh.open_sftp()
        remote_archive = f"{REMOTE_ROOT}/mda-deploy.tar.gz"
        print(f"Uploading to {remote_archive}...")
        sftp.put(str(archive), remote_archive)
        sftp.close()

        run_remote(ssh, f"cd {REMOTE_ROOT} && tar -xzf mda-deploy.tar.gz && rm mda-deploy.tar.gz")
        run_remote(ssh, f"mkdir -p {REMOTE_ROOT}/backend")
        run_remote(ssh, f"mkdir -p {REMOTE_ROOT}/infrastructure/docker")
        run_remote(
            ssh,
            f"cat > {REMOTE_ROOT}/backend/.env.cloud << 'ENVEOF'\n{env_cloud}ENVEOF",
        )
        docker_env = f"DB_NAME=mda_erp\nDB_USER=mda\nDB_PASSWORD={db_password}\n"
        run_remote(
            ssh,
            f"cat > {REMOTE_ROOT}/infrastructure/docker/.env << 'ENVEOF'\n{docker_env}ENVEOF",
        )

        run_remote(ssh, f"ufw allow {API_PORT}/tcp || true")

        compose = (
            f"cd {REMOTE_ROOT}/infrastructure/docker && "
            "docker compose -f docker-compose.yml -f docker-compose.vps.yml "
            "up -d --build"
        )
        run_remote(ssh, compose, check=False)

        migrate_cmds = [
            f"cd {REMOTE_ROOT}/infrastructure/docker && docker compose -f docker-compose.yml -f docker-compose.vps.yml exec -T api python manage.py migrate --settings=config.settings.production",
            f"cd {REMOTE_ROOT}/infrastructure/docker && docker compose -f docker-compose.yml -f docker-compose.vps.yml exec -T api python manage.py bootstrap_system --settings=config.settings.production",
            f"cd {REMOTE_ROOT}/infrastructure/docker && docker compose -f docker-compose.yml -f docker-compose.vps.yml exec -T api python manage.py bootstrap_platform --settings=config.settings.production",
        ]
        for cmd in migrate_cmds:
            run_remote(ssh, cmd, check=False)

        health = run_remote(
            ssh,
            f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{API_PORT}/api/v1/health/ || true",
            check=False,
        ).strip()

        print("\n=== DEPLOY SUMMARY ===")
        print(f"API URL:      http://88.222.220.238:{API_PORT}/api/v1")
        print(f"Health:       http://88.222.220.238:{API_PORT}/api/v1/health/ (HTTP {health})")
        print(f"DB tunnel:    ssh -L {DB_TUNNEL_PORT}:127.0.0.1:{DB_TUNNEL_PORT} root@88.222.220.238")
        print(f"DB name/user: mda_erp / mda")
        print(f"DB password:  {db_password}")
        print(f"SECRET_KEY:   {secret_key}")
        print("Save the DB password and SECRET_KEY securely.")
    finally:
        ssh.close()
        archive.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
