# Accounting Testing

**Date:** 2026-08-07  
**Status:** Target test plan — Phase 39

---

## 1. Existing coverage (STEP 21)

File: `backend/tests/unit/test_finance_step21.py`

| Test | Validates |
|------|-----------|
| `test_bootstrap_default_chart` | 16 accounts seeded per tenant |
| `test_balanced_manual_journal` | Manual entry debit = credit |
| `test_rejects_unbalanced_journal` | JournalError on imbalance |
| `test_expense_posts_balanced_journal` | Dr expense / Cr cash |
| `test_expense_posting_idempotent` | Duplicate post returns same entry |
| `test_daily_ops_create_posts_journal` | End-to-end expense bridge |
| `test_summary_includes_ledger` | FinanceSummaryService KPIs |
| `test_tenant_isolation` | Cross-tenant account access blocked |

Also: `test_sync_step29.py` — finance keys rejected from sync push.

---

## 2. Mandatory integration tests (target)

Create `backend/tests/integration/accounting/`:

### Module → accounting flows

| Test file | Flow |
|-----------|------|
| `test_pos_to_accounting.py` | POS checkout → SALE_COMPLETED → journal → GL balance |
| `test_refund_reversal.py` | Refund → SALE_REFUNDED → reversal journal |
| `test_pharmacy_pos_accounting.py` | Batch sale via POS → pharmacy revenue mapping |
| `test_gym_membership_accounting.py` | Gym checkout → membership revenue journal |
| `test_purchase_to_ap.py` | Receive PO → Dr Inventory / Cr AP |
| `test_customer_payment_ar.py` | AR invoice + payment → settlement journal |
| `test_supplier_payment_ap.py` | AP payment → Dr AP / Cr Bank |
| `test_expense_accounting.py` | Expense create/update/delete journal behavior |
| `test_inventory_writeoff.py` | Write-off event → expense journal |

### Engine integrity

| Test | Validates |
|------|-----------|
| `test_debit_equals_credit` | All automated postings balanced |
| `test_no_duplicate_posting` | Same idempotency_key → one journal |
| `test_tenant_isolation_accounting` | Tenant A cannot see/post to Tenant B |
| `test_closed_period_blocked` | Post to locked period → error |
| `test_posted_journal_immutable` | UPDATE posted line → error |
| `test_account_mapping_resolution` | Semantic key → correct tenant account |
| `test_ar_reconciliation` | AR sub-ledger = control account 1100 |
| `test_ap_reconciliation` | AP sub-ledger = control account 2000 |
| `test_inventory_gl_reconciliation` | Inventory asset vs valuation |
| `test_source_traceability` | journal.source_id → invoice navigable |

---

## 3. Unit test structure

```
backend/tests/unit/accounting/
  test_chart_service.py         # extend existing
  test_journal_service.py       # extend existing
  test_posting_service.py       # NEW
  test_mapping_service.py       # NEW
  test_period_service.py        # NEW
  test_reversal_service.py      # NEW
  test_posting_rules.py         # NEW
  test_selectors_trial_balance.py
  test_selectors_profit_loss.py
```

Keep `test_finance_step21.py` — extend, do not delete (regression guard).

---

## 4. Test fixtures

Extend `tests/helpers/shop_factory.py`:

```python
def create_with_ledger(tenant, ...):
    shop = ShopFactory.create(...)
    ChartService.ensure_default_chart(tenant_id=shop.tenant.id)
    MappingService.seed_defaults(tenant_id=shop.tenant.id)
    PeriodService.ensure_open_period(tenant_id=shop.tenant.id)
    return shop
```

Shared helpers:

```python
def assert_journal_balanced(entry):
    ...

def assert_gl_balance(account_code, expected, tenant_id):
    ...

def assert_one_journal_for(source_module, source_type, source_id):
    ...
```

---

## 5. Pytest markers

```ini
# pytest.ini
markers =
    accounting: Central accounting engine tests
    accounting_critical: Money-path integration tests
```

Makefile targets:

```makefile
test-accounting:
	pytest -m accounting -q

test-accounting-critical:
	pytest -m accounting_critical -q
```

---

## 6. Example integration test (POS)

```python
@pytest.mark.django_db
@pytest.mark.accounting_critical
def test_pos_checkout_posts_sale_journal(api_client, retail_shop, auth_client):
    inv_before = account_balance("4000", retail_shop.tenant)

    response = auth_client.post("/api/v1/pos/checkout/", payload, format="json")
    assert response.status_code == 201

    invoice_id = response.json()["data"]["invoice"]["id"]
    journal = JournalEntry.objects.get(
        source_type="invoice",
        source_id=invoice_id,
        status="posted",
    )
    assert_journal_balanced(journal)

    inv_after = account_balance("4000", retail_shop.tenant)
    assert inv_after - inv_before == Decimal("100.00")
```

---

## 7. CI requirements

- `test-accounting-critical` runs on every PR touching `apps/finance/` or `pos_service.py`
- Full `test-accounting` runs nightly
- Staging smoke: `scripts/smoke_deploy.sh` adds optional GL health check

---

## 8. Accounting health monitor tests

When integrity dashboard ships:

```python
def test_health_detects_unposted_sale():
    # Create invoice without journal (simulate failure)
    # Health check reports "business without journal"

def test_health_detects_ar_mismatch():
    # AR sub-ledger != control account
```

---

## 9. Coverage goals

| Area | Target |
|------|--------|
| Posting engine core | 95%+ |
| POS → GL integration | 100% critical paths |
| Reversal | 100% |
| Period enforcement | 100% |
| Selectors (reports) | 90%+ |

---

## 10. Test data migration verification

After historical backfill (see MIGRATION_PLAN):

```python
def test_backfill_journals_balance_to_invoices():
    # Sum revenue journals ≈ sum paid invoices (within tolerance)
```

---

*See also: [ACCOUNTING_MIGRATION_PLAN.md](./ACCOUNTING_MIGRATION_PLAN.md), [docs/TESTING.md](../TESTING.md)*
