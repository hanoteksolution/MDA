from django.db import transaction
from django.db.models import Q

import uuid

from apps.audit.repositories.audit_repository import AuditRepository
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Brand, Category, Product, Unit
from apps.products.services.attribute_service import AttributeService
from core.cache.catalog_cache import CatalogCache
from core.tenancy import apply_tenant_scope, resolve_acting_tenant, stamp_tenant_id


class CategoryService:
    _WRITABLE = ("name", "description", "is_active", "parent_id")

    @staticmethod
    def _prepare(data):
        prepared = {}
        for key in CategoryService._WRITABLE:
            if key not in data:
                continue
            value = data.get(key)
            if key == "parent_id" and value in ("", None):
                prepared["parent_id"] = None
            else:
                prepared[key] = value
        return prepared

    @staticmethod
    def list(*, search=None, is_active=None, user=None, request=None):
        qs = Category.active_objects().select_related("parent")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs.order_by("name")

    @staticmethod
    def create(*, data, user=None, request=None):
        prepared = CategoryService._prepare(data)
        if not prepared.get("name"):
            raise ValueError("Category name is required.")
        prepared = stamp_tenant_id(prepared, user=user, request=request)
        cat = Category.objects.create(**prepared, created_by=user)
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=user, request=request))
        return cat

    @staticmethod
    def update(*, instance, data, user=None):
        prepared = CategoryService._prepare(data)
        for key, value in prepared.items():
            setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=user))
        return instance


class BrandService:
    @staticmethod
    def list(*, search=None, user=None, request=None):
        qs = Brand.active_objects()
        qs = apply_tenant_scope(qs, user=user, request=request)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs.order_by("name")

    @staticmethod
    def create(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        brand = Brand.objects.create(**payload, created_by=user)
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=user, request=request))
        return brand

    @staticmethod
    def update(*, instance, data, user=None):
        for key, value in data.items():
            setattr(instance, key, value)
        instance.updated_by = user
        instance.save()
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=user))
        return instance


class UnitService:
    @staticmethod
    def list(*, user=None, request=None):
        qs = Unit.active_objects().filter(is_active=True)
        qs = apply_tenant_scope(qs, user=user, request=request)
        return qs.order_by("name")

    @staticmethod
    def create(*, data, user=None, request=None):
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        unit = Unit.objects.create(**payload, created_by=user)
        CatalogCache.invalidate_tenant(CatalogCache.tenant_id(user=user, request=request))
        return unit


class ProductService:
    @staticmethod
    def _default_unit(*, user=None, request=None):
        qs = apply_tenant_scope(Unit.objects.all(), user=user, request=request)
        unit = qs.filter(name__iexact="Each").first()
        if unit:
            return unit
        payload = stamp_tenant_id(
            {"name": "Each", "abbreviation": "ea"}, user=user, request=request
        )
        return Unit.objects.create(**payload)

    @staticmethod
    def _prepare_product_data(data, *, for_create: bool, user=None, request=None):
        prepared = dict(data)
        prepared.pop("attributes", None)
        prepared.pop("initial_stock", None)
        prepared.pop("stock", None)
        prepared.pop("warehouse_id", None)
        sku = (prepared.get("sku") or "").strip()
        if sku:
            prepared["sku"] = sku
        elif for_create:
            prepared["sku"] = f"SKU-{uuid.uuid4().hex[:8].upper()}"

        unit_id = prepared.get("unit_id") or prepared.get("unit")
        if unit_id:
            prepared["unit_id"] = unit_id
        elif for_create:
            prepared["unit_id"] = ProductService._default_unit(user=user, request=request).id

        prepared.pop("unit", None)
        if "requires_prescription" in prepared:
            prepared["requires_prescription"] = bool(prepared.get("requires_prescription"))
        if for_create:
            prepared = stamp_tenant_id(prepared, user=user, request=request)
        return prepared

    @staticmethod
    def list(*, search=None, category_id=None, brand_id=None, is_active=None, user=None, request=None):
        qs = Product.active_objects().select_related("category", "brand", "unit")
        qs = apply_tenant_scope(qs, user=user, request=request)
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
    def search_for_pos(
        *,
        search=None,
        category_id=None,
        limit=20,
        user=None,
        request=None,
    ):
        """Tenant-scoped active product search tuned for POS (exact barcode first)."""
        qs = Product.active_objects().select_related("category", "brand", "unit")
        qs = apply_tenant_scope(qs, user=user, request=request)
        qs = qs.filter(is_active=True)
        if category_id:
            qs = qs.filter(category_id=category_id)
        term = (search or "").strip()
        if term:
            exact = qs.filter(barcode=term)
            if exact.exists():
                return exact.order_by("name")[:limit]
            qs = qs.filter(
                Q(name__icontains=term)
                | Q(sku__icontains=term)
                | Q(barcode__icontains=term)
            )
        return qs.order_by("name")[:limit]

    @staticmethod
    def get_by_barcode(barcode, *, user=None, request=None):
        qs = Product.active_objects().select_related("category", "brand", "unit")
        qs = apply_tenant_scope(qs, user=user, request=request)
        return qs.get(barcode=barcode)

    @staticmethod
    def _resolve_warehouse(warehouse=None, user=None):
        if warehouse is not None:
            return warehouse
        branch_id = getattr(user, "branch_id", None) if user is not None else None
        tenant = resolve_acting_tenant(user=user)
        wh_qs = Warehouse.active_objects()
        if tenant is not None:
            wh_qs = wh_qs.filter(tenant_id=tenant.id)
        if branch_id:
            wh = (
                wh_qs.filter(branch_id=branch_id, is_default=True).first()
                or wh_qs.filter(branch_id=branch_id).first()
            )
            if wh:
                return wh
        return wh_qs.filter(is_default=True).first() or wh_qs.first()

    @staticmethod
    @transaction.atomic
    def set_stock(*, product, quantity, warehouse=None, user=None):
        """Ensure an inventory row exists and set on-hand quantity (0 is valid)."""
        from decimal import Decimal

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
    def create(*, data, user=None, request=None, initial_stock=0, warehouse=None):
        attributes = data.get("attributes") if isinstance(data, dict) else None
        product = Product.objects.create(
            **ProductService._prepare_product_data(
                data, for_create=True, user=user, request=request
            ),
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
        AttributeService.set_product_attributes(
            product=product,
            attributes=attributes if attributes is not None else [],
            user=user,
            request=request,
            validate_required=True,
        )
        AuditRepository.create(
            user=user, action="create", module="products",
            entity_type="Product", entity_id=product.id,
            new_values={"sku": product.sku, "name": product.name},
        )
        return product

    @staticmethod
    @transaction.atomic
    def update(*, product, data, user=None, request=None, stock=None, warehouse=None):
        attributes_provided = isinstance(data, dict) and "attributes" in data
        attributes = data.get("attributes") if attributes_provided else None
        prepared = ProductService._prepare_product_data(data, for_create=False, user=user)
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
        if attributes_provided:
            AttributeService.set_product_attributes(
                product=product,
                attributes=attributes,
                user=user,
                request=request,
                validate_required=True,
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
