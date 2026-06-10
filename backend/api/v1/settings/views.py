from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authentication.serializers.auth_serializers import BranchSerializer, CompanySerializer, SettingSerializer
from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import BranchService, SettingsService
from core.responses.api_response import error_response, success_response
from permissions.base import HasPermission


class BranchListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branches.view")]

    def get(self, request):
        branches = BranchService.list_branches()
        return success_response(data=BranchSerializer(branches, many=True).data)

    def post(self, request):
        if not request.user.has_permission("branches.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = BranchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = BranchService.create_branch(
            data=serializer.validated_data, created_by=request.user
        )
        return success_response(
            data=BranchSerializer(branch).data,
            message="Branch created.",
            status=status.HTTP_201_CREATED,
        )


class BranchDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branches.view")]

    def get(self, request, pk):
        branch = BranchService.list_branches().get(pk=pk)
        return success_response(data=BranchSerializer(branch).data)

    def put(self, request, pk):
        if not request.user.has_permission("branches.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        branch = BranchService.list_branches().get(pk=pk)
        serializer = BranchSerializer(branch, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        branch = BranchService.update_branch(
            branch=branch, data=serializer.validated_data, updated_by=request.user
        )
        return success_response(data=BranchSerializer(branch).data, message="Branch updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("branches.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        branch = BranchService.list_branches().get(pk=pk)
        branch.soft_delete(user=request.user)
        return success_response(message="Branch deleted.")


class BranchSetDefaultView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branches.update")]

    def post(self, request, pk):
        branch = BranchService.list_branches().get(pk=pk)
        branch = BranchService.set_default(branch=branch, updated_by=request.user)
        return success_response(data=BranchSerializer(branch).data, message="Default branch set.")


class SettingsListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("settings.view")]

    def get(self, request):
        category = request.query_params.get("category")
        settings = SettingsService.list_settings(category=category)
        return success_response(data=SettingSerializer(settings, many=True).data)


class SettingDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("settings.view")]

    def get(self, request, key):
        setting = SettingsService.get_by_key(key=key)
        if not setting:
            return error_response(message="Setting not found.", status=status.HTTP_404_NOT_FOUND)
        return success_response(data=SettingSerializer(setting).data)

    def put(self, request, key):
        if not request.user.has_permission("settings.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        setting = SettingsService.upsert(
            key=key,
            value=request.data.get("value", {}),
            category=request.data.get("category", "general"),
            user=request.user,
        )
        return success_response(data=SettingSerializer(setting).data, message="Setting updated.")


class CompanyProfileView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("settings.view")]

    def get(self, request):
        company = SettingsService.get_company_profile()
        if not company:
            return success_response(data=None)
        return success_response(data=CompanySerializer(company).data)

    def put(self, request):
        if not request.user.has_permission("settings.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        company = SettingsService.update_company_profile(data=request.data, user=request.user)
        return success_response(data=CompanySerializer(company).data, message="Company updated.")
