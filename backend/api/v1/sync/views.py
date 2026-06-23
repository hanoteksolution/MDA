from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.platform.services.sync_service import CloudShopSyncService, ShopSyncService
from core.responses.api_response import error_response, success_response


class SyncConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(data=ShopSyncService.get_config())

    def put(self, request):
        data = ShopSyncService.save_config(data=request.data, user=request.user)
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
        return success_response(data=result, message=result.get("message", "Bidirectional sync complete."))


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
