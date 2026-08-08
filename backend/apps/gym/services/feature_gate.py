"""Gym ModuleFeature gates (STEP 68)."""

from rest_framework import status

from apps.platform.services.module_feature_service import ModuleFeatureService
from core.responses.api_response import error_response


def require_gym_feature(request, feature: str):
    if ModuleFeatureService.tenant_has_feature(
        "gym", feature, user=request.user, request=request
    ):
        return None
    return error_response(
        message=f"Gym feature '{feature}' is not enabled for this business.",
        status=status.HTTP_403_FORBIDDEN,
        code="MODULE_FEATURE_DISABLED",
        details={"module": "gym", "feature": feature},
    )


def gym_feature_required(feature: str):
    """Class decorator: require a gym ModuleFeature after DRF auth/permissions."""

    def decorator(cls):
        original_dispatch = cls.dispatch

        def dispatch(self, request, *args, **kwargs):
            method = (getattr(request, "method", None) or "get").lower()
            handler = getattr(self, method, None)
            if callable(handler) and method in getattr(
                self, "http_method_names", ("get", "post", "put", "patch", "delete")
            ):

                def wrapped(request, *hargs, **hkwargs):
                    denied = require_gym_feature(request, feature)
                    if denied:
                        return denied
                    return handler(request, *hargs, **hkwargs)

                setattr(self, method, wrapped)
            return original_dispatch(self, request, *args, **kwargs)

        cls.dispatch = dispatch
        return cls

    return decorator
