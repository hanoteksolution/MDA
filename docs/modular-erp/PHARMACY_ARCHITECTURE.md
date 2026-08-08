# Pharmacy Architecture

**Date:** 2026-08-07  
**Status:** KEEP / EXTEND `apps/pharmacy`

---

## Existing

Batches, expiry, FEFO; module `pharmacy`; FE thin; POS batch-aware paths.  
Accounting: pharmacy POS profile posts `PHARMACY_SALE_COMPLETED` → `PHARMACY_SALES_REVENUE`  
(`source_module=pharmacy`, BusinessUnit **PHARM**) via the same CAE — not a parallel ledger.

Prescriptions (thin MVP + POS gate + FEFO): `Prescription` + `PrescriptionLine` (`quantity_dispensed`).  
`Product.requires_prescription` — pharmacy POS requires covering `prescription_id` and cart qty ≤ Rx remaining.  
POS sale stamps `Rx:` on notes, updates dispensed qty without double stock deduct.  
Manual dispense deducts inventory + FEFO (`reference_type=prescription`). Partial fills keep Rx active.

## EXTEND

- ~~CAE sale tagging (pharmacy POS → PHARMACY_SALE_COMPLETED)~~ ✓
- ~~Prescriptions thin MVP (list/create/dispense status)~~ ✓
- ~~Product `requires_prescription` + POS Rx gate~~ ✓
- ~~Rx FEFO on manual dispense + POS qty caps / remaining~~ ✓
- ~~Partial-fill dispense UI / line qty fills~~ ✓
- ~~Prescriptions depth (categories UX)~~ ✓ (filter batches/Rx by inventory Category; demo Analgesics/Antibiotics)
- Demo seeder medicines/batches/Rx ✓
- Module features: `batches`, `prescriptions`, `expiry_alerts`
- ~~Dependencies: require `inventory` + `pos` when enabling~~ ✓ (seed + sync expand + runtime gate)

## Mapping keys (CAE)

`PHARMACY_SALES_REVENUE` — used when POS profile code is `PHARMACY` (or pharmacy module + batches capability).
