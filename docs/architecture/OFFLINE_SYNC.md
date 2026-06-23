# Offline Sync — Shop Devices

## Short answer

**You do not need internet every time.** Install the desktop app on the shop PC, log in with your **local shop account**, and run POS, sales, and inventory **fully offline**. Internet is only used for short **sync bursts** when the PC is online (automatic every 5 minutes, or when Wi‑Fi returns).

---

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│  SHOP PC (desktop app)                                      │
│                                                             │
│  Daily work ──► Local SQLite @ 127.0.0.1:8000               │
│                 (no internet required)                      │
│                                                             │
│  When online ──► Sync engine (background)                   │
│       │                                                     │
│       ├── PUSH: sales, customers, stock → cloud             │
│       └── PULL: products, prices, catalog → local         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  CLOUD VPS (owner supervision)                              │
│  Platform admin, all shops, subscriptions, KPIs             │
└─────────────────────────────────────────────────────────────┘
```

| Activity | Internet required? |
|----------|-------------------|
| Login (shop user) | No |
| POS / sales / receipts | No |
| Add local customers | No |
| View reports (local data) | No |
| Sync products & sales with owner | Yes (brief) |
| Platform admin (owner abroad) | Yes |

---

## One-time shop setup

1. **Install** `MDA ERP` desktop (MSI) on the shop PC.
2. **First login** — use the shop account created on that PC (or seeded during install). This is **local only**.
3. **Settings → Connection → Cloud sync** (one-time):
   - **Cloud server URL:** e.g. `http://88.222.220.238:8010/api/v1`
   - **Shop slug:** from Platform → All Shops (e.g. `macquul`)
   - **Sync secret:** copy from Platform → Edit shop (generated per shop)
4. Click **Save settings**, then **Sync now** once while online.
5. Done — the app syncs automatically when internet is available.

Owner maintains the **product catalog on the cloud** (or on a master shop); shops **pull** products/prices down. Shops **push** sales, customers, and stock levels up.

---

## What syncs (bidirectional)

### Pull (cloud → shop)

- Categories, brands, units
- Products (SKU, prices, barcode, active flag)
- Opening stock quantities (default warehouse)
- Customers (updates from cloud)
- Subscription payment alerts (shown after pull)

### Push (shop → cloud)

- Invoices with line items
- Customers created/updated locally
- Current inventory quantities
- KPI snapshots for owner dashboard

**Conflict rule:** newest `updated_at` wins for the same SKU or customer code.

---

## Getting latest updates without daily internet

| Trigger | Behavior |
|---------|----------|
| App startup + online | Sync attempt |
| Every 5 minutes while online | Background sync |
| Wi‑Fi / cable reconnects | Immediate sync |
| Settings → **Sync now** | Manual sync |

If the shop is offline for days, nothing is lost — all sales stay in local SQLite. When internet returns, the next sync pushes everything since the last successful sync and pulls new products/prices.

**You never need internet to open the app or make a sale.** You only need a connection occasionally so the owner sees updated numbers and shops receive new products.

---

## API endpoints

| Endpoint | Direction | Auth |
|----------|-----------|------|
| `POST /api/v1/sync/run/` | Local bidirectional run | Shop JWT |
| `POST /api/v1/sync/shop-push/` | Shop → cloud | `X-Tenant-Slug` + `X-Sync-Secret` |
| `GET /api/v1/sync/shop-pull/?since=ISO` | Cloud → shop | Same headers |

---

## Local data location (Windows)

- Database: `%APPDATA%\com.mda.erp\mda_erp.sqlite3`
- Connection config: `%APPDATA%\com.mda.erp\connection.json`

---

## Owner vs shop accounts

- **Shop account** — local DB; used every day at the till.
- **Cloud admin** — Settings → Cloud admin login; only for Platform menu (manage shops/subscriptions). Not required for daily shop work.

---

## Future improvements

- Dedicated sync queue table with retry backoff
- Purchase orders / suppliers sync
- Multi-branch per shop device
- Image sync for product photos
