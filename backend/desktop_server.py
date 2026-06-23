#!/usr/bin/env python
"""
MDA ERP local API server for the desktop app.

Runs migrations, bootstraps roles/permissions, then serves on 127.0.0.1:8000.
First-time superuser and company are created via the in-app setup wizard.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_environment() -> Path:
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        os.chdir(bundle_dir)
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))
    else:
        backend_dir = Path(__file__).resolve().parent
        os.chdir(backend_dir)
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.desktop")

    data_dir = Path(os.environ.get("MDA_DATA_DIR", Path.cwd()))
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MDA_DATA_DIR"] = str(data_dir)
    return data_dir


def _ensure_initialized(data_dir: Path) -> None:
    import django

    django.setup()

    from django.core.management import call_command

    call_command("migrate", "--noinput", verbosity=0)

    marker = data_dir / ".bootstrapped"
    if not marker.exists():
        call_command("bootstrap_system", verbosity=0)
        marker.write_text("ok", encoding="utf-8")


def main() -> None:
    data_dir = _configure_environment()
    try:
        _ensure_initialized(data_dir)

        from django.conf import settings
        from django.core.management import execute_from_command_line

        host = getattr(settings, "API_HOST", "127.0.0.1")
        port = getattr(settings, "API_PORT", 8000)
        execute_from_command_line(
            [sys.argv[0], "runserver", f"{host}:{port}", "--noreload", "--insecure"]
        )
    except Exception:
        import traceback

        log_path = data_dir / "mda-api-error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
