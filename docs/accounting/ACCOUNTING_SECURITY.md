# Accounting Security

**Date:** 2026-08-07  
**Status:** Target design — Phase 37

---

## 1. Principles

- **Backend enforces all permissions** — frontend visibility is not authorization
- **Tenant isolation** on every query via `apply_tenant_scope`
- **Posted journals immutable** — corrections require reversal permission
- **Control accounts protected** from casual manual posting
- **Period close** requires elevated permission
- **GL data never synced from untrusted shop clients** (`SyncFinancePolicy`)
- **Audit trail** on create/post/reverse/close actions

---

## 2. Permission codenames (target)

Extend `bootstrap_roles_and_permissions`:

### Accounts

| Codename | Description |
|----------|-------------|
| `accounting.accounts.view` | List CoA, balances |
| `accounting.accounts.create` | Add custom accounts |
| `accounting.accounts.update` | Edit non-system accounts |
| `accounting.accounts.deactivate` | Deactivate accounts |

### Journals

| Codename | Description |
|----------|-------------|
| `accounting.journals.view` | List/read journals |
| `accounting.journals.create` | Create draft/manual entries |
| `accounting.journals.approve` | Approve pending entries |
| `accounting.journals.post` | Post draft entries |
| `accounting.journals.reverse` | Create reversal entries |
| `accounting.journals.post_control` | Manual post to control accounts |

### Periods

| Codename | Description |
|----------|-------------|
| `accounting.periods.view` | List periods |
| `accounting.periods.close` | Close period |
| `accounting.periods.reopen` | Reopen closed period |
| `accounting.periods.post_soft_closed` | Post to soft-closed period |

### AR / AP / Vouchers

| Codename | Description |
|----------|-------------|
| `accounting.receivables.view` | AR sub-ledger |
| `accounting.payables.view` | AP sub-ledger |
| `accounting.vouchers.create` | Payment/receipt/journal vouchers |
| `accounting.vouchers.approve` | Approve vouchers |

### Reconciliation & reports

| Codename | Description |
|----------|-------------|
| `accounting.reconciliation.manage` | Bank rec, AR/AP rec |
| `accounting.reports.view` | Official financial reports |
| `accounting.health.view` | Accounting integrity dashboard |
| `accounting.events.retry` | Retry failed posting events |

### Mappings & rules (admin)

| Codename | Description |
|----------|-------------|
| `accounting.mappings.manage` | Account mapping config |
| `accounting.rules.manage` | Posting rule config |

---

## 3. Migration from current permissions

| Current | Target |
|---------|--------|
| `finance.view` | `accounting.accounts.view` + `accounting.journals.view` + `accounting.reports.view` |
| `finance.create` | `accounting.journals.create` |

Keep `finance.*` as aliases during transition for backward compatibility.

Role defaults:

| Role | Permissions |
|------|-------------|
| admin | All accounting.* |
| branch_manager | view, reports, vouchers.create, journals.create (no period close) |
| cashier | none (POS posts automatically; no manual journal) |
| accountant (new) | full except rules.manage |

---

## 4. API enforcement

Every finance API view:

```python
permission_classes = [IsAuthenticated, HasPermission("accounting.journals.view")]
```

Posting service checks:

```python
if manual and account.is_control_account:
    require_perm(user, "accounting.journals.post_control")
```

Period service checks:

```python
if period.status == CLOSED:
    require_perm(user, "accounting.periods.post_soft_closed")  # or deny
```

---

## 5. Tenant isolation

- All models: `TenantScopedModel`
- `JournalService.create_entry`: resolves tenant from user/request — never from body alone
- Cross-tenant account IDs in journal lines → rejected
- Platform admin: explicit `all_tenants()` for support tools only

Existing tests: `test_finance_step21.py` tenant isolation — extend for all new endpoints.

---

## 6. Immutability enforcement

```python
# In JournalService — block updates to posted entries
if entry.status == JournalEntry.STATUS_POSTED:
    raise JournalError("Posted entries cannot be modified.")
```

Soft-delete posted entries: **forbidden** — use reversal.

Database: optional trigger or application-level guard on `JournalLine` UPDATE where entry.status = posted.

---

## 7. Sync security

`SyncFinancePolicy` (STEP 29) — **KEEP**:

- Shop push: invoices, inventory, customers — allowed
- Shop push: journals, accounts, expenses, ledger — **rejected**

Cloud is authoritative for GL. Document in tenant admin guide.

---

## 8. Sensitive operations audit

Log to `AuditLog` (existing app):

| Action | Fields |
|--------|--------|
| journal.posted | entry_id, user, tenant |
| journal.reversed | original_id, reversal_id |
| period.closed | period_id, user |
| mapping.changed | key, old_account, new_account |
| failed_event.retried | event_id, user |

---

## 9. Rate limiting

Apply DRF throttling to:

- Manual journal create (prevent spam)
- Report export endpoints
- Failed event retry

Existing STEP 27 throttling infrastructure applies.

---

## 10. Production checks

- Decimal fields only for amounts (already enforced)
- No float accumulation in posting engine
- Secret keys for sync remain out of journal payloads

---

*See also: [CENTRAL_ACCOUNTING_ARCHITECTURE.md](./CENTRAL_ACCOUNTING_ARCHITECTURE.md), [ACCOUNTING_TESTING.md](./ACCOUNTING_TESTING.md)*
