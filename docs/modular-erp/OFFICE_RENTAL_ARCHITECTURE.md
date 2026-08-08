# Office Rental Architecture

**Date:** 2026-08-07  
**Status:** CREATE + lease-charge billing EXTEND

---

## Domain extras on Unit / Lease

Office capacity lives on `PropertyUnit` (kind=`office`/`retail`).  
Commercial lease adds: company, registration, contact, service charge, parking, furnished, utilities flags.

```text
PropertyUnit (office|retail) → OfficeTenant → OfficeLease → OfficeLeaseCharge
→ Invoice / Payment → CAE (OFFICE_RENT_REVENUE / SECURITY_DEPOSIT_LIABILITY)
```

Module: `office_rental` requires `property_management`.

Reuse: Property, Building, Maintenance, deposit charge pattern — **no fork**.

Preset: `property_commercial` / `property_mixed`.

## Shipped

- Django app `apps.office_rental` + API `/api/v1/office/`
- Demo seeder + FE `/office` charges panel
- Activate/terminate syncs unit occupancy via PropertyService
- **Billing:** same `RentalBillingService` as housing — `POST /charges/<id>/invoice/` + `/paid/`
- RN staff `office_staff` workspace (requires property core)

## Later

- Utility metering / CAM reconciliations
- Mixed-use dashboards across housing + office
