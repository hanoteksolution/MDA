#!/usr/bin/env python3
"""Inspect VPS tenant_subscriptions schema."""
import subprocess

HOST = "safari-server"
DOCKER = (
    "cd /opt/mda/infrastructure/docker && "
    "docker compose -f docker-compose.yml -f docker-compose.vps.yml"
)

subprocess.run(
    [
        "ssh",
        HOST,
        f'{DOCKER} exec -T db psql -U mda -d mda_erp -c '
        f'"SELECT column_name FROM information_schema.columns '
        f"WHERE table_name = 'tenant_subscriptions' ORDER BY 1;\"",
    ],
    check=False,
)
subprocess.run(
    [
        "ssh",
        HOST,
        f'{DOCKER} exec -T db psql -U mda -d mda_erp -c '
        f'"SELECT indexname FROM pg_indexes WHERE tablename = \'tenant_subscriptions\';"',
    ],
    check=False,
)
