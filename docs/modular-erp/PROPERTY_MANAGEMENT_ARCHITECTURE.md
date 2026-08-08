# Property Management Architecture

**Date:** 2026-08-07  
**Status:** **CREATE** shared core shipped (PHASE 18)

---

## Shared kernel

```text
Owner → PropertyAsset → Building → PropertyUnit
MaintenanceRequest, PropertyDocument
```

Modules:
- `property_management` — core entities (**live**)
- `housing_rental` — residential leases (PHASE 19 — module catalog + deps only)
- `office_rental` — commercial leases (PHASE 20 — module catalog + deps only)

Do **not** duplicate Property/Building for housing vs office — specialize Unit `kind` + Lease apps later.

## Shipped

- Django app `apps.property_management` + API `/api/v1/property/`
- Unit status + maintenance tickets (open → in progress → done frees unit)
- Document metadata records (URL/title; upload later)
- BT `property`, presets `property_residential` / `property_commercial` / `property_mixed`
- Demo seeder + FE `/property` + workspace + dashboard card

## Accounting (later)

Rent invoice → AR / rental revenue  
Security deposit → liability until applied  
Celery rent scheduler → `RENT_INVOICE_GENERATED`

## Next

PHASE 19 Housing leases on this core; PHASE 20 Office leases — same Unit/Property, no fork.
