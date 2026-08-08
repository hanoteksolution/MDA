"""Mobile navigation registry — PHASE 24 dynamic modules for RN clients.

Server is source of truth: enabled TenantModules + permissions decide which
workspaces/screens the app may show. Clients must not invent parallel flags.
"""

from __future__ import annotations

from apps.platform.services.module_service import (
    tenant_module_ready,
    usable_module_codes,
)


# Catalog of mobile workspaces (member + staff audiences).
MOBILE_NAV_CATALOG: list[dict] = [
    {
        "id": "gym_member",
        "label": "Gym Member",
        "module": "gym",
        "permission": "gym.member_portal",
        "audience": "member",
        "screens": [
            {
                "id": "gym_home",
                "label": "Home",
                "route": "Home",
                "sort_order": 10,
            },
            {
                "id": "gym_qr",
                "label": "Membership QR",
                "route": "Qr",
                "sort_order": 20,
            },
            {
                "id": "gym_attendance",
                "label": "Attendance",
                "route": "Attendance",
                "sort_order": 30,
            },
            {
                "id": "gym_workouts",
                "label": "Workouts",
                "route": "Workouts",
                "sort_order": 40,
            },
            {
                "id": "gym_classes",
                "label": "Classes",
                "route": "Classes",
                "sort_order": 50,
            },
        ],
    },
    {
        "id": "staff_hub",
        "label": "Workspaces",
        "module": "",
        "permission": "",
        "audience": "staff",
        "screens": [
            {
                "id": "staff_switcher",
                "label": "Module switcher",
                "route": "WorkspaceSwitcher",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "gym_staff",
        "label": "Gym",
        "module": "gym",
        "permission": "gym.view",
        "audience": "staff",
        "screens": [
            {
                "id": "gym_staff_summary",
                "label": "Gym overview",
                "route": "GymWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "pharmacy_staff",
        "label": "Pharmacy",
        "module": "pharmacy",
        "permission": "pharmacy.view",
        "audience": "staff",
        "screens": [
            {
                "id": "pharmacy_staff_summary",
                "label": "Pharmacy overview",
                "route": "PharmacyWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "hotel_staff",
        "label": "Hotel",
        "module": "hotel",
        "permission": "hotel.view",
        "audience": "staff",
        "screens": [
            {
                "id": "hotel_staff_summary",
                "label": "Hotel overview",
                "route": "HotelWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "restaurant_staff",
        "label": "Restaurant",
        "module": "restaurant",
        "permission": "restaurant.view",
        "audience": "staff",
        "screens": [
            {
                "id": "restaurant_staff_summary",
                "label": "Restaurant overview",
                "route": "RestaurantWorkspace",
                "sort_order": 10,
            },
        ],
    },
]


class MobileNavService:
    @staticmethod
    def catalog(*, audience: str | None = None) -> list[dict]:
        rows = list(MOBILE_NAV_CATALOG)
        if audience:
            want = audience.strip().lower()
            rows = [r for r in rows if (r.get("audience") or "staff") == want]
        return rows

    @staticmethod
    def list_for_actor(*, user, request=None, tenant=None, audience: str | None = None) -> dict:
        """Return enabled_modules + filtered workspaces/screens for RN bootstrap.

        audience: "member" | "staff" | None (all matching permissions).
        staff_hub is only included when at least one other staff workspace qualifies.
        """
        if tenant is None:
            tenant = getattr(request, "tenant", None) if request is not None else None
        if tenant is None and user is not None:
            tenant = getattr(user, "tenant", None)

        modules = sorted(usable_module_codes(tenant=tenant, user=user, request=request))
        has_perm = getattr(user, "has_permission", None)
        want_audience = (audience or "").strip().lower() or None

        workspaces: list[dict] = []
        screens: list[dict] = []
        staff_module_workspaces: list[dict] = []

        for entry in MOBILE_NAV_CATALOG:
            entry_audience = (entry.get("audience") or "staff").strip().lower()
            if want_audience and entry_audience != want_audience:
                continue

            module_code = entry.get("module") or ""
            permission = entry.get("permission") or ""

            if entry["id"] == "staff_hub":
                # Deferred until we know if any staff module workspace qualifies.
                continue

            if module_code and not tenant_module_ready(
                module_code, tenant=tenant, user=user, request=request
            ):
                continue
            if permission and callable(has_perm) and not has_perm(permission):
                continue

            screen_rows = []
            for screen in entry.get("screens") or []:
                row = {
                    "id": screen["id"],
                    "label": screen["label"],
                    "route": screen["route"],
                    "workspace": entry["id"],
                    "module": module_code,
                    "sort_order": int(screen.get("sort_order") or 0),
                }
                screen_rows.append(row)
                screens.append(row)

            workspace = {
                "id": entry["id"],
                "label": entry["label"],
                "module": module_code,
                "audience": entry_audience,
                "screens": sorted(screen_rows, key=lambda s: s["sort_order"]),
            }
            if entry_audience == "staff":
                staff_module_workspaces.append(workspace)
            workspaces.append(workspace)

        # Staff hub / switcher when 1+ staff module workspaces (or always for staff audience with modules)
        include_hub = False
        if want_audience == "staff" and staff_module_workspaces:
            include_hub = True
        elif want_audience is None and staff_module_workspaces:
            include_hub = True

        if include_hub:
            hub = next(e for e in MOBILE_NAV_CATALOG if e["id"] == "staff_hub")
            hub_screens = []
            for screen in hub.get("screens") or []:
                row = {
                    "id": screen["id"],
                    "label": screen["label"],
                    "route": screen["route"],
                    "workspace": hub["id"],
                    "module": "",
                    "sort_order": int(screen.get("sort_order") or 0),
                }
                hub_screens.append(row)
                screens.append(row)
            workspaces.insert(
                0,
                {
                    "id": hub["id"],
                    "label": hub["label"],
                    "module": "",
                    "audience": "staff",
                    "screens": hub_screens,
                },
            )

        screens.sort(key=lambda s: (s.get("workspace") or "", s.get("sort_order") or 0))
        return {
            "enabled_modules": modules,
            "audience": want_audience or "all",
            "workspaces": workspaces,
            "screens": screens,
        }
