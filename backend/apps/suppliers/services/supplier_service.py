from django.db.models import Max, Q

from apps.suppliers.models import Supplier


class SupplierService:
    @staticmethod
    def list(*, search=None, is_active=None):
        qs = Supplier.active_objects()
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
    def _next_code():
        last = Supplier.objects.aggregate(m=Max("supplier_code"))["m"]
        if last and last.startswith("SUP-"):
            try:
                num = int(last.split("-")[1]) + 1
            except ValueError:
                num = Supplier.objects.count() + 1
        else:
            num = Supplier.objects.count() + 1
        return f"SUP-{num:05d}"

    @staticmethod
    def create(*, data, user=None):
        if not data.get("supplier_code"):
            data = {**data, "supplier_code": SupplierService._next_code()}
        return Supplier.objects.create(**data, created_by=user)

    @staticmethod
    def update(*, instance, data, user=None):
        for key, value in data.items():
            if key != "supplier_code":
                setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        return instance
