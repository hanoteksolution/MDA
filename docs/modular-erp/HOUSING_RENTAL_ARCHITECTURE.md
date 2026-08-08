# Housing Rental Architecture

**Date:** 2026-08-07  
**Status:** CREATE + lease-charge billing EXTEND

---

## Domain

```text
PropertyUnit (residential) → HousingTenant → Lease → LeaseCharge
→ Invoice / Payment → CAE (HOUSING_RENT_REVENUE / SECURITY_DEPOSIT_LIABILITY)
MaintenanceRequest stays on property_management
```

Lease statuses: `draft` / `active` / `expired` / `terminated` / `renewed`  
Activate → unit `occupied`; terminate/expire → unit `vacant` (shared PropertyService).

Module: `housing_rental` requires `property_management`.

## Shipped

- Django app `apps.housing_rental` + API `/api/v1/housing/`
- Models: HousingTenant, Lease, LeaseCharge
- **Billing:** `POST /charges/<id>/invoice/` (on-account AR) and `POST /charges/<id>/paid/` (collect cash/mobile/card)
  - Shared `RentalBillingService` → central Invoice/Payment + `SALE_COMPLETED` / `CUSTOMER_PAYMENT_RECEIVED`
  - Deposit charges map to `SECURITY_DEPOSIT_LIABILITY`
- Demo seeder + FE `/housing` charges panel (Invoice / Collect)
- No fork of Property/Building — leases FK `PropertyUnit`

## Later

- Rent scheduler / overdue dunning
- Renewals UI
- Deposit refund / apply-to-rent flows
