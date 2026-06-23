from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.authentication.serializers.auth_serializers import CompanySerializer, UserSerializer
from apps.authentication.services.auth_service import AuthService
from apps.authentication.services.setup_service import SetupService
from core.responses.api_response import error_response, success_response


class SetupStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return success_response(data={"needs_setup": SetupService.needs_setup()})


class SetupCompleteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not SetupService.needs_setup():
            return error_response(
                message="Setup has already been completed.",
                status=status.HTTP_403_FORBIDDEN,
            )

        company_data = request.data.get("company") or {}
        user_data = request.data.get("user") or {}
        branch_data = request.data.get("branch")

        username = (user_data.get("username") or "").strip()
        password = user_data.get("password") or ""
        email = (user_data.get("email") or "").strip()
        company_name = (company_data.get("name") or "").strip()

        errors = {}
        if not company_name:
            errors["company.name"] = "Company name is required."
        if not username:
            errors["user.username"] = "Username is required."
        if len(password) < 8:
            errors["user.password"] = "Password must be at least 8 characters."
        if not email:
            errors["user.email"] = "Email is required."

        if errors:
            return error_response(message="Validation failed.", errors=errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user, company, branch = SetupService.complete_setup(
                company_data={**company_data, "name": company_name},
                user_data={
                    "username": username,
                    "password": password,
                    "email": email,
                    "first_name": user_data.get("first_name", ""),
                    "last_name": user_data.get("last_name", ""),
                },
                branch_data=branch_data,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)

        _, tokens = AuthService.login(username=username, password=password, request=request)
        return success_response(
            data={
                **tokens,
                "user": UserSerializer(user).data,
                "company": CompanySerializer(company).data,
                "branch": {"id": str(branch.id), "name": branch.name, "code": branch.code},
            },
            message="Setup completed successfully.",
            status=status.HTTP_201_CREATED,
        )
