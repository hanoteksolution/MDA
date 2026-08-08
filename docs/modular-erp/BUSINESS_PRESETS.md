# Business Presets

**Date:** 2026-08-07  
**Status:** Design — **CREATE** (today folded into `BusinessType.default_modules`)

---

## Problem

`BusinessType` currently stores `default_modules` and acts as both **classification** and **onboarding pack**. That blocks:

- Multiple presets per type (Hotel Basic vs Hotel + Restaurant)
- Custom module mixes without inventing fake types
- Safe preset evolution (versioning)

---

## Target models

```text
BusinessPreset
  code, name, description, icon
  business_type FK (nullable for CUSTOM)
  version
  is_system, is_active

BusinessPresetModule
  preset, module
  is_required, is_default, display_order
  default_configuration JSON
  UNIQUE(preset, module)
```

Tenant stores audit snapshot only: `preset_used_code`, `preset_version` — **not** a live FK that re-reads modules.

---

## Example presets

| Preset | Type | Modules |
|--------|------|---------|
| `pharmacy` | healthcare_retail | pharmacy, pos, inventory, purchases |
| `gym_starter` | fitness | gym |
| `gym_full` | fitness | gym, pos, inventory, sales, purchases |
| `gym_cafeteria` | multi_business | gym, cafeteria, pos, inventory |
| `cafeteria` | food_service | cafeteria, pos, inventory, purchases |
| `hotel_basic` | hospitality | hotel |
| `hotel_restaurant` | hospitality | hotel, restaurant, pos, inventory |
| `property_residential` | property | property_management, housing_rental |
| `property_commercial` | property | property_management, office_rental |
| `property_mixed` | property | property_management, housing_rental, office_rental |
| `custom` | multi_business | empty — admin picks |

---

## Migration path

1. CREATE preset tables; seed one preset per existing BusinessType from `default_modules`
2. Onboarding: select type → list presets → apply copy to TenantModule
3. Stop writing new defaults onto BusinessType; keep JSON read-only for back-compat until removed

**KEEP** BusinessType. **CREATE** Preset. **REFACTOR** onboarding + `sync_tenant_modules` source.
