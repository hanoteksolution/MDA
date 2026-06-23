#!/bin/bash
set -e
cd /opt/mda/infrastructure/docker
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.vps.yml"

$COMPOSE exec -T db psql -U mda -d mda_erp <<'SQL'
DROP INDEX IF EXISTS tenant_subscriptions_reference_code_3c461680_like;
DROP INDEX IF EXISTS tenant_subscriptions_reference_code_key;
DROP INDEX IF EXISTS tenant_subscriptions_reference_code_3c461680;
SQL

$COMPOSE exec -T api python manage.py migrate platform --settings=config.settings.production
$COMPOSE exec -T api python manage.py bootstrap_platform --settings=config.settings.production
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8010/api/v1/health/
