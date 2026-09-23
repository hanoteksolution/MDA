"""Reserved subdomain / hostname helpers."""

import pytest

from apps.platform.services.domain_utils import build_tenant_hostname, validate_tenant_slug


@pytest.mark.unit
@pytest.mark.parametrize("value", ["shop", "shop-2", "a1"])
def test_valid_tenant_slug(value):
    assert validate_tenant_slug(value) == value


@pytest.mark.unit
@pytest.mark.parametrize("value", ["www", "API", "-shop", "shop-", "a", "💥"])
def test_invalid_or_reserved_tenant_slug(value):
    with pytest.raises(ValueError):
        validate_tenant_slug(value)


@pytest.mark.unit
def test_underscore_normalizes_to_hyphen():
    assert validate_tenant_slug("shop_name") == "shop-name"


@pytest.mark.unit
def test_hostname_is_built_under_configured_base(settings):
    settings.TENANT_BASE_DOMAIN = "erp.example.test"
    assert build_tenant_hostname("acme") == "acme.erp.example.test"
