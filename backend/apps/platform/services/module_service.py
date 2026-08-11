"""Tenant module enablement helpers (STEP 08 + PHASE 03–05)."""

from __future__ import annotations

from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.platform.models import Module, Tenant, TenantModule
from apps.platform.services.module_dependency_service import (
    ModuleDependencyError,
    ModuleDependencyService,
)
from core.tenancy import is_platform_unscoped_actor, resolve_acting_tenant

# Seed catalog — codes aligned with BusinessType.default_modules / presets.
# tuple: code, name, category, description, sort_order, deps, route, flags dict
MODULE_SEEDS = [
    (
        "pos",
        "Point of Sale",
        "core",
        "Checkout, holds, and receipts",
        10,
        [],
        "/pos",
        {"is_core": True, "supports_pos": True, "supports_mobile": True},
    ),
    (
        "inventory",
        "Inventory",
        "core",
        "Stock, warehouses, products, categories",
        20,
        [],
        "/inventory",
        {"is_core": True, "supports_inventory": True},
    ),
    (
        "sales",
        "Sales",
        "core",
        "Invoices, quotations, customers, daily ops",
        30,
        [],
        "/sales",
        {"is_core": True},
    ),
    (
        "purchases",
        "Purchases",
        "core",
        "Purchase orders and suppliers",
        40,
        [],
        "/purchases",
        {"is_core": True, "supports_inventory": True},
    ),
    (
        "pharmacy",
        "Pharmacy",
        "industry",
        "Prescription and batch controls",
        100,
        ["inventory", "pos"],
        "/pharmacy",
        {"supports_pos": True, "supports_inventory": True, "supports_mobile": True},
    ),
    (
        "restaurant",
        "Restaurant / Cafeteria",
        "industry",
        "Floor / kitchen flows",
        110,
        ["pos"],
        "/restaurant",
        {"supports_pos": True, "supports_inventory": True, "supports_mobile": True},
    ),
    (
        "hotel",
        "Hotel",
        "industry",
        "Rooms, reservations, folios",
        115,
        [],
        "/hotel",
        {"supports_pos": True, "supports_inventory": False, "supports_mobile": True},
    ),
    (
        "property_management",
        "Property Management",
        "industry",
        "Properties, buildings, units, maintenance",
        140,
        [],
        "/property",
        {"supports_pos": False, "supports_inventory": False, "supports_mobile": True},
    ),
    (
        "housing_rental",
        "Housing Rental",
        "industry",
        "Residential leases (requires property core)",
        141,
        ["property_management"],
        "/housing",
        {"supports_pos": False, "supports_mobile": True},
    ),
    (
        "office_rental",
        "Office Rental",
        "industry",
        "Commercial leases (requires property core)",
        142,
        ["property_management"],
        "/office",
        {"supports_pos": False, "supports_mobile": True},
    ),
    (
        "gym",
        "Gym",
        "industry",
        "Memberships and attendance",
        120,
        [],
        "/gym",
        {"supports_pos": True, "supports_mobile": True},
    ),
    (
        "futsal",
        "Futsal",
        "industry",
        "Courts, bookings, and teams",
        130,
        [],
        "/futsal",
        {"supports_mobile": False},
    ),
    (
        "project_management",
        "Project Management",
        "industry",
        "Projects, budgets, tasks, BOQ, workforce, and cost control",
        150,
        ["inventory", "purchases", "sales"],
        "/project",
        {"supports_inventory": True, "supports_mobile": True},
    ),
    (
        "travel_agency",
        "Travel Agency",
        "industry",
        "Bookings, tours, flights, hotels, visa, and travel finance",
        160,
        ["sales", "purchases"],
        "/travel",
        {"supports_mobile": True},
    ),
]

# API path prefix → required module code (first match wins).
MODULE_PATH_PREFIXES: list[tuple[str, str]] = [
    ("/api/v1/futsal/", "futsal"),
    ("/api/v1/pharmacy/", "pharmacy"),
    ("/api/v1/gym/", "gym"),
    ("/api/v1/restaurant/", "restaurant"),
    ("/api/v1/hotel/", "hotel"),
    ("/api/v1/property/", "property_management"),
    ("/api/v1/projects/", "project_management"),
    ("/api/v1/travel/", "travel_agency"),
    ("/api/v1/housing/", "housing_rental"),
    ("/api/v1/office/", "office_rental"),
    ("/api/v1/pos/", "pos"),
    ("/api/v1/sales/", "sales"),
    ("/api/v1/purchases/", "purchases"),
    ("/api/v1/suppliers/", "purchases"),
    ("/api/v1/inventory/", "inventory"),
    ("/api/v1/warehouses/", "inventory"),
    ("/api/v1/products/", "inventory"),
    ("/api/v1/categories/", "inventory"),
    ("/api/v1/brands/", "inventory"),
    ("/api/v1/units/", "inventory"),
    ("/api/v1/customers/", "sales"),
]


def ensure_default_modules() -> None:
    for code, name, category, description, sort_order, deps, route, flags in MODULE_SEEDS:
        Module.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "category": category,
                "description": description,
                "sort_order": sort_order,
                "is_active": True,
                "dependencies": list(deps),
                "optional_dependencies": [],
                "route": route,
                "dashboard_route": route,
                "is_core": bool(flags.get("is_core")),
                "supports_mobile": bool(flags.get("supports_mobile")),
                "supports_pos": bool(flags.get("supports_pos")),
                "supports_inventory": bool(flags.get("supports_inventory")),
                "supports_finance": True,
            },
        )


def default_module_codes_for_tenant(tenant: Tenant) -> list[str]:
    # Prefer preset snapshot if present
    settings_row = getattr(tenant, "settings", None)
    if settings_row and isinstance(settings_row.extras, dict):
        preset_code = settings_row.extras.get("preset_used_code")
        if preset_code:
            from apps.platform.services.business_preset_service import BusinessPresetService

            preset = BusinessPresetService.resolve(code=preset_code)
            if preset:
                return BusinessPresetService.module_codes(preset)
    bt = getattr(tenant, "business_type", None)
    codes = list(bt.default_modules or []) if bt is not None else []
    if not codes:
        codes = ["pos", "inventory", "sales", "purchases"]
    return codes


@transaction.atomic
def sync_tenant_modules(
    *,
    tenant: Tenant,
    enabled_codes: Iterable[str] | None = None,
    user=None,
    disable_missing: bool = False,
    validate_dependencies: bool = True,
) -> list[TenantModule]:
    """Ensure TenantModule rows exist. Optionally set enabled from a code list."""
    ensure_default_modules()
    if enabled_codes is None:
        enabled_codes = default_module_codes_for_tenant(tenant)
    wanted_raw = {str(c).strip().lower() for c in enabled_codes if c}
    if validate_dependencies:
        wanted = ModuleDependencyService.validate_enable_set(wanted_raw)
        if disable_missing:
            ModuleDependencyService.validate_disable(enabled_after=wanted)
    else:
        wanted = wanted_raw

    modules = {m.code: m for m in Module.active_objects().filter(is_active=True)}
    now = timezone.now()
    rows: list[TenantModule] = []
    for code, module in modules.items():
        enabled = code in wanted
        link, created = TenantModule.objects.get_or_create(
            tenant=tenant,
            module=module,
            defaults={
                "enabled": enabled,
                "created_by": user,
                "enabled_at": now if enabled else None,
                "enabled_by": user if enabled else None,
            },
        )
        if not created:
            if enabled and not link.enabled:
                link.enabled = True
                link.enabled_at = now
                link.enabled_by = user
                link.disabled_at = None
                link.disabled_by = None
                link.updated_by = user
                link.save(
                    update_fields=[
                        "enabled",
                        "enabled_at",
                        "enabled_by",
                        "disabled_at",
                        "disabled_by",
                        "updated_by",
                        "updated_at",
                    ]
                )
            elif disable_missing and not enabled and link.enabled:
                link.enabled = False
                link.disabled_at = now
                link.disabled_by = user
                link.updated_by = user
                link.save(
                    update_fields=[
                        "enabled",
                        "disabled_at",
                        "disabled_by",
                        "updated_by",
                        "updated_at",
                    ]
                )
        rows.append(link)
    from apps.platform.services.module_feature_service import ModuleFeatureService

    for link in rows:
        if link.enabled:
            ModuleFeatureService.seed_defaults(link)
    return rows


def enabled_module_codes(*, tenant=None, user=None, request=None) -> set[str]:
    """Return enabled module codes for the acting tenant (empty if none)."""
    if tenant is None:
        tenant = resolve_acting_tenant(request=request, user=user)
    if tenant is None:
        return set()
    return set(
        TenantModule.active_objects()
        .filter(tenant_id=tenant.pk, enabled=True, module__is_active=True, module__deleted_at__isnull=True)
        .values_list("module__code", flat=True)
    )


def tenant_has_module(code: str, *, tenant=None, user=None, request=None) -> bool:
    code = (code or "").strip().lower()
    if not code:
        return True
    actor = user or (getattr(request, "user", None) if request is not None else None)
    if is_platform_unscoped_actor(actor):
        return True
    if tenant is None:
        tenant = resolve_acting_tenant(request=request, user=user)
    if tenant is None:
        return False
    from apps.platform.services.entitlement_service import EntitlementService

    if not EntitlementService.plan_includes_module(tenant=tenant, module_code=code):
        return False
    return TenantModule.active_objects().filter(
        tenant_id=tenant.pk,
        module__code=code,
        module__is_active=True,
        enabled=True,
    ).exists()


def missing_module_dependencies(
    code: str,
    *,
    tenant=None,
    user=None,
    request=None,
    enabled: set[str] | None = None,
) -> list[str]:
    """Required (transitive) dependency codes that are not currently enabled."""
    code = (code or "").strip().lower()
    if not code:
        return []
    actor = user or (getattr(request, "user", None) if request is not None else None)
    if is_platform_unscoped_actor(actor):
        return []
    if enabled is None:
        enabled = enabled_module_codes(tenant=tenant, user=user, request=request)
    needed = ModuleDependencyService.expand_with_dependencies([code]) - {code}
    return sorted(d for d in needed if d not in enabled)


def tenant_module_ready(code: str, *, tenant=None, user=None, request=None) -> bool:
    """True when the module is enabled *and* all required dependencies are enabled."""
    code = (code or "").strip().lower()
    if not code:
        return True
    if not tenant_has_module(code, tenant=tenant, user=user, request=request):
        return False
    return not missing_module_dependencies(code, tenant=tenant, user=user, request=request)


def usable_module_codes(*, tenant=None, user=None, request=None) -> set[str]:
    """Enabled modules whose required dependencies are also enabled."""
    actor = user or (getattr(request, "user", None) if request is not None else None)
    if is_platform_unscoped_actor(actor):
        return {seed[0] for seed in MODULE_SEEDS}
    enabled = enabled_module_codes(tenant=tenant, user=user, request=request)
    return {
        code
        for code in enabled
        if not missing_module_dependencies(
            code, tenant=tenant, user=user, request=request, enabled=enabled
        )
    }


def module_required_for_path(path: str) -> str | None:
    path = path or ""
    for prefix, code in MODULE_PATH_PREFIXES:
        if path.startswith(prefix):
            return code
    return None


def module_payload(module: Module) -> dict:
    from apps.platform.services.module_feature_service import ModuleFeatureService

    return {
        "id": str(module.id),
        "code": module.code,
        "name": module.name,
        "description": module.description,
        "category": module.category,
        "is_active": module.is_active,
        "sort_order": module.sort_order,
        "route": module.route or "",
        "dashboard_route": module.dashboard_route or module.route or "",
        "icon": module.icon or "",
        "dependencies": list(module.dependencies or []),
        "optional_dependencies": list(module.optional_dependencies or []),
        "is_core": bool(module.is_core),
        "supports_mobile": bool(module.supports_mobile),
        "supports_pos": bool(module.supports_pos),
        "supports_inventory": bool(module.supports_inventory),
        "supports_finance": bool(module.supports_finance),
        "feature_catalog": ModuleFeatureService.catalog_for(module.code),
    }


def tenant_module_payload(link: TenantModule) -> dict:
    from apps.platform.services.module_feature_service import ModuleFeatureService

    features = (
        ModuleFeatureService.resolve_from_link(link, link.module.code)
        if link.enabled
        else {k: False for k in ModuleFeatureService.known_codes(link.module.code)}
    )
    return {
        **module_payload(link.module),
        "enabled": link.enabled,
        "tenant_module_id": str(link.id),
        "configuration": link.configuration or {},
        "features": features,
        "enabled_at": link.enabled_at.isoformat() if link.enabled_at else None,
        "disabled_at": link.disabled_at.isoformat() if link.disabled_at else None,
    }


# Re-export for callers
__all__ = [
    "MODULE_SEEDS",
    "MODULE_PATH_PREFIXES",
    "ModuleDependencyError",
    "ensure_default_modules",
    "default_module_codes_for_tenant",
    "sync_tenant_modules",
    "enabled_module_codes",
    "usable_module_codes",
    "tenant_has_module",
    "tenant_module_ready",
    "missing_module_dependencies",
    "module_required_for_path",
    "module_payload",
    "tenant_module_payload",
]
