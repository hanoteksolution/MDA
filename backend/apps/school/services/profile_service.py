from rest_framework.exceptions import ValidationError as ProfileError
from apps.school.models import SchoolProfile
from apps.school.policies.access import SchoolAccess
from apps.school.serializers.foundation import serialize
from .foundation_service import FoundationService

class ProfileService:
    serialize = staticmethod(serialize)
    upsert = staticmethod(FoundationService.profile)

    @staticmethod
    def get_for_branch(*, branch_id, user=None, request=None):
        access = SchoolAccess(user=user, request=request)
        access.require("profile", "view")
        branch = access.campus(branch_id)
        return SchoolProfile.objects.filter(tenant=access.tenant, branch=branch, deleted_at__isnull=True).select_related("branch", "principal_user").first()
