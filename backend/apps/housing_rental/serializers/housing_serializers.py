def serialize_tenant(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id) if row.branch_id else None,
        "customer_id": str(row.customer_id) if row.customer_id else None,
        "full_name": row.full_name,
        "phone": row.phone or "",
        "email": row.email or "",
        "id_number": row.id_number or "",
        "notes": row.notes or "",
        "is_active": row.is_active,
    }


def serialize_charge(row) -> dict:
    invoice = getattr(row, "invoice", None)
    return {
        "id": str(row.id),
        "lease_id": str(row.lease_id),
        "branch_id": str(row.branch_id),
        "charge_type": row.charge_type,
        "status": row.status,
        "description": row.description,
        "amount": float(row.amount or 0),
        "period_start": row.period_start.isoformat() if row.period_start else None,
        "period_end": row.period_end.isoformat() if row.period_end else None,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "invoice_id": str(row.invoice_id) if row.invoice_id else None,
        "invoice_number": invoice.invoice_number if invoice else None,
        "posted_at": row.posted_at.isoformat() if row.posted_at else None,
    }


def serialize_lease(row, *, include_charges=False) -> dict:
    data = {
        "id": str(row.id),
        "lease_number": row.lease_number,
        "branch_id": str(row.branch_id),
        "unit_id": str(row.unit_id),
        "unit_code": row.unit.code if row.unit_id else "",
        "building_name": row.unit.building.name if row.unit_id else "",
        "housing_tenant_id": str(row.housing_tenant_id),
        "tenant_name": row.housing_tenant.full_name if row.housing_tenant_id else "",
        "tenant_phone": row.housing_tenant.phone if row.housing_tenant_id else "",
        "status": row.status,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "rent_amount": float(row.rent_amount or 0),
        "deposit_amount": float(row.deposit_amount or 0),
        "deposit_held": row.deposit_held,
        "notes": row.notes or "",
        "activated_at": row.activated_at.isoformat() if row.activated_at else None,
        "terminated_at": row.terminated_at.isoformat() if row.terminated_at else None,
    }
    if include_charges:
        charges = list(row.charges.filter(deleted_at__isnull=True))
        data["charges"] = [serialize_charge(c) for c in charges]
        data["charge_count"] = len(charges)
    return data
