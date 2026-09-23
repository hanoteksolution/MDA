from django.db.models import Q, Count
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework import serializers
from apps.school.permissions import RESOURCES, allowed
from apps.school.policies.access import SchoolAccess
from apps.school.repositories.foundation import MODELS, queryset
from apps.school.serializers.foundation import serialize
from apps.school.services.foundation_service import FoundationService
from apps.school.models import SchoolProfile
from core.responses.api_response import success_response
from permissions.base import HasModule


class SchoolView(APIView):
    permission_classes = [IsAuthenticated, HasModule("school")]

    def access(self, request):
        return SchoolAccess(user=request.user, request=request)


def page(request, qs, serializer=serialize):
    class Params(serializers.Serializer):
        page = serializers.IntegerField(min_value=1, default=1)
        page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
    params = Params(data=request.query_params)
    params.is_valid(raise_exception=True)
    number, size = params.validated_data["page"], params.validated_data["page_size"]
    count = qs.count()
    return success_response(data={"results": [serializer(row) for row in qs[(number-1)*size:number*size]], "count": count, "page": number, "page_size": size, "total_pages": max(1, (count+size-1)//size)})


class ResourceView(SchoolView):
    def get(self, request, resource, pk=None):
        if resource not in MODELS:
            raise NotFound()
        access = self.access(request)
        access.require(RESOURCES[resource], "view")
        archived = request.query_params.get("archived") == "true"
        if pk:
            return success_response(data=serialize(FoundationService.get(resource, pk, access, archived=archived)))
        qs = queryset(resource, access, archived=archived)
        field_names = {f.attname for f in qs.model._meta.fields}
        for key in ("branch_id", "academic_year_id", "education_level_id", "school_class_id", "section_id", "subject_id", "category_id", "user_id"):
            value = request.query_params.get(key)
            if value and key in field_names:
                validator = serializers.UUIDField()
                value = validator.run_validation(value)
                qs = qs.filter(**{key: value})
        for key in ("status", "is_current", "is_active"):
            value = request.query_params.get(key)
            if value and key in field_names:
                if key != "status":
                    value = serializers.BooleanField().run_validation(value)
                qs = qs.filter(**{key:value})
        search = request.query_params.get("search", "").strip()[:100]
        if search:
            condition = Q()
            for key in ("name", "code", "description"):
                if key in field_names:
                    condition |= Q(**{key+"__icontains":search})
            if condition:
                qs = qs.filter(condition)
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering.lstrip("-") not in field_names & {"name", "code", "start_date", "sort_order", "sequence", "status", "created_at"}:
            raise ValidationError({"ordering":"Unsupported sorting field."})
        return page(request, qs.order_by(ordering, "pk"))

    def post(self, request, resource, pk=None, action=None):
        if resource not in MODELS:
            raise NotFound()
        row = FoundationService.action(resource, pk, action, user=request.user, request=request) if pk else FoundationService.save(resource, request.data, user=request.user, request=request)
        return success_response(data=serialize(row), status=200 if pk else 201)

    def patch(self, request, resource, pk):
        if resource not in MODELS:
            raise NotFound()
        return success_response(data=serialize(FoundationService.save(resource, request.data, pk=pk, user=request.user, request=request)))

    put = patch

    def delete(self, request, resource, pk):
        if resource not in MODELS:
            raise NotFound()
        row = FoundationService.action(resource, pk, "archive", user=request.user, request=request)
        return success_response(data=serialize(row), message="Record archived.")


class SchoolProfileView(SchoolView):
    def get(self, request):
        access = self.access(request)
        access.require("profile", "view")
        branch_id = serializers.UUIDField().run_validation(request.query_params.get("branch_id"))
        branch = access.campus(branch_id)
        row = SchoolProfile.objects.filter(tenant=access.tenant, branch=branch, deleted_at__isnull=True).select_related("branch", "principal_user").first()
        response = success_response(data=serialize(row) if row else None)
        response.data["defaults"] = {"branch_id": str(branch.pk), "school_name": branch.name, "currency": access.tenant.currency, "timezone": access.tenant.timezone, "language": access.tenant.language, "academic_calendar_type": "terms", "school_type": "k12", "attendance_mode": "daily", "status": "active", "term_label": "Term"}
        return response

    def put(self, request):
        return success_response(data=serialize(FoundationService.profile(request.data, user=request.user, request=request)))

    patch = put


class SchoolSummaryView(SchoolView):
    def get(self, request):
        access = self.access(request)
        if not request.user.has_permission("school.view"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        branch_id = request.query_params.get("branch_id")
        if branch_id:
            branch_id = serializers.UUIDField().run_validation(branch_id)
            access.campus(branch_id)
        from apps.school.services.summary_service import SummaryService
        return success_response(data=SummaryService.summary(user=request.user, request=request, branch_id=branch_id))


class LookupView(SchoolView):
    def get(self, request, kind):
        access = self.access(request)
        from apps.settings_app.models import Company
        from apps.authentication.models import User
        if kind == "campuses":
            # Used by selectors; this reveals only the actor's accessible campus identities.
            if not request.user.has_permission("school.view"):
                access.require("campus", "view")
            return page(request, access.campuses().order_by("name", "pk"))
        if kind == "companies":
            access.require("campus", "create")
            return page(request, Company.objects.filter(tenant=access.tenant, deleted_at__isnull=True).order_by("name", "pk"))
        if kind in ("teachers", "principals", "users"):
            if kind == "users":
                access.require("campus_access", "view")
            elif kind == "principals":
                access.require("profile", "view")
            elif not any(allowed(request.user, r, "view") for r in ("class", "section", "subject_offering")):
                access.require("class", "view")
            branch = access.campus(serializers.UUIDField().run_validation(request.query_params.get("branch_id")))
            users = User.objects.filter(tenant=access.tenant, is_active=True, deleted_at__isnull=True).order_by("username", "pk")
            search = request.query_params.get("search", "")[:100]
            if search:
                users = users.filter(Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))
            if kind != "users":
                from apps.school.policies.staff import eligible_staff
                users = users.filter(pk__in=eligible_staff(tenant=access.tenant, branch=branch, principal=kind == "principals").values("pk"))
            return page(request, users, lambda person: {"id":str(person.pk), "name":person.get_full_name() or person.username})
        raise NotFound()


class ActivityView(SchoolView):
    def get(self, request, resource, pk):
        access = self.access(request)
        if resource not in MODELS:
            raise NotFound()
        access.require(RESOURCES[resource], "view")
        row = FoundationService.get(resource, pk, access, archived=request.query_params.get("archived") == "true")
        from apps.audit.models import AuditLog
        qs = AuditLog.objects.filter(tenant=access.tenant, module="school", entity_id=row.pk).order_by("-timestamp")
        return page(request, qs, lambda log: {"id":str(log.pk), "action":log.action, "timestamp":log.timestamp.isoformat(), "before":log.old_values, "after":log.new_values})

class CapabilitiesView(SchoolView):
    def get(self, request):
        access = self.access(request)
        result = {key:[action for action in ("view","create","update","archive","restore","activate","close") if access.allows(resource, action)] for key,resource in RESOURCES.items()}
        result["profile"] = [a for a in ("view","update") if access.allows("profile",a)]
        return success_response(data=result)

class ProfileLogoView(SchoolView):
    def post(self, request):
        access = self.access(request)
        access.require("profile", "update")
        branch = access.campus(serializers.UUIDField().run_validation(request.query_params.get("branch_id")))
        uploaded = request.FILES.get("image")
        if not uploaded:
            raise ValidationError({"image":"Choose an image to upload."})
        from core.utils.media import save_company_logo
        try:
            logo_url = save_company_logo(uploaded_file=uploaded)
        except ValueError as exc:
            raise ValidationError({"image":str(exc)}) from exc
        row = FoundationService.profile({"branch_id":str(branch.pk), "logo_url":logo_url}, user=request.user, request=request)
        return success_response(data=serialize(row))
