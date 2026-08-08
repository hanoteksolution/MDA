"""Modular demo data seeders (PHASE 10–11).

Each seeder is opt-in when the matching TenantModule is enabled.
Property / Office stubs stay empty until those verticals ship.
"""

from __future__ import annotations

from apps.platform.demo import gym as gym_demo
from apps.platform.demo import hotel as hotel_demo
from apps.platform.demo import housing as housing_demo
from apps.platform.demo import office as office_demo
from apps.platform.demo import pharmacy as pharmacy_demo
from apps.platform.demo import property as property_demo
from apps.platform.demo import restaurant as restaurant_demo
from apps.platform.services.module_service import enabled_module_codes


def seed_core(*, tenant, user=None) -> dict:
    """Always runs for demos — foundation already provisioned by create_shop."""
    return {"core": {"ok": True}}


def seed_finance(*, tenant, user=None) -> dict:
    return {"finance": {"skipped": True, "reason": "stub — CoA via provision"}}


def seed_pos(*, tenant, user=None) -> dict:
    return {"pos": {"skipped": True, "reason": "stub"}}


def seed_inventory(*, tenant, user=None) -> dict:
    return {"inventory": {"skipped": True, "reason": "catalog via pharmacy/pos seeders"}}


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
    "gym": seed_gym,
    "pharmacy": seed_pharmacy,
    "restaurant": seed_restaurant,
    "hotel": seed_hotel,
    "property_management": seed_property_management,
    "property": seed_property,
    "housing_rental": seed_housing_rental,
    "office_rental": seed_office_rental,
}


def generate_demo_data(*, tenant, user=None, modules: list[str] | None = None) -> dict:
    """Run modular seeders for enabled (or requested) modules."""
    codes = set(modules) if modules is not None else set(enabled_module_codes(tenant=tenant))
    report: dict = {"modules": sorted(codes), "results": {}}
    report["results"].update(seed_core(tenant=tenant, user=user))
    for code in sorted(codes):
        fn = SEEDERS.get(code)
        if not fn:
            report["results"][code] = {"skipped": True, "reason": "no seeder"}
            continue
        if code == "core":
            continue
        report["results"].update(fn(tenant=tenant, user=user))
    return report
