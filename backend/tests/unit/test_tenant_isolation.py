"""STEP 06 — cross-tenant isolation for shared-schema tenant_id scoping."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.customers.models import Customer
from apps.customers.services.customer_service import CustomerService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.products.services.product_service import ProductService
from apps.sales.models import Invoice
from apps.sales.services.sales_service import InvoiceService
from apps.settings_app.models import Branch, Company


User = get_user_model()


def _shop(*, slug: str, username: str):
    tenant = Tenant.objects.create(name=slug.title(), slug=slug, status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name=f"{slug} Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company,
        tenant=tenant,
        name="Main",
        code=f"{slug[:4].upper()}-M",
        is_default=True,
    )
    user = User.objects.create_user(
        username=username,
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku=f"SKU-{slug.upper()}",
        name=f"{slug} Product",
        category=category,
        unit=unit,
        cost_price=Decimal("1.00"),
        selling_price=Decimal("2.00"),
        barcode=f"BC-{slug.upper()}",
    )
    customer = Customer.objects.create(
        tenant=tenant,
        customer_code=f"C-{slug.upper()}",
        full_name=f"{slug} Customer",
        branch=branch,
    )
    invoice = Invoice.objects.create(
        tenant=tenant,
        invoice_number=f"INV-{slug.upper()}-1",
        customer=customer,
        branch=branch,
        status=Invoice.STATUS_DRAFT,
        subtotal=Decimal("2.00"),
        total_amount=Decimal("2.00"),
        created_by_user=user,
    )
    return {
        "tenant": tenant,
        "user": user,
        "branch": branch,
        "product": product,
        "customer": customer,
        "invoice": invoice,
    }


@pytest.fixture
def two_tenants(db):
    return _shop(slug="alpha", username="alpha_user"), _shop(slug="beta", username="beta_user")


@pytest.mark.django_db
def test_product_list_scoped_to_acting_tenant(two_tenants):
    a, b = two_tenants
    ids = set(ProductService.list(user=a["user"]).values_list("id", flat=True))
    assert a["product"].id in ids
    assert b["product"].id not in ids


@pytest.mark.django_db
def test_product_detail_blocks_cross_tenant(two_tenants):
    a, b = two_tenants
    with pytest.raises(Product.DoesNotExist):
        ProductService.list(user=a["user"]).get(pk=b["product"].id)


@pytest.mark.django_db
def test_customer_list_scoped_to_acting_tenant(two_tenants):
    a, b = two_tenants
    ids = set(CustomerService.list(user=a["user"]).values_list("id", flat=True))
    assert a["customer"].id in ids
    assert b["customer"].id not in ids


@pytest.mark.django_db
def test_invoice_list_scoped_to_acting_tenant(two_tenants):
    a, b = two_tenants
    ids = set(InvoiceService.list(user=a["user"]).values_list("id", flat=True))
    assert a["invoice"].id in ids
    assert b["invoice"].id not in ids


@pytest.mark.django_db
def test_invoice_detail_blocks_cross_tenant(two_tenants):
    a, b = two_tenants
    with pytest.raises(Invoice.DoesNotExist):
        InvoiceService.list(user=a["user"]).get(pk=b["invoice"].id)


@pytest.mark.django_db
def test_barcode_lookup_scoped_to_tenant(two_tenants):
    a, b = two_tenants
    found = ProductService.get_by_barcode(b["product"].barcode, user=b["user"])
    assert found.id == b["product"].id
    with pytest.raises(Product.DoesNotExist):
        ProductService.get_by_barcode(b["product"].barcode, user=a["user"])


@pytest.mark.django_db
def test_create_product_stamps_tenant(two_tenants):
    a, _ = two_tenants
    unit = Unit.objects.filter(tenant=a["tenant"]).first()
    category = Category.objects.filter(tenant=a["tenant"]).first()
    product = ProductService.create(
        data={
            "name": "Stamped Item",
            "sku": "SKU-STAMP-1",
            "category_id": category.id,
            "unit_id": unit.id,
            "cost_price": "1.00",
            "selling_price": "3.00",
        },
        user=a["user"],
    )
    assert product.tenant_id == a["tenant"].id


@pytest.mark.django_db
def test_authenticated_user_without_tenant_sees_nothing(db):
    orphan = User.objects.create_user(username="orphan", password="pass12345")
    Tenant.objects.create(name="Ghost", slug="ghost", status=Tenant.STATUS_ACTIVE)
    Product.objects.create(
        tenant=Tenant.objects.get(slug="ghost"),
        sku="GHOST-1",
        name="Ghost Product",
        category=Category.objects.create(name="G", tenant=Tenant.objects.get(slug="ghost")),
        unit=Unit.objects.create(name="u", abbreviation="u", tenant=Tenant.objects.get(slug="ghost")),
        cost_price=Decimal("1"),
        selling_price=Decimal("1"),
    )
    assert ProductService.list(user=orphan).count() == 0


@pytest.mark.django_db
def test_platform_admin_unscoped(two_tenants):
    a, b = two_tenants
    admin = User.objects.create_user(
        username="plat_iso",
        password="pass12345",
        is_platform_admin=True,
    )
    ids = set(ProductService.list(user=admin).values_list("id", flat=True))
    assert a["product"].id in ids
    assert b["product"].id in ids
