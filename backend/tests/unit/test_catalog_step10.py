"""STEP 10 — universal catalog attributes."""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.platform.models import BusinessType, Tenant
from apps.products.models import (
    AttributeDefinition,
    Category,
    Product,
    ProductAttributeValue,
    Unit,
)
from apps.products.services.attribute_service import (
    AttributeService,
    AttributeValidationError,
)
from apps.products.services.product_service import ProductService


@pytest.fixture
def attr_env(db):
    bt = BusinessType.objects.create(
        code="retail_test",
        name="Retail Test",
        default_modules=["pos", "inventory"],
    )
    tenant_a = Tenant.objects.create(
        name="Shop A", slug="shop-a-attr", status=Tenant.STATUS_ACTIVE, business_type=bt
    )
    tenant_b = Tenant.objects.create(
        name="Shop B", slug="shop-b-attr", status=Tenant.STATUS_ACTIVE, business_type=bt
    )
    cat_a = Category.objects.create(name="Meds", tenant=tenant_a)
    cat_b = Category.objects.create(name="Meds", tenant=tenant_b)
    unit_a = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant_a)
    unit_b = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant_b)
    return {
        "bt": bt,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "cat_a": cat_a,
        "cat_b": cat_b,
        "unit_a": unit_a,
        "unit_b": unit_b,
    }


@pytest.mark.django_db
def test_tenant_sku_unique_isolation(attr_env):
    a = attr_env["tenant_a"]
    b = attr_env["tenant_b"]
    Product.objects.create(
        tenant=a,
        sku="SAME-SKU",
        name="A",
        category=attr_env["cat_a"],
        unit=attr_env["unit_a"],
        cost_price=Decimal("1"),
        selling_price=Decimal("2"),
    )
    Product.objects.create(
        tenant=b,
        sku="SAME-SKU",
        name="B",
        category=attr_env["cat_b"],
        unit=attr_env["unit_b"],
        cost_price=Decimal("1"),
        selling_price=Decimal("2"),
    )
    assert Product.objects.filter(sku="SAME-SKU").count() == 2
    with pytest.raises(IntegrityError):
        Product.objects.create(
            tenant=a,
            sku="SAME-SKU",
            name="Dup",
            category=attr_env["cat_a"],
            unit=attr_env["unit_a"],
            cost_price=Decimal("1"),
            selling_price=Decimal("2"),
        )


@pytest.mark.django_db
def test_category_attribute_required_on_create(attr_env):
    tenant = attr_env["tenant_a"]
    defn = AttributeService.create_definition(
        data={
            "code": "color",
            "name": "Color",
            "data_type": "select",
            "is_required": True,
            "options": ["red", "blue"],
        },
        user=None,
        request=None,
    )
    # Stamp tenant manually (no user context)
    defn.tenant = tenant
    defn.save(update_fields=["tenant"])
    AttributeService.assign_to_category(
        category_id=attr_env["cat_a"].id,
        definition_id=defn.id,
        is_required=True,
    )

    with pytest.raises(AttributeValidationError, match="Color is required"):
        ProductService.create(
            data={
                "name": "Widget",
                "category_id": attr_env["cat_a"].id,
                "unit_id": attr_env["unit_a"].id,
                "cost_price": "1",
                "selling_price": "2",
                "tenant": tenant,
                "attributes": [],
            },
            user=None,
        )

    product = ProductService.create(
        data={
            "name": "Widget",
            "sku": "W-1",
            "category_id": attr_env["cat_a"].id,
            "unit_id": attr_env["unit_a"].id,
            "cost_price": "1",
            "selling_price": "2",
            "tenant": tenant,
            "attributes": [{"code": "color", "value": "red"}],
        },
        user=None,
    )
    values = AttributeService.values_for_product(product)
    assert len(values) == 1
    assert values[0]["value"] == "red"


@pytest.mark.django_db
def test_business_type_attributes_resolve(attr_env):
    tenant = attr_env["tenant_a"]
    defn = AttributeDefinition.objects.create(
        tenant=None,
        code="material",
        name="Material",
        data_type=AttributeDefinition.TYPE_TEXT,
        is_required=False,
    )
    AttributeService.assign_to_business_type(
        business_type_id=attr_env["bt"].id,
        definition_id=defn.id,
    )
    product = Product.objects.create(
        tenant=tenant,
        sku="BT-1",
        name="Shirt",
        category=attr_env["cat_a"],
        unit=attr_env["unit_a"],
        cost_price=Decimal("5"),
        selling_price=Decimal("10"),
    )
    applicable = AttributeService.resolve_applicable(product=product)
    codes = [a["definition"].code for a in applicable]
    assert "material" in codes

    AttributeService.set_product_attributes(
        product=product,
        attributes={"material": "cotton"},
        validate_required=True,
    )
    assert ProductAttributeValue.active_objects().filter(product=product).count() == 1


@pytest.mark.django_db
def test_typed_coercion_and_invalid_select(attr_env):
    tenant = attr_env["tenant_a"]
    defn = AttributeService.create_definition(
        data={
            "code": "size",
            "name": "Size",
            "data_type": "select",
            "options": ["S", "M", "L"],
        },
    )
    defn.tenant = tenant
    defn.save(update_fields=["tenant"])
    AttributeService.assign_to_category(
        category_id=attr_env["cat_a"].id, definition_id=defn.id
    )
    product = Product.objects.create(
        tenant=tenant,
        sku="SZ-1",
        name="Tee",
        category=attr_env["cat_a"],
        unit=attr_env["unit_a"],
        cost_price=Decimal("1"),
        selling_price=Decimal("2"),
    )
    with pytest.raises(AttributeValidationError, match="Invalid option"):
        AttributeService.set_product_attributes(
            product=product, attributes={"size": "XXL"}, validate_required=False
        )
    AttributeService.set_product_attributes(
        product=product, attributes={"size": "M"}, validate_required=False
    )
    val = AttributeService.values_for_product(product)[0]
    assert val["value"] == "M"
