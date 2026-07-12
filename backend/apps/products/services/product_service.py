from django.db import transaction
from django.db.models import Q

import uuid

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
    def _default_unit():
        unit = Unit.objects.filter(name__iexact="Each").first()
        if unit:
            return unit
        return Unit.objects.create(name="Each", abbreviation="ea")

    @staticmethod
    def _prepare_product_data(data, *, for_create: bool):
        prepared = dict(data)
        sku = (prepared.get("sku") or "").strip()
        if sku:
            prepared["sku"] = sku
        elif for_create:
            prepared["sku"] = f"SKU-{uuid.uuid4().hex[:8].upper()}"

        unit_id = prepared.get("unit_id") or prepared.get("unit")
        if unit_id:
            prepared["unit_id"] = unit_id
        elif for_create:
            prepared["unit_id"] = ProductService._default_unit().id

        prepared.pop("unit", None)
        return prepared

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
    def _resolve_warehouse(warehouse=None, user=None):
        if warehouse is not None:
            return warehouse
        branch_id = getattr(user, "branch_id", None) if user is not None else None
        if branch_id:
            wh = (
                Warehouse.active_objects().filter(branch_id=branch_id, is_default=True).first()
                or Warehouse.active_objects().filter(branch_id=branch_id).first()
            )
            if wh:
                return wh
        return (
            Warehouse.active_objects().filter(is_default=True).first()
            or Warehouse.active_objects().first()
        )

    @staticmethod
    @transaction.atomic
    def set_stock(*, product, quantity, warehouse=None, user=None):
        """Ensure an inventory row exists and set on-hand quantity (0 is valid)."""
        from decimal import Decimal

        # Pull any stock that landed on duplicate same-named warehouses onto this branch
        branch_id = getattr(user, "branch_id", None) if user is not None else None
        InventoryService.dedupe_inventory(user=user, preferred_branch_id=branch_id)

        wh = ProductService._resolve_warehouse(warehouse, user=user)
        if not wh:
            raise ValueError("No warehouse available. Create a warehouse before setting stock.")
        qty = Decimal(str(quantity if quantity is not None else 0))
        if qty < 0:
            raise ValueError("Stock quantity cannot be negative.")
        inv = InventoryService.ensure_inventory_record(product=product, warehouse=wh, user=user)
        inv.quantity = qty
        inv.updated_by = user
        inv.save(update_fields=["quantity", "updated_by", "updated_at"])
        return inv

    @staticmethod
    @transaction.atomic
    def create(*, data, user=None, initial_stock=0, warehouse=None):
        product = Product.objects.create(
            **ProductService._prepare_product_data(data, for_create=True),
            created_by=user,
        )
        wh = ProductService._resolve_warehouse(warehouse, user=user)
        if wh is not None:
            ProductService.set_stock(
                product=product,
                quantity=initial_stock if initial_stock is not None else 0,
                warehouse=wh,
                user=user,
            )
        AuditRepository.create(
            user=user, action="create", module="products",
            entity_type="Product", entity_id=product.id,
            new_values={"sku": product.sku, "name": product.name},
        )
        return product

    @staticmethod
    @transaction.atomic
    def update(*, product, data, user=None, stock=None, warehouse=None):
        prepared = ProductService._prepare_product_data(data, for_create=False)
        if not (data.get("sku") or "").strip():
            prepared.pop("sku", None)
        if not data.get("unit_id") and "unit" not in data:
            prepared.pop("unit_id", None)
        for key, value in prepared.items():
            setattr(product, key, value)
        product.updated_by = user
        product.save()
        if stock is not None:
            ProductService.set_stock(
                product=product,
                quantity=stock,
                warehouse=warehouse,
                user=user,
            )
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
