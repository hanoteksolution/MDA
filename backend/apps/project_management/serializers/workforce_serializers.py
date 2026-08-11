def serialize_worker(row):
    return {"id": str(row.id), "project_id": str(row.project_id), "code": row.code, "full_name": row.full_name, "worker_type": row.worker_type, "phone": row.phone, "trade": row.trade, "daily_rate": float(row.daily_rate), "is_active": row.is_active, "employee_user_id": str(row.employee_user_id) if row.employee_user_id else None, "notes": row.notes or ""}


def serialize_attendance(row):
    return {"id": str(row.id), "project_id": str(row.project_id), "worker_id": str(row.worker_id), "work_date": row.work_date.isoformat(), "hours_worked": float(row.hours_worked), "status": row.status, "rate_applied": float(row.rate_applied), "wbs_node_id": str(row.wbs_node_id) if row.wbs_node_id else None, "task_id": str(row.task_id) if row.task_id else None, "notes": row.notes or ""}


def serialize_wage(row):
    return {"id": str(row.id), "project_id": str(row.project_id), "worker_id": str(row.worker_id), "attendance_id": str(row.attendance_id) if row.attendance_id else None, "work_date": row.work_date.isoformat(), "hours": float(row.hours), "rate": float(row.rate), "amount": float(row.amount), "status": row.status, "notes": row.notes or ""}
