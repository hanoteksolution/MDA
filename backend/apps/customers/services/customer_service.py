from django.db.models import Max, Q

from apps.customers.models import Customer
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class CustomerService:
    @staticmethod
    def list(*, search=None, customer_type=None, is_active=None, branch_id=None, user=None, request=None):
        qs = Customer.active_objects().select_related("branch")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(customer_code__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )
        if customer_type:
            qs = qs.filter(customer_type=customer_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs.order_by("full_name")

    @staticmethod
    def _next_code(*, user=None, request=None):
        qs = apply_tenant_scope(Customer.objects.all(), user=user, request=request)
        last = qs.aggregate(m=Max("customer_code"))["m"]
        if last and last.startswith("CUST-"):
            try:
                num = int(last.split("-")[1]) + 1
            except ValueError:
                num = qs.count() + 1
        else:
            num = qs.count() + 1
        return f"CUST-{num:05d}"

    @staticmethod
    def create(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        if not payload.get("customer_code"):
            payload["customer_code"] = CustomerService._next_code(user=user, request=request)
        return Customer.objects.create(**payload, created_by=user)

    @staticmethod
    def update(*, instance, data, user=None):
        for key, value in data.items():
            if key != "customer_code":
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        return instance
