"""Mobile navigation registry — PHASE 24 dynamic modules for RN clients.

Server is source of truth: enabled TenantModules + permissions decide which
workspaces/screens the app may show. Clients must not invent parallel flags.
"""

from __future__ import annotations

from apps.platform.services.module_feature_service import ModuleFeatureService
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
        "feature": "members",
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
                "feature": "attendance",
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
                "feature": "classes",
            },
        ],
    },
    {
        "id": "staff_hub",
        "label": "Workspaces",
        "module": "",
        "permission": "",
        "audience": "staff",
        "group": "core",
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
        "id": "dashboard_staff",
        "label": "Dashboard",
        "module": "",
        "permission": "dashboard.view",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "dashboard_staff_home",
                "label": "Dashboard",
                "route": "DashboardWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "pos_staff",
        "label": "POS",
        "module": "pos",
        "permission": "pos.access",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "pos_staff_checkout",
                "label": "Point of sale",
                "route": "PosWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "sales_staff",
        "label": "Sales",
        "module": "sales",
        "permission": "sales.view",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "sales_staff_invoices",
                "label": "Invoices",
                "route": "SalesWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "inventory_staff",
        "label": "Inventory",
        "module": "inventory",
        "permission": "inventory.view",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "inventory_staff_stock",
                "label": "Stock",
                "route": "InventoryWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "purchases_staff",
        "label": "Purchases",
        "module": "purchases",
        "permission": "purchases.view",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "purchases_staff_orders",
                "label": "Purchase orders",
                "route": "PurchasesWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "customers_staff",
        "label": "Customers",
        "module": "sales",
        "permission": "customers.view",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "customers_staff_list",
                "label": "Customers",
                "route": "CustomersWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "suppliers_staff",
        "label": "Suppliers",
        "module": "purchases",
        "permission": "suppliers.view",
        "audience": "staff",
        "group": "core",
        "screens": [
            {
                "id": "suppliers_staff_list",
                "label": "Suppliers",
                "route": "SuppliersWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "finance_staff",
        "label": "Finance",
        "module": "",
        "permission": "finance.view",
        "audience": "staff",
        "group": "finance",
        "screens": [
            {
                "id": "finance_staff_summary",
                "label": "Finance overview",
                "route": "FinanceWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "business_units_staff",
        "label": "Business Units",
        "module": "",
        "permission": "finance.view",
        "audience": "staff",
        "group": "finance",
        "screens": [
            {
                "id": "business_units_staff_list",
                "label": "Business units",
                "route": "BusinessUnitsWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "reports_staff",
        "label": "Reports",
        "module": "",
        "permission": "reports.view",
        "audience": "staff",
        "group": "finance",
        "screens": [
            {
                "id": "reports_staff_catalog",
                "label": "Reports",
                "route": "ReportsWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "settings_staff",
        "label": "Settings",
        "module": "",
        "permission": "settings.view",
        "audience": "staff",
        "group": "finance",
        "screens": [
            {
                "id": "settings_staff_company",
                "label": "Settings",
                "route": "SettingsWorkspace",
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
        "group": "venue",
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
        "group": "venue",
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
        "group": "venue",
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
        "group": "venue",
        "screens": [
            {
                "id": "restaurant_staff_summary",
                "label": "Restaurant overview",
                "route": "RestaurantWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "property_staff",
        "label": "Property",
        "module": "property_management",
        "permission": "property_management.view",
        "audience": "staff",
        "group": "venue",
        "screens": [
            {
                "id": "property_staff_summary",
                "label": "Property overview",
                "route": "PropertyWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "housing_staff",
        "label": "Housing",
        "module": "housing_rental",
        "permission": "housing_rental.view",
        "audience": "staff",
        "group": "venue",
        "screens": [
            {
                "id": "housing_staff_summary",
                "label": "Housing overview",
                "route": "HousingWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "office_staff",
        "label": "Office",
        "module": "office_rental",
        "permission": "office_rental.view",
        "audience": "staff",
        "group": "venue",
        "screens": [
            {
                "id": "office_staff_summary",
                "label": "Office overview",
                "route": "OfficeWorkspace",
                "sort_order": 10,
            },
        ],
    },
    {
        "id": "futsal_staff",
        "label": "Futsal",
        "module": "futsal",
        "permission": "futsal.view",
        "audience": "staff",
        "group": "venue",
        "screens": [
            {
                "id": "futsal_staff_summary",
                "label": "Futsal overview",
                "route": "FutsalWorkspace",
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
            workspace_feature = (entry.get("feature") or "").strip()
            if workspace_feature and module_code and not ModuleFeatureService.tenant_has_feature(
                module_code, workspace_feature, tenant=tenant, user=user, request=request
            ):
                continue

            screen_rows = []
            for screen in entry.get("screens") or []:
                screen_feature = (screen.get("feature") or "").strip()
                if screen_feature and module_code and not ModuleFeatureService.tenant_has_feature(
                    module_code, screen_feature, tenant=tenant, user=user, request=request
                ):
                    continue
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
                "group": entry.get("group") or ("venue" if module_code else "core"),
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
                    "group": "core",
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
