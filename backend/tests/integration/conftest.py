"""Integration test fixtures — built on shared shop factory."""

import pytest

from tests.helpers.shop_factory import ShopFactory, auth_client_as


@pytest.fixture
def retail_shop(db):
    return ShopFactory.create(slug="retail-int", modules=["pos", "inventory", "sales", "purchases"])


@pytest.fixture
def gym_shop(db):
    return ShopFactory.create(
        slug="gym-int",
        role_slug="receptionist",
        modules=["gym"],
    )


@pytest.fixture
def pharmacy_shop(db):
    return ShopFactory.create(
        slug="pharm-int",
        role_slug="pharmacist",
        modules=["pos", "inventory", "sales", "purchases", "pharmacy"],
        product_name="Paracetamol 500",
        sku="PARA-500",
        barcode="8699990001",
    )


@pytest.fixture
def two_shops(db):
    a = ShopFactory.create(slug="shop-a", username="shop_a_user")
    b = ShopFactory.create(slug="shop-b", username="shop_b_user")
    return a, b


@pytest.fixture
def auth_client(api_client):
    def _auth(user):
        return auth_client_as(api_client, user)

    return _auth
