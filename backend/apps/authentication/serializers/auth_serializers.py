from rest_framework import serializers

from apps.authentication.models import Permission, Role, User
from apps.settings_app.models import Branch, Company, Setting


class RoleMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "slug"]


class BranchMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "code"]


class UserSerializer(serializers.ModelSerializer):
    role = RoleMinimalSerializer(read_only=True)
    branch = BranchMinimalSerializer(read_only=True)
    role_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    branch_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    permissions = serializers.SerializerMethodField()
    shop_slug = serializers.SerializerMethodField()
    managed_shop_group = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "phone", "avatar", "role", "branch", "role_id", "branch_id",
            "is_active", "is_platform_admin", "permissions", "shop_slug",
            "managed_shop_group", "last_login", "date_joined",
        ]
        read_only_fields = ["id", "last_login", "date_joined"]

    def get_permissions(self, obj):
        return obj.get_permissions()

    def get_shop_slug(self, obj):
        if obj.tenant_id:
            return obj.tenant.slug
        if obj.branch_id and getattr(obj.branch, "company", None) and obj.branch.company.tenant_id:
            return obj.branch.company.tenant.slug
        return None

    def get_managed_shop_group(self, obj):
        if not obj.managed_shop_group_id:
            return None
        g = obj.managed_shop_group
        return {"id": str(g.id), "name": g.name, "slug": g.slug}


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    role_id = serializers.UUIDField(required=False, allow_null=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "username", "email", "password", "first_name", "last_name",
            "phone", "role_id", "branch_id", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.partial:
            self.fields["password"].required = False

    def create(self, validated_data):
        role_id = validated_data.pop("role_id", None)
        branch_id = validated_data.pop("branch_id", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        if role_id:
            user.role_id = role_id
        if branch_id:
            user.branch_id = branch_id
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "module", "description"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id", "name", "slug", "description", "is_system",
            "permissions", "permission_ids", "permission_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]

    def get_permission_count(self, obj):
        return obj.role_permissions.count()

    def get_permissions(self, obj):
        perms = obj.role_permissions.select_related("permission")
        return PermissionSerializer([rp.permission for rp in perms], many=True).data


class BranchSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Branch
        fields = [
            "id", "company_id", "name", "code", "address", "phone", "email",
            "is_active", "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id", "name", "legal_name", "tax_id", "email",
            "phone", "address", "logo",
        ]
        read_only_fields = ["id"]


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ["id", "key", "value", "category", "branch", "company"]
        read_only_fields = ["id"]
