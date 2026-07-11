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

## One-time shop setup (new device)

Create the shop and users on the **cloud Platform** first. Do **not** use the local Setup wizard for cloud-managed shops — that creates an orphan shop that only exists on that PC.

1. **Install** `MDA ERP` desktop (MSI) on the shop PC.
2. On first launch you see **Shop connection** (not Setup):
   - **Cloud server URL:** e.g. `http://88.222.220.238:8010/api/v1`
   - **Shop slug:** from Platform → All Shops
   - **Sync secret:** from Platform → Edit shop
3. **Save connection**, then **sign in** with the shop user created on the platform.
4. First sign-in **provisions** the account locally (role + permissions), then **syncs** catalog/sales when online.
5. Later sign-ins work **offline** on this PC. Sync runs when the internet is available.

Optional: **Offline-only setup** (`/setup?offline=1`) creates a local shop that is **not** managed from the cloud — only for devices that will never connect.

Owner maintains the **product catalog on the cloud**; shops **pull** products/prices down. Shops **push** sales, customers, and stock levels up.

---

## What syncs (bidirectional)

Every online sync **pulls then pushes**.

### Pull (cloud → shop)

- Categories, brands, units
- Products (SKU, prices, barcode, active flag) — including newly created cloud products
- Opening / current stock quantities (shop warehouse)
- Customers (shop-scoped when possible)
- Shop users (metadata + roles; password via first online desktop login)
- Waiters (shared POS waiter list)
- Subscription payment alerts

### Push (shop → cloud)

- Invoices with line items
- Customers created/updated locally
- Current inventory quantities
- Waiters configured on the shop POS
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

- **Shop account** — created on cloud (Platform → Shops / Users) with that shop’s tenant. On desktop, first login **while online** provisions the local SQLite user (same username/password), then works **offline**.
- **Cloud admin** — Settings → Cloud admin login; only for Platform menu (manage shops/subscriptions). Not required for daily shop work.

### Cloud → desktop user access

1. Create the user on the cloud for that shop (tenant).
2. On the shop PC: Settings → Connection (cloud URL, shop slug, sync secret).
3. Sign in once **online** with that username/password — MDA copies the account locally.
4. Later logins work offline. Sync pulls new products/users and pushes sales when internet returns.

---

## Subscription lock (offline shops)

| State | Behavior |
|-------|----------|
| Active / paid | Full use, no dialog |
| Warning window (before expiry) | Soft alert — dismissible for the day |
| Grace period (after expiry) | Critical soft alert — still usable |
| Past grace / suspended | **Hard lock** — POS checkout blocked; Sync / Connection still available |

**Offline:** the last synced subscription (`sync.subscription_alert`) is checked against the **device date**. No internet is required to lock after grace ends.

**Renew unlock:**
1. Owner records payment / renews on cloud (Platform → Subscriptions → Renew).
2. Shop PC goes online.
3. User taps **Sync now** (or automatic sync runs).
4. Fresh subscription is pulled → lock clears.

---

## Future improvements

- Dedicated sync queue table with retry backoff
- Purchase orders / suppliers sync
- Multi-branch per shop device
- Image sync for product photos
