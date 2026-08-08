"""Short-TTL cache for non-authoritative catalog reference lists."""

from django.core.cache import cache

from core.tenancy import resolve_acting_tenant

CATALOG_LIST_TTL = 60


class CatalogCache:
    @staticmethod
    def _key(prefix: str, tenant_id) -> str:
        return f"mda:catalog:{prefix}:{tenant_id}"

    @staticmethod
    def tenant_id(*, user=None, request=None):
        tenant = resolve_acting_tenant(user=user, request=request)
        return tenant.id if tenant is not None else None

    @staticmethod
    def get_or_load(*, prefix, tenant_id, loader):
        if tenant_id is None:
            return loader()
        key = CatalogCache._key(prefix, tenant_id)
        cached = cache.get(key)
        if cached is not None:
            return cached
        data = list(loader())
        cache.set(key, data, CATALOG_LIST_TTL)
        return data

    @staticmethod
    def invalidate_tenant(tenant_id):
        if tenant_id is None:
            return
        cache.delete_many(
            [
                CatalogCache._key("categories", tenant_id),
                CatalogCache._key("brands", tenant_id),
                CatalogCache._key("units", tenant_id),
            ]
        )
