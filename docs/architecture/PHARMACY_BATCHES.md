# Pharmacy Batches + FEFO

**Status:** STEP 13 slice 1 shipped  
**Date:** 2026-08-07

## Models

- `ProductBatch` — tenant, product, warehouse, batch_number, expiry, quantity  
  UQ(tenant, product, warehouse, batch_number)
- `BatchDispense` — audit of FEFO allocations per invoice reference

## Behavior

1. **Receive (GRN):** when `pharmacy` module enabled or line has batch/expiry → create/increase batch
2. **Sale:** if any batches exist for product+warehouse → deduct earliest expiry first (`BatchService.deduct_fefo`); else inventory-only
3. **Return:** restore prior dispenses for invoice reference; leftover → `RETURN-{invoice}` batch
4. **Alerts:** `TenantSettings.expiry_alert_days` (default 30)

## APIs

`/api/v1/pharmacy/` (module-gated):

- `GET summary/`
- `GET|POST batches/`
- `GET batches/expiring/`
- `GET batches/fefo-preview/?product_id=&warehouse_id=&quantity=`
- `GET|POST prescriptions/`
- `POST prescriptions/<id>/dispense/`

## Permissions

`pharmacy.view`, `pharmacy.manage`, `pharmacy.dispense`
