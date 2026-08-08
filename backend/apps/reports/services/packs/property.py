"""Property / housing / office report pack."""

from django.db.models import Count, Sum

from apps.housing_rental.models import Lease, LeaseCharge
from apps.office_rental.models import OfficeLease, OfficeLeaseCharge
from apps.platform.services.module_service import enabled_module_codes
from apps.property_management.models import PropertyUnit
from core.tenancy import apply_tenant_scope


def run(*, report, branch_id=None, date_from=None, date_to=None, user=None, request=None):
    modules = enabled_module_codes(user=user, request=request)

    if report == "Unit Occupancy":
        qs = apply_tenant_scope(
            PropertyUnit.active_objects().select_related("building", "branch"),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        qs = qs.filter(is_active=True)
        rows = [
            {
                "unit": u.code,
                "building": u.building.name if u.building_id else "—",
                "kind": u.kind,
                "status": u.status,
                "rent": float(u.rent_amount or 0),
                "branch": u.branch.name if u.branch_id else "—",
            }
            for u in qs.order_by("building__name", "code")[:100]
        ]
        return {
            "columns": ["unit", "building", "kind", "status", "rent", "branch"],
            "rows": rows,
        }

    if report == "Housing Leases":
        if "housing_rental" not in modules:
            return {"columns": [], "rows": [], "message": "housing_rental module not enabled"}
        qs = apply_tenant_scope(
            Lease.active_objects().select_related(
                "housing_tenant", "unit", "unit__building", "branch"
            ),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "lease": l.lease_number,
                "tenant": l.housing_tenant.full_name if l.housing_tenant_id else "—",
                "unit": l.unit.code if l.unit_id else "—",
                "status": l.status,
                "rent": float(l.rent_amount or 0),
                "start": l.start_date.isoformat() if l.start_date else "—",
                "end": l.end_date.isoformat() if l.end_date else "—",
            }
            for l in qs.order_by("-start_date")[:100]
        ]
        return {
            "columns": ["lease", "tenant", "unit", "status", "rent", "start", "end"],
            "rows": rows,
        }

    if report == "Office Leases":
        if "office_rental" not in modules:
            return {"columns": [], "rows": [], "message": "office_rental module not enabled"}
        qs = apply_tenant_scope(
            OfficeLease.active_objects().select_related(
                "office_tenant", "unit", "unit__building", "branch"
            ),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        rows = [
            {
                "lease": l.lease_number,
                "company": l.office_tenant.company_name if l.office_tenant_id else "—",
                "unit": l.unit.code if l.unit_id else "—",
                "status": l.status,
                "rent": float(l.rent_amount or 0),
                "service": float(l.service_charge or 0),
                "start": l.start_date.isoformat() if l.start_date else "—",
            }
            for l in qs.order_by("-start_date")[:100]
        ]
        return {
            "columns": [
                "lease",
                "company",
                "unit",
                "status",
                "rent",
                "service",
                "start",
            ],
            "rows": rows,
        }

    if report == "Pending Charges":
        rows = []
        if "housing_rental" in modules:
            hqs = apply_tenant_scope(
                LeaseCharge.active_objects()
                .filter(
                    status__in=[
                        LeaseCharge.STATUS_PENDING,
                        LeaseCharge.STATUS_INVOICED,
                    ]
                )
                .select_related("lease", "lease__housing_tenant", "lease__unit"),
                user=user,
                request=request,
            )
            if branch_id:
                hqs = hqs.filter(branch_id=branch_id)
            for c in hqs.order_by("due_date")[:80]:
                rows.append(
                    {
                        "source": "housing",
                        "lease": c.lease.lease_number if c.lease_id else "—",
                        "party": (
                            c.lease.housing_tenant.full_name
                            if c.lease_id and c.lease.housing_tenant_id
                            else "—"
                        ),
                        "type": c.charge_type,
                        "status": c.status,
                        "amount": float(c.amount or 0),
                        "due": c.due_date.isoformat() if c.due_date else "—",
                    }
                )
        if "office_rental" in modules:
            oqs = apply_tenant_scope(
                OfficeLeaseCharge.active_objects()
                .filter(
                    status__in=[
                        OfficeLeaseCharge.STATUS_PENDING,
                        OfficeLeaseCharge.STATUS_INVOICED,
                    ]
                )
                .select_related("lease", "lease__office_tenant", "lease__unit"),
                user=user,
                request=request,
            )
            if branch_id:
                oqs = oqs.filter(branch_id=branch_id)
            for c in oqs.order_by("due_date")[:80]:
                rows.append(
                    {
                        "source": "office",
                        "lease": c.lease.lease_number if c.lease_id else "—",
                        "party": (
                            c.lease.office_tenant.company_name
                            if c.lease_id and c.lease.office_tenant_id
                            else "—"
                        ),
                        "type": c.charge_type,
                        "status": c.status,
                        "amount": float(c.amount or 0),
                        "due": c.due_date.isoformat() if c.due_date else "—",
                    }
                )
        rows.sort(key=lambda r: r.get("due") or "")
        return {
            "columns": ["source", "lease", "party", "type", "status", "amount", "due"],
            "rows": rows[:100],
        }

    if report == "Units by Kind":
        qs = apply_tenant_scope(
            PropertyUnit.active_objects().filter(is_active=True),
            user=user,
            request=request,
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        grouped = (
            qs.values("kind", "status")
            .annotate(count=Count("id"), rent_total=Sum("rent_amount"))
            .order_by("kind", "status")
        )
        rows = [
            {
                "kind": r["kind"],
                "status": r["status"],
                "count": r["count"],
                "rent_total": float(r["rent_total"] or 0),
            }
            for r in grouped
        ]
        return {"columns": ["kind", "status", "count", "rent_total"], "rows": rows}

    return {"columns": [], "rows": []}
