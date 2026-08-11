def serialize_budget_line(row) -> dict:
    return {
        "id": str(row.id),
        "category": row.category,
        "description": row.description,
        "planned_amount": float(row.planned_amount or 0),
        "committed_amount": float(row.committed_amount or 0),
        "actual_amount": float(row.actual_amount or 0),
        "variance": float((row.planned_amount or 0) - (row.actual_amount or 0)),
        "sort_order": row.sort_order,
        "notes": row.notes or "",
    }


def serialize_budget(row, *, include_lines=False) -> dict:
    data = {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "project_code": row.project.project_code if row.project_id else "",
        "project_name": row.project.name if row.project_id else "",
        "version": row.version,
        "name": row.name,
        "status": row.status,
        "currency": row.currency or "USD",
        "total_planned": float(row.total_planned or 0),
        "total_committed": float(row.total_committed or 0),
        "total_actual": float(row.total_actual or 0),
        "variance": float((row.total_planned or 0) - (row.total_actual or 0)),
        "notes": row.notes or "",
        "is_active": row.is_active,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_lines:
        data["lines"] = [serialize_budget_line(line) for line in row.lines.all()]
    return data
