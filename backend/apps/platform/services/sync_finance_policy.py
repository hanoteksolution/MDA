"""Explicit finance boundaries for shop ↔ cloud sync (STEP 29)."""

from __future__ import annotations

# Shop push may include operational sales data only — never authoritative finance ledgers.
FINANCE_SYNC_RULES = {
    "push_allowed": frozenset({"customers", "invoices", "inventory", "waiters", "kpis", "device_id", "company_name", "synced_at", "branch_code"}),
    "push_forbidden": frozenset(
        {
            "journal_entries",
            "accounts",
            "payments",
            "finance_summary",
            "expenses",
            "ledger",
        }
    ),
    "invoice_fields_allowed": frozenset(
        {
            "invoice_number",
            "issue_date",
            "status",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "amount_paid",
            "customer_code",
            "customer_name",
            "notes",
            "updated_at",
            "items",
            "idempotency_key",
            "device_id",
            "local_id",
        }
    ),
    "notes": (
        "Synced invoices update cloud sales totals only. "
        "General ledger / journal posting remains a cloud-side or manual finance workflow."
    ),
}


class SyncFinancePolicy:
    @staticmethod
    def validate_push_payload(payload: dict) -> list[str]:
        """Return list of rejected top-level keys (for logging/tests)."""
        rejected = []
        for key in payload.keys():
            if key in FINANCE_SYNC_RULES["push_forbidden"]:
                rejected.append(key)
        return rejected

    @staticmethod
    def sanitize_push_payload(payload: dict) -> dict:
        """Strip forbidden finance keys before ingest."""
        cleaned = dict(payload)
        for key in FINANCE_SYNC_RULES["push_forbidden"]:
            cleaned.pop(key, None)
        return cleaned

    @staticmethod
    def public_rules() -> dict:
        return {
            "push_allowed": sorted(FINANCE_SYNC_RULES["push_allowed"]),
            "push_forbidden": sorted(FINANCE_SYNC_RULES["push_forbidden"]),
            "notes": FINANCE_SYNC_RULES["notes"],
        }
