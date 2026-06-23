#!/usr/bin/env python3
"""Fix partial platform migration on VPS and complete deploy."""
from __future__ import annotations

import subprocess
import sys

HOST = "safari-server"
DOCKER = (
    "cd /opt/mda/infrastructure/docker && "
    "docker compose -f docker-compose.yml -f docker-compose.vps.yml"
)


def ssh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ ssh {HOST} {cmd[:80]}...")
    return subprocess.run(["ssh", HOST, cmd], check=check)


def main() -> None:
    inspect = (
        "SELECT indexname FROM pg_indexes WHERE tablename = 'tenant_subscriptions'; "
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'tenant_subscriptions' ORDER BY 1;"
    )
    ssh(f'{DOCKER} exec -T db psql -U mda -d mda_erp -c "{inspect}"', check=False)

    sql = (
        "DROP INDEX IF EXISTS tenant_subscriptions_reference_code_3c461680_like; "
        "DROP INDEX IF EXISTS tenant_subscriptions_reference_code_key; "
        "DROP INDEX IF EXISTS tenant_subscriptions_reference_code_3c461680; "
        "DROP INDEX IF EXISTS tenant_subscriptions_reference_code_like; "
        "DROP INDEX IF EXISTS tenant_subscriptions_tenant_id_key;"
    )
    ssh(f'{DOCKER} exec -T db psql -U mda -d mda_erp -c "{sql}"')
    ssh(f"{DOCKER} exec -T api python manage.py migrate --settings=config.settings.production")
    ssh(f"{DOCKER} exec -T api python manage.py bootstrap_platform --settings=config.settings.production")
    result = ssh(
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8010/api/v1/health/",
        check=False,
    )
    code = result.stdout.decode().strip() if result.stdout else "?"
    print(f"\nHealth check: HTTP {code}")
    if code != "200":
        sys.exit(1)
    print("VPS migration fix complete.")


if __name__ == "__main__":
    main()
