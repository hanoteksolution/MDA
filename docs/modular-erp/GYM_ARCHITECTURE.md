# Gym Architecture

**Date:** 2026-08-07  
**Status:** KEEP / EXTEND existing `apps/gym`

---

## Existing

Members, plans, subscriptions, attendance, trainers, classes, workouts  
API `/api/v1/gym/` · FE `modules/gym` · RN `mobile/gym-member/`  
Accounting:
- `GYM_MEMBERSHIP_SOLD` via CAE (membership checkout)
- `GYM_SERVICE_SOLD` via CAE:
  - PT session → `GYM_PERSONAL_TRAINING_REVENUE`
  - Class drop-in → `GYM_CLASS_REVENUE` (`POST /gym/class-bookings/<id>/checkout/`)

Module code: `gym`

---

## EXTEND (done / open)

- ~~Demo seeder `demo/gym.py`~~ ✓
- ~~PT session → Invoice + CAE~~ ✓
- ~~Class drop-in → Invoice + CAE~~ ✓ (`GymClass.drop_in_price`)
- ModuleFeature flags (classes, PT, lockers, access control)
- Dashboard widgets for main ERP home
- Optional POS profile for membership retail

## Not required

Separate GymAccounting ledger — **forbidden**.
