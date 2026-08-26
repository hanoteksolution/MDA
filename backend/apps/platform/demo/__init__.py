"""Modular demo data seeders (PHASE 10–11).

Each seeder is opt-in when the matching TenantModule is enabled.
Industry seeders and shared POS/catalog seeders all run when selected.
"""

from __future__ import annotations

from django.db import transaction

from apps.platform.demo import catalog as catalog_demo
from apps.platform.demo import gym as gym_demo
from apps.platform.demo import hotel as hotel_demo
from apps.platform.demo import housing as housing_demo
from apps.platform.demo import office as office_demo
from apps.platform.demo import pharmacy as pharmacy_demo
from apps.platform.demo import pos as pos_demo
from apps.platform.demo import property as property_demo
from apps.platform.demo import purchases as purchases_demo
from apps.platform.demo import restaurant as restaurant_demo
from apps.platform.demo import sales as sales_demo
from apps.platform.services.module_service import enabled_module_codes


def seed_core(*, tenant, user=None) -> dict:
    """Always runs for demos — foundation already provisioned by create_shop."""
    return {"core": {"ok": True}}


def seed_finance(*, tenant, user=None) -> dict:
    return {"finance": {"skipped": True, "reason": "CoA via provision"}}


def seed_pos(*, tenant, user=None) -> dict:
    from apps.platform.services.module_service import enabled_module_codes

    codes = enabled_module_codes(tenant=tenant)
    module_code = "retail"
    for industry in ("gym", "pharmacy", "hotel", "futsal", "restaurant"):
        if industry in codes:
            module_code = industry
            break
    return pos_demo.seed(tenant=tenant, user=user, module_code=module_code)


def seed_inventory(*, tenant, user=None) -> dict:
    from apps.platform.services.module_service import enabled_module_codes

    codes = enabled_module_codes(tenant=tenant)
    module_code = "retail"
    for industry in ("gym", "pharmacy", "hotel", "futsal", "restaurant"):
        if industry in codes:
            module_code = industry
            break
    return catalog_demo.seed(tenant=tenant, user=user, module_code=module_code)


def seed_sales(*, tenant, user=None) -> dict:
    from apps.platform.services.module_service import enabled_module_codes

    codes = enabled_module_codes(tenant=tenant)
    module_code = "retail"
    for industry in ("gym", "pharmacy", "hotel", "futsal", "restaurant"):
        if industry in codes:
            module_code = industry
            break
    return sales_demo.seed(tenant=tenant, user=user, module_code=module_code)


def seed_purchases(*, tenant, user=None) -> dict:
    from apps.platform.services.module_service import enabled_module_codes

    codes = enabled_module_codes(tenant=tenant)
    module_code = "retail"
    for industry in ("gym", "pharmacy", "hotel", "futsal", "restaurant"):
        if industry in codes:
            module_code = industry
            break
    return purchases_demo.seed(tenant=tenant, user=user, module_code=module_code)


def seed_gym(*, tenant, user=None) -> dict:
    return gym_demo.seed(tenant=tenant, user=user)


def seed_pharmacy(*, tenant, user=None) -> dict:
    return pharmacy_demo.seed(tenant=tenant, user=user)


def seed_restaurant(*, tenant, user=None) -> dict:
    return restaurant_demo.seed(tenant=tenant, user=user)


def seed_hotel(*, tenant, user=None) -> dict:
    return hotel_demo.seed(tenant=tenant, user=user)


def seed_property_management(*, tenant, user=None) -> dict:
    return property_demo.seed(tenant=tenant, user=user)


def seed_property(*, tenant, user=None) -> dict:
    """Alias for older demo registry key."""
    return seed_property_management(tenant=tenant, user=user)


def seed_housing_rental(*, tenant, user=None) -> dict:
    return housing_demo.seed(tenant=tenant, user=user)


def seed_office_rental(*, tenant, user=None) -> dict:
    return office_demo.seed(tenant=tenant, user=user)


SEEDERS = {
    "core": seed_core,
    "finance": seed_finance,
    "pos": seed_pos,
    "inventory": seed_inventory,
    "sales": seed_sales,
    "purchases": seed_purchases,
    "gym": seed_gym,
    "pharmacy": seed_pharmacy,
    "restaurant": seed_restaurant,
    "hotel": seed_hotel,
    "property_management": seed_property_management,
    "property": seed_property,
    "housing_rental": seed_housing_rental,
    "office_rental": seed_office_rental,
}

# Shared engines first so industry seeders can reuse catalog rows.
_SEED_PRIORITY = (
    "inventory",
    "pos",
    "sales",
    "purchases",
    "gym",
    "pharmacy",
    "restaurant",
    "hotel",
    "property_management",
    "property",
    "housing_rental",
    "office_rental",
    "futsal",
    "travel_agency",
    "project_management",
)


def _ordered_codes(codes: set[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for code in _SEED_PRIORITY:
        if code in codes and code not in seen:
            ordered.append(code)
            seen.add(code)
    for code in sorted(codes):
        if code not in seen and code != "core":
            ordered.append(code)
            seen.add(code)
    return ordered


def generate_demo_data(*, tenant, user=None, modules: list[str] | None = None) -> dict:
    """Run modular seeders for enabled (or requested) modules.

    Always unions requested codes with currently enabled TenantModules so
    multi-module demos (e.g. gym + restaurant + POS) all get data.
    Each seeder runs in a savepoint so one failure does not wipe the rest.
    """
    codes = set(enabled_module_codes(tenant=tenant))
    if modules is not None:
        codes |= {str(c).strip().lower() for c in modules if c}
    try:
        from apps.platform.services.module_service import _settings_extras

        extras = _settings_extras(tenant)
        provisioned = extras.get("provisioned_modules") or extras.get("demo_seed_modules")
        if isinstance(provisioned, list):
            codes |= {str(c).strip().lower() for c in provisioned if c}
    except Exception:  # noqa: BLE001 — extras optional
        pass

    report: dict = {"modules": sorted(codes), "results": {}}
    report["results"].update(seed_core(tenant=tenant, user=user))

    with transaction.atomic():
        for code in _ordered_codes(codes):
            fn = SEEDERS.get(code)
            if not fn:
                report["results"][code] = {"skipped": True, "reason": "no seeder"}
                continue
            sid = transaction.savepoint()
            try:
                report["results"].update(fn(tenant=tenant, user=user))
                transaction.savepoint_commit(sid)
            except Exception as exc:  # noqa: BLE001 — isolate seeder failures
                transaction.savepoint_rollback(sid)
                report["results"][code] = {"seeded": False, "error": str(exc)[:400]}
    return report
