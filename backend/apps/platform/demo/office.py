"""Office rental demo seeder — commercial lease on office PropertyUnit."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.office_rental.models import OfficeLease
from apps.office_rental.services import OfficeService
from apps.property_management.models import PropertyUnit
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
            return {"office_rental": {"seeded": False, "reason": "no branch"}}

        existing = OfficeLease.active_objects().filter(tenant=tenant).count()
        if existing:
            return {
                "office_rental": {
                    "seeded": True,
                    "idempotent": True,
                    "leases": existing,
                }
            }

        from apps.platform.demo import property as property_demo

        property_demo.seed(tenant=tenant, user=user)

        unit = (
            PropertyUnit.active_objects()
            .filter(
                tenant=tenant,
                kind__in=[PropertyUnit.KIND_OFFICE, PropertyUnit.KIND_RETAIL],
                status__in=[
                    PropertyUnit.STATUS_VACANT,
                    PropertyUnit.STATUS_RESERVED,
                ],
            )
            .first()
        )
        if unit is None:
            prop = PropertyService.list_properties(branch_id=branch.id).first()
            building = PropertyService.list_buildings(
                branch_id=branch.id, property_id=prop.id if prop else None
            ).first()
            if not building:
                return {
                    "office_rental": {
                        "seeded": False,
                        "reason": "no building — enable property_management first",
                    }
                }
            unit = PropertyService.create_unit(
                data={
                    "branch_id": branch.id,
                    "building_id": building.id,
                    "code": "O-DEMO-1",
                    "kind": "office",
                    "rent_amount": "800",
                    "deposit_amount": "1600",
                    "area_sqm": "40",
                },
                user=user,
            )

        today = timezone.localdate()
        lease = OfficeService.create_lease(
            data={
                "branch_id": branch.id,
                "unit_id": unit.id,
                "company_name": "Acme Consulting Ltd",
                "registration_number": "CO-12345",
                "contact_name": "Jane Mwangi",
                "phone": "+255700000030",
                "email": "jane@acme.example.com",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=365)).isoformat(),
                "rent_amount": unit.rent_amount,
                "service_charge": Decimal("50"),
                "deposit_amount": unit.deposit_amount,
                "parking_slots": 1,
                "furnished": True,
                "internet_included": True,
                "activate": True,
            },
            user=user,
        )
        OfficeService.post_rent_charge(lease=lease, user=user)

        return {
            "office_rental": {
                "seeded": True,
                "leases": 1,
                "active": lease.lease_number,
                "unit": unit.code,
                "charges": lease.charges.filter(deleted_at__isnull=True).count(),
            }
        }
