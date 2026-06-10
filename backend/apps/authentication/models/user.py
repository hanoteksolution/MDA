import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models.base import BaseModel


class Role(BaseModel):
    SYSTEM_ROLES = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin"),
        ("branch_manager", "Branch Manager"),
        ("accountant", "Accountant"),
        ("inventory_manager", "Inventory Manager"),
        ("cashier", "Cashier"),
        ("sales_staff", "Sales Staff"),
        ("read_only", "Read Only User"),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        db_table = "roles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Permission(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True, db_index=True)
    module = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permissions"
        ordering = ["module", "name"]

    def __str__(self):
        return self.codename


class RolePermission(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )

    class Meta:
        db_table = "role_permissions"
        unique_together = ["role", "permission"]

    def __str__(self):
        return f"{self.role.slug} -> {self.permission.codename}"


from apps.authentication.models.managers import UserManager


class User(AbstractUser):
    objects = UserManager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    phone = models.CharField(max_length=50, blank=True)
    avatar = models.CharField(max_length=500, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_users",
    )

    class Meta:
        db_table = "users"
        ordering = ["username"]

    def __str__(self):
        return self.username

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def get_permissions(self):
        if not self.role:
            return []
        return list(
            self.role.role_permissions.select_related("permission").values_list(
                "permission__codename", flat=True
            )
        )

    def has_permission(self, codename):
        if self.is_superuser or (self.role and self.role.slug == "super_admin"):
            return True
        return codename in self.get_permissions()

    def soft_delete(self, user=None):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.is_active = False
        self.save(update_fields=["deleted_at", "deleted_by", "is_active"])
