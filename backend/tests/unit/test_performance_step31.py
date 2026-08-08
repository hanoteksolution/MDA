"""STEP 31 — performance optimization (indexes, batch stock, catalog cache)."""

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.inventory.models import Inventory, Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.products.serializers.catalog_serializers import serialize_products_batch
from apps.products.services.product_service import ProductService
from apps.sales.services.pos_service import get_pos_profile, save_pos_profile
from apps.settings_app.models import Branch, Company
from apps.platform.services.module_service import sync_tenant_modules
from core.cache.catalog_cache import CatalogCache


@pytest.fixture
def perf_env(db):
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(name="Perf Co", slug="perf-co", status=Tenant.STATUS_ACTIVE)
    sync_tenant_modules(tenant=tenant, enabled_codes=["pos", "inventory", "sales", "products"])
    company = Company.objects.create(name="Perf Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="Main WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    products = []
    for i in range(12):
        product = Product.objects.create(
            tenant=tenant,
            sku=f"PERF-{i:02d}",
            barcode=f"869000000{i:04d}",
            name=f"Perf Item {i}",
            category=category,
            unit=unit,
            cost_price=Decimal("1"),
            selling_price=Decimal("10"),
        )
        inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
        inv.quantity = Decimal(str(i + 1))
        inv.reserved_quantity = Decimal("0")
        inv.tenant_id = tenant.id
        inv.save(update_fields=["quantity", "reserved_quantity", "tenant_id", "updated_at"])
        products.append(product)

    from django.contrib.auth import get_user_model

    User = get_user_model()
    admin_role = Role.objects.get(slug="admin")
    user = User.objects.create_user(
        username="perf_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=admin_role,
    )
    return {
        "tenant": tenant,
        "branch": branch,
        "warehouse": warehouse,
        "category": category,
        "unit": unit,
        "products": products,
        "user": user,
    }


def _auth(api_client, user):
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.mark.django_db
def test_search_for_pos_exact_barcode_first(perf_env):
    user = perf_env["user"]
    target = perf_env["products"][3]
    hits = list(ProductService.search_for_pos(search=target.barcode, limit=5, user=user))
    assert len(hits) == 1
    assert hits[0].id == target.id


@pytest.mark.django_db
def test_serialize_products_batch_avoids_n_plus_one_stock(perf_env):
    products = perf_env["products"][:10]
    with CaptureQueriesContext(connection) as ctx:
        rows = serialize_products_batch(products, include_stock=True, include_attributes=False)
    assert len(rows) == 10
    assert all("total_stock" in row for row in rows)
    # 1 stock aggregate query; no per-product inventory queries.
    stock_queries = [q["sql"] for q in ctx.captured_queries if "inventory" in q["sql"].lower()]
    assert len(stock_queries) <= 1


@pytest.mark.django_db
def test_product_search_api_query_budget(api_client, perf_env):
    client = _auth(api_client, perf_env["user"])
    with CaptureQueriesContext(connection) as ctx:
        response = client.get("/api/v1/products/search/?q=Perf&limit=20")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 10
    assert len(ctx.captured_queries) <= 16


@pytest.mark.django_db
def test_product_list_page_query_budget(api_client, perf_env):
    client = _auth(api_client, perf_env["user"])
    with CaptureQueriesContext(connection) as ctx:
        response = client.get("/api/v1/products/?page_size=10&is_active=true")
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) == 10
    assert all("total_stock" in item for item in results)
    assert len(ctx.captured_queries) <= 18


@pytest.mark.django_db
def test_catalog_categories_cached(api_client, perf_env):
    cache.clear()
    client = _auth(api_client, perf_env["user"])
    with CaptureQueriesContext(connection) as first_ctx:
        first = client.get("/api/v1/categories/?page_size=100")
    assert first.status_code == 200
    tenant_id = perf_env["tenant"].id
    assert cache.get(CatalogCache._key("categories", tenant_id)) is not None

    with CaptureQueriesContext(connection) as second_ctx:
        second = client.get("/api/v1/categories/?page_size=100")
    assert second.status_code == 200
    category_queries = [q for q in second_ctx.captured_queries if "categories" in q["sql"].lower()]
    assert category_queries == []
    assert len(second_ctx.captured_queries) < len(first_ctx.captured_queries)


@pytest.mark.django_db
def test_pos_profile_short_cache(perf_env):
    cache.clear()
    user = perf_env["user"]
    first = get_pos_profile(user=user)
    assert first["default_payment_method"] == "cash"
    save_pos_profile(user=user, data={**first, "default_payment_method": "card"})
    refreshed = get_pos_profile(user=user)
    assert refreshed["default_payment_method"] == "card"
