# Account Mapping

**Date:** 2026-08-07  
**Status:** Target design — Phase 08

---

## 1. Problem

Today, finance code hardcodes account codes:

```python
# chart_service.py
cash_account = ChartService.get_by_code(code="1000", ...)
expense_account = ChartService.get_by_code(code=category_code, ...)

# EXPENSE_CATEGORY_ACCOUNT dict maps expense.category → "6010" etc.
```

This breaks when:

- Tenants customize their chart of accounts
- Business types need different revenue accounts (gym vs pharmacy vs restaurant)
- Multi-currency or multi-branch cash accounts are added

---

## 2. Solution — semantic mapping keys

Business modules and posting rules reference **keys**, not IDs or codes.

```
PostingRule: credit_mapping_key = "DEFAULT_SALES_REVENUE"
                          ↓
AccountMapping: tenant + key → Account row
                          ↓
JournalLine.account_id = resolved UUID
```

---

## 3. Standard mapping keys

### Core (all business types)

| Key | Default account code | Type | Control |
|-----|-------------------|------|---------|
| `DEFAULT_CASH` | 1000 | Asset | |
| `DEFAULT_BANK` | 1010 | Asset | |
| `DEFAULT_MOBILE_MONEY` | 1020 | Asset | |
| `DEFAULT_RECEIVABLE` | 1100 | Asset | Yes |
| `DEFAULT_INVENTORY` | 1200 | Asset | Yes |
| `DEFAULT_PAYABLE` | 2000 | Liability | Yes |
| `DEFAULT_TAX_PAYABLE` | 2100 | Liability | Sales tax collected |
| `DEFAULT_EQUITY` | 3000 | Equity | |
| `DEFAULT_SALES_REVENUE` | 4000 | Revenue | |
| `DEFAULT_SALES_RETURNS` | 4000 | Revenue | contra |
| `FUTSAL_REVENUE` | 4100 | Revenue | Court / booking income |
| `DEFAULT_COGS` | 5000 | Expense | |
| `DEFAULT_TAX_PAYABLE` | (future) | Liability | |
| `DEFAULT_TAX_RECEIVABLE` | (future) | Asset | |

### Expense categories

| Key | Default code |
|-----|--------------|
| `EXPENSE_UTILITIES` | 6010 |
| `EXPENSE_RENT` | 6020 |
| `EXPENSE_SUPPLIES` | 6030 |
| `EXPENSE_SALARIES` | 6040 |
| `EXPENSE_TRANSPORT` | 6050 |
| `EXPENSE_FOOD` | 6060 |
| `EXPENSE_MAINTENANCE` | 6070 |
| `EXPENSE_OTHER` | 6090 |

Maps 1:1 from existing `EXPENSE_CATEGORY_ACCOUNT` dict — migrate to DB rows.

### Industry-specific revenue

| Key | Used by |
|-----|---------|
| `PHARMACY_SALES_REVENUE` | Pharmacy POS |
| `GYM_MEMBERSHIP_REVENUE` | Gym checkout |
| `GYM_PERSONAL_TRAINING_REVENUE` | Gym PT |
| `GYM_CLASS_REVENUE` | Gym classes |
| `RESTAURANT_SALES_REVENUE` | Restaurant POS |
| `WHOLESALE_SALES_REVENUE` | Wholesale |

If industry key not configured, fall back to `DEFAULT_SALES_REVENUE`.

---

## 4. AccountMapping model

```python
class AccountMapping(TenantScopedModel, BaseModel):
    mapping_key = models.CharField(max_length=50, db_index=True)
    account = models.ForeignKey(Account, on_delete=PROTECT)
    business_type_code = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["tenant", "mapping_key", "business_type_code"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_account_mapping",
            )
        ]
```

Resolution order:

1. `(tenant, key, tenant.business_type)` — specific override
2. `(tenant, key, "")` — tenant default
3. System template for business type
4. System global default
5. Raise `MappingError` — never silently post to wrong account

---

## 5. MappingService (proposed)

```python
class MappingService:
    @staticmethod
    def resolve(*, key: str, tenant_id, business_type_code=None) -> Account:
        ...

    @staticmethod
    def seed_defaults(*, tenant_id, business_type_code=None):
        """Called from ChartService.ensure_default_chart after CoA bootstrap."""
        ...

    @staticmethod
    def set_mapping(*, tenant_id, key, account_id, business_type_code=""):
        """Admin API for tenant customization."""
        ...
```

---

## 6. Payment method → mapping key

POS tenders map to asset accounts:

| Payment method | Mapping key |
|----------------|-------------|
| `cash` | `DEFAULT_CASH` |
| `card` | `DEFAULT_BANK` |
| `mobile` | `DEFAULT_MOBILE_MONEY` |
| `bank` | `DEFAULT_BANK` |
| `on_account` | `DEFAULT_RECEIVABLE` |
| `split` | Per payment row in `payments[]` |

Posting rule conditions:

```json
{"payment_method": "on_account"}  → receivable rule
{"payment_method__in": ["cash","card","mobile"]}  → cash rule
```

---

## 7. Tenant customization rules

- System accounts (`is_system=True`) cannot be deleted
- Mapping may point to tenant-created accounts (e.g. custom "Petty Cash" for `DEFAULT_CASH`)
- Changing a mapping affects **future** postings only — never retroactive
- UI: Finance → Settings → Account Mappings (web-first)

---

## 8. Migration from hardcoded dict

| Current | Target |
|---------|--------|
| `EXPENSE_CATEGORY_ACCOUNT` dict | `AccountMapping` rows seeded on chart bootstrap |
| `get_by_code("1000")` in `post_expense` | `MappingService.resolve("DEFAULT_CASH")` |
| `get_by_code("4000")` (future POS) | `MappingService.resolve("DEFAULT_SALES_REVENUE")` |

Keep dict as fallback during transition with deprecation warning.

---

## 9. API

```
GET  /api/v1/finance/mappings/
PUT  /api/v1/finance/mappings/{key}/
GET  /api/v1/finance/mappings/keys/   # list available semantic keys
```

Permissions: `accounting.accounts.update` or dedicated `accounting.mappings.manage`.

---

*See also: [POSTING_ENGINE.md](./POSTING_ENGINE.md), [ACCOUNTING_ERD.md](./ACCOUNTING_ERD.md)*
