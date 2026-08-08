# MDA Staff (React Native)

Expo staff **ERP** app. Navigation comes from `GET /mobile/bootstrap/?audience=staff` — same module + permission gates as web.

## Features (v0.2 — STEP 69)

- Tenant slug + staff login
- Workspace switcher grouped as Operations / Finance / Venues
- **Operations:** Dashboard, POS (search + cash checkout), Sales, Inventory, Purchases, Customers, Suppliers
- **Finance:** Finance KPIs, **Business Units** + P&L, Reports catalog, Settings
- **Venues:** Gym, Pharmacy, Hotel, Restaurant, Property, Housing, Office, Futsal

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
| Dashboard | `/dashboard/kpis/`, `/recent-sales/`, `/low-stock/`, `/widgets/` |
| POS | `/products/search/`, `POST /pos/checkout/` |
| Sales | `/sales/summary/`, `/sales/invoices/` |
| Inventory | `/inventory/summary/`, `/inventory/`, `/inventory/low-stock/` |
| Purchases | `/purchases/summary/`, `/purchases/` |
| Customers | `/customers/summary/`, `/customers/` |
| Suppliers | `/suppliers/` |
| Finance | `/finance/summary/`, `/finance/equation/` |
| Business units | `/finance/business-units/`, `/finance/reports/profit-loss/?business_unit_id=` |
| Reports | `/reports/catalog/`, `/reports/data/` |
| Settings | `/settings/company/`, `/settings/branches/` |
| Venue KPIs | `/gym|pharmacy|hotel|restaurant|property|housing|office|futsal/summary/` |

Member portal remains in [`../gym-member/`](../gym-member/) (`audience=member`).
