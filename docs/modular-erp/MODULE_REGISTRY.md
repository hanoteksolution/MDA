# Module Registry

**Date:** 2026-08-07  
**Status:** Target catalog — extend existing `MODULE_SEEDS`

---

## Live today

| Code | Category | App | Notes |
|------|----------|-----|-------|
| `pos` | core | sales/pos | Universal POS |
| `inventory` | core | inventory | |
| `sales` | core | sales | |
| `purchases` | core | purchases | |
| `pharmacy` | industry | pharmacy | Batches/FEFO |
| `restaurant` | industry | restaurant | Floor / menu / pay-table |
| `hotel` | industry | hotel | Rooms / reservations / folios |
| `property_management` | industry | property_management | Assets / units / maintenance |
| `housing_rental` | industry | housing_rental | Leases on PropertyUnit |
| `office_rental` | industry | office_rental | Commercial leases on PropertyUnit |
| `gym` | industry | gym | Full + mobile |
| `futsal` | industry | futsal | Courts/bookings |

---

## Target registry (add incrementally)

### Core business
`core` (implicit), `finance`, `pos`, `sales`, `purchases`, `inventory`, `reporting`

### Retail & commerce
`retail`, `supermarket`, `pharmacy`

### Food & hospitality
`cafeteria`, `restaurant`, `hotel`

### Fitness
`gym`, `futsal`

### Property
`property_management`, `housing_rental`, `office_rental`

### Enterprise
`crm`, `hrm`

**Registration rule:** new vertical = new `Module` seed + Django app + path gate + nav entries. No fork of the platform.

---

## Metadata template

```text
code: gym
name: Gym Management
category: industry
route: /gym
dashboard_route: /gym
dependencies: [finance]          # soft until finance is catalogued; today FINANCE via perms
optional_dependencies: [pos, inventory]
supports_mobile: true
supports_pos: true
is_core: false
display_order: 40
```

Centralize seeds in `module_service.MODULE_SEEDS` (KEEP pattern). Do not scatter definitions in FE components — FE reads catalog / enabled list from API.
