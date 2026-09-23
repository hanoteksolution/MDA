"""Authorized, atomic CRUD and lifecycle for the School foundation."""
from uuid import uuid4
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from apps.audit.services import write_audit
from apps.school.models import AcademicYear, AcademicTerm, SchoolProfile, SchoolCampusAccess
from apps.settings_app.models import Branch, Company
from apps.authentication.models import User
from apps.school.policies.access import SchoolAccess
from apps.school.permissions import RESOURCES
from apps.school.repositories.foundation import MODELS, queryset
from apps.school.serializers.foundation import validate_input, serialize
from .integrity import AcademicStructureService, invalid


def save_validated(row):
    try:
        row.full_clean()
        row.save()
    except ModelValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", {"detail": exc.messages})) from exc
    except IntegrityError as exc:
        raise ValidationError({"detail": "A record with this unique configuration already exists."}) from exc


def audit(row, action, access, before=None):
    write_audit(action=action, module="school", entity=row, user=access.user, request=access.request, old_values=before or {}, new_values=serialize(row))


class FoundationService:
    @staticmethod
    def get(resource, pk, access, *, archived=False):
        row = queryset(resource, access, archived=archived).filter(pk=pk).first()
        if not row:
            raise NotFound("School record not found or not accessible.")
        return row

    @staticmethod
    @transaction.atomic
    def save(resource, data, *, pk=None, user=None, request=None):
        access = SchoolAccess(user=user, request=request)
        access.require(RESOURCES[resource], "update" if pk else "create")
        values = validate_input(resource, data, partial=bool(pk))
        # A stable tenant lock also serializes global catalog and cross-campus changes.
        type(access.tenant).objects.select_for_update().get(pk=access.tenant.pk)
        row = FoundationService.get(resource, pk, access) if pk else MODELS[resource](tenant=access.tenant, created_by=access.user)
        before = serialize(row) if pk else {}
        if pk and isinstance(row, (AcademicYear, AcademicTerm)) and row.status in ("closed", "archived"):
            invalid("status", "Closed academic periods cannot be edited.")
        for field in ("branch_id", "academic_year_id", "school_class_id", "company_id", "user_id"):
            if pk and field in values and str(values[field]) != str(getattr(row, field, None)):
                invalid(field, "This relationship cannot be changed; create a new record instead.")
        if "status" in values and (values["status"] == "archived" or getattr(row, "status", None) == "archived"):
            invalid("status", "Use the archive or restore action.")
        for key, value in values.items():
            setattr(row, key, value)
        if isinstance(row, AcademicTerm) and not row.branch_id:
            year = access.scope(AcademicYear.objects.all()).filter(pk=row.academic_year_id, deleted_at__isnull=True).first()
            if not year:
                invalid("academic_year_id", "Academic year not available.")
            row.branch_id = year.branch_id
        if isinstance(row, (AcademicYear, AcademicTerm)) and not row.code:
            row.code = f"{'AY' if isinstance(row, AcademicYear) else 'T'}-{uuid4().hex[:12]}"
        if isinstance(row, Branch):
            FoundationService.validate_campus(row, access, pk)
        elif isinstance(row, SchoolCampusAccess):
            access.campus(row.branch_id)
            if not User.objects.filter(pk=row.user_id, tenant=access.tenant, is_active=True, deleted_at__isnull=True).exists():
                invalid("user_id", "Select an active user from this tenant.")
        else:
            AcademicStructureService.validate(row, access)
        row.updated_by = access.user
        save_validated(row)
        audit(row, "update" if pk else "create", access, before)
        return row

    @staticmethod
    def validate_campus(row, access, pk):
        if not pk and not access.user.has_permission("school.campus.all"):
            raise PermissionDenied("Creating campuses requires all-campus access.")
        if not Company.objects.filter(pk=row.company_id, tenant=access.tenant, deleted_at__isnull=True).exists():
            invalid("company_id", "Choose a company belonging to this tenant.")
        if Branch.objects.filter(tenant=access.tenant, code=row.code).exclude(pk=row.pk).exists():
            invalid("code", "Campus code must be unique within the tenant.")
        if pk and not row.is_active:
            invalid("is_active", "Use the archive action to deactivate a campus.")
        if row.is_default:
            if not access.user.has_permission("school.campus.all"):
                raise PermissionDenied("Changing the main campus requires all-campus access.")
            for other in Branch.objects.filter(tenant=access.tenant, company=row.company, is_default=True).exclude(pk=row.pk):
                before = serialize(other)
                other.is_default = False
                other.updated_by = access.user
                other.save()
                audit(other, "main_campus_changed", access, before)

    @staticmethod
    @transaction.atomic
    def action(resource, pk, action, *, user=None, request=None):
        access = SchoolAccess(user=user, request=request)
        action = "activate" if action == "make-current" else action
        if action not in ("archive", "restore", "close", "activate"):
            raise NotFound("Unknown academic action.")
        access.require(RESOURCES[resource], action)
        type(access.tenant).objects.select_for_update().get(pk=access.tenant.pk)
        row = FoundationService.get(resource, pk, access, archived=action == "restore")
        before = serialize(row)
        period = isinstance(row, (AcademicYear, AcademicTerm))
        if action in ("activate", "close") and not period:
            invalid("action", "This resource does not have an academic lifecycle.")
        if action == "activate":
            if row.status not in ("planning", "active"):
                invalid("status", "Only planning or active periods can be activated.")
            AcademicStructureService.validate(row, access)
            if isinstance(row, AcademicTerm) and row.academic_year.status != "active":
                invalid("academic_year_id", "Activate the academic year before activating a term.")
            if isinstance(row, AcademicYear):
                for other in AcademicYear.objects.filter(tenant=access.tenant, branch=row.branch, is_current=True).exclude(pk=row.pk):
                    old = serialize(other)
                    other.is_current = False
                    other.updated_by = access.user
                    other.save()
                    audit(other, "current_cleared", access, old)
                row.is_current = True
            row.status = "active"
        elif action == "close":
            if row.status not in ("planning", "active"):
                invalid("status", "Only an open period can be closed.")
            AcademicStructureService.check_close(row)
            row.status = "closed"
            if isinstance(row, AcademicYear):
                row.is_current = row.admission_open = row.enrollment_open = False
        elif action == "archive":
            if not isinstance(row, SchoolCampusAccess):
                AcademicStructureService.check_archive(row)
            if isinstance(row, Branch):
                if row.is_default:
                    invalid("is_default", "Choose another main campus before archiving this campus.")
                row.is_active = False
            else:
                from django.utils import timezone
                row.deleted_at = timezone.now()
                row.deleted_by = access.user
                if hasattr(row, "status"):
                    row.status = "archived"
                if isinstance(row, AcademicYear):
                    row.is_current = row.admission_open = row.enrollment_open = False
        else:
            row.deleted_at = row.deleted_by = None
            if isinstance(row, Branch):
                row.is_active = True
            elif hasattr(row, "status"):
                row.status = "planning" if period else "inactive"
            if not isinstance(row, (Branch, SchoolCampusAccess)):
                AcademicStructureService.validate(row, access)
        row.updated_by = access.user
        save_validated(row)
        audit(row, action, access, before)
        return row

    @staticmethod
    @transaction.atomic
    def profile(data, *, user=None, request=None):
        access = SchoolAccess(user=user, request=request)
        access.require("profile", "update")
        values = validate_input("profile", data, partial=True)
        branch = access.campus(values.get("branch_id"))
        type(access.tenant).objects.select_for_update().get(pk=access.tenant.pk)
        row = SchoolProfile.objects.filter(tenant=access.tenant, branch=branch).first()
        before = serialize(row) if row else {}
        row = row or SchoolProfile(tenant=access.tenant, branch=branch, school_name=branch.name, currency=access.tenant.currency, created_by=access.user)
        for key, value in values.items():
            setattr(row, key, value)
        row.deleted_at = row.deleted_by = None
        row.updated_by = access.user
        AcademicStructureService.validate(row, access)
        save_validated(row)
        audit(row, "profile_updated", access, before)
        if before.get("principal_user_id") != (str(row.principal_user_id) if row.principal_user_id else None):
            audit(row, "principal_assigned", access, before)
        return row
