from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone

from apps.platform.models import Tenant
from apps.platform.services.sync_service import CloudShopSyncService, ShopSyncService
from core.responses.api_response import error_response, success_response


class SyncConfigView(APIView):
    """
    Authenticated sync settings.

    On desktop with an empty user DB, AllowAny so Connection can be saved
    before the first cloud shop login/provision.
    """

    def get_permissions(self):
        from django.conf import settings

        from apps.authentication.services.setup_service import SetupService

        if (
            getattr(settings, "DESKTOP_MODE", False)
            and SetupService.needs_setup()
            and self.request.method in ("PUT", "PATCH", "GET")
        ):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        ShopSyncService.ensure_connection_config()
        return success_response(data=ShopSyncService.get_config())

    def put(self, request):
        user = request.user if getattr(request.user, "is_authenticated", False) else None
        data = ShopSyncService.save_config(data=request.data, user=user)
        return success_response(data=data, message="Sync settings saved.")


class SyncRunView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = ShopSyncService.run_sync(user=request.user)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return error_response(message=str(exc), status=status.HTTP_502_BAD_GATEWAY)
        result["subscription"] = ShopSyncService.get_subscription_status()
        return success_response(data=result, message=result.get("message", "Bidirectional sync complete."))


class SubscriptionStatusView(APIView):
    """Local subscription lock status from last cloud sync (works offline)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = ShopSyncService.get_subscription_status()
        # Cloud browser shops: evaluate live subscription when no sync cache exists
        if not data.get("has_subscription"):
            from django.conf import settings

            if not getattr(settings, "DESKTOP_MODE", False):
                from apps.platform.services.platform_service import PlatformService

                tenant = PlatformService.resolve_user_tenant(request.user)
                sub = getattr(tenant, "subscription", None) if tenant else None
                if sub:
                    alert = PlatformService.enrich_alert_payload(sub, user=request.user)
                    locked = not sub.is_usable
                    show = locked or sub.needs_payment_alert
                    data = {
                        "has_subscription": True,
                        "locked": locked,
                        "show_alert": show,
                        "is_usable": not locked,
                        "alert": alert if show else None,
                        "evaluated_on": timezone.localdate().isoformat(),
                        "source": "live",
                    }
        return success_response(data=data)


class SyncReportPaymentView(APIView):
    """Desktop shop reports Waafi/EVC payment → cloud tracking + auto-renew."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = ShopSyncService.report_subscription_payment(
                payer_phone=request.data.get("payer_phone", ""),
                notes=request.data.get("notes", ""),
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return error_response(message=str(exc), status=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data, message="Payment reported to cloud.")


class SyncPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            data = ShopSyncService.cloud_payment_status()
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return error_response(message=str(exc), status=status.HTTP_502_BAD_GATEWAY)
        return success_response(data=data)


class ShopReportPaymentView(APIView):
    """Cloud endpoint: shop PC reports payment using sync secret."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        slug = request.headers.get("X-Tenant-Slug", "").strip()
        secret = request.headers.get("X-Sync-Secret", "").strip()
        if not slug or not secret:
            return error_response(message="Missing sync credentials.", status=status.HTTP_401_UNAUTHORIZED)
        try:
            data = CloudShopSyncService.report_payment(
                tenant_slug=slug,
                sync_secret=secret,
                payer_phone=request.data.get("payer_phone", ""),
                notes=request.data.get("notes", ""),
            )
        except Tenant.DoesNotExist:
            return error_response(message="Invalid shop sync credentials.", status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return error_response(message="Invalid shop sync credentials.", status=status.HTTP_403_FORBIDDEN)
        return success_response(data=data, message="Payment reported.")


class ShopPaymentStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        slug = request.headers.get("X-Tenant-Slug", "").strip()
        secret = request.headers.get("X-Sync-Secret", "").strip()
        if not slug or not secret:
            return error_response(message="Missing sync credentials.", status=status.HTTP_401_UNAUTHORIZED)
        try:
            data = CloudShopSyncService.payment_status(tenant_slug=slug, sync_secret=secret)
        except Exception:
            return error_response(message="Invalid shop sync credentials.", status=status.HTTP_403_FORBIDDEN)
        return success_response(data=data)


class ShopPushSyncView(APIView):
    """Receive shop data from offline PCs (no user JWT — uses tenant slug + sync secret)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        slug = request.headers.get("X-Tenant-Slug", "").strip()
        secret = request.headers.get("X-Sync-Secret", "").strip()
        if not slug or not secret:
            return error_response(message="Missing sync credentials.", status=status.HTTP_401_UNAUTHORIZED)
        try:
            snap = CloudShopSyncService.receive_push(
                tenant_slug=slug,
                sync_secret=secret,
                payload=request.data,
            )
        except Exception:
            return error_response(message="Invalid shop sync credentials.", status=status.HTTP_403_FORBIDDEN)
        apply_stats = (snap.payload or {}).get("apply_stats", {})
        return success_response(
            data={
                "snapshot_id": str(snap.id),
                "synced_at": snap.synced_at.isoformat(),
                "invoice_count": len(snap.invoices),
                "applied": apply_stats,
            },
            message="Shop data received and applied.",
        )


class ShopPullSyncView(APIView):
    """Send catalog + customers from cloud to offline shop PCs."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        slug = request.headers.get("X-Tenant-Slug", "").strip()
        secret = request.headers.get("X-Sync-Secret", "").strip()
        if not slug or not secret:
            return error_response(message="Missing sync credentials.", status=status.HTTP_401_UNAUTHORIZED)
        since = request.query_params.get("since", "").strip() or None
        try:
            data = CloudShopSyncService.build_pull(
                tenant_slug=slug,
                sync_secret=secret,
                since=since,
            )
        except Exception:
            return error_response(message="Invalid shop sync credentials.", status=status.HTTP_403_FORBIDDEN)
        return success_response(data=data, message="Catalog bundle ready.")
