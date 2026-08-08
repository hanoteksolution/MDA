"""Mobile API contract endpoints (STEP 27)."""

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.authentication.serializers.auth_serializers import UserSerializer
from apps.platform.services.entitlement_service import EntitlementService
from apps.platform.services.mobile_nav_service import MobileNavService
from apps.platform.services.tenant_resolver import resolution_public_payload
from core.responses.api_response import success_response


class MobileMetaView(APIView):
    """Public API contract metadata for React Native bootstrap."""

    permission_classes = [AllowAny]
    throttle_classes = []  # discovery endpoint; avoid counting against auth limits

    def get(self, request):
        page_size = getattr(settings, "REST_FRAMEWORK", {}).get("PAGE_SIZE", 20)
        throttle_rates = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})
        return success_response(
            data={
                "api_version": "v1",
                "auth": {
                    "login": "/api/v1/auth/login/",
                    "refresh": "/api/v1/auth/refresh/",
                    "logout": "/api/v1/auth/logout/",
                    "me": "/api/v1/auth/me/",
                },
                "mobile": {
                    "meta": "/api/v1/mobile/meta/",
                    "bootstrap": "/api/v1/mobile/bootstrap/",
                    "gym": {
                        "home": "/api/v1/mobile/gym/home/",
                        "profile": "/api/v1/mobile/gym/profile/",
                        "qr": "/api/v1/mobile/gym/qr/",
                        "attendance": "/api/v1/mobile/gym/attendance/",
                        "workouts": "/api/v1/mobile/gym/workouts/",
                        "classes": "/api/v1/mobile/gym/classes/",
                    },
                },
                "tenant": {
                    "slug_header": getattr(settings, "MOBILE_TENANT_SLUG_HEADER", "X-Tenant-Slug"),
                    "host_pattern": "{slug}.{base_domain}",
                    "resolve_host": "/api/v1/platform/resolve-host/",
                    "resolution": "Host subdomain or slug header on platform API host",
                },
                "pagination": {
                    "page_param": "page",
                    "page_size_param": "page_size",
                    "default_page_size": page_size,
                    "max_page_size": 100,
                    "envelope": {
                        "results": "data.results",
                        "count": "data.count",
                        "page": "data.page",
                        "page_size": "data.page_size",
                        "total_pages": "data.total_pages",
                    },
                },
                "response_envelope": {
                    "success_field": "success",
                    "data_field": "data",
                    "message_field": "message",
                    "code_field": "code",
                    "errors_field": "errors",
                    "details_field": "details",
                },
                "openapi": {
                    "schema": "/api/v1/schema/",
                    "docs": "/api/v1/docs/",
                },
                "rate_limits": throttle_rates,
            }
        )


class MobileBootstrapView(APIView):
    """Authenticated mobile session bootstrap: user, tenant, entitlements, nav."""

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        resolution = getattr(request, "tenant_resolution", None)
        entitlements = EntitlementService.evaluate(tenant=tenant) if tenant else None
        audience = (request.query_params.get("audience") or "").strip().lower() or None
        if audience not in (None, "member", "staff"):
            audience = None
        mobile_nav = MobileNavService.list_for_actor(
            user=request.user,
            request=request,
            tenant=tenant,
            audience=audience,
        )
        gym_member = None
        try:
            from apps.gym.services.member_portal_service import MemberPortalService

            if request.user.has_permission("gym.member_portal") and any(
                w["id"] == "gym_member" for w in mobile_nav["workspaces"]
            ):
                gym_member = MemberPortalService.profile(user=request.user, request=request)
        except Exception:
            gym_member = None
        return success_response(
            data={
                "user": UserSerializer(request.user).data,
                "tenant_context": resolution_public_payload(resolution) if resolution else None,
                "entitlements": entitlements,
                "enabled_modules": mobile_nav["enabled_modules"],
                "mobile_nav": mobile_nav,
                "gym_member": gym_member,
            }
        )
