from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.platform.models import RegistrationRequest
from apps.platform.services.registration_service import (
    PublicCatalogService,
    RegistrationError,
    RegistrationService,
)
from core.responses.api_response import error_response, success_response


class PublicView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]


class CatalogView(PublicView):
    throttle_scope = "public_catalog"

    def get(self, request):
        return success_response(data=PublicCatalogService.catalog())


class CatalogSectionView(PublicView):
    throttle_scope = "public_catalog"
    section = ""

    def get(self, request):
        return success_response(data=PublicCatalogService.catalog()[self.section])


class BusinessTypesView(CatalogSectionView):
    section = "business_types"


class BusinessPresetsView(CatalogSectionView):
    section = "business_presets"


class ModulesView(CatalogSectionView):
    section = "modules"


class PlansView(CatalogSectionView):
    section = "plans"


class SubdomainCheckView(PublicView):
    throttle_scope = "subdomain_check"

    def get(self, request):
        value = request.query_params.get("subdomain") or request.query_params.get("slug") or ""
        return success_response(data=RegistrationService.check_subdomain(value))


class RegistrationView(PublicView):
    throttle_scope = "registration"

    def post(self, request):
        try:
            row = RegistrationService.create(
                data=request.data,
                idempotency_key=request.headers.get("Idempotency-Key", ""),
                request=request,
            )
        except RegistrationError as exc:
            return error_response(
                message=str(exc),
                code=exc.code,
                errors=exc.field_errors,
                details={
                    "field_errors": exc.field_errors,
                    **({"suggestions": exc.suggestions} if exc.suggestions else {}),
                },
                status=exc.status,
            )
        return success_response(
            data=RegistrationService.payload(row),
            message="Your workspace is ready." if row.status == row.STATUS_READY else "Check your email to continue.",
            status=status.HTTP_201_CREATED,
        )


class RegistrationStatusView(PublicView):
    throttle_scope = "registration_status"

    def get(self, request, registration_id):
        row = RegistrationRequest.active_objects().select_related("tenant").filter(id=registration_id).first()
        if not row:
            return error_response(message="Registration was not found.", code="NOT_FOUND", status=404)
        return success_response(data=RegistrationService.payload(row))


class VerifyEmailView(PublicView):
    throttle_scope = "email_verification"

    def post(self, request):
        try:
            row = RegistrationService.verify(request.data.get("token", ""))
        except RegistrationError as exc:
            return error_response(message=str(exc), code=exc.code, status=exc.status)
        return success_response(data=RegistrationService.payload(row), message="Email verified. Your workspace is ready.")
