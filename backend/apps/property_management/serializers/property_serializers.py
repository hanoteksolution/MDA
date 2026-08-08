def serialize_owner(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id) if row.branch_id else None,
        "full_name": row.full_name,
        "phone": row.phone or "",
        "email": row.email or "",
        "notes": row.notes or "",
        "is_active": row.is_active,
    }


def serialize_property(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "branch_name": row.branch.name if row.branch_id else "",
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "owner_name": row.owner.full_name if row.owner_id else "",
        "name": row.name,
        "code": row.code or "",
        "kind": row.kind,
        "address": row.address or "",
        "city": row.city or "",
        "notes": row.notes or "",
        "is_active": row.is_active,
    }


def serialize_building(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "property_id": str(row.property_asset_id),
        "property_name": row.property_asset.name if row.property_asset_id else "",
        "name": row.name,
        "code": row.code or "",
        "floors": row.floors,
        "notes": row.notes or "",
        "is_active": row.is_active,
    }


def serialize_unit(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "building_id": str(row.building_id),
        "building_name": row.building.name if row.building_id else "",
        "property_id": str(row.building.property_asset_id) if row.building_id else None,
        "property_name": (
            row.building.property_asset.name
            if row.building_id and row.building.property_asset_id
            else ""
        ),
        "code": row.code,
        "label": row.label or row.code,
        "floor": row.floor or "",
        "kind": row.kind,
        "status": row.status,
        "bedrooms": row.bedrooms,
        "bathrooms": row.bathrooms,
        "area_sqm": float(row.area_sqm) if row.area_sqm is not None else None,
        "rent_amount": float(row.rent_amount or 0),
        "deposit_amount": float(row.deposit_amount or 0),
        "notes": row.notes or "",
        "is_active": row.is_active,
    }


def serialize_maintenance(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "unit_id": str(row.unit_id),
        "unit_code": row.unit.code if row.unit_id else "",
        "building_name": row.unit.building.name if row.unit_id else "",
        "title": row.title,
        "description": row.description or "",
        "status": row.status,
        "priority": row.priority,
        "reported_by": row.reported_by or "",
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def serialize_document(row) -> dict:
    return {
        "id": str(row.id),
        "branch_id": str(row.branch_id),
        "property_id": str(row.property_asset_id) if row.property_asset_id else None,
        "unit_id": str(row.unit_id) if row.unit_id else None,
        "title": row.title,
        "doc_type": row.doc_type or "",
        "file_url": row.file_url or "",
        "notes": row.notes or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
