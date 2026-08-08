"""Per-module feature flags stored on TenantModule.configuration (PHASE 16 / STEP 37–68).

Catalog lives in code; tenant overrides live in
`TenantModule.configuration["features"]` — no parallel feature table.
Missing keys default to catalog `is_default` (True for pharmacy + gym).
"""

from __future__ import annotations

from typing import Any

from apps.platform.models import TenantModule
from core.tenancy import is_platform_unscoped_actor, resolve_acting_tenant

# code → [{code, name, is_default, is_required}]
MODULE_FEATURE_CATALOG: dict[str, list[dict[str, Any]]] = {
    "pharmacy": [
        {
            "code": "batches",
            "name": "Batches / FEFO",
            "is_default": True,
            "is_required": False,
        },
        {
            "code": "prescriptions",
            "name": "Prescriptions",
            "is_default": True,
            "is_required": False,
        },
        {
            "code": "expiry_alerts",
            "name": "Expiry alerts",
            "is_default": True,
            "is_required": False,
        },
    ],
    "gym": [
        {
            "code": "members",
            "name": "Members & memberships",
            "is_default": True,
            "is_required": False,
        },
        {
            "code": "classes",
            "name": "Classes",
            "is_default": True,
            "is_required": False,
        },
        {
            "code": "attendance",
            "name": "Attendance / check-in",
            "is_default": True,
            "is_required": False,
        },
    ],
}


class ModuleFeatureError(ValueError):
    def __init__(self, message: str, *, code: str = "MODULE_FEATURE"):
        super().__init__(message)
        self.code = code


class ModuleFeatureService:
    @staticmethod
    def catalog_for(module_code: str) -> list[dict[str, Any]]:
        code = (module_code or "").strip().lower()
        return list(MODULE_FEATURE_CATALOG.get(code) or [])

    @staticmethod
    def known_codes(module_code: str) -> set[str]:
        return {str(row["code"]) for row in ModuleFeatureService.catalog_for(module_code)}

    @staticmethod
    def default_map(module_code: str) -> dict[str, bool]:
        return {
            str(row["code"]): bool(row.get("is_default", True))
            for row in ModuleFeatureService.catalog_for(module_code)
        }

    @staticmethod
    def _normalize_stored(raw) -> dict[str, bool]:
        if not isinstance(raw, dict):
            return {}
        out: dict[str, bool] = {}
        for key, val in raw.items():
            code = str(key).strip().lower()
            if not code:
                continue
            out[code] = bool(val)
        return out

    @staticmethod
    def resolve_from_link(link: TenantModule | None, module_code: str) -> dict[str, bool]:
        catalog = ModuleFeatureService.catalog_for(module_code)
        if not catalog:
            return {}
        stored = {}
        if link is not None:
            cfg = link.configuration or {}
            stored = ModuleFeatureService._normalize_stored(cfg.get("features"))
        out: dict[str, bool] = {}
        for row in catalog:
            code = str(row["code"])
            if code in stored:
                out[code] = stored[code]
            else:
                out[code] = bool(row.get("is_default", True))
        if out.get("batches") is False and "expiry_alerts" in out:
            out["expiry_alerts"] = False
        return out

    @staticmethod
    def _link(*, module_code: str, tenant=None, user=None, request=None) -> TenantModule | None:
        if tenant is None:
            tenant = resolve_acting_tenant(request=request, user=user)
        if tenant is None:
            return None
        return (
            TenantModule.active_objects()
            .filter(
                tenant_id=tenant.pk,
                module__code=module_code,
                module__is_active=True,
                enabled=True,
            )
            .select_related("module")
            .first()
        )

    @staticmethod
    def resolve_features(
        module_code: str, *, tenant=None, user=None, request=None
    ) -> dict[str, bool]:
        code = (module_code or "").strip().lower()
        actor = user or (getattr(request, "user", None) if request is not None else None)
        if is_platform_unscoped_actor(actor):
            return ModuleFeatureService.default_map(code) or {}
        link = ModuleFeatureService._link(
            module_code=code, tenant=tenant, user=user, request=request
        )
        if link is None:
            return {k: False for k in ModuleFeatureService.known_codes(code)}
        return ModuleFeatureService.resolve_from_link(link, code)

    @staticmethod
    def tenant_has_feature(
        module_code: str, feature: str, *, tenant=None, user=None, request=None
    ) -> bool:
        feature = (feature or "").strip().lower()
        if not feature:
            return True
        actor = user or (getattr(request, "user", None) if request is not None else None)
        if is_platform_unscoped_actor(actor):
            return True
        known = ModuleFeatureService.known_codes(module_code)
        if known and feature not in known:
            return False
        if not known:
            return True
        features = ModuleFeatureService.resolve_features(
            module_code, tenant=tenant, user=user, request=request
        )
        return bool(features.get(feature))

    @staticmethod
    def seed_defaults(link: TenantModule) -> bool:
        """Fill missing feature keys on an enabled TenantModule. Returns True if saved."""
        if link is None or not link.enabled:
            return False
        catalog = ModuleFeatureService.catalog_for(link.module.code)
        if not catalog:
            return False
        cfg = dict(link.configuration or {})
        features = ModuleFeatureService._normalize_stored(cfg.get("features"))
        changed = False
        for row in catalog:
            code = str(row["code"])
            if code not in features:
                features[code] = bool(row.get("is_default", True))
                changed = True
        if not changed:
            return False
        cfg["features"] = features
        link.configuration = cfg
        link.save(update_fields=["configuration", "updated_at"])
        return True

    @staticmethod
    def set_features(
        *,
        tenant,
        module_code: str,
        features: dict,
        user=None,
    ) -> dict[str, bool]:
        code = (module_code or "").strip().lower()
        catalog = ModuleFeatureService.catalog_for(code)
        if not catalog:
            raise ModuleFeatureError(f"Module '{code}' has no feature catalog.")
        known = {str(row["code"]) for row in catalog}
        incoming = ModuleFeatureService._normalize_stored(features)
        unknown = sorted(k for k in incoming if k not in known)
        if unknown:
            raise ModuleFeatureError(
                f"Unknown feature(s) for {code}: {', '.join(unknown)}."
            )
        link = (
            TenantModule.active_objects()
            .filter(tenant_id=tenant.pk, module__code=code)
            .select_related("module")
            .first()
        )
        if link is None or not link.enabled:
            raise ModuleFeatureError(f"Module '{code}' is not enabled.")
        cfg = dict(link.configuration or {})
        current = ModuleFeatureService._normalize_stored(cfg.get("features"))
        for row in catalog:
            fcode = str(row["code"])
            if fcode not in current:
                current[fcode] = bool(row.get("is_default", True))
        current.update(incoming)
        if current.get("batches") is False:
            current["expiry_alerts"] = False
        cfg["features"] = current
        link.configuration = cfg
        link.updated_by = user
        link.save(update_fields=["configuration", "updated_by", "updated_at"])
        return ModuleFeatureService.resolve_from_link(link, code)

    @staticmethod
    def features_by_module(*, tenant=None, user=None, request=None) -> dict[str, dict[str, bool]]:
        """Resolved feature maps for enabled catalog modules that define features."""
        from apps.platform.services.module_service import usable_module_codes

        actor = user or (getattr(request, "user", None) if request is not None else None)
        if is_platform_unscoped_actor(actor):
            return {
                code: ModuleFeatureService.default_map(code)
                for code in MODULE_FEATURE_CATALOG
            }
        enabled = usable_module_codes(tenant=tenant, user=user, request=request)
        out: dict[str, dict[str, bool]] = {}
        for code in MODULE_FEATURE_CATALOG:
            if code in enabled:
                out[code] = ModuleFeatureService.resolve_features(
                    code, tenant=tenant, user=user, request=request
                )
        return out
