#!/usr/bin/env bash
set -euo pipefail

# Keep erp.safaritechno.com TLS SANs aligned with TenantDomain hostnames.
# Usage:
#   sync-erp-cert.sh [--dry-run]
#
# Prefer a DNS-01 wildcard (*.erp.safaritechno.com) long-term; this script is the
# HTTP-01 expand fallback so newly registered shops become HTTPS quickly.

PROJECT_DIR="/home/ubuntu/projects/mda"
COMPOSE_FILES=(
  "-f" "${PROJECT_DIR}/docker-compose.yml"
  "-f" "${PROJECT_DIR}/docker-compose.vps.yml"
  "-f" "${PROJECT_DIR}/docker-compose.volumes.yml"
)

CERT_NAME="erp.safaritechno.com"
BASE_DOMAIN="erp.safaritechno.com"
LOCK_FILE="/var/lock/sync-erp-cert.lock"
WEBROOT="/var/www/html"
TRIGGER_FILE="/var/lib/mda/tls-sync/request"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

mkdir -p "$(dirname "${LOCK_FILE}")" "$(dirname "${TRIGGER_FILE}")"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[sync-erp-cert] another run is in progress; exiting."
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[sync-erp-cert] docker is required."
  exit 1
fi
if ! command -v certbot >/dev/null 2>&1; then
  echo "[sync-erp-cert] certbot is required."
  exit 1
fi

domain_pattern="^[a-z0-9]([a-z0-9-]*[a-z0-9])?\\.${BASE_DOMAIN//./\\.}$"

domains_raw="$(
  docker compose "${COMPOSE_FILES[@]}" exec -T api \
    python manage.py shell -c "
from apps.platform.models import TenantDomain
domains = sorted({
    (d.domain or '').strip().lower()
    for d in TenantDomain.objects.filter(deleted_at__isnull=True)
    if (d.domain or '').strip().lower().endswith('.${BASE_DOMAIN}')
})
print('\\n'.join(domains))
" 2>/dev/null || true
)"

mapfile -t domain_list < <(
  printf '%s\n' "${domains_raw}" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/\r$//' \
    | grep -E "${domain_pattern}" \
    | sort -u
)

if (( ${#domain_list[@]} == 0 )); then
  echo "[sync-erp-cert] no tenant domains returned; keeping current cert."
  rm -f "${TRIGGER_FILE}"
  exit 0
fi

wanted=("${CERT_NAME}")
for d in "${domain_list[@]}"; do
  if [[ "${d}" != "${CERT_NAME}" ]]; then
    wanted+=("${d}")
  fi
done

# Let's Encrypt SAN cap is 100 names/certificate.
if (( ${#wanted[@]} > 100 )); then
  echo "[sync-erp-cert] refusing update: ${#wanted[@]} domains exceeds SAN limit 100."
  exit 1
fi

cert_pem="/etc/letsencrypt/live/${CERT_NAME}/cert.pem"
have_all=1
if [[ -f "${cert_pem}" ]]; then
  san_line="$(openssl x509 -in "${cert_pem}" -noout -ext subjectAltName 2>/dev/null | tr -d ' ' || true)"
  for d in "${wanted[@]}"; do
    if [[ "${san_line}" != *"DNS:${d}"* ]]; then
      have_all=0
      break
    fi
  done
else
  have_all=0
fi

if (( have_all == 1 )); then
  echo "[sync-erp-cert] certificate already covers all ${#wanted[@]} domains."
  rm -f "${TRIGGER_FILE}"
  exit 0
fi

mkdir -p "${WEBROOT}/.well-known/acme-challenge"
args=()
for d in "${wanted[@]}"; do
  args+=("-d" "${d}")
done

echo "[sync-erp-cert] updating certificate for ${#wanted[@]} domains:"
printf '  - %s\n' "${wanted[@]}"

if (( DRY_RUN == 1 )); then
  certbot certonly \
    --dry-run \
    --webroot -w "${WEBROOT}" \
    --cert-name "${CERT_NAME}" \
    --expand \
    --non-interactive \
    --agree-tos \
    "${args[@]}"
else
  certbot certonly \
    --webroot -w "${WEBROOT}" \
    --cert-name "${CERT_NAME}" \
    --expand \
    --non-interactive \
    --agree-tos \
    "${args[@]}"
  systemctl reload nginx
  rm -f "${TRIGGER_FILE}"
  echo "[sync-erp-cert] certificate updated and nginx reloaded."
fi
