"""Housing rental demo seeder — lease on residential unit from property core."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.housing_rental.models import Lease
from apps.housing_rental.services import HousingService
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
            return {"housing_rental": {"seeded": False, "reason": "no branch"}}

        existing = Lease.active_objects().filter(tenant=tenant).count()
        if existing:
            return {
                "housing_rental": {
                    "seeded": True,
                    "idempotent": True,
                    "leases": existing,
                }
            }

        # Ensure property core inventory exists
        from apps.platform.demo import property as property_demo

        property_demo.seed(tenant=tenant, user=user)

        unit = (
            PropertyUnit.active_objects()
            .filter(
                tenant=tenant,
                kind=PropertyUnit.KIND_RESIDENTIAL,
                status__in=[
                    PropertyUnit.STATUS_VACANT,
                    PropertyUnit.STATUS_RESERVED,
                ],
            )
            .first()
        )
        if unit is None:
            # Create a dedicated residential unit if property seed only left occupied/maint
            prop = PropertyService.list_properties(branch_id=branch.id).first()
            building = PropertyService.list_buildings(
                branch_id=branch.id, property_id=prop.id if prop else None
            ).first()
            if not building:
                return {
                    "housing_rental": {
                        "seeded": False,
                        "reason": "no building — enable property_management first",
                    }
                }
            unit = PropertyService.create_unit(
                data={
                    "branch_id": branch.id,
                    "building_id": building.id,
                    "code": "H-DEMO-1",
                    "kind": "residential",
                    "rent_amount": "400",
                    "deposit_amount": "400",
                    "bedrooms": 2,
                    "bathrooms": 1,
                },
                user=user,
            )

        today = timezone.localdate()
        lease = HousingService.create_lease(
            data={
                "branch_id": branch.id,
                "unit_id": unit.id,
                "tenant_name": "Amina Hassan",
                "phone": "+255700000020",
                "email": "amina@example.com",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=365)).isoformat(),
                "rent_amount": unit.rent_amount,
                "deposit_amount": unit.deposit_amount,
                "activate": True,
            },
            user=user,
        )
        HousingService.post_rent_charge(lease=lease, user=user)

        return {
            "housing_rental": {
                "seeded": True,
                "leases": 1,
                "active": lease.lease_number,
                "unit": unit.code,
                "charges": lease.charges.filter(deleted_at__isnull=True).count(),
            }
        }
