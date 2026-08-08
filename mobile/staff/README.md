# MDA Staff (React Native)

Expo staff app with **module workspace switcher** driven by `GET /mobile/bootstrap/?audience=staff`.

## Features (v0.1 — PHASE 24)

- Tenant slug + staff login
- Bootstrap `mobile_nav` filtered to staff audience
  (`staff_hub`, `gym_staff`, `pharmacy_staff`, `hotel_staff`, `restaurant_staff`)
- Workspace switcher → Gym / Pharmacy / Hotel / Restaurant KPI screens

## Setup

```bash
cd mobile/staff
npm install
npx expo start
```

Configure `extra.apiBase` / `extra.tenantSlug` in `app.json` as needed.

## API

| Screen | Endpoint |
|--------|----------|
| Login | `POST /api/v1/auth/login/` |
| Nav / modules | `GET /api/v1/mobile/bootstrap/?audience=staff` |
| Gym workspace | `GET /api/v1/gym/summary/` |
| Pharmacy workspace | `GET /api/v1/pharmacy/summary/` |
| Hotel workspace | `GET /api/v1/hotel/summary/` |
| Restaurant workspace | `GET /api/v1/restaurant/summary/` |

Member portal remains in [`../gym-member/`](../gym-member/) (`audience=member` / default member workspace).
