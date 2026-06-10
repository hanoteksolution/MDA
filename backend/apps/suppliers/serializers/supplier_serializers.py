from apps.suppliers.models import Supplier


def serialize_supplier(s: Supplier) -> dict:
    return {
        "id": str(s.id),
        "supplier_code": s.supplier_code,
        "company_name": s.company_name,
        "contact_person": s.contact_person,
        "email": s.email,
        "phone": s.phone,
        "address": s.address,
        "payment_terms": s.payment_terms,
        "outstanding_balance": float(s.outstanding_balance),
        "is_active": s.is_active,
        "total_orders": 0,
        "created_at": s.created_at.isoformat(),
    }
