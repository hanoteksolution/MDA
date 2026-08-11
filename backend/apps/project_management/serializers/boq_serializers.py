def serialize_boq_line(row):
    return {"id": str(row.id), "item_code": row.item_code, "description": row.description, "unit_of_measure": row.unit_of_measure, "quantity": float(row.quantity), "unit_rate": float(row.unit_rate), "amount": float(row.amount), "category": row.category, "sort_order": row.sort_order, "wbs_node_id": str(row.wbs_node_id) if row.wbs_node_id else None, "unit_id": str(row.unit_id) if row.unit_id else None, "notes": row.notes or ""}


def serialize_boq(row, *, include_lines=False):
    data = {"id": str(row.id), "project_id": str(row.project_id), "version": row.version, "name": row.name, "status": row.status, "currency": row.currency, "total_amount": float(row.total_amount), "notes": row.notes or "", "is_active": row.is_active, "approved_at": row.approved_at.isoformat() if row.approved_at else None}
    if include_lines: data["lines"] = [serialize_boq_line(line) for line in row.lines.all()]
    return data
