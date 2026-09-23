"""Real, permission- and campus-scoped foundation metrics."""
from apps.school.policies.access import SchoolAccess
from apps.school.permissions import RESOURCES, allowed
from apps.school.repositories.foundation import queryset
from apps.school.serializers.foundation import serialize
from rest_framework.exceptions import PermissionDenied

class SummaryService:
    @staticmethod
    def summary(*, user=None, request=None, branch_id=None):
        access = SchoolAccess(user=user, request=request)
        user = access.user
        if not user.has_permission("school.view"):
            raise PermissionDenied()
        if branch_id:
            access.campus(branch_id)
        result = {}
        for resource in ("academic-years", "terms", "campuses", "classes", "sections", "subjects", "subject-offerings"):
            if not access.allows(RESOURCES[resource], "view"):
                continue
            qs = queryset(resource, access)
            if branch_id and resource == "campuses":
                qs = qs.filter(pk=branch_id)
            elif branch_id and any(f.name == "branch" for f in qs.model._meta.fields):
                qs = qs.filter(branch_id=branch_id)
            result[resource.replace("-", "_")] = qs.count()
            if resource == "academic-years":
                result["current_years"] = [serialize(r) for r in qs.filter(is_current=True)[:100]]
            if resource == "terms":
                result["active_terms"] = qs.filter(status="active").count()
            if resource == "subject-offerings":
                result["teacher_assignments"] = qs.filter(status="active", teacher__is_active=True, teacher__deleted_at__isnull=True).count()
        return result

