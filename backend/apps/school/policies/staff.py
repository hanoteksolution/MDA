"""SQL-scoped staff selectors avoid leaking unrelated campus identities."""
from django.db.models import Q
from apps.authentication.models import User, RolePermission, UserPermission, UserPermissionRevoke, Role
from apps.school.models import SchoolCampusAccess


def permission_users(code):
    elevated = Q(is_superuser=True) | Q(is_platform_admin=True) | Q(role__slug__in=Role.ELEVATED_SLUGS)
    roles = RolePermission.objects.filter(deleted_at__isnull=True, permission__codename=code).values("role_id")
    grants = UserPermission.objects.filter(deleted_at__isnull=True, permission__codename=code).values("user_id")
    revokes = UserPermissionRevoke.objects.filter(deleted_at__isnull=True, permission__codename=code).values("user_id")
    return User.objects.filter(elevated | ((Q(role_id__in=roles) | Q(pk__in=grants)) & ~Q(pk__in=revokes))).values("pk")


def eligible_staff(*, tenant, branch, principal=False):
    code = "school.leadership.assignable" if principal else "school.teacher.assignable"
    extra = SchoolCampusAccess.objects.filter(tenant=tenant, branch=branch, deleted_at__isnull=True, is_active=True).values("user_id")
    revoked = SchoolCampusAccess.objects.filter(tenant=tenant, branch=branch, deleted_at__isnull=True, is_active=False).values("user_id")
    all_campuses = permission_users("school.campus.all")
    campus = Q(pk__in=all_campuses) | ((Q(branch=branch) | Q(pk__in=extra)) & ~Q(pk__in=revoked))
    return User.objects.filter(tenant=tenant, is_active=True, deleted_at__isnull=True, pk__in=permission_users(code)).filter(campus)
