from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.authentication.models import Permission, Role, RolePermission, User
from apps.settings_app.models import Branch, Company, Setting
from apps.audit.models import AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "branch", "is_active"]
    list_filter = ["is_active", "role", "branch"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("MDA", {"fields": ("role", "branch", "phone", "avatar")}),
    )


admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(Company)
admin.site.register(Branch)
admin.site.register(Setting)
admin.site.register(AuditLog)
