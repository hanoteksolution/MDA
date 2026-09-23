"""One tenant/campus boundary for HTTP, domain services and future jobs."""
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from apps.authentication.models import User
from apps.settings_app.models import Branch
from apps.school.models import SchoolCampusAccess
from apps.school.permissions import allowed
from core.tenancy import resolve_acting_tenant


class SchoolAccess:
    def __init__(self, *, user=None, request=None):
        self.user = user or getattr(request, "user", None)
        self.request = request
        self.tenant = resolve_acting_tenant(user=self.user, request=request)
        if not self.user or not self.user.is_authenticated or not self.user.is_active or self.user.deleted_at or not self.tenant:
            raise PermissionDenied("An active user and explicit school tenant are required.")
        if not self.user.is_elevated_admin and self.user.tenant_id != self.tenant.pk:
            raise PermissionDenied("School tenant does not match your account.")

        from apps.platform.services.module_service import tenant_has_module, missing_module_dependencies
        if not tenant_has_module("school", tenant=self.tenant, user=self.user, request=request) or missing_module_dependencies("school", user=self.user, request=request):
            raise PermissionDenied("The school module and its dependencies must be enabled.")

    def allows(self, resource, action):
        if not hasattr(self, "_codes"):
            self._codes = set(self.user.get_permissions())
            self._revoked = set(self.user.get_revoked_permissions())
        return allowed(self.user, resource, action, codes=self._codes, revoked=self._revoked)

    def require(self, resource, action):
        if not self.allows(resource, action):
            raise PermissionDenied("You do not have permission for this school action.")

    def campuses(self, *, include_inactive=False):
        qs = Branch.objects.filter(tenant=self.tenant, company__tenant=self.tenant, deleted_at__isnull=True)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if self.user.has_permission("school.campus.all"):
            return qs
        grants = SchoolCampusAccess.objects.filter(tenant=self.tenant, user=self.user, is_active=True, deleted_at__isnull=True).values("branch_id")
        # Explicit inactive grant revokes a user's default campus too.
        revoked = SchoolCampusAccess.objects.filter(tenant=self.tenant, user=self.user, is_active=False, deleted_at__isnull=True).values("branch_id")
        return qs.filter(Q(pk=self.user.branch_id) | Q(pk__in=grants)).exclude(pk__in=revoked)

    def campus(self, pk, *, include_inactive=False):
        row = self.campuses(include_inactive=include_inactive).filter(pk=pk).first()
        if not row:
            raise NotFound("Campus not found or not accessible.")
        return row

    def scope(self, qs, *, include_inactive=False):
        qs = qs.filter(tenant=self.tenant)
        if qs.model is Branch:
            return qs.filter(pk__in=self.campuses(include_inactive=include_inactive).values("pk"))
        if any(f.name == "branch" for f in qs.model._meta.fields):
            qs = qs.filter(branch_id__in=self.campuses(include_inactive=include_inactive).values("pk"))
        return qs

    def staff(self, pk, branch, *, principal=False):
        if not pk:
            return None
        from .staff import eligible_staff
        person = eligible_staff(tenant=self.tenant, branch=branch, principal=principal).filter(pk=pk).first()
        if not person:
            raise ValidationError({"principal_user_id" if principal else "teacher_id": "Select an active, eligible school staff member assigned to this campus."})
        return person
