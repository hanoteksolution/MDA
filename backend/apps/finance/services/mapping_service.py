"""Semantic account mapping — resolves keys to tenant Account rows."""

from __future__ import annotations

from apps.finance.models import Account, AccountMapping
from apps.finance.services.chart_service import EXPENSE_CATEGORY_ACCOUNT
from core.tenancy import apply_tenant_scope


class MappingError(ValueError):
    pass


DEFAULT_MAPPING_SPECS = [
    ("DEFAULT_CASH", "1000"),
    ("DEFAULT_BANK", "1010"),
    ("DEFAULT_MOBILE_MONEY", "1020"),
    ("DEFAULT_RECEIVABLE", "1100"),
    ("DEFAULT_INVENTORY", "1200"),
    ("DEFAULT_PAYABLE", "2000"),
    ("DEFAULT_TAX_PAYABLE", "2100"),
    ("DEFAULT_EQUITY", "3000"),
    ("DEFAULT_SALES_REVENUE", "4000"),
    ("DEFAULT_SALES_RETURNS", "4000"),
    ("FUTSAL_REVENUE", "4100"),
    ("DEFAULT_COGS", "5000"),
    ("EXPENSE_UTILITIES", "6010"),
    ("EXPENSE_RENT", "6020"),
    ("EXPENSE_SUPPLIES", "6030"),
    ("EXPENSE_SALARIES", "6040"),
    ("EXPENSE_TRANSPORT", "6050"),
    ("EXPENSE_FOOD", "6060"),
    ("EXPENSE_MAINTENANCE", "6070"),
    ("FUTSAL_EXPENSE", "6080"),
    ("EXPENSE_OTHER", "6090"),
    ("PHARMACY_SALES_REVENUE", "4000"),
    ("GYM_MEMBERSHIP_REVENUE", "4000"),
    ("GYM_PERSONAL_TRAINING_REVENUE", "4000"),
    ("GYM_CLASS_REVENUE", "4000"),
    ("RESTAURANT_SALES_REVENUE", "4000"),
    ("HOTEL_ROOM_REVENUE", "4000"),
    ("HOTEL_SERVICE_REVENUE", "4000"),
    ("HOUSING_RENT_REVENUE", "4200"),
    ("OFFICE_RENT_REVENUE", "4200"),
    ("SECURITY_DEPOSIT_LIABILITY", "2200"),
    ("WHOLESALE_SALES_REVENUE", "4000"),
]

EXPENSE_CATEGORY_TO_MAPPING_KEY = {
    category: f"EXPENSE_{category.upper()}" if category != "other" else "EXPENSE_OTHER"
    for category in EXPENSE_CATEGORY_ACCOUNT
}
EXPENSE_CATEGORY_TO_MAPPING_KEY.update(
    {
        "utilities": "EXPENSE_UTILITIES",
        "rent": "EXPENSE_RENT",
        "supplies": "EXPENSE_SUPPLIES",
        "salaries": "EXPENSE_SALARIES",
        "transport": "EXPENSE_TRANSPORT",
        "food": "EXPENSE_FOOD",
        "maintenance": "EXPENSE_MAINTENANCE",
        "other": "EXPENSE_OTHER",
    }
)


class MappingService:
    @staticmethod
    def expense_mapping_key(category: str) -> str:
        return EXPENSE_CATEGORY_TO_MAPPING_KEY.get(category, "EXPENSE_OTHER")

    @staticmethod
    def resolve(*, key: str, tenant_id, business_type_code=None, user=None, request=None) -> Account:
        qs = apply_tenant_scope(AccountMapping.active_objects(), user=user, request=request)
        qs = qs.filter(tenant_id=tenant_id, mapping_key=key, is_active=True).select_related(
            "account"
        )
        if business_type_code:
            row = qs.filter(business_type_code=business_type_code).first()
            if row:
                return row.account
        row = qs.filter(business_type_code="").first()
        if row:
            return row.account
        raise MappingError(f"Account mapping '{key}' not found for tenant.")

    @staticmethod
    def seed_defaults(*, tenant_id, user=None):
        if not tenant_id:
            return []
        existing = AccountMapping.active_objects().filter(tenant_id=tenant_id).exists()
        if existing:
            MappingService._ensure_missing_and_upgrade(tenant_id=tenant_id, user=user)
            return list(AccountMapping.active_objects().filter(tenant_id=tenant_id))
        created = []
        for mapping_key, code in DEFAULT_MAPPING_SPECS:
            account = Account.active_objects().filter(tenant_id=tenant_id, code=code).first()
            if account is None:
                continue
            row = AccountMapping.objects.create(
                tenant_id=tenant_id,
                mapping_key=mapping_key,
                account=account,
                business_type_code="",
                is_active=True,
                created_by=user,
            )
            created.append(row)
        return created

    @staticmethod
    def _ensure_missing_and_upgrade(*, tenant_id, user=None):
        """Create missing keys; point BANK/MOBILE at 1010/1020 when still on Cash."""
        by_key = {
            m.mapping_key: m
            for m in AccountMapping.active_objects()
            .filter(tenant_id=tenant_id, business_type_code="")
            .select_related("account")
        }
        for mapping_key, code in DEFAULT_MAPPING_SPECS:
            account = Account.active_objects().filter(tenant_id=tenant_id, code=code).first()
            if account is None:
                continue
            row = by_key.get(mapping_key)
            if row is None:
                AccountMapping.objects.create(
                    tenant_id=tenant_id,
                    mapping_key=mapping_key,
                    account=account,
                    business_type_code="",
                    is_active=True,
                    created_by=user,
                )
                continue
            if mapping_key in ("DEFAULT_BANK", "DEFAULT_MOBILE_MONEY"):
                if row.account_id != account.id and row.account.code == "1000":
                    row.account = account
                    row.updated_by = user
                    row.save(update_fields=["account", "updated_by", "updated_at"])
