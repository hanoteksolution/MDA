# Safari branding — public auth & onboarding

Scope: the public pages only — `/login`, `/forgot-password`, `/setup`,
`/connection`, `/onboard` (`/register`). The ERP workspace (AppShell, modules)
keeps its own theme and per-workspace colors (`src/theme/workspaceBrand.ts`).

## Logo

- Canonical asset: `frontend/src/assets/brand/safari-logo.png` (the official
  file, unmodified; 567×219, transparent). Do not add copies elsewhere.
- Render it only through `components/brand/SafariLogo.tsx` (`size` sm/md/lg).
  It fixes the height and lets width follow the aspect ratio (`object-contain`),
  so the logo is never stretched. The artwork has black lettering, so in dark
  mode it sits on a white plate instead of being recolored.
- Name, alt text and intrinsic size: `SAFARI_BRAND` in `src/design-system/brand.ts`.

## Brand tokens

Sampled from the logo and defined once in `src/styles/globals.css`
(`:root` and `.dark`), exposed to Tailwind as `brand-*`:

| Token | Light | Use |
| --- | --- | --- |
| `brand-primary` | `#6B4FA1` violet (6.4:1 on white) | primary actions, active/selected states, focus |
| `brand-primary-hover` | `#5A4290` | hover |
| `brand-secondary` | `#09ABD1` cyan | decorative accents only (fails text contrast) |
| `brand-accent` | `#D94C9B` magenta | subtle gradient highlight only |
| `brand-deep` | `#2A68B2` deep blue (5.6:1) | URLs, secondary emphasis |
| `brand-ink` / `brand-soft` / `brand-soft-foreground` / `brand-surface` | — | headings, tinted panels, text on tint, cards |

`AuthLayout` wraps every public route in `.safari-brand`, which remaps the
shared `--primary`, `--ring` and `--accent` variables to the brand tokens. The
existing `Button`, `Input`, `Checkbox` and focus rings therefore turn Safari
violet on these pages without new components or per-page hex values.
`.safari-brand-rule` is the thin violet→magenta→cyan rule at the top of the pages.
Success/error text keeps the semantic green/red colors.

`AuthLayout` also sets framer-motion `MotionConfig reducedMotion="user"`;
spinners and hover lifts use `motion-reduce:` variants.

## Layout

- `components/auth/LoginBrandingPanel.tsx` is the shared left panel (desktop
  `lg+` only): logo, headline, three real capabilities. On narrow screens
  the panel is hidden and the page shows the logo above the form.
- Login: sign-in behavior is unchanged (setup check, tenant-host branding,
  remember-me, desktop connection hints). The show/hide password button now
  has a label and can be reached with the keyboard.

## Onboarding steps

Company → Industry → Modules → Plan → Workspace URL → Owner & branch →
Review → (create) → provisioning → success.

There is no branding/logo upload step: the registration API does not accept
one. The first branch name is collected on the Owner & branch step.
**Review** is frontend-only and lets you edit each section before the single
`POST /public/registrations/` call.

### Provisioning (no simulated progress)

Provisioning runs synchronously inside the registration request. While the
request is in flight, `ProvisioningPanel` shows a spinner and lists what the
server will do (`PROVISIONING_STAGES`, which mirrors
`TenantProvisioningService.STAGES`), with every stage shown as pending. Stages are shown
as complete only from the response's `stages` job log
(`summarizeProvisioningStages`, `src/pages/auth/provisioningStages.ts`).

### Success

Shows the company name, the final `https://<slug>.<base domain>` URL, the
server-confirmed stages, a notice when `tls_ready` is false, and **Open
Workspace** (goes to `<workspace>/login?welcome=1`, as before).

## Tests

`src/pages/auth/provisioningStages.test.ts`, `src/pages/auth/workspaceUrl.test.ts`.
