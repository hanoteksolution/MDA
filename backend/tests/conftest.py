import pytest
from django.contrib.auth import get_user_model

from tests.helpers.shop_factory import auth_client_as


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="smoke_user",
        password="smoke-pass-123",
        email="smoke@example.com",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    return auth_client_as(api_client, user)
