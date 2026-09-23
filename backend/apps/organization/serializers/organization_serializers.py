from __future__ import annotations

from rest_framework import serializers

from apps.organization.models import (
    BranchAccessProfile,
    CashRegister,
    PosTerminal,
    StockLocation,
    UserBranchAccess,
)


class BranchAccessProfileSerializer(serializers.ModelSerializer):
    permission_codenames = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    class Meta:
        model = BranchAccessProfile
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_manager",
            "grants_all_permissions",
            "is_system",
            "is_active",
            "permission_codenames",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["permission_codenames"] = sorted(instance.permission_codenames())
        return data


class UserBranchAccessSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField()
    branch_id = serializers.UUIDField()
    access_profile_id = serializers.UUIDField(required=False, allow_null=True)
    username = serializers.CharField(source="user.username", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    branch_code = serializers.CharField(source="branch.code", read_only=True)
    profile_name = serializers.CharField(source="access_profile.name", read_only=True, default=None)
    is_effective = serializers.SerializerMethodField()

    class Meta:
        model = UserBranchAccess
        fields = [
            "id",
            "user_id",
            "username",
            "branch_id",
            "branch_name",
            "branch_code",
            "access_profile_id",
            "profile_name",
            "is_default",
            "status",
            "starts_on",
            "ends_on",
            "notes",
            "is_effective",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "username", "branch_name", "branch_code", "profile_name", "created_at", "updated_at"]

    def get_is_effective(self, obj) -> bool:
        return obj.is_effective()


class StockLocationSerializer(serializers.ModelSerializer):
    warehouse_id = serializers.UUIDField()
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    branch_id = serializers.UUIDField(source="warehouse.branch_id", read_only=True)
    branch_name = serializers.CharField(source="warehouse.branch.name", read_only=True)

    class Meta:
        model = StockLocation
        fields = [
            "id",
            "warehouse_id",
            "warehouse_name",
            "warehouse_code",
            "branch_id",
            "branch_name",
            "parent_id",
            "code",
            "name",
            "location_type",
            "status",
            "is_sellable",
            "is_default",
            "sort_order",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "warehouse_name",
            "warehouse_code",
            "branch_id",
            "branch_name",
            "created_at",
            "updated_at",
        ]


class CashRegisterSerializer(serializers.ModelSerializer):
    branch_id = serializers.UUIDField()
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    cash_account_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = CashRegister
        fields = [
            "id",
            "branch_id",
            "branch_name",
            "code",
            "name",
            "cash_account_id",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "branch_name", "created_at", "updated_at"]


class PosTerminalSerializer(serializers.ModelSerializer):
    branch_id = serializers.UUIDField()
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    default_warehouse_id = serializers.UUIDField(required=False, allow_null=True)
    default_location_id = serializers.UUIDField(required=False, allow_null=True)
    default_cash_register_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = PosTerminal
        fields = [
            "id",
            "branch_id",
            "branch_name",
            "code",
            "name",
            "default_warehouse_id",
            "default_location_id",
            "default_cash_register_id",
            "status",
            "device_identifier",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "branch_name", "created_at", "updated_at"]


class BranchContextSerializer(serializers.Serializer):
    """What the frontend branch switcher needs: the branches this user may act in."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    branch_type = serializers.CharField()
    status = serializers.CharField()
    is_default = serializers.BooleanField()
    is_manager = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())
