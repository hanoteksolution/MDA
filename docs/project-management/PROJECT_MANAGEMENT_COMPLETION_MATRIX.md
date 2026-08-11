# PROJECT MANAGEMENT COMPLETION MATRIX

Status key: `COMPLETE` | `PARTIAL` | `MISSING` | `BLOCKED`

## Phase Snapshot

| Phase | Scope | Status |
|---|---|---|
| 1–25 | Core PM through billing + GL posting | COMPLETE |
| 26 | Project portfolio reports | COMPLETE |
| 27 | Mobile field workflows (web + API + Expo) | COMPLETE |
| 28 | PO/GRN/Inventory project dimensions | COMPLETE |
| 29 | API unit coverage | COMPLETE |

## Entity Matrix

| Entity | Status |
|---|---|
| Projects, Budgets, WBS, Tasks, Milestones | COMPLETE |
| Construction (Site/Building/Floor/Unit) | COMPLETE |
| BOQ, Workforce, Attendance, Daily Wages (rate snapshot) | COMPLETE |
| Material Requests, Equipment, Expenses, Change Orders | COMPLETE |
| Site Reports, Quality, Safety, Risks, Issues | COMPLETE |
| Project Invoices + central GL posting | COMPLETE |
| Purchase Orders (project/WBS dimension) | COMPLETE |
| Goods Receipts → Project Inventory Allocations | COMPLETE |
| Mobile Field API + `/project/field` + Expo Field Ops | COMPLETE |
| Portfolio reports `/project/portfolio` + shared `/project/reports` | COMPLETE |
| Documents | COMPLETE via shared document/engine workspace capability |

## Notes

- Daily wage `rate_applied` is historical snapshot.
- Project invoice posting uses `AccountingPostingService` (`PROJECT_INVOICE_ISSUED`).
- Project inventory allocations live at `/project/allocations` (shared stock engine remains `/project/inventory`).
