from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from django.db.models import Q

from apps.authentication.models import Permission, Role, User
from apps.authentication.serializers.auth_serializers import (
    LoginSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from apps.authentication.services.auth_service import AuthService, RoleService, UserService
from apps.authentication.services.login_lockout_service import LoginLockoutService
from apps.platform.services.desktop_provision import DesktopProvisionService
from apps.platform.services.tenant_resolver import user_matches_host_tenant
from core.responses.api_response import error_response, success_response
from core.throttling import AuthRateThrottle
from permissions.base import HasPermission


class MobileTokenRefreshView(TokenRefreshView):
    """JWT refresh with the standard success envelope for mobile clients."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return success_response(data=response.data, message="Token refreshed.")
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        locked, lock_details = LoginLockoutService.is_locked(username=username, request=request)
        if locked:
            return error_response(
                message=LoginLockoutService.lockout_message(lock_details),
                status=status.HTTP_403_FORBIDDEN,
                code="ACCOUNT_LOCKED",
                details=lock_details or {},
            )
        user, result = AuthService.login(
            username=username,
            password=serializer.validated_data["password"],
            request=request,
        )
        if not user:
            LoginLockoutService.record_failure(username=username, request=request)
            return error_response(
                message=result,
                status=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_CREDENTIALS",
            )
        LoginLockoutService.record_success(username=username, request=request)
        host_tenant = getattr(request, "tenant", None)
        if getattr(request, "tenant_mode", None) == "tenant" and host_tenant is not None:
            if not user_matches_host_tenant(user, host_tenant):
                return error_response(
                    message="This account does not belong to this business domain.",
                    status=status.HTTP_403_FORBIDDEN,
                    code="TENANT_HOST_MISMATCH",
                )
        return success_response(
            data={
                **result,
                "user": UserSerializer(user).data,
            },
            message="Login successful.",
        )


class LogoutView(APIView):
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            AuthService.logout(user=request.user, refresh_token=refresh, request=request)
        return success_response(message="Logout successful.")


class MeView(APIView):
    def get(self, request):
        return success_response(data=UserSerializer(request.user).data)


class DesktopUserStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        username = (request.query_params.get("username") or "").strip()
        if not username:
            return error_response(message="Username is required.", status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=DesktopProvisionService.user_status(username=username))


class DesktopProvisionView(APIView):
    """First-time shop login: verify cloud account, create local user with cloud role/permissions."""

    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        cloud_access = (request.data.get("cloud_access_token") or "").strip()
        if not username or not password or not cloud_access:
            return error_response(
                message="Username, password, and cloud access token are required.",
                status=status.HTTP_400_BAD_REQUEST,
            )
        connection = {
            "cloud_api_base": (request.data.get("cloud_api_base") or "").strip(),
            "tenant_slug": (request.data.get("tenant_slug") or "").strip(),
            "sync_secret": (request.data.get("sync_secret") or "").strip(),
        }
        try:
            user, tokens = DesktopProvisionService.provision_from_cloud(
                username=username,
                password=password,
                cloud_access_token=cloud_access,
                request=request,
                connection=connection,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data={
                **tokens,
                "user": UserSerializer(user).data,
            },
            message="Shop account provisioned. Sign in locally from now on.",
            status=status.HTTP_201_CREATED,
        )


class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("users.view")]

    def get(self, request):
        users = UserService.list_users(viewer=request.user)
        search = request.query_params.get("search")
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        serializer = UserSerializer(users, many=True)
        return success_response(data=serializer.data)

    def post(self, request):
        if not request.user.has_permission("users.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        permission_ids = data.pop("permission_ids", None)
        if role_id:
            data["role_id"] = role_id
        if branch_id:
            data["branch_id"] = branch_id
        if permission_ids is not None:
            data["permission_ids"] = permission_ids
        try:
            user = UserService.create_user(data=data, created_by=request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(
            data=UserSerializer(user).data,
            message="User created.",
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("users.view")]

    def get_object(self, pk, viewer):
        return UserService.get_manageable_user(pk=pk, viewer=viewer)

    def get(self, request, pk):
        try:
            user = self.get_object(pk, request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
        return success_response(data=UserSerializer(user).data)

    def put(self, request, pk):
        if not request.user.has_permission("users.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            user = self.get_object(pk, request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
        serializer = UserCreateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        permission_ids = data.pop("permission_ids", None)
        if role_id is not None:
            data["role_id"] = role_id
        if branch_id is not None:
            data["branch_id"] = branch_id
        if permission_ids is not None:
            data["permission_ids"] = permission_ids
        try:
            user = UserService.update_user(user=user, data=data, updated_by=request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(data=UserSerializer(user).data, message="User updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("users.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        try:
            user = self.get_object(pk, request.user)
            UserService.deactivate(user=user, deactivated_by=request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(message="User deactivated.")


class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("roles.view")]

    def get(self, request):
        roles = RoleService.list_roles(viewer=request.user)
        return success_response(data=RoleSerializer(roles, many=True).data)

    def post(self, request):
        if not request.user.has_permission("roles.create"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        permission_ids = data.pop("permission_ids", [])
        role = RoleService.create_role(
            permission_ids=permission_ids,
            created_by=request.user,
            **data,
        )
        return success_response(
            data=RoleSerializer(role).data,
            message="Role created.",
            status=status.HTTP_201_CREATED,
        )


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("roles.view")]

    def get(self, request, pk):
        role = RoleService.list_roles().get(pk=pk)
        return success_response(data=RoleSerializer(role).data)

    def put(self, request, pk):
        if not request.user.has_permission("roles.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        role = RoleService.list_roles().get(pk=pk)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        permission_ids = data.pop("permission_ids", None)
        update_data = dict(data)
        if permission_ids is not None:
            update_data["permission_ids"] = permission_ids
        role = RoleService.update_role(role=role, data=update_data, updated_by=request.user)
        return success_response(data=RoleSerializer(role).data, message="Role updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("roles.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        role = RoleService.list_roles().get(pk=pk)
        try:
            RoleService.delete_role(role=role, deleted_by=request.user)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return success_response(message="Role deleted.")


class PermissionListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("roles.view")]

    def get(self, request):
        permissions = UserService.list_assignable_permissions(viewer=request.user)
        grouped = {}
        for perm in permissions:
            grouped.setdefault(perm.module, []).append(PermissionSerializer(perm).data)
        return success_response(data=grouped)
