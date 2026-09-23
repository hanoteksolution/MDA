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
    tenant_id = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    direct_permissions = serializers.SerializerMethodField()
    permission_ids = serializers.SerializerMethodField()
    role_permission_ids = serializers.SerializerMethodField()
    revoke_ids = serializers.SerializerMethodField()
    shop_slug = serializers.SerializerMethodField()
    managed_shop_group = serializers.SerializerMethodField()
    enabled_modules = serializers.SerializerMethodField()
    module_features = serializers.SerializerMethodField()
    is_super_admin = serializers.SerializerMethodField()
    business_type_code = serializers.SerializerMethodField()
    business_type_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "phone", "avatar", "role", "branch", "role_id", "branch_id",
            "tenant_id", "tenant_name",
            "is_active", "is_platform_admin", "is_superuser", "is_super_admin",
            "permissions", "direct_permissions",
            "permission_ids", "role_permission_ids", "revoke_ids",
            "shop_slug", "managed_shop_group", "enabled_modules",
            "module_features",
            "business_type_code", "business_type_name",
            "last_login", "date_joined",
        ]
        read_only_fields = ["id", "last_login", "date_joined", "is_superuser", "is_super_admin"]

    def get_permissions(self, obj):
        return obj.get_permissions()

    def get_is_super_admin(self, obj):
        return bool(getattr(obj, "is_elevated_admin", False))

    def get_tenant_id(self, obj):
        if obj.tenant_id:
            return str(obj.tenant_id)
        if obj.branch_id and getattr(obj.branch, "company", None) and obj.branch.company.tenant_id:
            return str(obj.branch.company.tenant_id)
        return None

    def get_tenant_name(self, obj):
        if obj.tenant_id:
            return obj.tenant.name
        if obj.branch_id and getattr(obj.branch, "company", None) and obj.branch.company.tenant_id:
            return obj.branch.company.tenant.name
        return None

    def get_direct_permissions(self, obj):
        perms = (
            obj.direct_permissions.filter(deleted_at__isnull=True)
            .select_related("permission")
        )
        return PermissionSerializer([up.permission for up in perms], many=True).data

    def get_permission_ids(self, obj):
        """Effective permission UUIDs (role ∪ direct − revokes) for the access matrix."""
        codes = set(obj.get_permissions())
        if not codes:
            return []
        return [
            str(p.id)
            for p in Permission.objects.filter(codename__in=codes, deleted_at__isnull=True)
        ]

    def get_role_permission_ids(self, obj):
        if not obj.role_id:
            return []
        return [
            str(rp.permission_id)
            for rp in obj.role.role_permissions.filter(deleted_at__isnull=True)
        ]

    def get_revoke_ids(self, obj):
        return [
            str(up.permission_id)
            for up in obj.revoked_permissions.filter(deleted_at__isnull=True)
        ]

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

    def get_enabled_modules(self, obj):
        from apps.platform.services.module_service import usable_module_codes
        from core.tenancy import is_platform_unscoped_actor

        if is_platform_unscoped_actor(obj):
            from apps.platform.services.module_service import MODULE_SEEDS

            return [code for code, *_ in MODULE_SEEDS]
        return sorted(usable_module_codes(user=obj))

    def get_module_features(self, obj):
        from apps.platform.services.module_feature_service import ModuleFeatureService

        return ModuleFeatureService.features_by_module(user=obj)

    def _tenant(self, obj):
        if getattr(obj, "tenant_id", None) and getattr(obj, "tenant", None):
            return obj.tenant
        if obj.branch_id and getattr(obj.branch, "company", None) and obj.branch.company.tenant_id:
            return obj.branch.company.tenant
        return None

    def get_business_type_code(self, obj):
        tenant = self._tenant(obj)
        if not tenant:
            return None
        bt = getattr(tenant, "business_type", None)
        return getattr(bt, "code", None) if bt else None

    def get_business_type_name(self, obj):
        tenant = self._tenant(obj)
        if not tenant:
            return None
        bt = getattr(tenant, "business_type", None)
        return getattr(bt, "name", None) if bt else None


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    role_id = serializers.UUIDField(required=False, allow_null=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    tenant_id = serializers.UUIDField(required=False, allow_null=True)
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = User
        fields = [
            "username", "email", "password", "first_name", "last_name",
            "phone", "role_id", "branch_id", "tenant_id", "is_active", "permission_ids",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.partial:
            self.fields["password"].required = False

    def create(self, validated_data):
        # Prefer UserService.create_user from the view — this path is a fallback.
        from apps.authentication.services.auth_service import UserService

        return UserService.create_user(data=validated_data)


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
    company_id = serializers.UUIDField(required=False)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id", "company_id", "company_name", "name", "code", "address", "phone", "email",
            "is_active", "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "company_name", "created_at", "updated_at"]


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
