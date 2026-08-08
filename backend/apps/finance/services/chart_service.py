"""Chart of accounts bootstrap and balances (STEP 21)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from apps.finance.models import Account, JournalEntry, JournalLine
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class ChartError(ValueError):
    pass


CONTROL_ACCOUNT_CODES = frozenset({"1100", "1200", "2000"})


DEFAULT_ACCOUNTS = [
    ("1000", "Cash", Account.TYPE_ASSET, True),
    ("1010", "Bank", Account.TYPE_ASSET, True),
    ("1020", "Mobile Money", Account.TYPE_ASSET, True),
    ("1100", "Accounts Receivable", Account.TYPE_ASSET, True),
    ("1200", "Inventory", Account.TYPE_ASSET, True),
    ("2000", "Accounts Payable", Account.TYPE_LIABILITY, True),
    ("2100", "Tax Payable", Account.TYPE_LIABILITY, True),
    ("2200", "Security Deposits Liability", Account.TYPE_LIABILITY, True),
    ("3000", "Owner's Equity", Account.TYPE_EQUITY, True),
    ("4000", "Sales Revenue", Account.TYPE_REVENUE, True),
    ("4100", "Futsal Revenue", Account.TYPE_REVENUE, True),
    ("4200", "Rental Revenue", Account.TYPE_REVENUE, True),
    ("5000", "Cost of Goods Sold", Account.TYPE_EXPENSE, True),
    ("6000", "Operating Expenses", Account.TYPE_EXPENSE, True),
    ("6010", "Utilities Expense", Account.TYPE_EXPENSE, True),
    ("6020", "Rent Expense", Account.TYPE_EXPENSE, True),
    ("6030", "Supplies Expense", Account.TYPE_EXPENSE, True),
    ("6040", "Salaries Expense", Account.TYPE_EXPENSE, True),
    ("6050", "Transport Expense", Account.TYPE_EXPENSE, True),
    ("6060", "Food & Beverage Expense", Account.TYPE_EXPENSE, True),
    ("6070", "Maintenance Expense", Account.TYPE_EXPENSE, True),
    ("6080", "Futsal Operating Expense", Account.TYPE_EXPENSE, True),
    ("6090", "Other Operating Expense", Account.TYPE_EXPENSE, True),
]

EXPENSE_CATEGORY_ACCOUNT = {
    "utilities": "6010",
    "rent": "6020",
    "supplies": "6030",
    "salaries": "6040",
    "transport": "6050",
    "food": "6060",
    "maintenance": "6070",
    "other": "6090",
}


class ChartService:
    @staticmethod
    def list(*, account_type=None, is_active=None, user=None, request=None):
        qs = Account.active_objects().select_related("parent")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if account_type:
            qs = qs.filter(account_type=account_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("code")

    @staticmethod
    def get_by_code(*, code, tenant_id, user=None, request=None):
        qs = apply_tenant_scope(Account.active_objects(), user=user, request=request)
        account = qs.filter(code=code).first()
        if account is None and tenant_id:
            account = Account.active_objects().filter(tenant_id=tenant_id, code=code).first()
        if account is None:
            raise ChartError(f"Account '{code}' not found.")
        return account

    @staticmethod
    def account_balance(*, account: Account, user=None, request=None) -> Decimal:
        lines = JournalLine.active_objects().filter(
            account=account,
            entry__status=JournalEntry.STATUS_POSTED,
            entry__deleted_at__isnull=True,
        )
        lines = lines.filter(entry__tenant_id=account.tenant_id)
        agg = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
        debit = agg["d"] or Decimal("0")
        credit = agg["c"] or Decimal("0")
        if account.normal_debit:
            return debit - credit
        return credit - debit

    @staticmethod
    def serialize(account: Account, *, balance=None) -> dict:
        if balance is None:
            balance = ChartService.account_balance(account=account)
        return {
            "id": str(account.id),
            "code": account.code,
            "name": account.name,
            "type": account.account_type,
            "parent_id": str(account.parent_id) if account.parent_id else None,
            "is_system": account.is_system,
            "is_active": account.is_active,
            "balance": float(balance),
        }

    @staticmethod
    @transaction.atomic
    def ensure_default_chart(*, tenant_id, user=None, request=None):
        if not tenant_id:
            return []
        existing = Account.active_objects().filter(tenant_id=tenant_id).count()
        if existing:
            ChartService._ensure_control_flags(tenant_id=tenant_id)
            ChartService._ensure_standard_accounts(tenant_id=tenant_id, user=user)
            from apps.finance.services.mapping_service import MappingService

            MappingService.seed_defaults(tenant_id=tenant_id, user=user)
            from apps.finance.services.cost_center_service import CostCenterService

            CostCenterService.seed_defaults(tenant_id=tenant_id, user=user)
            from apps.finance.services.business_unit_service import BusinessUnitService

            BusinessUnitService.seed_defaults(tenant_id=tenant_id, user=user)
            return list(Account.active_objects().filter(tenant_id=tenant_id).order_by("code"))
        created = []
        for code, name, account_type, is_system in DEFAULT_ACCOUNTS:
            row = Account.objects.create(
                tenant_id=tenant_id,
                code=code,
                name=name,
                account_type=account_type,
                is_system=is_system,
                is_active=True,
                is_control_account=code in CONTROL_ACCOUNT_CODES,
                allow_manual_posting=code not in CONTROL_ACCOUNT_CODES,
                created_by=user,
            )
            created.append(row)
        from apps.finance.services.mapping_service import MappingService

        MappingService.seed_defaults(tenant_id=tenant_id, user=user)
        from apps.finance.services.cost_center_service import CostCenterService

        CostCenterService.seed_defaults(tenant_id=tenant_id, user=user)
        from apps.finance.services.business_unit_service import BusinessUnitService

        BusinessUnitService.seed_defaults(tenant_id=tenant_id, user=user)
        return created

    @staticmethod
    def _ensure_control_flags(*, tenant_id):
        Account.active_objects().filter(tenant_id=tenant_id, code__in=CONTROL_ACCOUNT_CODES).update(
            is_control_account=True,
            allow_manual_posting=False,
        )

    @staticmethod
    def _ensure_standard_accounts(*, tenant_id, user=None):
        """Add any missing default CoA rows (e.g. Bank / Mobile Money split)."""
        existing_codes = set(
            Account.active_objects().filter(tenant_id=tenant_id).values_list("code", flat=True)
        )
        for code, name, account_type, is_system in DEFAULT_ACCOUNTS:
            if code in existing_codes:
                continue
            Account.objects.create(
                tenant_id=tenant_id,
                code=code,
                name=name,
                account_type=account_type,
                is_system=is_system,
                is_active=True,
                is_control_account=code in CONTROL_ACCOUNT_CODES,
                allow_manual_posting=code not in CONTROL_ACCOUNT_CODES,
                created_by=user,
            )
        # Soft rename legacy combined cash account when still named Cash & Bank
        Account.active_objects().filter(
            tenant_id=tenant_id, code="1000", name="Cash & Bank"
        ).update(name="Cash")

    @staticmethod
    def list_with_balances(*, user=None, request=None):
        ChartService.ensure_default_chart(
            tenant_id=_resolve_tenant_id(user=user, request=request),
            user=user,
            request=request,
        )
        rows = []
        for account in ChartService.list(is_active=True, user=user, request=request):
            rows.append(ChartService.serialize(account))
        return rows


def _resolve_tenant_id(*, user=None, request=None):
    payload = stamp_tenant_id({}, user=user, request=request)
    return payload.get("tenant_id")
