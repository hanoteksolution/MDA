# Mobile Architecture

## Apps

| App | Path | Role |
|---|---|---|
| Staff ERP | `mobile/staff` | Full ERP nav (currently engine + vertical peers) |
| Gym member | `mobile/gym-member` | QR attendance, workouts, classes |

## Target (same backend)

After login: tenant + enabled workspaces + capabilities + features + permissions → **industry-first** home:

```
Business Workspaces
  Restaurant → Dashboard, POS, Orders, Menu, Inventory, Kitchen, Finance
  Gym → Dashboard, Members, Attendance, Memberships, Classes, POS, Finance
  …
Central Finance
Administration
```

Do not create a second API. Reuse `/api/v1`.

## Status

Web increment 1+2 (hub + tab sync) first. RN catalog refactor = Phase 26. `docs/modular-erp/MOBILE_ARCHITECTURE.md` remains the deep nav catalog reference.
