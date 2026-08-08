from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.authentication.serializers.auth_serializers import UserSerializer
from apps.authentication.services.auth_service import AuthService
from apps.platform.services.onboarding_service import OnboardingError, OnboardingService
from core.responses.api_response import error_response, success_response


class OnboardingCatalogView(APIView):
    """Public catalog for the self-serve wizard (business types + plans)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return success_response(data=OnboardingService.catalog())


class OnboardingSlugCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raw = (request.query_params.get("slug") or request.query_params.get("subdomain") or "").strip()
        return success_response(data=OnboardingService.check_slug(raw))


class OnboardingProvisionView(APIView):
    """
    Self-serve shop provisioning.

    Idempotent: retrying with the same subdomain + owner credentials returns the
    existing tenant instead of failing.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            result = OnboardingService.provision(data=request.data)
        except OnboardingError as exc:
            http_status = status.HTTP_409_CONFLICT if exc.code == "SLUG_TAKEN" else status.HTTP_400_BAD_REQUEST
            return error_response(
                message=exc.message,
                status=http_status,
                code=exc.code,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)

        owner_username = (request.data.get("owner") or {}).get("username") or ""
        owner_password = (request.data.get("owner") or {}).get("password") or ""
        user, tokens_or_error = AuthService.login(
            username=owner_username,
            password=owner_password,
            request=request,
        )
        if not user or not isinstance(tokens_or_error, dict):
            return success_response(
                data=result,
                message="Shop provisioned. Please sign in.",
                status=status.HTTP_201_CREATED,
            )

        return success_response(
            data={
                **result,
                **tokens_or_error,
                "user": UserSerializer(user).data,
            },
            message="Shop provisioned." if not result.get("idempotent_replay") else "Shop already provisioned.",
            status=status.HTTP_200_OK if result.get("idempotent_replay") else status.HTTP_201_CREATED,
        )
