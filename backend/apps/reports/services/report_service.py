"""Central reporting service — catalog, run, export (STEP 22 + vertical packs)."""

from __future__ import annotations

import csv
import io
from typing import Any

from apps.platform.services.module_service import enabled_module_codes
from apps.reports.services.packs import gym as gym_pack
from apps.reports.services.packs import hotel as hotel_pack
from apps.reports.services.packs import pharmacy as pharmacy_pack
from apps.reports.services.packs import property as property_pack
from apps.reports.services.packs import restaurant as restaurant_pack
from core.services.analytics_service import AnalyticsService


class ReportError(ValueError):
    pass


REPORT_CATALOG: list[dict[str, Any]] = [
    {
        "id": "sales",
        "title": "Sales Reports",
        "description": "Revenue, invoices, and sales performance by period",
        "module": None,
        "reports": [
            "Daily Sales",
            "Products Sold",
            "Unpaid Receipts",
            "Customer Monthly",
            "Sales by Product",
            "Sales by Customer",
            "Tax Summary",
        ],
    },
    {
        "id": "inventory",
        "title": "Inventory Reports",
        "description": "Stock levels, valuation, and movement history",
        "module": "inventory",
        "reports": ["Stock Valuation", "Low Stock"],
    },
    {
        "id": "purchases",
        "title": "Purchase Reports",
        "description": "Supplier orders, receiving, and payables",
        "module": "purchases",
        "reports": ["Purchase Summary", "Supplier Analysis"],
    },
    {
        "id": "customers",
        "title": "Customer Reports",
        "description": "Customer activity, credit, and loyalty metrics",
        "module": None,
        "reports": ["Customer Ledger"],
    },
    {
        "id": "finance",
        "title": "Financial Reports",
        "description": "Profit & loss and expense breakdown",
        "module": None,
        "reports": ["Profit & Loss", "Expense Breakdown"],
    },
    {
        "id": "gym",
        "title": "Gym Reports",
        "description": "Members, subscriptions, attendance, and classes",
        "module": "gym",
        "reports": [
            "Active Members",
            "Subscription Summary",
            "Attendance Log",
            "Class Bookings",
            "Plan Catalog",
        ],
    },
    {
        "id": "pharmacy",
        "title": "Pharmacy Reports",
        "description": "Batch stock, expiry, and FEFO dispenses",
        "module": "pharmacy",
        "reports": ["Batch Stock", "Expiring Soon", "FEFO Dispenses"],
    },
    {
        "id": "hotel",
        "title": "Hotel Reports",
        "description": "Occupancy, in-house guests, and open folios",
        "module": "hotel",
        "reports": [
            "Room Occupancy",
            "In-House Guests",
            "Open Folios",
            "Arrivals & Departures",
        ],
    },
    {
        "id": "restaurant",
        "title": "Restaurant Reports",
        "description": "Tables, open tickets, and menu catalog",
        "module": "restaurant",
        "reports": [
            "Table Status",
            "Open Orders",
            "Orders by Status",
            "Menu Catalog",
        ],
    },
    {
        "id": "property",
        "title": "Property Reports",
        "description": "Units, housing/office leases, and pending charges",
        "module": "property_management",
        "reports": [
            "Unit Occupancy",
            "Units by Kind",
            "Housing Leases",
            "Office Leases",
            "Pending Charges",
        ],
    },
]


_PACK_RUNNERS = {
    "gym": gym_pack.run,
    "pharmacy": pharmacy_pack.run,
    "hotel": hotel_pack.run,
    "restaurant": restaurant_pack.run,
    "property": property_pack.run,
}


class ReportService:
    @staticmethod
    def catalog(*, user=None, request=None) -> list[dict]:
        enabled = enabled_module_codes(user=user, request=request)
        packs = []
        for pack in REPORT_CATALOG:
            module = pack.get("module")
            if module and module not in enabled:
                continue
            packs.append(
                {
                    "id": pack["id"],
                    "title": pack["title"],
                    "description": pack["description"],
                    "reports": list(pack["reports"]),
                }
            )
        return packs

    @staticmethod
    def run(
        *,
        category: str,
        report: str,
        branch_id=None,
        date_from=None,
        date_to=None,
        user=None,
        request=None,
    ) -> dict:
        if not category or not report:
            raise ReportError("category and report are required.")

        runner = _PACK_RUNNERS.get(category)
        if runner is not None:
            return runner(
                report=report,
                branch_id=branch_id,
                date_from=date_from,
                date_to=date_to,
                user=user,
                request=request,
            )

        return AnalyticsService.get_report(
            category=category,
            report=report,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            user=user,
            request=request,
        )

    @staticmethod
    def export_csv(*, category: str, report: str, **kwargs) -> str:
        data = ReportService.run(category=category, report=report, **kwargs)
        output = io.StringIO()
        writer = csv.writer(output)
        columns = data.get("columns") or []
        writer.writerow(columns)
        for row in data.get("rows") or []:
            writer.writerow([row.get(col, "") for col in columns])
        return output.getvalue()
