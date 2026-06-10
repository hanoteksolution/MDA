#!/usr/bin/env python3
"""Restore MDA ERP database and media from a backup archive."""

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
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
DEFAULT_LOCAL_DIR = PROJECT_ROOT / "backups"
ARCHIVE_PREFIX = "mda_erp_backup_"


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


def list_backups(local_dir: Path, drive_dir: Path | None) -> list[Path]:
    seen: set[str] = set()
    backups: list[Path] = []
    for directory in (local_dir, drive_dir):
        if directory is None or not directory.exists():
            continue
        for backup_file in sorted(directory.glob(f"{ARCHIVE_PREFIX}*.zip"), reverse=True):
            if backup_file.name not in seen:
                seen.add(backup_file.name)
                backups.append(backup_file)
    return backups


def restore_sqlite(backup_db: Path, target: Path) -> None:
    if target.exists():
        backup_target = target.with_suffix(".sqlite3.bak")
        shutil.copy2(target, backup_target)
        print(f"Previous database saved to: {backup_target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    src_conn = sqlite3.connect(backup_db)
    try:
        dst_conn = sqlite3.connect(target)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


def restore_postgres(backup_db: Path, env: dict[str, str]) -> None:
    cmd = [
        "pg_restore",
        "-h",
        env.get("DB_HOST", "localhost"),
        "-p",
        env.get("DB_PORT", "5432"),
        "-U",
        env.get("DB_USER", "postgres"),
        "-d",
        env.get("DB_NAME", "mda_erp"),
        "--clean",
        "--if-exists",
        str(backup_db),
    ]
    run_env = {**os.environ, "PGPASSWORD": env.get("DB_PASSWORD", "")}
    try:
        subprocess.run(cmd, check=True, env=run_env, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("pg_restore not found. Install PostgreSQL client tools.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pg_restore failed: {exc.stderr or exc.stdout}") from exc


def restore_media(extracted_dir: Path, media_dir: Path) -> int:
    source = extracted_dir / "media"
    if not source.exists():
        return 0

    if media_dir.exists():
        backup_media = media_dir.with_name(f"{media_dir.name}.bak")
        if backup_media.exists():
            shutil.rmtree(backup_media)
        shutil.copytree(media_dir, backup_media)
        print(f"Previous media saved to: {backup_media}")

    if media_dir.exists():
        shutil.rmtree(media_dir)
    shutil.copytree(source, media_dir)

    return sum(1 for path in media_dir.rglob("*") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore MDA ERP from a backup archive.")
    parser.add_argument(
        "archive",
        nargs="?",
        help="Path to backup .zip (defaults to latest local or Drive backup)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Restore without confirmation",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available backups and exit",
    )
    args = parser.parse_args()

    env = load_env(BACKEND_DIR / ".env")
    local_dir = Path(env.get("BACKUP_LOCAL_DIR", "")).expanduser() if env.get("BACKUP_LOCAL_DIR") else DEFAULT_LOCAL_DIR
    drive_raw = env.get("GOOGLE_DRIVE_BACKUP_DIR", "").strip()
    drive_dir = Path(drive_raw).expanduser() if drive_raw else None

    backups = list_backups(local_dir, drive_dir)
    if args.list:
        if not backups:
            print("No backups found.")
            return 0
        for index, backup in enumerate(backups, start=1):
            print(f"{index}. {backup}")
        return 0

    if args.archive:
        archive_path = Path(args.archive).expanduser()
    elif backups:
        archive_path = backups[0]
        print(f"Using latest backup: {archive_path}")
    else:
        print("No backups found. Run: make backup", file=sys.stderr)
        return 1

    if not archive_path.exists():
        print(f"Backup not found: {archive_path}", file=sys.stderr)
        return 1

    if not args.yes:
        print("This will overwrite the current database and media files.")
        print("Stop the Django server before restoring.")
        answer = input("Continue? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Restore cancelled.")
            return 0

    with tempfile.TemporaryDirectory() as temp_dir:
        extracted = Path(temp_dir)
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(extracted)

        manifest_path = extracted / "manifest.json"
        if not manifest_path.exists():
            print("Invalid backup: manifest.json missing.", file=sys.stderr)
            return 1

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        db_engine = manifest.get("db_engine", "sqlite")
        db_name = manifest.get("database_file", "database.sqlite3")
        db_file = extracted / db_name
        if not db_file.exists():
            print(f"Invalid backup: database file missing ({db_name}).", file=sys.stderr)
            return 1

        if db_engine == "sqlite":
            restore_sqlite(db_file, BACKEND_DIR / "db.sqlite3")
            print("Database restored (SQLite).")
        else:
            restore_postgres(db_file, env)
            print("Database restored (PostgreSQL).")

        media_count = restore_media(extracted, BACKEND_DIR / "media")
        print(f"Media restored ({media_count} file(s)).")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
