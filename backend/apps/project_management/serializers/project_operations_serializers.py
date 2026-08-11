from decimal import Decimal
from uuid import UUID


def serialize_project_operation(row):
    """Serialize project operational models without coupling APIs to model internals."""
    data = {}
    for field in row._meta.fields:
        name = field.name
        value = getattr(row, field.attname if field.is_relation else name)
        key = field.attname if field.is_relation else name
        if isinstance(value, (UUID,)):
            value = str(value)
        elif isinstance(value, Decimal):
            value = float(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        data[key] = value
    if getattr(row, "project_id", None):
        data["project_id"] = str(row.project_id)
    if hasattr(row, "lines"):
        data["lines"] = [
            serialize_project_operation(line)
            for line in row.lines.filter(deleted_at__isnull=True)
        ]
    return data
