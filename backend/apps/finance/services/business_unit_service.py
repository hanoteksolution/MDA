"""Business unit dimension for multi-module P&L (PHASE 09)."""

from __future__ import annotations

from django.db import transaction

from apps.finance.models import BusinessUnit
from core.tenancy import apply_tenant_scope, stamp_tenant_id

# (code, name, module_code)
DEFAULT_BUSINESS_UNITS = (
    ("RETAIL", "Retail / POS", "pos"),
    ("GYM", "Gym", "gym"),
    ("PHARM", "Pharmacy", "pharmacy"),
    ("REST", "Restaurant", "restaurant"),
    ("HOTEL", "Hotel", "hotel"),
    ("PROP", "Property / Rental", "property_management"),
    ("CORP", "Corporate / Shared", ""),
)

# Map AccountingEvent / journal source_module → BusinessUnit.code
SOURCE_MODULE_TO_BU = {
    "pos": "RETAIL",
    "sales": "RETAIL",
    "gym": "GYM",
    "pharmacy": "PHARM",
    "restaurant": "REST",
    "hotel": "HOTEL",
    "housing_rental": "PROP",
    "office_rental": "PROP",
    "property_management": "PROP",
    "property": "PROP",
}


class BusinessUnitError(ValueError):
    def __init__(self, message: str, *, code: str = "BUSINESS_UNIT_ERROR"):
        super().__init__(message)
        self.code = code


class BusinessUnitService:
    @staticmethod
    def list(*, is_active=None, user=None, request=None, tenant_id=None):
        qs = BusinessUnit.active_objects()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        else:
            qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("sort_order", "code")

    @staticmethod
    def serialize(bu: BusinessUnit) -> dict:
        return {
            "id": str(bu.id),
            "code": bu.code,
            "name": bu.name,
            "module_code": bu.module_code or "",
            "is_active": bu.is_active,
            "description": bu.description or "",
            "sort_order": bu.sort_order,
        }

    @staticmethod
    def get(
        *,
        business_unit_id=None,
        code=None,
        tenant_id=None,
        user=None,
        request=None,
    ) -> BusinessUnit:
        qs = BusinessUnit.active_objects()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        else:
            qs = apply_tenant_scope(qs, user=user, request=request)
        if business_unit_id:
            bu = qs.filter(pk=business_unit_id).first()
        elif code:
            bu = qs.filter(code=str(code).strip().upper()).first()
        else:
            raise BusinessUnitError(
                "business_unit_id or code required.", code="BUSINESS_UNIT_LOOKUP"
            )
        if bu is None:
            raise BusinessUnitError(
                "Business unit not found.", code="BUSINESS_UNIT_NOT_FOUND"
            )
        return bu

    @staticmethod
    def resolve_for_line(*, row: dict, tenant_id, user=None, request=None) -> BusinessUnit | None:
        bu_id = row.get("business_unit_id")
        bu_code = row.get("business_unit_code")
        if not bu_id and not bu_code:
            return None
        return BusinessUnitService.get(
            business_unit_id=bu_id,
            code=bu_code,
            tenant_id=tenant_id,
            user=user,
            request=request,
        )

    @staticmethod
    def resolve_for_source_module(
        *, source_module: str, tenant_id, user=None
    ) -> BusinessUnit | None:
        code = SOURCE_MODULE_TO_BU.get((source_module or "").strip().lower())
        if not code or not tenant_id:
            return None
        BusinessUnitService.seed_defaults(tenant_id=tenant_id, user=user)
        return (
            BusinessUnit.active_objects()
            .filter(tenant_id=tenant_id, code=code, is_active=True)
            .first()
        )

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> BusinessUnit:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id") or data.get("tenant_id")
        if not tenant_id:
            raise BusinessUnitError("Tenant required.", code="BUSINESS_UNIT_NO_TENANT")
        code = (data.get("code") or "").strip().upper()
        name = (data.get("name") or "").strip()
        if not code or not name:
            raise BusinessUnitError(
                "Code and name are required.", code="BUSINESS_UNIT_INVALID"
            )
        if BusinessUnit.active_objects().filter(tenant_id=tenant_id, code=code).exists():
            raise BusinessUnitError(
                f"Business unit '{code}' already exists.",
                code="BUSINESS_UNIT_DUPLICATE",
            )
        return BusinessUnit.objects.create(
            tenant_id=tenant_id,
            code=code,
            name=name,
            module_code=(data.get("module_code") or "").strip().lower(),
            description=data.get("description") or "",
            is_active=data.get("is_active", True) is not False,
            sort_order=int(data.get("sort_order") or 100),
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def seed_defaults(*, tenant_id, user=None) -> list[BusinessUnit]:
        if not tenant_id:
            return []
        created = []
        for idx, (code, name, module_code) in enumerate(DEFAULT_BUSINESS_UNITS):
            existing = (
                BusinessUnit.active_objects()
                .filter(tenant_id=tenant_id, code=code)
                .first()
            )
            if existing:
                continue
            created.append(
                BusinessUnit.objects.create(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    module_code=module_code,
                    is_active=True,
                    sort_order=10 + idx * 10,
                    created_by=user,
                )
            )
        return created
