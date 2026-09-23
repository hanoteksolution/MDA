#!/usr/bin/env bash
set -euo pipefail

# Issue / renew the DNS-01 wildcard certificate for the ERP tenant subdomains.
#
#   erp.safaritechno.com  +  *.erp.safaritechno.com
#
# A wildcard means every tenant subdomain is valid HTTPS the moment its DNS
# resolves — nothing is provisioned per shop, there is no insecure window after
# a workspace is created, and there is no Let's Encrypt 100-SAN ceiling. This
# replaces the per-tenant SAN expansion in sync-erp-cert.sh.
#
# Validation goes through acme-dns rather than a DNS provider API, because
# safaritechno.com is held via Hostinger collaborator access and collaborator
# rights do not extend to API tokens. Hostinger's editor also has no NS record
# type, so the acme-dns zone cannot be self-hosted and the public instance is
# used instead, with a CAA accounturi pin as the safeguard. See
# ../acme-dns/README.md.
#
# Requirements:
#   - acme.sh >= 3.1.5 at ACME_HOME
#   - acme-dns account (register response) in ACMEDNS_ACCOUNT_FILE
#   - CNAME _acme-challenge.erp.safaritechno.com -> <fulldomain> in hPanel
#
# Usage:
#   sudo /usr/local/sbin/issue-erp-wildcard            # issue (no-op if current)
#   sudo /usr/local/sbin/issue-erp-wildcard --force    # force re-issue
#   sudo /usr/local/sbin/issue-erp-wildcard --staging  # LE staging rehearsal

BASE_DOMAIN="erp.safaritechno.com"
ACME_HOME="/root/.acme.sh"
ACME_CONFIG_HOME="/root/.acme.sh/data"
ACMEDNS_ACCOUNT_FILE="/root/.acmedns-account.json"
ACMEDNS_URL="https://auth.acme-dns.io"
CERT_DIR="/etc/ssl/mda/erp-wildcard"
LOCK_FILE="/var/lock/issue-erp-wildcard.lock"

FORCE=0
STAGING=0
for arg in "$@"; do
  case "${arg}" in
    --force) FORCE=1 ;;
    --staging) STAGING=1 ;;
    *) echo "[issue-erp-wildcard] unknown argument: ${arg}" >&2; exit 2 ;;
  esac
done

mkdir -p "$(dirname "${LOCK_FILE}")"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[issue-erp-wildcard] another run is in progress; exiting."
  exit 0
fi

if [[ ! -x "${ACME_HOME}/acme.sh" ]]; then
  echo "[issue-erp-wildcard] acme.sh not found at ${ACME_HOME}/acme.sh" >&2
  exit 1
fi
if [[ ! -r "${ACMEDNS_ACCOUNT_FILE}" ]]; then
  echo "[issue-erp-wildcard] acme-dns account not found at ${ACMEDNS_ACCOUNT_FILE}" >&2
  echo "  curl -s -X POST ${ACMEDNS_URL}/register | sudo tee ${ACMEDNS_ACCOUNT_FILE}" >&2
  exit 1
fi

# acme.sh reads these; the account file is the single source of truth.
ACMEDNS_BASE_URL="${ACMEDNS_URL}"
ACMEDNS_USERNAME="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["username"])' "${ACMEDNS_ACCOUNT_FILE}")"
ACMEDNS_PASSWORD="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["password"])' "${ACMEDNS_ACCOUNT_FILE}")"
ACMEDNS_SUBDOMAIN="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["subdomain"])' "${ACMEDNS_ACCOUNT_FILE}")"
ACMEDNS_FULLDOMAIN="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["fulldomain"])' "${ACMEDNS_ACCOUNT_FILE}")"
export ACMEDNS_BASE_URL ACMEDNS_USERNAME ACMEDNS_PASSWORD ACMEDNS_SUBDOMAIN

if [[ -z "${ACMEDNS_USERNAME}" || -z "${ACMEDNS_PASSWORD}" || -z "${ACMEDNS_SUBDOMAIN}" ]]; then
  echo "[issue-erp-wildcard] ${ACMEDNS_ACCOUNT_FILE} is missing required fields." >&2
  exit 1
fi

# Fail early with a clear message if the one-time CNAME is missing, rather than
# after a slow ACME round trip. Query public resolvers directly: the
# systemd-resolved stub flattens CNAME chains and returns no CNAME record.
challenge_cname=""
for resolver in 1.1.1.1 8.8.8.8 9.9.9.9; do
  challenge_cname="$(dig +short CNAME "_acme-challenge.${BASE_DOMAIN}" "@${resolver}" 2>/dev/null | sed 's/\.$//' | head -1)"
  [[ -n "${challenge_cname}" ]] && break
done
if [[ "${challenge_cname}" != "${ACMEDNS_FULLDOMAIN%.}" ]]; then
  echo "[issue-erp-wildcard] _acme-challenge.${BASE_DOMAIN} does not point at acme-dns." >&2
  echo "  expected CNAME -> ${ACMEDNS_FULLDOMAIN}" >&2
  echo "  got            -> ${challenge_cname:-<none>}" >&2
  exit 1
fi

mkdir -p "${CERT_DIR}"
chmod 700 "${CERT_DIR}"

issue_args=(
  --issue
  --dns dns_acmedns
  -d "${BASE_DOMAIN}"
  -d "*.${BASE_DOMAIN}"
  --config-home "${ACME_CONFIG_HOME}"
  --keylength ec-256
)
(( FORCE == 1 )) && issue_args+=(--force)
(( STAGING == 1 )) && issue_args+=(--staging)

echo "[issue-erp-wildcard] issuing ${BASE_DOMAIN} + *.${BASE_DOMAIN} via acme-dns"
set +e
"${ACME_HOME}/acme.sh" "${issue_args[@]}"
rc=$?
set -e

# acme.sh exits 2 when the certificate is current and no renewal is due.
if (( rc != 0 && rc != 2 )); then
  echo "[issue-erp-wildcard] issuance failed (exit ${rc})." >&2
  exit "${rc}"
fi

if (( STAGING == 1 )); then
  echo "[issue-erp-wildcard] staging run complete; not installing."
  exit 0
fi

"${ACME_HOME}/acme.sh" --install-cert \
  -d "${BASE_DOMAIN}" \
  --ecc \
  --config-home "${ACME_CONFIG_HOME}" \
  --key-file "${CERT_DIR}/privkey.pem" \
  --fullchain-file "${CERT_DIR}/fullchain.pem" \
  --reloadcmd "systemctl reload nginx"

chmod 600 "${CERT_DIR}/privkey.pem"
chmod 644 "${CERT_DIR}/fullchain.pem"

echo "[issue-erp-wildcard] installed:"
openssl x509 -in "${CERT_DIR}/fullchain.pem" -noout -subject -dates -ext subjectAltName
