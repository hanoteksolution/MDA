from decimal import Decimal


def _value(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_travel(row, *, include_related=True):
    data = {}
    for field in row._meta.fields:
        value = getattr(row, field.name)
        if field.is_relation and field.many_to_one:
            data[f"{field.name}_id"] = str(value.id) if value else None
            if value and field.name in {"destination", "traveler", "booking", "package", "customer", "branch"}:
                data[f"{field.name}_name"] = str(value)
        else:
            data[field.name] = _value(value)
    data["id"] = str(row.id)
    if include_related:
        related = {
            "booking_travelers": ("travelers", "traveler"),
            "flights": ("flights", None),
            "hotel_stays": ("hotel_stays", None),
            "visa_applications": ("visa_applications", None),
            "commissions": ("commissions", None),
            "insurance_policies": ("insurance_policies", None),
            "transfers": ("transfers", None),
            "itineraries": ("itineraries", None),
            "activities": ("activities", None),
            "lines": ("lines", None),
            "documents": ("documents", None),
        }
        for accessor, (key, nested) in related.items():
            if hasattr(row, accessor):
                rows = getattr(row, accessor).filter(deleted_at__isnull=True)
                if nested:
                    rows = rows.select_related(nested)
                    data[key] = [serialize_travel(getattr(item, nested), include_related=False) for item in rows]
                else:
                    data[key] = [serialize_travel(item, include_related=False) for item in rows]
    return data
