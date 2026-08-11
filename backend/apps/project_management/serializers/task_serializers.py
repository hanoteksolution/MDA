def serialize_task(row) -> dict:
    assignee = row.assignee
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "project_code": row.project.project_code if row.project_id else "",
        "project_name": row.project.name if row.project_id else "",
        "wbs_node_id": str(row.wbs_node_id) if row.wbs_node_id else None,
        "wbs_code": row.wbs_node.code if row.wbs_node_id else "",
        "wbs_name": row.wbs_node.name if row.wbs_node_id else "",
        "assignee_id": str(row.assignee_id) if row.assignee_id else None,
        "assignee_name": (
            assignee.get_full_name() or assignee.username if assignee else ""
        ),
        "task_code": row.task_code,
        "title": row.title,
        "description": row.description or "",
        "priority": row.priority,
        "status": row.status,
        "planned_start": row.planned_start.isoformat() if row.planned_start else None,
        "planned_end": row.planned_end.isoformat() if row.planned_end else None,
        "actual_start": row.actual_start.isoformat() if row.actual_start else None,
        "actual_end": row.actual_end.isoformat() if row.actual_end else None,
        "progress_percent": float(row.progress_percent or 0),
        "estimated_hours": float(row.estimated_hours or 0),
        "actual_hours": float(row.actual_hours or 0),
        "sort_order": row.sort_order,
        "notes": row.notes or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
