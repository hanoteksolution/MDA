"""Block write API calls when tenant subscription is past grace period."""

from __future__ import annotations

import json

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from apps.platform.services.entitlement_service import EntitlementService


class SubscriptionEntitlementMiddleware(MiddlewareMixin):
    """
    Read-only mode after subscription grace expires. Data is never deleted.

    Runs after TenantResolutionMiddleware; JWT may be resolved here like ModuleGateMiddleware.
    """

    def process_request(self, request):
        err = EntitlementService.write_blocked_for_request(request)
        if err is None:
            return None
        body = json.dumps(
            {
                "success": False,
                "message": err.message,
                "code": err.code,
                "details": {"can_read": True},
                "data": None,
            }
        )
        return HttpResponse(body, status=403, content_type="application/json")
