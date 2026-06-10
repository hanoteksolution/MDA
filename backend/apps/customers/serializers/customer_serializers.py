from apps.customers.models import Customer


def serialize_customer(c: Customer) -> dict:
    return {
        "id": str(c.id),
        "customer_code": c.customer_code,
        "full_name": c.full_name,
        "email": c.email,
        "phone": c.phone,
        "address": c.address,
        "customer_type": c.customer_type,
        "credit_limit": float(c.credit_limit),
        "outstanding_balance": float(c.outstanding_balance),
        "branch_id": str(c.branch_id) if c.branch_id else None,
        "branch_name": c.branch.name if c.branch else None,
        "is_active": c.is_active,
        "total_orders": 0,
        "created_at": c.created_at.isoformat(),
    }
