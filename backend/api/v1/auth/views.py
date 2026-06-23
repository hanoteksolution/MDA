from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.authentication.models import Permission, Role, User
from apps.authentication.serializers.auth_serializers import (
    LoginSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from apps.authentication.services.auth_service import AuthService, RoleService, UserService
from apps.platform.services.desktop_provision import DesktopProvisionService
from core.responses.api_response import error_response, success_response
from permissions.base import HasPermission


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, result = AuthService.login(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            request=request,
        )
        if not user:
            return error_response(message=result, status=status.HTTP_401_UNAUTHORIZED)
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
        try:
            user, tokens = DesktopProvisionService.provision_from_cloud(
                username=username,
                password=password,
                cloud_access_token=cloud_access,
                request=request,
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
        users = UserService.list_users()
        search = request.query_params.get("search")
        if search:
            users = users.filter(username__icontains=search)
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
        if role_id:
            data["role_id"] = role_id
        if branch_id:
            data["branch_id"] = branch_id
        user = UserService.create_user(data=data, created_by=request.user)
        return success_response(
            data=UserSerializer(user).data,
            message="User created.",
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("users.view")]

    def get_object(self, pk):
        return UserService.list_users().get(pk=pk)

    def get(self, request, pk):
        user = self.get_object(pk)
        return success_response(data=UserSerializer(user).data)

    def put(self, request, pk):
        if not request.user.has_permission("users.update"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        serializer = UserCreateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        role_id = data.pop("role_id", None)
        branch_id = data.pop("branch_id", None)
        if role_id:
            data["role_id"] = role_id
        if branch_id:
            data["branch_id"] = branch_id
        user = UserService.update_user(user=user, data=data, updated_by=request.user)
        return success_response(data=UserSerializer(user).data, message="User updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("users.delete"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        UserService.deactivate(user=user, deactivated_by=request.user)
        return success_response(message="User deactivated.")


class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("roles.view")]

    def get(self, request):
        roles = RoleService.list_roles()
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
        permissions = Permission.active_objects().all()
        grouped = {}
        for perm in permissions:
            grouped.setdefault(perm.module, []).append(PermissionSerializer(perm).data)
        return success_response(data=grouped)
