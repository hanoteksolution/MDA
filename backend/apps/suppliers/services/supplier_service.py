from django.db.models import Max, Q

from apps.suppliers.models import Supplier
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class SupplierService:
    @staticmethod
    def list(*, search=None, is_active=None, user=None, request=None):
        qs = Supplier.active_objects()
        qs = apply_tenant_scope(qs, user=user, request=request)
        if search:
            qs = qs.filter(
                Q(company_name__icontains=search)
                | Q(supplier_code__icontains=search)
                | Q(contact_person__icontains=search)
                | Q(email__icontains=search)
            )
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("company_name")

    @staticmethod
    def _next_code(*, user=None, request=None):
        qs = apply_tenant_scope(Supplier.objects.all(), user=user, request=request)
        last = qs.aggregate(m=Max("supplier_code"))["m"]
        if last and last.startswith("SUP-"):
            try:
                num = int(last.split("-")[1]) + 1
            except ValueError:
                num = qs.count() + 1
        else:
            num = qs.count() + 1
        return f"SUP-{num:05d}"

    @staticmethod
    def create(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        if not payload.get("supplier_code"):
            payload["supplier_code"] = SupplierService._next_code(user=user, request=request)
        return Supplier.objects.create(**payload, created_by=user)

    @staticmethod
    def update(*, instance, data, user=None):
        for key, value in data.items():
            if key != "supplier_code":
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        return instance
