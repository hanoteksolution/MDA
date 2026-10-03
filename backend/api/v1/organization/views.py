"""Organization / branch-structure API.

Every list here is filtered through ``core.branching`` rather than through a local
branch filter, so there is one place to audit for scope-bypass bugs.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.organization.models import (
    BranchAccessProfile,
    CashRegister,
    PosTerminal,
    StockLocation,
    UserBranchAccess,
)
from apps.organization.serializers import (
    BranchAccessProfileSerializer,
    CashRegisterSerializer,
    PosTerminalSerializer,
    StockLocationSerializer,
    UserBranchAccessSerializer,
)
from apps.organization.services import (
    BranchAccessProfileService,
    BranchAccessService,
    CashRegisterService,
    PosTerminalService,
    StockLocationService,
)
from core.branching import (
    accessible_branches,
    branch_permissions,
    default_branch_for,
    get_branch_scope,
    is_branch_manager,
    resolve_branch_scope,
)
from core.responses.api_response import error_response, success_response
from permissions.base import HasPermission


def _scope(request, permission=None):
    return get_branch_scope(request, permission=permission)


class MyBranchesView(APIView):
    """Branches the caller may act in — the source for the global branch switcher.

    Deliberately requires no extra permission: it returns only what this user already
    has, and the frontend needs it to render a correct switcher.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        branches = accessible_branches(request.user, request=request)
        default_id = default_branch_for(request.user, request=request)
        payload = []
        for branch in branches:
            payload.append(
                {
                    "id": str(branch.pk),
                    "name": branch.name,
                    "code": branch.code,
                    "branch_type": getattr(branch, "branch_type", ""),
                    "status": getattr(branch, "status", "ACTIVE" if branch.is_active else "INACTIVE"),
                    "is_default": str(branch.pk) == str(default_id),
                    "is_manager": is_branch_manager(request.user, branch),
                    "permissions": sorted(branch_permissions(request.user, branch)),
                }
            )
        # "All branches" (consolidated) is only meaningful to someone who can see every branch of
        # the tenant — dashboards refuse it otherwise (reports.resolve_view_branch_id).
        from apps.settings_app.models import Branch
        from core.tenancy import resolve_acting_tenant

        tenant = resolve_acting_tenant(request=request, user=request.user)
        mine = {row["id"] for row in payload}
        tenant_ids = {
            str(pk) for pk in Branch.active_objects().filter(tenant_id=getattr(tenant, "pk", None)).values_list("pk", flat=True)
        } if tenant is not None else mine
        return success_response(
            data={
                "branches": payload,
                "default_branch_id": str(default_id) if default_id else None,
                "count": len(payload),
                "covers_all": len(payload) > 1 and bool(tenant_ids) and tenant_ids <= mine,
            }
        )


class BranchContextView(APIView):
    """The branch scope the backend resolved for this request (debugging + UI state)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = resolve_branch_scope(request=request)
        return success_response(
            data={
                "branch_ids": [str(b) for b in scope.branch_ids],
                "branch_id": str(scope.branch_id) if scope.branch_id else None,
                "is_all": scope.is_all,
                "requested_all": scope.requested_all,
                "unscoped": scope.unscoped,
            }
        )


class AccessProfileListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branch.access.view")]

    def get(self, request):
        profiles = BranchAccessProfileService.list_profiles(user=request.user, request=request)
        return success_response(data=BranchAccessProfileSerializer(profiles, many=True).data)

    def post(self, request):
        if not request.user.has_permission("branch.access.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = BranchAccessProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = BranchAccessProfileService.create_profile(
            data=dict(serializer.validated_data), actor=request.user, request=request
        )
        return success_response(
            data=BranchAccessProfileSerializer(profile).data,
            message="Access profile created.",
            status=status.HTTP_201_CREATED,
        )


class AccessProfileDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branch.access.view")]

    def _get(self, request, pk):
        return get_object_or_404(
            BranchAccessProfileService.list_profiles(user=request.user, request=request), pk=pk
        )

    def get(self, request, pk):
        return success_response(data=BranchAccessProfileSerializer(self._get(request, pk)).data)

    def put(self, request, pk):
        if not request.user.has_permission("branch.access.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        profile = self._get(request, pk)
        serializer = BranchAccessProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = BranchAccessProfileService.update_profile(
            profile=profile, data=dict(serializer.validated_data), actor=request.user, request=request
        )
        return success_response(
            data=BranchAccessProfileSerializer(profile).data, message="Access profile updated."
        )

    def delete(self, request, pk):
        if not request.user.has_permission("branch.access.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        BranchAccessProfileService.delete_profile(
            profile=self._get(request, pk), actor=request.user, request=request
        )
        return success_response(message="Access profile deleted.")


class BranchAccessListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branch.access.view")]

    def get(self, request):
        from apps.authentication.models import User
        from apps.settings_app.models import Branch

        branch = None
        target_user = None
        if request.query_params.get("branch"):
            branch = Branch.objects.filter(pk=request.query_params["branch"]).first()
        if request.query_params.get("user"):
            target_user = User.objects.filter(pk=request.query_params["user"]).first()
        rows = BranchAccessService.list_access(
            actor=request.user, request=request, branch=branch, target_user=target_user
        )
        return success_response(data=UserBranchAccessSerializer(rows, many=True).data)

    def post(self, request):
        if not request.user.has_permission("branch.access.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        from apps.authentication.models import User
        from apps.settings_app.models import Branch

        serializer = UserBranchAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # The branch must be one the actor can actually see — no cross-tenant probing.
        branch = accessible_branches(request.user, request=request).filter(
            pk=data["branch_id"]
        ).first()
        if branch is None:
            return error_response(
                message="You do not have access to this branch.", status=status.HTTP_403_FORBIDDEN
            )
        target_user = User.objects.filter(pk=data["user_id"], deleted_at__isnull=True).first()
        if target_user is None:
            return error_response(message="User not found.", status=status.HTTP_404_NOT_FOUND)

        profile = None
        if data.get("access_profile_id"):
            profile = BranchAccessProfileService.list_profiles(
                user=request.user, request=request
            ).filter(pk=data["access_profile_id"]).first()
            if profile is None:
                return error_response(
                    message="Access profile not found.", status=status.HTTP_404_NOT_FOUND
                )

        access = BranchAccessService.grant(
            target_user=target_user,
            branch=branch,
            access_profile=profile,
            is_default=data.get("is_default", False),
            starts_on=data.get("starts_on"),
            ends_on=data.get("ends_on"),
            notes=data.get("notes", ""),
            actor=request.user,
            request=request,
        )
        return success_response(
            data=UserBranchAccessSerializer(access).data,
            message="Branch access granted.",
            status=status.HTTP_201_CREATED,
        )


class BranchAccessDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("branch.access.view")]

    def _get(self, request, pk):
        return get_object_or_404(
            BranchAccessService.list_access(actor=request.user, request=request), pk=pk
        )

    def get(self, request, pk):
        return success_response(data=UserBranchAccessSerializer(self._get(request, pk)).data)

    def put(self, request, pk):
        if not request.user.has_permission("branch.access.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        access = self._get(request, pk)
        serializer = UserBranchAccessSerializer(access, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("user_id", None)
        data.pop("branch_id", None)
        if "access_profile_id" in data:
            profile_id = data.pop("access_profile_id")
            data["access_profile"] = (
                BranchAccessProfileService.list_profiles(user=request.user, request=request)
                .filter(pk=profile_id)
                .first()
                if profile_id
                else None
            )
        access = BranchAccessService.update(
            access=access, data=data, actor=request.user, request=request
        )
        return success_response(
            data=UserBranchAccessSerializer(access).data, message="Branch access updated."
        )

    def delete(self, request, pk):
        if not request.user.has_permission("branch.access.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        BranchAccessService.revoke(
            access=self._get(request, pk), actor=request.user, request=request
        )
        return success_response(message="Branch access revoked.")


class StockLocationListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def get(self, request):
        scope = _scope(request, permission="inventory.view")
        locations = StockLocationService.list_locations(
            branch_ids=None if scope.unscoped else scope.branch_ids,
            user=request.user,
            request=request,
            include_inactive=request.query_params.get("include_inactive") == "true",
        )
        if request.query_params.get("warehouse"):
            locations = locations.filter(warehouse_id=request.query_params["warehouse"])
        return success_response(data=StockLocationSerializer(locations, many=True).data)

    def post(self, request):
        from apps.inventory.models import Warehouse

        if not request.user.has_permission("inventory.adjust"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = StockLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        scope = _scope(request, permission="inventory.adjust")
        warehouse = Warehouse.active_objects().filter(pk=data.pop("warehouse_id")).first()
        if warehouse is None or not (scope.unscoped or scope.allows(warehouse.branch_id)):
            return error_response(
                message="You do not have access to this warehouse.",
                status=status.HTTP_403_FORBIDDEN,
            )
        parent_id = data.pop("parent_id", None)
        if parent_id:
            data["parent"] = StockLocation.active_objects().filter(
                pk=parent_id, warehouse=warehouse
            ).first()
        location = StockLocationService.create_location(
            warehouse=warehouse, data=data, actor=request.user, request=request
        )
        return success_response(
            data=StockLocationSerializer(location).data,
            message="Location created.",
            status=status.HTTP_201_CREATED,
        )


class StockLocationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("inventory.view")]

    def _get(self, request, pk, permission="inventory.view"):
        scope = _scope(request, permission=permission)
        qs = StockLocationService.list_locations(
            branch_ids=None if scope.unscoped else scope.branch_ids,
            user=request.user,
            request=request,
            include_inactive=True,
        )
        return get_object_or_404(qs, pk=pk)

    def get(self, request, pk):
        return success_response(data=StockLocationSerializer(self._get(request, pk)).data)

    def put(self, request, pk):
        if not request.user.has_permission("inventory.adjust"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        location = self._get(request, pk, permission="inventory.adjust")
        serializer = StockLocationSerializer(location, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("warehouse_id", None)
        data.pop("parent_id", None)
        location = StockLocationService.update_location(
            location=location, data=data, actor=request.user, request=request
        )
        return success_response(data=StockLocationSerializer(location).data, message="Location updated.")

    def delete(self, request, pk):
        if not request.user.has_permission("inventory.adjust"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        StockLocationService.delete_location(
            location=self._get(request, pk, permission="inventory.adjust"),
            actor=request.user,
            request=request,
        )
        return success_response(message="Location deleted.")


class CashRegisterListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("organization.view")]

    def get(self, request):
        scope = _scope(request, permission="organization.view")
        registers = CashRegisterService.list_registers(
            branch_ids=None if scope.unscoped else scope.branch_ids,
            user=request.user,
            request=request,
        )
        return success_response(data=CashRegisterSerializer(registers, many=True).data)

    def post(self, request):
        if not request.user.has_permission("organization.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = CashRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        branch = accessible_branches(request.user, request=request).filter(
            pk=data.pop("branch_id")
        ).first()
        if branch is None:
            return error_response(
                message="You do not have access to this branch.", status=status.HTTP_403_FORBIDDEN
            )
        register = CashRegisterService.create_register(
            branch=branch, data=data, actor=request.user, request=request
        )
        return success_response(
            data=CashRegisterSerializer(register).data,
            message="Cash register created.",
            status=status.HTTP_201_CREATED,
        )


class CashRegisterDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("organization.view")]

    def _get(self, request, pk):
        scope = _scope(request, permission="organization.view")
        return get_object_or_404(
            CashRegisterService.list_registers(
                branch_ids=None if scope.unscoped else scope.branch_ids,
                user=request.user,
                request=request,
            ),
            pk=pk,
        )

    def get(self, request, pk):
        return success_response(data=CashRegisterSerializer(self._get(request, pk)).data)

    def put(self, request, pk):
        if not request.user.has_permission("organization.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        register = self._get(request, pk)
        serializer = CashRegisterSerializer(register, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("branch_id", None)
        register = CashRegisterService.update_register(
            register=register, data=data, actor=request.user, request=request
        )
        return success_response(
            data=CashRegisterSerializer(register).data, message="Cash register updated."
        )


class PosTerminalListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("organization.view")]

    def get(self, request):
        scope = _scope(request, permission="organization.view")
        terminals = PosTerminalService.list_terminals(
            branch_ids=None if scope.unscoped else scope.branch_ids,
            user=request.user,
            request=request,
        )
        return success_response(data=PosTerminalSerializer(terminals, many=True).data)

    def post(self, request):
        from apps.inventory.models import Warehouse

        if not request.user.has_permission("organization.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        serializer = PosTerminalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        branch = accessible_branches(request.user, request=request).filter(
            pk=data.pop("branch_id")
        ).first()
        if branch is None:
            return error_response(
                message="You do not have access to this branch.", status=status.HTTP_403_FORBIDDEN
            )
        warehouse_id = data.pop("default_warehouse_id", None)
        location_id = data.pop("default_location_id", None)
        register_id = data.pop("default_cash_register_id", None)
        if warehouse_id:
            data["default_warehouse"] = Warehouse.active_objects().filter(
                pk=warehouse_id, branch=branch
            ).first()
        if location_id:
            data["default_location"] = StockLocation.active_objects().filter(
                pk=location_id, warehouse__branch=branch
            ).first()
        if register_id:
            data["default_cash_register"] = CashRegister.active_objects().filter(
                pk=register_id, branch=branch
            ).first()
        terminal = PosTerminalService.create_terminal(
            branch=branch, data=data, actor=request.user, request=request
        )
        return success_response(
            data=PosTerminalSerializer(terminal).data,
            message="POS terminal created.",
            status=status.HTTP_201_CREATED,
        )


class PosTerminalDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("organization.view")]

    def _get(self, request, pk):
        scope = _scope(request, permission="organization.view")
        return get_object_or_404(
            PosTerminalService.list_terminals(
                branch_ids=None if scope.unscoped else scope.branch_ids,
                user=request.user,
                request=request,
            ),
            pk=pk,
        )

    def get(self, request, pk):
        return success_response(data=PosTerminalSerializer(self._get(request, pk)).data)

    def put(self, request, pk):
        if not request.user.has_permission("organization.manage"):
            return error_response(message="Forbidden.", status=status.HTTP_403_FORBIDDEN)
        terminal = self._get(request, pk)
        serializer = PosTerminalSerializer(terminal, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        for key in ("branch_id", "default_warehouse_id", "default_location_id", "default_cash_register_id"):
            data.pop(key, None)
        terminal = PosTerminalService.update_terminal(
            terminal=terminal, data=data, actor=request.user, request=request
        )
        return success_response(
            data=PosTerminalSerializer(terminal).data, message="POS terminal updated."
        )
