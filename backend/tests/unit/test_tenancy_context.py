import pytest

from core.tenancy import (
    clear_current_tenant,
    get_current_tenant,
    get_current_tenant_id,
    is_tenant_enforcement_enabled,
    set_current_tenant,
    set_tenant_enforcement,
    tenant_context,
)


class _FakeTenant:
    def __init__(self, pk):
        self.pk = pk
        self.id = pk


def test_tenant_context_sets_and_clears():
    clear_current_tenant()
    set_tenant_enforcement(False)
    assert get_current_tenant() is None

    tenant = _FakeTenant("tenant-a")
    with tenant_context(tenant, enforce=True):
        assert get_current_tenant() is tenant
        assert get_current_tenant_id() == "tenant-a"
        assert is_tenant_enforcement_enabled() is True

    assert get_current_tenant() is None
    assert is_tenant_enforcement_enabled() is False


def test_set_current_tenant_direct():
    clear_current_tenant()
    tenant = _FakeTenant("tenant-b")
    set_current_tenant(tenant)
    assert get_current_tenant_id() == "tenant-b"
    clear_current_tenant()
    assert get_current_tenant() is None
