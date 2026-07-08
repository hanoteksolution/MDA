#!/usr/bin/env bash
set -euo pipefail

NEW=/home/ubuntu/projects/mda
OLD=/opt/mda

mkdir -p /home/ubuntu/projects

if [ ! -d "$NEW/backend" ]; then
  cp -a "$OLD" "$NEW"
  echo "Copied $OLD to $NEW"
else
  rsync -a --exclude backend/.env.cloud "$OLD/" "$NEW/"
  echo "Synced $OLD to $NEW"
fi

if [ -d "$OLD/infrastructure/docker" ]; then
  cd "$OLD/infrastructure/docker"
  docker compose -f docker-compose.yml -f docker-compose.vps.yml down || true
fi

cd "$NEW/infrastructure/docker"
docker compose -p docker -f docker-compose.yml -f docker-compose.vps.yml up -d --build
docker compose -p docker -f docker-compose.yml -f docker-compose.vps.yml exec -T api python manage.py migrate --settings=config.settings.production
docker compose -p docker -f docker-compose.yml -f docker-compose.vps.yml exec -T api python manage.py bootstrap_system --settings=config.settings.production
docker compose -p docker -f docker-compose.yml -f docker-compose.vps.yml exec -T api python manage.py bootstrap_platform --settings=config.settings.production

curl -s -o /dev/null -w "health HTTP %{http_code}\n" http://127.0.0.1:8010/api/v1/health/
curl -s -o /dev/null -w "web HTTP %{http_code}\n" http://127.0.0.1:8010/
docker compose -p docker ps
