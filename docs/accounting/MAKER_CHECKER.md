# Maker-Checker (Manual Journals)

**Date:** 2026-08-07  
**Status:** STEP 37 — draft → approve → post

---

## Flow

```text
Maker  (finance.create)
   │  POST /finance/journal/   → status=draft
   ▼
Draft journal (mutable / discardable)
   │  POST /finance/journal/{id}/post/   (finance.approve)
   ▼
Posted journal (immutable)
```

Automated module posting (POS, expense, purchase, …) still creates **posted** journals immediately — no maker-checker.

## Rules

| Rule | Code |
|------|------|
| Maker ≠ checker by default | `JOURNAL_MAKER_CHECKER` |
| Solo override | `allow_self_approve: true` on post body |
| Only drafts can be posted/discarded | `JOURNAL_NOT_DRAFT` |
| Discard soft-deletes draft + lines | `POST …/discard/` |

## Permission

- `finance.approve` — approve/post drafts (admin, accountant, branch_manager, shop_group_manager)

## Fields

`JournalEntry.approved_by`, `JournalEntry.approved_at`
