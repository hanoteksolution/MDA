#!/usr/bin/env bash
# Re-register MDA under Hostinger Docker Manager as project "mda" (compose at project root).
set -euo pipefail

ROOT=/home/ubuntu/projects/mda
cd "$ROOT"

# Stop old generic "docker" project (nested compose folder)
if [ -f infrastructure/docker/docker-compose.yml ]; then
  (cd infrastructure/docker && docker compose -p docker -f docker-compose.yml -f docker-compose.vps.yml down) || true
fi

# Re-use existing database/media volumes from the old "docker" project
cat > docker-compose.volumes.yml <<'EOF'
name: mda
volumes:
  mda_pgdata:
    external: true
    name: docker_mda_pgdata
  mda_media:
    external: true
    name: docker_mda_media
EOF

docker compose -f docker-compose.yml -f docker-compose.vps.yml -f docker-compose.volumes.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.vps.yml -f docker-compose.volumes.yml exec -T api python manage.py migrate --settings=config.settings.production

curl -s -o /dev/null -w "health HTTP %{http_code}\n" http://127.0.0.1:8010/api/v1/health/
docker compose -f docker-compose.yml -f docker-compose.vps.yml ps

echo "MDA is now Docker project: mda (visible in Hostinger Docker Manager)"
