def serialize_construction(row):
    data = {"id": str(row.id), "project_id": str(row.project_id), "code": row.code, "name": row.name, "notes": row.notes or ""}
    for field in ("address", "location", "status", "floors_count", "level_number", "unit_type", "area_sqm"):
        if hasattr(row, field):
            value = getattr(row, field)
            data[field] = float(value) if field == "area_sqm" else value
    for field in ("site_id", "building_id", "floor_id"):
        if hasattr(row, field):
            data[field] = str(getattr(row, field)) if getattr(row, field) else None
    return data
