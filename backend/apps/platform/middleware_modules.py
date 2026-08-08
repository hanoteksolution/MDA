"""Reject API calls when the acting tenant does not have the required module enabled."""

from __future__ import annotations

import json

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from apps.platform.services.module_service import (
    missing_module_dependencies,
    module_required_for_path,
    tenant_has_module,
)


class ModuleGateMiddleware(MiddlewareMixin):
    """
    Path-prefix module enforcement after JWT can be resolved.

    Unauthenticated requests are left for DRF (401). Platform admins bypass.
    """

    def process_request(self, request):
        path = request.path or ""
        code = module_required_for_path(path)
        if not code:
            return None

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            user = self._authenticate_jwt(request)

        if user is None or not getattr(user, "is_authenticated", False):
            return None

        if tenant_has_module(code, user=user, request=request):
            missing = missing_module_dependencies(code, user=user, request=request)
            if not missing:
                return None
            body = json.dumps(
                {
                    "success": False,
                    "message": f"Module '{code}' requires: {', '.join(missing)}.",
                    "code": "MODULE_DEPENDENCY",
                    "details": {"module": code, "missing": missing},
                    "data": None,
                }
            )
            return HttpResponse(body, status=403, content_type="application/json")

        body = json.dumps(
            {
                "success": False,
                "message": f"Module '{code}' is not enabled for this business.",
                "code": "MODULE_DISABLED",
                "details": {"module": code},
                "data": None,
            }
        )
        return HttpResponse(body, status=403, content_type="application/json")

    @staticmethod
    def _authenticate_jwt(request):
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication

            result = JWTAuthentication().authenticate(request)
            if result is None:
                return None
            return result[0]
        except Exception:
            return None
