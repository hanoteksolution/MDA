import json
import os
import secrets
import uuid
from datetime import date, timedelta
from pathlib import Path
from urllib import error, request

from django.conf import settings
from django.utils import timezone

from apps.platform.models import ShopSyncSnapshot, Tenant
from apps.platform.services.sync_catalog import CatalogSyncEngine, parse_since
from apps.platform.services.sync_outbox_service import SyncOutboxService
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
    "subscription_alert": "sync.subscription_alert",
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
            "queue": SyncOutboxService.summary(),
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
    def _connection_file_path() -> Path | None:
        data_dir = os.environ.get("MDA_DATA_DIR") or getattr(settings, "DATA_DIR", None)
        if not data_dir:
            return None
        return Path(data_dir) / "connection.json"

    @staticmethod
    def load_connection_file() -> dict:
        """Read Tauri connection.json from the desktop data directory."""
        path = ShopSyncService._connection_file_path()
        if not path or not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        cloud = (raw.get("cloud_api_base") or raw.get("api_base") or "").strip().rstrip("/")
        return {
            "cloud_api_base": cloud,
            "tenant_slug": (raw.get("tenant_slug") or "").strip(),
            "sync_secret": (raw.get("sync_secret") or "").strip(),
        }

    @staticmethod
    def ensure_connection_config(*, overrides: dict | None = None, user=None) -> dict:
        """
        Merge connection into Django sync settings.

        Priority: explicit overrides → existing DB values → connection.json on disk.
        """
        cfg = ShopSyncService.get_config()
        file_cfg = ShopSyncService.load_connection_file()
        merged = {
            "cloud_api_base": (
                ((overrides or {}).get("cloud_api_base") or "").strip().rstrip("/")
                or (cfg.get("cloud_api_base") or "").strip().rstrip("/")
                or (file_cfg.get("cloud_api_base") or "").strip().rstrip("/")
            ),
            "tenant_slug": (
                ((overrides or {}).get("tenant_slug") or "").strip()
                or (cfg.get("tenant_slug") or "").strip()
                or (file_cfg.get("tenant_slug") or "").strip()
            ),
            "sync_secret": (
                ((overrides or {}).get("sync_secret") or "").strip()
                or (cfg.get("sync_secret") or "").strip()
                or (file_cfg.get("sync_secret") or "").strip()
            ),
        }
        if (
            merged["cloud_api_base"] != (cfg.get("cloud_api_base") or "")
            or merged["tenant_slug"] != (cfg.get("tenant_slug") or "")
            or merged["sync_secret"] != (cfg.get("sync_secret") or "")
        ):
            ShopSyncService.save_config(data=merged, user=user)
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
            "waiters": catalog.get("waiters", []),
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

        try:
            # Always pull catalog from cloud when online (products, prices, users, waiters).
            since_pull = None if not initial_done else parse_since(cfg.get("last_pull_at"))
            pull_url = f"{cloud}/sync/shop-pull/"
            if since_pull:
                pull_url = f"{pull_url}?since={since_pull.isoformat()}"
            pull_response = ShopSyncService._http_json("GET", pull_url, headers)
            pull_data = pull_response.get("data", pull_response)
            pulled_stats = CatalogSyncEngine.apply_pull_bundle(pull_data, user=user)

            now = timezone.now().isoformat()
            ShopSyncService._set_setting(SYNC_KEYS["initial_pull_done"], "1", user)
            ShopSyncService._set_setting(
                SYNC_KEYS["last_pull_at"], pull_data.get("server_time", now), user
            )

            if not initial_done:
                ShopSyncService._set_setting(SYNC_KEYS["last_at"], now, user)
                ShopSyncService._set_setting(SYNC_KEYS["last_status"], "success", user)
                msg = (
                    f"Initial download from cloud: {pulled_stats.get('products', 0)} products, "
                    f"{pulled_stats.get('customers', 0)} customers, "
                    f"{pulled_stats.get('users', 0)} users."
                )
                ShopSyncService._set_setting(SYNC_KEYS["last_message"], msg, user)
                return {
                    "status": "success",
                    "mode": "initial_pull",
                    "synced_at": now,
                    "pulled": pulled_stats,
                    "message": msg,
                    "queue": SyncOutboxService.summary(),
                }

            # Then push local sales / customers / stock / waiters to cloud.
            since_push = parse_since(cfg.get("last_sync_at") or cfg.get("last_at"))
            push_payload = ShopSyncService._collect_payload(since=since_push)
            push_result = ShopSyncService._http_json(
                "POST",
                f"{cloud}/sync/shop-push/",
                headers,
                push_payload,
            )

            invoice_ids = [
                inv.get("local_id")
                for inv in push_payload.get("invoices", [])
                if inv.get("local_id")
            ]
            SyncOutboxService.mark_invoices_synced(invoice_ids=invoice_ids)

            ShopSyncService._set_setting(SYNC_KEYS["last_at"], now, user)
            ShopSyncService._set_setting(SYNC_KEYS["last_status"], "success", user)

            pushed_invoices = len(push_payload.get("invoices", []))
            pushed_customers = len(push_payload.get("customers", []))
            msg = (
                f"Synced — pulled {pulled_stats.get('products', 0)} products, "
                f"{pulled_stats.get('users', 0)} users; "
                f"uploaded {pushed_invoices} invoices, {pushed_customers} customers."
            )
            ShopSyncService._set_setting(SYNC_KEYS["last_message"], msg, user)

            return {
                "status": "success",
                "mode": "bidirectional",
                "synced_at": now,
                "pulled": pulled_stats,
                "pushed": {
                    "invoices": pushed_invoices,
                    "customers": pushed_customers,
                    "inventory": len(push_payload.get("inventory", [])),
                    "waiters": len(push_payload.get("waiters", [])),
                },
                "cloud": push_result.get("data", {}),
                "message": msg,
                "queue": SyncOutboxService.summary(),
            }
        except Exception as exc:
            err_msg = str(exc)[:500]
            SyncOutboxService.mark_push_failed(err_msg)
            ShopSyncService._set_setting(SYNC_KEYS["last_status"], "error", user)
            ShopSyncService._set_setting(SYNC_KEYS["last_message"], err_msg, user)
            raise

    @staticmethod
    def get_subscription_status() -> dict:
        """
        Evaluate synced subscription against the device clock.
        Used offline to soft-warn or hard-lock the shop app.
        """
        row = SettingsService.get_by_key(key=SYNC_KEYS["subscription_alert"])
        raw = row.value if row else None
        payload = None
        if isinstance(raw, dict):
            payload = raw
        elif isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    payload = parsed
            except (json.JSONDecodeError, TypeError):
                payload = None

        if not payload:
            return {
                "has_subscription": False,
                "locked": False,
                "show_alert": False,
                "is_usable": True,
                "alert": None,
                "evaluated_on": timezone.localdate().isoformat(),
                "source": "none",
            }

        today = timezone.localdate()
        expires_raw = payload.get("expires_at")
        grace_days = int(payload.get("grace_period_days") or 5)
        warning_days = int(payload.get("warning_days") or 5)
        status = (payload.get("status") or "").lower()
        payment_current = bool(payload.get("is_payment_current"))

        expires_at = None
        if expires_raw:
            try:
                expires_at = date.fromisoformat(str(expires_raw)[:10])
            except ValueError:
                expires_at = None

        days_until = (expires_at - today).days if expires_at else None
        grace_remaining = None
        if expires_at and days_until is not None and days_until < 0:
            grace_remaining = max(grace_days - (today - expires_at).days, 0)

        if status == "suspended":
            locked = True
        elif expires_at:
            locked = today > (expires_at + timedelta(days=grace_days))
        else:
            locked = False

        show_alert = False
        if not locked and expires_at and not payment_current:
            if days_until is not None and 0 <= days_until <= warning_days:
                show_alert = True
            elif days_until is not None and days_until < 0 and grace_remaining is not None and grace_remaining >= 0:
                show_alert = True

        alert = {
            **payload,
            "is_usable": not locked,
            "days_until_expiry": days_until,
            "grace_days_remaining": grace_remaining,
            "severity": "critical" if (locked or (days_until is not None and days_until < 0)) else "warning",
        }
        if locked:
            alert["title"] = "Subscription expired — app locked"
            merchant = (payload.get("payment") or {}).get("merchant_number") or ""
            alert["message"] = (
                f"This shop's subscription ended on {expires_at.isoformat() if expires_at else '—'}. "
                + (
                    f"Pay merchant {merchant} via Waafi/EVC (scan QR below), then tap Sync now to unlock."
                    if merchant
                    else "Pay via Waafi/EVC using the QR below, then tap Sync now to unlock."
                )
            )

        return {
            "has_subscription": True,
            "locked": locked,
            "show_alert": show_alert or locked,
            "is_usable": not locked,
            "alert": alert,
            "evaluated_on": today.isoformat(),
            "source": "sync",
            "last_pull_at": ShopSyncService._get_setting(SYNC_KEYS["last_pull_at"]),
        }

    @staticmethod
    def assert_subscription_usable():
        status = ShopSyncService.get_subscription_status()
        if status.get("locked"):
            raise ValueError(
                status.get("alert", {}).get("message")
                or "Subscription expired. Sync after payment to unlock."
            )
        return status

    @staticmethod
    def ensure_tenant_sync_secret(tenant: Tenant) -> str:
        if not tenant.sync_secret:
            tenant.sync_secret = secrets.token_urlsafe(24)
            tenant.save(update_fields=["sync_secret", "updated_at"])
        return tenant.sync_secret

    @staticmethod
    def report_subscription_payment(*, payer_phone: str = "", notes: str = "") -> dict:
        """Forward 'I paid' from desktop shop → cloud (sync secret auth)."""
        cfg = ShopSyncService.ensure_connection_config()
        cloud = (cfg.get("cloud_api_base") or "").rstrip("/")
        if not cloud:
            raise ValueError("Cloud API base URL is not configured.")
        headers = ShopSyncService._sync_headers(cfg)
        url = f"{cloud}/sync/shop-report-payment/"
        response = ShopSyncService._http_json(
            "POST",
            url,
            headers,
            {"payer_phone": payer_phone or "", "notes": notes or "Reported from desktop shop"},
        )
        data = response.get("data", response)
        # Refresh local subscription alert cache if cloud returned updated alert
        alert = data.get("alert")
        if isinstance(alert, dict):
            ShopSyncService._set_setting(SYNC_KEYS["subscription_alert"], alert, None)
        return data

    @staticmethod
    def cloud_payment_status() -> dict:
        """Poll cloud for payment confirmation / auto-renew status."""
        cfg = ShopSyncService.ensure_connection_config()
        cloud = (cfg.get("cloud_api_base") or "").rstrip("/")
        if not cloud:
            raise ValueError("Cloud API base URL is not configured.")
        headers = ShopSyncService._sync_headers(cfg)
        url = f"{cloud}/sync/shop-payment-status/"
        response = ShopSyncService._http_json("GET", url, headers)
        data = response.get("data", response)
        alert = data.get("alert")
        if isinstance(alert, dict):
            ShopSyncService._set_setting(SYNC_KEYS["subscription_alert"], alert, None)
        return data


class CloudShopSyncService:
    @staticmethod
    def _tenant_from_sync(*, tenant_slug: str, sync_secret: str) -> Tenant:
        """Resolve tenant from desktop sync headers (constant-time secret check)."""
        slug = (tenant_slug or "").strip()
        secret = (sync_secret or "").strip()
        if not slug or not secret:
            raise Tenant.DoesNotExist("Missing sync credentials.")
        tenant = (
            Tenant.objects.select_related("subscription__plan")
            .filter(slug=slug, is_active=True, deleted_at__isnull=True)
            .first()
        )
        if not tenant or not tenant.sync_secret:
            raise Tenant.DoesNotExist("Invalid shop sync credentials.")
        if not secrets.compare_digest(str(tenant.sync_secret), secret):
            raise Tenant.DoesNotExist("Invalid shop sync credentials.")
        return tenant

    @staticmethod
    def verify(*, tenant_slug: str, sync_secret: str) -> dict:
        tenant = CloudShopSyncService._tenant_from_sync(
            tenant_slug=tenant_slug, sync_secret=sync_secret
        )
        return {
            "ok": True,
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "tenant_name": tenant.name,
            "status": tenant.status,
        }

    @staticmethod
    def receive_push(*, tenant_slug: str, sync_secret: str, payload: dict) -> ShopSyncSnapshot:
        tenant = CloudShopSyncService._tenant_from_sync(
            tenant_slug=tenant_slug, sync_secret=sync_secret
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
        tenant = CloudShopSyncService._tenant_from_sync(
            tenant_slug=tenant_slug, sync_secret=sync_secret
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

    @staticmethod
    def report_payment(*, tenant_slug: str, sync_secret: str, payer_phone: str = "", notes: str = "") -> dict:
        from apps.platform.services.platform_service import PlatformService

        tenant = CloudShopSyncService._tenant_from_sync(
            tenant_slug=tenant_slug, sync_secret=sync_secret
        )
        sub = getattr(tenant, "subscription", None)
        if not sub:
            raise ValueError("Shop has no subscription.")
        payment = PlatformService.report_subscription_payment(
            subscription=sub,
            payer_phone=payer_phone,
            notes=notes or "Reported via shop sync",
        )
        alert = PlatformService.enrich_alert_payload(sub)
        return {
            "payment": PlatformService.serialize_payment(payment),
            "alert": alert,
            "subscription_usable": sub.is_usable,
            "is_payment_current": sub.is_payment_current,
        }

    @staticmethod
    def payment_status(*, tenant_slug: str, sync_secret: str) -> dict:
        from apps.platform.services.platform_service import PlatformService
        from apps.platform.models import SubscriptionPayment

        tenant = CloudShopSyncService._tenant_from_sync(
            tenant_slug=tenant_slug, sync_secret=sync_secret
        )
        sub = getattr(tenant, "subscription", None)
        if not sub:
            raise ValueError("Shop has no subscription.")
        payment = (
            SubscriptionPayment.active_objects()
            .filter(subscription=sub)
            .order_by("-created_at")
            .first()
        )
        alert = PlatformService.enrich_alert_payload(sub)
        return {
            "payment": PlatformService.serialize_payment(payment) if payment else None,
            "alert": alert,
            "subscription_usable": sub.is_usable,
            "is_payment_current": sub.is_payment_current,
        }
