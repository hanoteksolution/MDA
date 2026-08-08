# Mobile Architecture

**Status:** Foundation note (updated 2026-08-07)  
**Client technology:** **React Native** (not Flutter)

---

## Principle

```
             Django API (/api/v1)
                     │
           ┌─────────┴──────────┐
           │                    │
        React SPA          React Native
        (Web ERP)          (Mobile apps)
```

Business rules stay on the backend. Mobile clients must not re-implement pricing, stock, membership validity, or tenant isolation.

---

## Planned apps

| App | Audience | First slices |
|-----|----------|--------------|
| Gym Member | Members | Login, membership QR, attendance, workouts, classes — **v0.1 in `mobile/gym-member/`** |
| Business Owner / Staff | Managers, cashiers | **v0.2 in `mobile/staff/`** — dashboard, POS, sales, inventory, purchases, customers, suppliers, finance, business units, reports, settings + venue modules |

---

## API requirements (STEP 27) — implemented

- JWT access + refresh (`/api/v1/auth/login/`, `/api/v1/auth/refresh/` with standard envelope)
- Tenant context via host **or** `X-Tenant-Slug` on platform API host (`api.{base_domain}`)
- Stable pagination (`page`, `page_size`), filtering, error envelope (`success`, `code`, `message`, `details`)
- OpenAPI: `/api/v1/schema/`, Swagger UI: `/api/v1/docs/`
- Rate limiting: anon/user defaults + stricter `auth` scope on login/refresh
- Mobile contract: `GET /api/v1/mobile/meta/` (public), `GET /api/v1/mobile/bootstrap/` (authenticated)
  — bootstrap includes `enabled_modules` + `mobile_nav` (PHASE 24); optional `?audience=member|staff`
  — Staff app: `mobile/staff/` full ERP workspaces (STEP 69); member app: `mobile/gym-member/`

---

## Member portal API (STEP 28)

Role `gym_member` + permission `gym.member_portal`. Member must be linked via `Member.user`.

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/mobile/gym/home/` | Dashboard |
| `GET /api/v1/mobile/gym/profile/` | Member + subscription |
| `GET /api/v1/mobile/gym/qr/` | QR payload (`mem:{membership_number}`) |
| `GET /api/v1/mobile/gym/attendance/` | Visit history |
| `GET /api/v1/mobile/gym/workouts/` | Assigned plans |
| `GET /api/v1/mobile/gym/classes/` | Bookings |

---

## Still out of scope

- Offline-first mobile accounting sync
- Separate mobile backend
- Full desktop-parity POS (split tender, holds, charge-to-room) on phone

See [ERP_TRANSFORMATION_ROADMAP.md](./ERP_TRANSFORMATION_ROADMAP.md) STEP 29+.
