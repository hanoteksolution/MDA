from django.db import transaction
from django.db.models import Q

from apps.audit.repositories.audit_repository import AuditRepository
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Brand, Category, Product, Unit


class CategoryService:
    @staticmethod
    def list(*, search=None, is_active=None):
        qs = Category.active_objects().select_related("parent")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs.order_by("name")

    @staticmethod
    def create(*, data, user=None):
        return Category.objects.create(**data, created_by=user)

    @staticmethod
    def update(*, instance, data, user=None):
        for key, value in data.items():
            setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        return instance


class BrandService:
    @staticmethod
    def list(*, search=None):
        qs = Brand.active_objects()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs.order_by("name")

    @staticmethod
    def create(*, data, user=None):
        return Brand.objects.create(**data, created_by=user)

    @staticmethod
    def update(*, instance, data, user=None):
        for key, value in data.items():
            setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        return instance


class UnitService:
    @staticmethod
    def list():
        return Unit.active_objects().filter(is_active=True).order_by("name")

    @staticmethod
    def create(*, data, user=None):
        return Unit.objects.create(**data, created_by=user)


class ProductService:
    @staticmethod
    def list(*, search=None, category_id=None, brand_id=None, is_active=None):
        qs = Product.active_objects().select_related("category", "brand", "unit")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(sku__icontains=search)
                | Q(barcode__icontains=search)
            )
        if category_id:
            qs = qs.filter(category_id=category_id)
        if brand_id:
            qs = qs.filter(brand_id=brand_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("name")

    @staticmethod
    def get_by_barcode(barcode):
        return Product.active_objects().select_related("category", "brand", "unit").get(barcode=barcode)

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, initial_stock=0, warehouse=None):
        product = Product.objects.create(**data, created_by=user)
        if warehouse and initial_stock:
            inv = InventoryService.ensure_inventory_record(
                product=product, warehouse=warehouse, user=user
            )
            inv.quantity = initial_stock
            inv.save(update_fields=["quantity", "updated_at"])
        AuditRepository.create(
            user=user, action="create", module="products",
            entity_type="Product", entity_id=product.id,
            new_values={"sku": product.sku, "name": product.name},
        )
        return product

    @staticmethod
    @transaction.atomic
    def update(*, product, data, user=None):
        for key, value in data.items():
            setattr(product, key, value)
        product.updated_by = user
        product.save()
        AuditRepository.create(
            user=user, action="update", module="products",
            entity_type="Product", entity_id=product.id,
        )
        return product

    @staticmethod
    def soft_delete(*, product, user=None):
        product.soft_delete(user=user)
        AuditRepository.create(
            user=user, action="delete", module="products",
            entity_type="Product", entity_id=product.id,
        )
        return product
