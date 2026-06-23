import json
import secrets
import uuid
from urllib import error, request

from django.utils import timezone

from apps.platform.models import ShopSyncSnapshot, Tenant
from apps.platform.services.sync_catalog import CatalogSyncEngine, parse_since
from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import SettingsService
from core.services.analytics_service import AnalyticsService


SYNC_KEYS = {
    "cloud_url": "sync.cloud_api_base",
    "tenant_slug": "sync.tenant_slug",
    "sync_secret": "sync.sync_secret",
    "device_id": "sync.device_id",
    "last_at": "sync.last_at",
    "last_pull_at": "sync.last_pull_at",
    "last_status": "sync.last_status",
    "last_message": "sync.last_message",
    "initial_pull_done": "sync.initial_pull_done",
}


class ShopSyncService:
    @staticmethod
    def _get_setting(key: str, default: str = "") -> str:
        row = SettingsService.get_by_key(key=key)
        return row.value if row else default

    @staticmethod
    def _set_setting(key: str, value: str, user=None):
        SettingsService.upsert(key=key, value=value, category="sync", user=user)

    @staticmethod
    def get_config() -> dict:
        device_id = ShopSyncService._get_setting(SYNC_KEYS["device_id"])
        if not device_id:
            device_id = str(uuid.uuid4())
            ShopSyncService._set_setting(SYNC_KEYS["device_id"], device_id)
        return {
            "cloud_api_base": ShopSyncService._get_setting(SYNC_KEYS["cloud_url"]),
            "tenant_slug": ShopSyncService._get_setting(SYNC_KEYS["tenant_slug"]),
            "sync_secret": ShopSyncService._get_setting(SYNC_KEYS["sync_secret"]),
            "device_id": device_id,
            "last_sync_at": ShopSyncService._get_setting(SYNC_KEYS["last_at"]),
            "last_pull_at": ShopSyncService._get_setting(SYNC_KEYS["last_pull_at"]),
            "last_status": ShopSyncService._get_setting(SYNC_KEYS["last_status"]),
            "last_message": ShopSyncService._get_setting(SYNC_KEYS["last_message"]),
            "initial_pull_done": ShopSyncService._get_setting(SYNC_KEYS["initial_pull_done"]) == "1",
        }

    @staticmethod
    def save_config(*, data: dict, user=None):
        if "cloud_api_base" in data:
            ShopSyncService._set_setting(SYNC_KEYS["cloud_url"], data.get("cloud_api_base") or "", user)
        if "tenant_slug" in data:
            ShopSyncService._set_setting(SYNC_KEYS["tenant_slug"], data.get("tenant_slug") or "", user)
        if "sync_secret" in data:
            ShopSyncService._set_setting(SYNC_KEYS["sync_secret"], data.get("sync_secret") or "", user)
        return ShopSyncService.get_config()

    @staticmethod
    def _device_id() -> str:
        return ShopSyncService.get_config()["device_id"]

    @staticmethod
    def _sync_headers(cfg: dict) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Tenant-Slug": cfg.get("tenant_slug") or "",
            "X-Sync-Secret": cfg.get("sync_secret") or "",
        }

    @staticmethod
    def _collect_payload(*, since=None):
        company = Company.active_objects().first()
        branch_id = None
        if company:
            branch = Branch.active_objects().filter(company=company, is_active=True).first()
            branch_id = str(branch.id) if branch else None

        catalog = CatalogSyncEngine.export_shop_push(since=since)
        return {
            "device_id": ShopSyncService._device_id(),
            "company_name": company.name if company else "",
            "kpis": {
                "today": AnalyticsService.get_kpis(branch_id=branch_id, period="today"),
                "month": AnalyticsService.get_kpis(branch_id=branch_id, period="month"),
            },
            "customers": catalog["customers"],
            "invoices": catalog["invoices"],
            "inventory": catalog["inventory"],
            "synced_at": timezone.now().isoformat(),
        }

    @staticmethod
    def _http_json(method: str, url: str, headers: dict, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Cloud sync failed ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Cloud unreachable: {exc.reason}") from exc

    @staticmethod
    def run_sync(*, user=None) -> dict:
        cfg = ShopSyncService.get_config()
        cloud = (cfg.get("cloud_api_base") or "").rstrip("/")
        slug = cfg.get("tenant_slug") or ""
        secret = cfg.get("sync_secret") or ""
        if not cloud or not slug or not secret:
            raise ValueError("Cloud sync is not configured. Set cloud URL, shop slug, and sync secret.")

        headers = ShopSyncService._sync_headers(cfg)
        initial_done = ShopSyncService._get_setting(SYNC_KEYS["initial_pull_done"], "") == "1"
        if not initial_done and ShopSyncService._get_setting(SYNC_KEYS["last_at"]):
            initial_done = True

        if not initial_done:
            pull_url = f"{cloud}/sync/shop-pull/"
            pull_response = ShopSyncService._http_json("GET", pull_url, headers)
            pull_data = pull_response.get("data", pull_response)
            pulled_stats = CatalogSyncEngine.apply_pull_bundle(pull_data, user=user)
            now = timezone.now().isoformat()
            ShopSyncService._set_setting(SYNC_KEYS["initial_pull_done"], "1", user)
            ShopSyncService._set_setting(SYNC_KEYS["last_at"], now, user)
            ShopSyncService._set_setting(SYNC_KEYS["last_pull_at"], pull_data.get("server_time", now), user)
            ShopSyncService._set_setting(SYNC_KEYS["last_status"], "success", user)
            msg = (
                f"Initial download from cloud: {pulled_stats.get('products', 0)} products, "
                f"{pulled_stats.get('customers', 0)} customers."
            )
            ShopSyncService._set_setting(SYNC_KEYS["last_message"], msg, user)
            return {
                "status": "success",
                "mode": "initial_pull",
                "synced_at": now,
                "pulled": pulled_stats,
                "message": msg,
            }

        since = parse_since(cfg.get("last_sync_at"))
        push_payload = ShopSyncService._collect_payload(since=since)
        push_result = ShopSyncService._http_json(
            "POST",
            f"{cloud}/sync/shop-push/",
            headers,
            push_payload,
        )

        now = timezone.now().isoformat()
        ShopSyncService._set_setting(SYNC_KEYS["last_at"], now, user)
        ShopSyncService._set_setting(SYNC_KEYS["last_status"], "success", user)

        pushed_invoices = len(push_payload.get("invoices", []))
        pushed_customers = len(push_payload.get("customers", []))
        msg = f"Uploaded to cloud: {pushed_invoices} invoices, {pushed_customers} customers."
        ShopSyncService._set_setting(SYNC_KEYS["last_message"], msg, user)

        return {
            "status": "success",
            "mode": "push",
            "synced_at": now,
            "pushed": {
                "invoices": pushed_invoices,
                "customers": pushed_customers,
                "inventory": len(push_payload.get("inventory", [])),
            },
            "cloud": push_result.get("data", {}),
            "message": msg,
        }

    @staticmethod
    def ensure_tenant_sync_secret(tenant: Tenant) -> str:
        if not tenant.sync_secret:
            tenant.sync_secret = secrets.token_urlsafe(24)
            tenant.save(update_fields=["sync_secret", "updated_at"])
        return tenant.sync_secret


class CloudShopSyncService:
    @staticmethod
    def receive_push(*, tenant_slug: str, sync_secret: str, payload: dict) -> ShopSyncSnapshot:
        tenant = Tenant.objects.select_related("subscription__plan").get(
            slug=tenant_slug, sync_secret=sync_secret, is_active=True
        )
        apply_stats = CatalogSyncEngine.apply_shop_push(tenant=tenant, payload=payload)
        snap = ShopSyncSnapshot.objects.create(
            tenant=tenant,
            device_id=payload.get("device_id", ""),
            synced_at=timezone.now(),
            kpis=payload.get("kpis", {}),
            invoices=payload.get("invoices", []),
            company_name=payload.get("company_name", ""),
            payload={**payload, "apply_stats": apply_stats},
        )
        return snap

    @staticmethod
    def build_pull(*, tenant_slug: str, sync_secret: str, since: str | None = None) -> dict:
        tenant = Tenant.objects.select_related("subscription__plan").get(
            slug=tenant_slug, sync_secret=sync_secret, is_active=True
        )
        since_dt = parse_since(since)
        return CatalogSyncEngine.export_pull_bundle(tenant=tenant, since=since_dt)

    @staticmethod
    def latest_kpis(tenant: Tenant) -> dict | None:
        snap = tenant.sync_snapshots.order_by("-synced_at").first()
        if not snap:
            return None
        month = snap.kpis.get("month") if isinstance(snap.kpis, dict) else None
        return month or snap.kpis
