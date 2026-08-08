"""Property management demo seeder — owner, asset, building, units, maintenance."""

from __future__ import annotations

from decimal import Decimal

from apps.property_management.models import MaintenanceRequest, PropertyAsset, PropertyUnit
from apps.property_management.services import PropertyService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


def seed(*, tenant, user=None) -> dict:
    with tenant_context(tenant, enforce=True):
        branch = (
            Branch.active_objects()
            .filter(tenant=tenant, is_default=True)
            .first()
            or Branch.active_objects().filter(tenant=tenant).first()
        )
        if branch is None:
            return {"property_management": {"seeded": False, "reason": "no branch"}}

        existing = PropertyAsset.active_objects().filter(tenant=tenant).count()
        if existing:
            return {
                "property_management": {
                    "seeded": True,
                    "idempotent": True,
                    "properties": existing,
                    "units": PropertyUnit.active_objects().filter(tenant=tenant).count(),
                }
            }

        owner = PropertyService.create_owner(
            data={
                "branch_id": branch.id,
                "full_name": "Demo Landlord",
                "phone": "+255700000010",
                "email": "landlord@example.com",
            },
            user=user,
        )
        prop = PropertyService.create_property(
            data={
                "branch_id": branch.id,
                "owner_id": owner.id,
                "name": "Sunrise Residences",
                "code": "SUN-1",
                "kind": "mixed",
                "address": "12 Independence Ave",
                "city": "Dar es Salaam",
            },
            user=user,
        )
        building = PropertyService.create_building(
            data={
                "branch_id": branch.id,
                "property_id": prop.id,
                "name": "Block A",
                "code": "A",
                "floors": 3,
            },
            user=user,
        )

        units = []
        for code, kind, rent in (
            ("A-101", "residential", "350"),
            ("A-102", "residential", "375"),
            ("A-201", "office", "600"),
            ("A-202", "office", "650"),
        ):
            units.append(
                PropertyService.create_unit(
                    data={
                        "branch_id": branch.id,
                        "building_id": building.id,
                        "code": code,
                        "kind": kind,
                        "floor": code.split("-")[1][0],
                        "rent_amount": Decimal(rent),
                        "deposit_amount": Decimal(rent),
                        "bedrooms": 2 if kind == "residential" else 0,
                        "bathrooms": 1,
                        "area_sqm": "45" if kind == "residential" else "32",
                    },
                    user=user,
                )
            )

        PropertyService.set_unit_status(
            unit=units[0], status=PropertyUnit.STATUS_OCCUPIED, user=user
        )
        maint = PropertyService.create_maintenance(
            data={
                "branch_id": branch.id,
                "unit_id": units[1].id,
                "title": "Leaky faucet",
                "description": "Kitchen sink drip — demo ticket",
                "priority": "normal",
                "reported_by": "Tenant",
            },
            user=user,
        )
        PropertyService.create_document(
            data={
                "branch_id": branch.id,
                "property_id": prop.id,
                "title": "Title deed (demo)",
                "doc_type": "deed",
                "file_url": "",
                "notes": "Placeholder document record",
            },
            user=user,
        )

        return {
            "property_management": {
                "seeded": True,
                "properties": 1,
                "buildings": 1,
                "units": len(units),
                "owners": 1,
                "maintenance": 1,
                "open_ticket": maint.title,
                "maintenance_status": MaintenanceRequest.STATUS_OPEN,
            }
        }
