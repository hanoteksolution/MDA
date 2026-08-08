"""Business preset catalog + apply-to-tenant helpers (PHASE 06)."""

from __future__ import annotations

from django.db import transaction

from apps.platform.models import BusinessPreset, BusinessPresetModule, BusinessType, Module
from apps.platform.services.module_service import ensure_default_modules, sync_tenant_modules
from apps.platform.services.platform_service import PlatformService


class PresetError(ValueError):
    def __init__(self, message: str, *, code: str = "PRESET_ERROR"):
        super().__init__(message)
        self.code = code


# Extra multi-module presets beyond 1:1 business-type seeds.
EXTRA_PRESET_SEEDS = [
    {
        "code": "gym_cafeteria",
        "name": "Gym + Cafeteria",
        "description": "Fitness center with food service",
        "business_type_code": "gym",
        "modules": ["pos", "inventory", "sales", "gym", "restaurant"],
        "sort_order": 105,
    },
    {
        "code": "hotel_basic",
        "name": "Hotel Basic",
        "description": "Rooms, reservations, and folios",
        "business_type_code": "hotel",
        "modules": ["pos", "inventory", "sales", "hotel"],
        "sort_order": 106,
    },
    {
        "code": "hotel_restaurant",
        "name": "Hotel + Restaurant",
        "description": "Lodging with food service and POS",
        "business_type_code": "hotel",
        "modules": ["pos", "inventory", "sales", "hotel", "restaurant"],
        "sort_order": 107,
    },
    {
        "code": "property_residential",
        "name": "Property Residential",
        "description": "Property core + housing rental module",
        "business_type_code": "property",
        "modules": ["property_management", "housing_rental"],
        "sort_order": 108,
    },
    {
        "code": "property_commercial",
        "name": "Property Commercial",
        "description": "Property core + office rental module",
        "business_type_code": "property",
        "modules": ["property_management", "office_rental"],
        "sort_order": 109,
    },
    {
        "code": "property_mixed",
        "name": "Property Mixed",
        "description": "Property core with housing and office rental",
        "business_type_code": "property",
        "modules": ["property_management", "housing_rental", "office_rental"],
        "sort_order": 110,
    },
    {
        "code": "custom",
        "name": "Custom Business",
        "description": "Start empty — select modules manually",
        "business_type_code": None,
        "modules": [],
        "sort_order": 900,
    },
]


class BusinessPresetService:
    @staticmethod
    @transaction.atomic
    def ensure_default_presets() -> None:
        PlatformService.ensure_default_business_types()
        ensure_default_modules()
        modules = {m.code: m for m in Module.active_objects().filter(is_active=True)}

        for bt in BusinessType.active_objects().filter(is_active=True):
            preset, _ = BusinessPreset.objects.get_or_create(
                code=bt.code,
                defaults={
                    "name": bt.name,
                    "description": bt.description or f"Starter pack for {bt.name}",
                    "business_type": bt,
                    "version": 1,
                    "is_system": True,
                    "is_active": True,
                    "sort_order": bt.sort_order,
                },
            )
            if preset.business_type_id != bt.id:
                preset.business_type = bt
                preset.save(update_fields=["business_type", "updated_at"])
            codes = list(bt.default_modules or [])
            BusinessPresetService._sync_preset_modules(preset, codes, modules)

        for spec in EXTRA_PRESET_SEEDS:
            bt = None
            if spec.get("business_type_code"):
                bt = BusinessType.active_objects().filter(code=spec["business_type_code"]).first()
            preset, _ = BusinessPreset.objects.update_or_create(
                code=spec["code"],
                defaults={
                    "name": spec["name"],
                    "description": spec.get("description") or "",
                    "business_type": bt,
                    "version": 1,
                    "is_system": True,
                    "is_active": True,
                    "sort_order": spec.get("sort_order", 100),
                },
            )
            BusinessPresetService._sync_preset_modules(preset, spec.get("modules") or [], modules)

    @staticmethod
    def _sync_preset_modules(preset: BusinessPreset, codes: list, modules: dict) -> None:
        wanted = [str(c).strip().lower() for c in codes if c]
        for order, code in enumerate(wanted):
            module = modules.get(code)
            if module is None:
                continue
            BusinessPresetModule.objects.update_or_create(
                preset=preset,
                module=module,
                defaults={
                    "is_required": False,
                    "is_default": True,
                    "display_order": (order + 1) * 10,
                },
            )
        # Soft-remove modules no longer in seed (do not hard-delete historical rows)
        BusinessPresetModule.active_objects().filter(preset=preset).exclude(
            module__code__in=wanted
        ).update(is_default=False)

    @staticmethod
    def list_presets(*, business_type_code: str | None = None):
        BusinessPresetService.ensure_default_presets()
        qs = (
            BusinessPreset.active_objects()
            .filter(is_active=True)
            .select_related("business_type")
            .prefetch_related("preset_modules__module")
            .order_by("sort_order", "name")
        )
        if business_type_code:
            qs = qs.filter(business_type__code=str(business_type_code).strip().lower())
        return qs

    @staticmethod
    def resolve(*, code: str | None = None, preset_id=None) -> BusinessPreset | None:
        BusinessPresetService.ensure_default_presets()
        if preset_id:
            return BusinessPreset.active_objects().filter(pk=preset_id).first()
        if code:
            return BusinessPreset.active_objects().filter(
                code=str(code).strip().lower(), is_active=True
            ).first()
        return None

    @staticmethod
    def module_codes(preset: BusinessPreset) -> list[str]:
        return list(
            BusinessPresetModule.active_objects()
            .filter(preset=preset, is_default=True)
            .order_by("display_order")
            .values_list("module__code", flat=True)
        )

    @staticmethod
    def serialize(preset: BusinessPreset) -> dict:
        codes = BusinessPresetService.module_codes(preset)
        return {
            "id": str(preset.id),
            "code": preset.code,
            "name": preset.name,
            "description": preset.description or "",
            "icon": preset.icon or "",
            "version": preset.version,
            "is_system": preset.is_system,
            "business_type_code": (
                preset.business_type.code if preset.business_type_id else None
            ),
            "modules": codes,
            "sort_order": preset.sort_order,
        }

    @staticmethod
    @transaction.atomic
    def apply_to_tenant(*, tenant, preset: BusinessPreset, user=None, extra_modules=None):
        """Copy preset modules onto tenant (snapshot). Does not bind tenant to preset."""
        codes = set(BusinessPresetService.module_codes(preset))
        if extra_modules:
            codes |= {str(c).strip().lower() for c in extra_modules if c}
        sync_tenant_modules(
            tenant=tenant,
            enabled_codes=codes,
            user=user,
            disable_missing=True,
            validate_dependencies=True,
        )
        # Audit snapshot on settings extras (no live FK)
        settings_row = getattr(tenant, "settings", None)
        if settings_row is None:
            from apps.platform.models import TenantSettings

            settings_row, _ = TenantSettings.objects.get_or_create(
                tenant=tenant, defaults={"created_by": user}
            )
        extras = dict(settings_row.extras or {})
        extras["preset_used_code"] = preset.code
        extras["preset_version_used"] = preset.version
        settings_row.extras = extras
        settings_row.updated_by = user
        settings_row.save(update_fields=["extras", "updated_by", "updated_at"])
        return sorted(codes)
