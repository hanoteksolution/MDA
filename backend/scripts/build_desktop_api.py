#!/usr/bin/env python
"""
Build standalone mda-api.exe for the Tauri desktop installer.

Output: backend/dist/mda-api-x86_64-pc-windows-msvc.exe
Target PCs do not need Python installed.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DIST = BACKEND / "dist"
BUILD = BACKEND / "build" / "pyinstaller"
SPEC_NAME = "mda-api"
TARGET_TRIPLE = "x86_64-pc-windows-msvc"

HIDDEN_IMPORTS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.db.backends.sqlite3",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "PIL",
    "PIL._imagingtk",
    "config.settings.desktop",
    "config.urls",
    "config.wsgi",
    "core",
    "core.pagination",
    "core.exceptions",
    "core.responses.api_response",
    "permissions.base",
    "apps.authentication",
    "apps.authentication.models",
    "apps.authentication.apps",
    "apps.authentication.serializers.auth_serializers",
    "apps.authentication.bootstrap",
    "apps.authentication.management.commands.bootstrap_system",
    "apps.authentication.management.commands.seed_data",
    "apps.authentication.services.setup_service",
    "apps.authentication.services.auth_service",
    "apps.authentication.services.staff_evaluation_service",
    "apps.authentication.models.staff_evaluation",
    "apps.settings_app",
    "apps.settings_app.models",
    "apps.settings_app.services.settings_service",
    "apps.audit",
    "apps.audit.models",
    "apps.products",
    "apps.products.models",
    "apps.products.serializers",
    "apps.inventory",
    "apps.inventory.models",
    "apps.inventory.serializers.inventory_serializers",
    "apps.inventory.services.inventory_service",
    "apps.customers",
    "apps.customers.models",
    "apps.customers.serializers.customer_serializers",
    "apps.customers.services.customer_service",
    "apps.suppliers",
    "apps.suppliers.models",
    "apps.purchases",
    "apps.purchases.models",
    "apps.sales",
    "apps.sales.models",
    "apps.sales.services.pos_service",
    "apps.sales.services.sales_service",
    "apps.platform",
    "apps.platform.models",
    "apps.platform.apps",
    "apps.platform.services.platform_service",
    "apps.platform.management.commands.bootstrap_platform",
    "core.services.analytics_service",
]


def _collect_api_modules() -> list[str]:
    """PyInstaller misses Django urlconf modules unless explicitly bundled."""
    modules: list[str] = []
    api_root = BACKEND / "api"
    for path in api_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.name not in {"urls.py", "views.py", "__init__.py"}:
            continue
        rel = path.relative_to(BACKEND).with_suffix("")
        modules.append(str(rel).replace("\\", "."))
    return sorted(set(modules))


def _migration_datas() -> list[tuple[str, str]]:
    datas: list[tuple[str, str]] = []
    seen: set[str] = set()
    for migrations_dir in BACKEND.rglob("migrations"):
        if not migrations_dir.is_dir() or "__pycache__" in migrations_dir.parts:
            continue
        rel = migrations_dir.relative_to(BACKEND)
        dest = str(rel).replace("\\", "/")
        if dest in seen:
            continue
        seen.add(dest)
        datas.append((str(migrations_dir), dest))
    return datas


def _django_datas() -> list[tuple[str, str]]:
    import django

    root = Path(django.__file__).resolve().parent
    datas: list[tuple[str, str]] = []
    for sub in (
        "contrib/admin",
        "contrib/admin/static",
        "contrib/admin/templates",
        "contrib/auth",
        "contrib/contenttypes",
        "contrib/sessions",
        "forms",
        "conf/locale",
    ):
        src = root / sub
        if src.exists():
            datas.append((str(src), str(Path("django") / sub)))
    return datas


def main() -> None:
    try:
        import PyInstaller.__main__
        from PyInstaller.utils.hooks import collect_all
    except ImportError:
        print("PyInstaller is required. Run: pip install -r backend/requirements/bundle.txt")
        sys.exit(1)

    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.desktop")

    DIST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    datas: list[tuple[str, str]] = []
    hiddenimports = list(HIDDEN_IMPORTS)
    hiddenimports.extend(_collect_api_modules())

    for pkg in ("rest_framework", "rest_framework_simplejwt", "corsheaders", "django_filters"):
        pkg_datas, pkg_hidden, _ = collect_all(pkg)
        datas.extend(pkg_datas)
        hiddenimports.extend(pkg_hidden)

    datas.extend(_django_datas())
    datas.extend(_migration_datas())

    sep = os.pathsep
    args = [
        str(BACKEND / "desktop_server.py"),
        "--name",
        SPEC_NAME,
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        f"--specpath={BUILD}",
        "--console",
        "--exclude-module",
        "django.contrib.gis",
    ]

    for src, dest in datas:
        args.extend(["--add-data", f"{src}{sep}{dest}"])

    for hidden in hiddenimports:
        args.extend(["--hidden-import", hidden])

    print("Running PyInstaller (this may take several minutes)...")
    PyInstaller.__main__.run(args)

    built = DIST / f"{SPEC_NAME}.exe"
    if not built.is_file():
        print(f"ERROR: expected output not found: {built}")
        sys.exit(1)

    target = DIST / f"{SPEC_NAME}-{TARGET_TRIPLE}.exe"
    shutil.copy2(built, target)
    print(f"Built portable API: {target}")
    print(f"Size: {target.stat().st_size / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    main()
