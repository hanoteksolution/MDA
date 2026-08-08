"""Dashboard widget registry (PHASE 08) — compose by module code, not BusinessType."""

from __future__ import annotations

from typing import Any, Callable

from apps.platform.services.module_service import usable_module_codes

# Static catalog: register widgets against module codes.
# Frontend / RN map `icon` + `id` to loaders; BusinessType must not drive this list.
DASHBOARD_WIDGET_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "finance_ledger_kpis",
        "module": "",  # permission-gated; finance is not a TenantModule yet
        "permission": "finance.view",
        "title": "Finance",
        "route": "/finance",
        "icon": "wallet",
        "sort_order": 5,
    },
    {
        "id": "gym_summary",
        "module": "gym",
        "permission": "gym.view",
        "title": "Gym",
        "route": "/gym",
        "icon": "dumbbell",
        "sort_order": 10,
    },
    {
        "id": "pharmacy_summary",
        "module": "pharmacy",
        "permission": "pharmacy.view",
        "title": "Pharmacy",
        "route": "/pharmacy",
        "icon": "pill",
        "sort_order": 20,
    },
    {
        "id": "restaurant_summary",
        "module": "restaurant",
        "permission": "restaurant.view",
        "title": "Restaurant",
        "route": "/restaurant",
        "icon": "utensils",
        "sort_order": 30,
    },
    {
        "id": "hotel_summary",
        "module": "hotel",
        "permission": "hotel.view",
        "title": "Hotel",
        "route": "/hotel",
        "icon": "bed",
        "sort_order": 40,
    },
    {
        "id": "property_summary",
        "module": "property_management",
        "permission": "property_management.view",
        "title": "Property",
        "route": "/property",
        "icon": "building",
        "sort_order": 50,
    },
    {
        "id": "housing_summary",
        "module": "housing_rental",
        "permission": "housing_rental.view",
        "title": "Housing",
        "route": "/housing",
        "icon": "home",
        "sort_order": 60,
    },
    {
        "id": "office_summary",
        "module": "office_rental",
        "permission": "office_rental.view",
        "title": "Office",
        "route": "/office",
        "icon": "briefcase",
        "sort_order": 70,
    },
)


def serialize_widget(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "module": row["module"],
        "permission": row["permission"],
        "title": row["title"],
        "route": row["route"],
        "icon": row["icon"],
        "sort_order": row["sort_order"],
    }


class DashboardWidgetService:
    @staticmethod
    def catalog() -> list[dict[str, Any]]:
        return [serialize_widget(w) for w in DASHBOARD_WIDGET_CATALOG]

    @staticmethod
    def list_for_actor(
        *,
        user=None,
        request=None,
        tenant=None,
        has_permission: Callable[[str], bool] | None = None,
        is_super_admin: bool = False,
    ) -> list[dict[str, Any]]:
        """Return widgets for usable modules the actor may view.

        BusinessType is intentionally ignored — TenantModule + permissions only.
        A module is usable only when its required dependencies are also enabled.
        Super-admins see the full catalog (matches FE useModules bypass).
        """
        mods = usable_module_codes(tenant=tenant, user=user, request=request)
        out: list[dict[str, Any]] = []
        for row in DASHBOARD_WIDGET_CATALOG:
            module = (row.get("module") or "").strip()
            if module and not is_super_admin and module not in mods:
                continue
            perm = (row.get("permission") or "").strip()
            if perm and not is_super_admin:
                allowed = False
                if has_permission is not None:
                    allowed = bool(has_permission(perm))
                elif user is not None and hasattr(user, "has_permission"):
                    allowed = bool(user.has_permission(perm))
                if not allowed:
                    continue
            out.append(serialize_widget(row))
        out.sort(key=lambda w: (w["sort_order"], w["id"]))
        return out
