#!/usr/bin/env python3
"""Create MDA ERP backups and copy to a Google Drive sync folder."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
DEFAULT_LOCAL_DIR = PROJECT_ROOT / "backups"
ARCHIVE_PREFIX = "mda_erp_backup_"
DEFAULT_RETENTION_DAYS = 30


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def detect_db_engine(env: dict[str, str]) -> tuple[str, Path | None]:
    sqlite_path = BACKEND_DIR / "db.sqlite3"
    if sqlite_path.exists():
        return "sqlite", sqlite_path
    return "postgresql", None


def backup_sqlite(db_path: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = dest / "database.sqlite3"
    src_conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst_conn = sqlite3.connect(out)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    return out


def backup_postgres(env: dict[str, str], dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "database.dump"
    cmd = [
        "pg_dump",
        "-h",
        env.get("DB_HOST", "localhost"),
        "-p",
        env.get("DB_PORT", "5432"),
        "-U",
        env.get("DB_USER", "postgres"),
        "-d",
        env.get("DB_NAME", "mda_erp"),
        "-F",
        "c",
        "-f",
        str(out),
    ]
    run_env = {**os.environ, "PGPASSWORD": env.get("DB_PASSWORD", "")}
    try:
        subprocess.run(cmd, check=True, env=run_env, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pg_dump not found. Install PostgreSQL client tools or use SQLite in development."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pg_dump failed: {exc.stderr or exc.stdout}") from exc
    return out


def create_archive(
    work_dir: Path,
    db_engine: str,
    db_file: Path,
    media_dir: Path,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = work_dir / f"{ARCHIVE_PREFIX}{timestamp}.zip"
    manifest = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "db_engine": db_engine,
        "database_file": db_file.name,
    }

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.write(db_file, db_file.name)
        if media_dir.exists():
            for file_path in media_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(
                        file_path,
                        f"media/{file_path.relative_to(media_dir).as_posix()}",
                    )
    return archive_path


def prune_old_backups(directory: Path, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for backup_file in directory.glob(f"{ARCHIVE_PREFIX}*.zip"):
        modified = datetime.fromtimestamp(backup_file.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            backup_file.unlink()
            removed += 1
    return removed


def copy_to_drive(archive_path: Path, drive_dir: Path) -> Path:
    drive_dir.mkdir(parents=True, exist_ok=True)
    destination = drive_dir / archive_path.name
    shutil.copy2(archive_path, destination)
    return destination


def resolve_path(raw: str, default: Path) -> Path:
    if raw.strip():
        return Path(raw).expanduser()
    return default


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup MDA ERP database and media.")
    parser.add_argument(
        "--no-drive",
        action="store_true",
        help="Skip copying backup to GOOGLE_DRIVE_BACKUP_DIR",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help="Delete backups older than N days (default: BACKUP_RETENTION_DAYS or 30)",
    )
    args = parser.parse_args()

    env = load_env(BACKEND_DIR / ".env")
    retention_days = args.retention_days or int(
        env.get("BACKUP_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)
    )
    local_dir = resolve_path(env.get("BACKUP_LOCAL_DIR", ""), DEFAULT_LOCAL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)

    media_dir = BACKEND_DIR / "media"
    db_engine, sqlite_path = detect_db_engine(env)

    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)
        if db_engine == "sqlite":
            assert sqlite_path is not None
            db_file = backup_sqlite(sqlite_path, work_dir)
        else:
            db_file = backup_postgres(env, work_dir)

        archive_path = create_archive(work_dir, db_engine, db_file, media_dir)
        local_copy = local_dir / archive_path.name
        shutil.copy2(archive_path, local_copy)

    print(f"Local backup: {local_copy}")

    if not args.no_drive:
        drive_raw = env.get("GOOGLE_DRIVE_BACKUP_DIR", "").strip()
        if drive_raw:
            drive_dir = Path(drive_raw).expanduser()
            if not drive_dir.exists():
                print(
                    f"Warning: GOOGLE_DRIVE_BACKUP_DIR does not exist: {drive_dir}",
                    file=sys.stderr,
                )
            else:
                drive_copy = copy_to_drive(local_copy, drive_dir)
                print(f"Google Drive copy: {drive_copy}")
        else:
            print(
                "Tip: Set GOOGLE_DRIVE_BACKUP_DIR in backend/.env to sync backups to Google Drive.",
                file=sys.stderr,
            )

    removed_local = prune_old_backups(local_dir, retention_days)
    if removed_local:
        print(f"Pruned {removed_local} old local backup(s)")

    drive_raw = env.get("GOOGLE_DRIVE_BACKUP_DIR", "").strip()
    if drive_raw and not args.no_drive:
        drive_dir = Path(drive_raw).expanduser()
        if drive_dir.exists():
            removed_drive = prune_old_backups(drive_dir, retention_days)
            if removed_drive:
                print(f"Pruned {removed_drive} old Google Drive backup(s)")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
