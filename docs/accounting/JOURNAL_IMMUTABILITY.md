# Posted Journal Immutability

**Date:** 2026-08-07  
**Status:** Enforced at model + service layer (STEP 37)

---

## Rule

Once a journal is **posted**, it must not be edited or soft-deleted. Corrections use `AccountingReversalService` (offsetting journal).

| Action | Allowed? |
|--------|----------|
| Create (draft → lines → post) | Yes |
| Update posted header/lines | No — `JOURNAL_POSTED_IMMUTABLE` |
| Soft-delete posted entry/lines | No |
| Reverse posted entry | Yes — new journal with `reverses_entry` |

## Implementation

- `JournalEntry.save` / `soft_delete` — block when prior/current status is `posted`
- `JournalLine.save` / `soft_delete` — block insert/update/delete when parent is `posted`
- `JournalService.create_entry` — create as `draft`, attach lines, promote to `posted`
- `JournalService.assert_mutable` — service-level guard (`code=JOURNAL_POSTED_IMMUTABLE`)
- Escape hatch: `force_posted_mutation=True` / `_force_posted_mutation` (ops only; not used by APIs)

`QuerySet.update()` bypasses model `save`; prefer service APIs. Optional DB triggers can be added later.
