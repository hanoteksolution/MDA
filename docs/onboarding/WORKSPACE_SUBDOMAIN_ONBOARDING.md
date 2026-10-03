# Workspace Subdomain Onboarding

How a self-serve signup picks a workspace URL (`<slug>.erp.safaritechno.com`),
how the platform validates and reserves it, and why the URL the user approves
is always the URL the workspace gets.

## Canonical slug rules

Backend-authoritative, implemented once in `backend/apps/platform/services/domain_utils.py`
(`normalize_tenant_slug` / `validate_tenant_slug`). No frontend copy of this logic exists;
the frontend (`frontend/src/pages/auth/workspaceUrl.ts`) mirrors only the normalization
regex for live UX and always defers to the backend for the authoritative answer.

- Lowercase only; spaces and underscores become hyphens.
- Allowed characters: `a-z`, `0-9`, `-`.
- No leading or trailing hyphen; no repeated hyphens (collapsed to one).
- Length 2–63 characters (DNS label limit).
- Must match `^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$` after normalization.

Normalization never invents a different brand — it only lowercases/strips/collapses
what the user typed. A slug that fails validation is rejected (`reason: "invalid"`),
never silently rewritten into something else.

## Reserved subdomains

`RESERVED_TENANT_SLUGS` in `domain_utils.py` is the single source of truth (checked
in `validate_tenant_slug`); the frontend never maintains its own copy. Covers
infrastructure/system names: `www, api, admin, app, apps, auth, login, register,
signup, billing, payments, payment, sms, integrations, support, help, status, docs,
static, media, assets, files, cdn, mail, email, smtp, ftp, dev, staging, test, demo,
dashboard, portal, system, internal, platform, erp, health, null, undefined,
localhost, safaritechno, safari`.

## Availability API (UX only — not a reservation)

`GET /api/v1/public/workspaces/subdomain-availability/?subdomain=<value>`
(alias: `GET /api/v1/public/subdomains/check/?subdomain=<value>`; the authenticated
onboarding wizard also has `GET /api/v1/onboarding/slug-check/?slug=<value>`, same
underlying `check_subdomain_availability()` call).

Response shape:

```json
{
  "requested": "Barista",
  "normalized": "barista",
  "available": true,
  "hostname": "barista.erp.safaritechno.com",
  "reason": null,
  "suggestions": []
}
```

`reason` is one of `null`, `"taken"`, `"reserved"`, `"invalid"`. Taken/reserved
responses include up to 3 clickable suggestions built by appending a fixed word
list (`-cafe`, `-coffee`, `-shop`, …) to the requested root and checking each for
availability — never a random numeric suffix (`suggest_subdomains` in
`domain_utils.py`). The endpoint returns no tenant-private data: no company name,
owner, user, email, or tenant id — verified by
`test_workspace_subdomain.py::test_availability_taken_with_suggestions`.

## Frontend states

`frontend/src/pages/auth/workspaceUrl.ts` (`deriveWorkspaceUiState`) drives
`WorkspaceUrlField.tsx`: `empty`, `checking`, `available`, `taken`, `reserved`,
`invalid`, `error` (network failure). The workspace step in `OnboardingPage.tsx`
debounces the availability call by `WORKSPACE_CHECK_DEBOUNCE_MS` (400ms) after
each keystroke, shows inline feedback (no toasts), and disables **Continue**
on the URL step unless the state is `available` (the workspace is created later,
from the **Review** step). Company-name-derived suggestions
only pre-fill the slug field until the user edits it manually
(`nextSlugFromCompanyName`); after that, changing the company name never
overwrites the chosen slug. Clicking a suggestion re-populates the field and
re-runs the same debounced check. The final URL preview
(`https://<slug>.erp.safaritechno.com`) always renders from the same
`normalizeWorkspaceSlug` the backend uses, so the preview matches what
submission will request.

Visual branding of these screens (Safari logo, `brand-*` tokens, step layout,
provisioning and success states) is described in
[`SAFARI_AUTH_BRANDING.md`](SAFARI_AUTH_BRANDING.md).

## Create-time (authoritative) validation

The availability check is UX only. `OnboardingService.provision` /
`PlatformService.create_shop` re-validate and re-check the slug inside the
creation transaction, and never fall back to generating a different slug on
conflict:

1. `validate_tenant_slug` re-runs the same canonical rules.
2. If a non-deleted `Tenant` with that slug already exists, or the hostname
   already has a primary `TenantDomain`, provisioning raises
   `SubdomainTakenError` / `OnboardingError(code="SUBDOMAIN_TAKEN")` — HTTP 409.
   The idempotent-replay exception is when the same slug **and** the same
   owner username/password are resubmitted (safe retry of a request that
   already succeeded).
3. `Tenant.objects.create(slug=...)` and `TenantDomain.objects.create(domain=...)`
   are wrapped so a DB `IntegrityError` (concurrent winner) also becomes
   `SubdomainTakenError` → 409, not a rename.

Response on conflict:

```json
{
  "code": "SUBDOMAIN_TAKEN",
  "message": "This workspace URL was just taken. Please choose another.",
  "suggestions": ["barista-cafe", "barista-coffee", "barista-shop"]
}
```

## Database uniqueness and concurrency

`Tenant.slug` (`apps/platform/models/tenant.py`) and `TenantDomain.domain`
(`apps/platform/models/tenant_config.py`) both carry a DB-level `unique=True`
constraint — the uniqueness guarantee does not rely on an `exists()` check alone.
`PlatformService.create_shop` is `@transaction.atomic`; a losing concurrent
request's `IntegrityError` on the unique constraint is caught and turned into
the 409 response above, inside the same transaction, so no partial tenant is
left behind.

`tests/unit/test_workspace_subdomain.py::test_concurrent_duplicate_creation_returns_conflict`
fires two simultaneous `POST /api/v1/onboarding/provision/` requests for the
same slug (`coffee`) against PostgreSQL (skipped on SQLite, which does not
enforce `select_for_update`/real concurrent uniqueness — see project test
notes). Expected and verified result: one `201`, one `409`, exactly one
`Tenant` row with `slug="coffee"`, and no `coffee123`/`coffee456` rows ever
created.

## Company name vs. workspace slug vs. hostname

These are three separate values: `Company Name` (display), `slug` (stable
workspace identifier, chosen once at signup), and `hostname` (`slug` +
`.erp.safaritechno.com`). Editing the company/tenant display name later never
touches the tenant's `slug` or its primary `TenantDomain` row — there is no
code path that renames an established tenant's hostname. A future
workspace-domain-change workflow would be a distinct, explicit feature.

## TLS

TLS certificate provisioning is not part of workspace creation.
`*.erp.safaritechno.com` is covered by the platform wildcard certificate.
Workspace creation contains no certificate-issuing, ACME, DNS, or Nginx logic,
and none was added for this feature.
