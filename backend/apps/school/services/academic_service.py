"""Backward-compatible names delegating to the authorized foundation service."""
from rest_framework.exceptions import ValidationError as AcademicError
from apps.school.policies.access import SchoolAccess
from apps.school.repositories.foundation import queryset
from apps.school.serializers.foundation import serialize
from .foundation_service import FoundationService

class AcademicService:
    serialize_year = staticmethod(serialize)
    serialize_term = staticmethod(serialize)
    @staticmethod
    def create_year(*, user=None, request=None, **kwargs):
        return FoundationService.save("academic-years", kwargs["data"], user=user, request=request)

    @staticmethod
    def update_year(*, user=None, request=None, **kwargs):
        return FoundationService.save("academic-years", kwargs["data"], pk=kwargs["pk"], user=user, request=request)

    @staticmethod
    def archive_year(*, user=None, request=None, **kwargs):
        return FoundationService.action("academic-years", kwargs["pk"], "archive", user=user, request=request)

    @staticmethod
    def activate_year(*, user=None, request=None, **kwargs):
        return FoundationService.action("academic-years", kwargs["pk"], "activate", user=user, request=request)

    @staticmethod
    def create_term(*, user=None, request=None, **kwargs):
        return FoundationService.save("terms", kwargs["data"], user=user, request=request)

    @staticmethod
    def update_term(*, user=None, request=None, **kwargs):
        return FoundationService.save("terms", kwargs["data"], pk=kwargs["pk"], user=user, request=request)

    @staticmethod
    def archive_term(*, user=None, request=None, **kwargs):
        return FoundationService.action("terms", kwargs["pk"], "archive", user=user, request=request)
    @staticmethod
    def get_year(*, pk, user=None, request=None):
        access = SchoolAccess(user=user, request=request)
        access.require("academic_year", "view")
        return FoundationService.get("academic-years", pk, access)

    @staticmethod
    def list_years(*, user=None, request=None, branch_id=None, search=None, **filters):
        access = SchoolAccess(user=user, request=request)
        access.require("academic_year", "view")
        rows = queryset("academic-years", access)
        if branch_id:
            rows = rows.filter(branch_id=branch_id)
        if search:
            rows = rows.filter(name__icontains=search)
        return rows.filter(**{k:v for k,v in filters.items() if v and k in ("status", "academic_year_id")})

    @staticmethod
    def get_term(*, pk, user=None, request=None):
        access = SchoolAccess(user=user, request=request)
        access.require("term", "view")
        return FoundationService.get("terms", pk, access)

    @staticmethod
    def list_terms(*, user=None, request=None, branch_id=None, search=None, **filters):
        access = SchoolAccess(user=user, request=request)
        access.require("term", "view")
        rows = queryset("terms", access)
        if branch_id:
            rows = rows.filter(branch_id=branch_id)
        if search:
            rows = rows.filter(name__icontains=search)
        return rows.filter(**{k:v for k,v in filters.items() if v and k in ("status", "academic_year_id")})
