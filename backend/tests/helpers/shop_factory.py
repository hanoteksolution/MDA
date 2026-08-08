"""Shared shop/tenant factories for integration and critical-path tests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.customers.models import Customer
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company

User = get_user_model()


@dataclass
class ShopContext:
    tenant: Tenant
    company: Company
    branch: Branch
    warehouse: Warehouse
    category: Category
    unit: Unit
    user: User


def auth_client_as(api_client: APIClient, user) -> APIClient:
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


class ShopFactory:
    @classmethod
    def bootstrap(cls):
        bootstrap_roles_and_permissions()
        PlatformService.ensure_default_plans()

    @classmethod
    def create(
        cls,
        *,
        slug: str,
        username: str | None = None,
        role_slug: str = "admin",
        modules: Iterable[str] | None = None,
        product_name: str = "Test Product",
        sku: str | None = None,
        barcode: str | None = None,
        stock_qty: Decimal | str = Decimal("20"),
    ) -> ShopContext:
        cls.bootstrap()
        tenant = Tenant.objects.create(
            name=f"{slug.title()} Co",
            slug=slug,
            status=Tenant.STATUS_ACTIVE,
        )
        sync_tenant_modules(
            tenant=tenant,
            enabled_codes=list(modules or ["pos", "inventory", "sales", "purchases", "products"]),
        )
        company = Company.objects.create(name=f"{slug.title()} Co", tenant=tenant)
        branch = Branch.objects.create(
            company=company,
            tenant=tenant,
            name="Main",
            code=f"{slug[:4].upper()}-M",
            is_default=True,
        )
        warehouse = Warehouse.objects.create(
            branch=branch,
            tenant=tenant,
            name="Main WH",
            code=f"WH-{slug[:4].upper()}",
            is_default=True,
        )
        category = Category.objects.create(name="General", tenant=tenant)
        unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
        role = Role.objects.get(slug=role_slug)
        user = User.objects.create_user(
            username=username or f"{slug}_user",
            password="pass12345",
            tenant=tenant,
            branch=branch,
            role=role,
        )
        product = Product.objects.create(
            tenant=tenant,
            sku=sku or f"SKU-{slug.upper()}",
            barcode=barcode or f"BC-{slug.upper()}",
            name=product_name,
            category=category,
            unit=unit,
            cost_price=Decimal("1"),
            selling_price=Decimal("10"),
        )
        inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
        inv.quantity = Decimal(str(stock_qty))
        inv.reserved_quantity = Decimal("0")
        inv.tenant_id = tenant.id
        inv.save(update_fields=["quantity", "reserved_quantity", "tenant_id", "updated_at"])
        Customer.objects.create(
            tenant=tenant,
            customer_code=f"WALK-{slug.upper()}",
            full_name="Walk-in Customer",
            branch=branch,
        )
        ctx = ShopContext(
            tenant=tenant,
            company=company,
            branch=branch,
            warehouse=warehouse,
            category=category,
            unit=unit,
            user=user,
        )
        ctx.product = product  # type: ignore[attr-defined]
        ctx.inventory = inv  # type: ignore[attr-defined]
        return ctx
