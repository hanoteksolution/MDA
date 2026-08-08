"""Cost center dimension for journal lines."""

from __future__ import annotations

from django.db import transaction

from apps.finance.models import CostCenter
from core.tenancy import apply_tenant_scope, stamp_tenant_id

DEFAULT_COST_CENTERS = (
    ("HQ", "Headquarters"),
    ("OPS", "Operations"),
    ("SALES", "Sales"),
)


class CostCenterError(ValueError):
    def __init__(self, message: str, *, code: str = "COST_CENTER_ERROR"):
        super().__init__(message)
        self.code = code


class CostCenterService:
    @staticmethod
    def list(*, is_active=None, user=None, request=None, tenant_id=None):
        qs = CostCenter.active_objects().select_related("parent")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        else:
            qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("code")

    @staticmethod
    def serialize(cc: CostCenter) -> dict:
        return {
            "id": str(cc.id),
            "code": cc.code,
            "name": cc.name,
            "parent_id": str(cc.parent_id) if cc.parent_id else None,
            "is_active": cc.is_active,
            "description": cc.description or "",
        }

    @staticmethod
    def get(*, cost_center_id=None, code=None, tenant_id=None, user=None, request=None) -> CostCenter:
        qs = CostCenter.active_objects()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        else:
            qs = apply_tenant_scope(qs, user=user, request=request)
        if cost_center_id:
            cc = qs.filter(pk=cost_center_id).first()
        elif code:
            cc = qs.filter(code=code).first()
        else:
            raise CostCenterError("cost_center_id or code required.", code="COST_CENTER_LOOKUP")
        if cc is None:
            raise CostCenterError("Cost center not found.", code="COST_CENTER_NOT_FOUND")
        return cc

    @staticmethod
    def resolve_for_line(*, row: dict, tenant_id, user=None, request=None) -> CostCenter | None:
        cc_id = row.get("cost_center_id")
        cc_code = row.get("cost_center_code")
        if not cc_id and not cc_code:
            return None
        return CostCenterService.get(
            cost_center_id=cc_id,
            code=cc_code,
            tenant_id=tenant_id,
            user=user,
            request=request,
        )

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, request=None) -> CostCenter:
        payload = stamp_tenant_id({}, user=user, request=request)
        tenant_id = payload.get("tenant_id") or data.get("tenant_id")
        if not tenant_id:
            raise CostCenterError("Tenant required.", code="COST_CENTER_NO_TENANT")
        code = (data.get("code") or "").strip().upper()
        name = (data.get("name") or "").strip()
        if not code or not name:
            raise CostCenterError("Code and name are required.", code="COST_CENTER_INVALID")
        if CostCenter.active_objects().filter(tenant_id=tenant_id, code=code).exists():
            raise CostCenterError(f"Cost center '{code}' already exists.", code="COST_CENTER_DUPLICATE")
        return CostCenter.objects.create(
            tenant_id=tenant_id,
            code=code,
            name=name,
            parent_id=data.get("parent_id"),
            description=data.get("description") or "",
            is_active=data.get("is_active", True) is not False,
            created_by=user,
        )

    @staticmethod
    @transaction.atomic
    def seed_defaults(*, tenant_id, user=None) -> list[CostCenter]:
        if not tenant_id:
            return []
        created = []
        for code, name in DEFAULT_COST_CENTERS:
            existing = CostCenter.active_objects().filter(tenant_id=tenant_id, code=code).first()
            if existing:
                continue
            created.append(
                CostCenter.objects.create(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    is_active=True,
                    created_by=user,
                )
            )
        return created
