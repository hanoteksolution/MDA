# Testing Strategy

## Backend (KEEP expanding `backend/tests/`)

| Layer | Required for “complete” |
|---|---|
| Model / service | Constraints, workflows, Dr=Cr |
| API | List/Create/Retrieve/Update/Delete + approve/post/cancel |
| Permission | 403 without code; elevated admin bypass |
| Tenant isolation | Cross-tenant 404/empty |
| Accounting | Every money workflow: TB still balances |

Existing CAE tests are the template (`test_pos_accounting_step35`, `test_gym_accounting_step35`, `test_pharmacy_cae_step54`).

New vertical U/D APIs must ship with tests in the same PR.

## Frontend

Today: `tsc -b` only. Add (Phase 29):

- Vitest: `useWorkspaceTab`, `filterVisibleWorkspaces`, `postLoginPath`, form validation
- Component: Create button visibility vs permissions
- Playwright E2E: login → hub → restaurant POS alias; gym member create; journal draft post

## E2E business flows

Create → View → Update → Archive/Cancel → (finance) Post → Reverse.  
Never “button exists” without API assertion.

## Accounting assertions

Restaurant sale, gym membership, pharmacy sale, hotel folio settle, rent invoice, PO receive, supplier payment, expense: **sum(debit) == sum(credit)** on resulting journals.
