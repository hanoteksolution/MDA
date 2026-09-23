# Self-Service Onboarding Flow

## Host routing

- `erp.safaritechno.com/` → public Safari ERP landing page.
- `/pricing`, `/modules`, `/solutions`, `/resources`, `/contact` → public content.
- `/register` → self-service wizard; retain `/onboard` as a temporary redirect.
- `/login` → login/workspace discovery.
- `{tenant}.erp.safaritechno.com/*` → existing tenant application.
- Unknown tenant host → generic workspace-not-found experience.

Because the existing frontend is a Vite SPA, public and tenant route switching should be implemented in the current React Router application, not by introducing Next.js.

## Wizard

1. Business profile: name, industry, country, currency, timezone and size.
2. Business type: broad classification only.
3. Business preset: backend catalog recommendation.
4. Modules: selectable cards; backend returns dependency and plan impact.
5. Company details: legal/trading name, registration/tax details, address, contacts, locale/fiscal defaults and validated logo.
6. Workspace: strict slug entry, availability, suggestions and HTTPS preview.
7. Owner: name, email, phone, password/confirmation and strength guidance.
8. Plan/trial: backend-driven plan capabilities; no fake payment.
9. Review: editable summary plus explicit Terms and Privacy acceptance.
10. Verification/provisioning: email verification when enabled, real stage display and safe retry.
11. Success: HTTPS tenant link and first-time setup route.

## UX rules

- Persist non-sensitive draft fields in session storage or a server draft; never persist passwords in browser storage.
- Debounce availability checks, but revalidate on submit.
- Disable duplicate submit and send an idempotency key.
- Use an accessible stepper, field-level messages, error summary, keyboard focus management, reduced-motion support and sticky mobile actions.
- Logo upload provides preview/replace/remove and uses existing server-side image verification.
- Pricing and module inclusion come only from public backend catalogs.

## Provisioning and failure experience

The progress screen polls a safe registration status endpoint and renders actual stages, not invented percentages. Retryable failure offers retry using the same registration/idempotency identity. Non-retryable validation returns the user to the relevant step. Manual-intervention states provide a support reference without exposing infrastructure details.

## First-time setup

After readiness, direct the owner to `https://{slug}.erp.safaritechno.com/onboarding`. Reuse existing tenant settings and module services for company confirmation, branch, currency, tax, fiscal year, receipt setup, module-specific configuration, team invites and imports. Optional steps may be skipped. Persist a checklist in tenant settings initially or a dedicated checklist model if per-user tracking is needed.

## Landing page scope

The landing page should use the existing Safari design system and current React stack. Required sections are hero, solutions, module catalog, central finance, projects, mobile, analytics, multi-branch, security, how it works, backend-driven pricing, FAQ, CTA and footer. Keep content concise and ensure all calls to action route into the same registration flow.

