# Mobile Architecture (Modular)

**Date:** 2026-08-07  
**Status:** EXTEND gym-member; CREATE staff app (thin)

Canonical broader mobile notes: `docs/MOBILE_ARCHITECTURE.md`.

---

## Current

- `mobile/gym-member/` — member portal; gated by gym module / permissions
- `mobile/staff/` — staff workspace switcher (gym, pharmacy, hotel, restaurant, property, housing, office KPIs)
- Auth must resolve tenant (slug / host) like web
- **PHASE 24:** `GET /mobile/bootstrap/?audience=member|staff` returns `enabled_modules` + `mobile_nav`

---

## Target after login

```text
GET /mobile/bootstrap/?audience=staff → workspaces (staff_hub, gym/pharmacy/hotel/restaurant/property/housing/office_staff, …)
  → Staff app: WorkspaceSwitcher → module KPI screens
GET /mobile/bootstrap/ (or audience=member) → gym_member screens
  → Gym-member app Home nav
```

| Tenant modules | Mobile workspaces |
|----------------|-------------------|
| gym + member portal | gym_member → Home, QR, Attendance, Workouts, Classes |
| gym + gym.view | gym_staff → Gym overview |
| pharmacy + pharmacy.view | pharmacy_staff → Pharmacy overview |
| hotel + hotel.view | hotel_staff → Hotel overview |
| restaurant + restaurant.view | restaurant_staff → Restaurant overview |
| property_management + view | property_staff → Property overview |
| housing_rental + view (+ property core) | housing_staff → Housing overview |
| office_rental + view (+ property core) | office_staff → Office overview |
| multi staff | staff_hub switcher → module workspaces |

Staff apps share the same entitlement / `mobile_nav` payload — no parallel module flags on device.

## Classification

| Piece | Action |
|-------|--------|
| Gym member app | KEEP / EXTEND |
| `MobileNavService` + bootstrap `mobile_nav` | **DONE** (member + staff audiences) |
| Dynamic module switcher RN | **DONE** thin (`mobile/staff`) |
| Offline POS mobile | separate roadmap (desktop sync exists) |
