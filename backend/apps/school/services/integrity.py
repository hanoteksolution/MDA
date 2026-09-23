"""Academic invariants shared by every write entry point."""
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from apps.school.models import AcademicYear, AcademicTerm, SchoolProfile, SchoolClass, Section, SubjectOffering


def invalid(field, message):
    raise ValidationError({field: message})


class AcademicStructureService:
    @staticmethod
    def validate(row, access):
        if getattr(row, "branch_id", None):
            access.campus(row.branch_id)
        # Validate every related academic record, including tenant-global catalogs.
        for field in row._meta.fields:
            if not field.is_relation or field.name in ("tenant", "created_by", "updated_by", "deleted_by", "branch", "teacher", "principal_user", "user", "company"):
                continue
            pk = getattr(row, field.attname)
            if not pk:
                continue
            related = access.scope(field.related_model.objects.all()).filter(pk=pk, deleted_at__isnull=True).first()
            if not related or getattr(related, "status", "active") in ("archived", "inactive", "closed"):
                invalid(field.attname, "Choose an available record in the permitted school scope.")
            if getattr(related, "branch_id", None) and related.branch_id != getattr(row, "branch_id", None):
                invalid(field.attname, "Related record belongs to a different campus.")
        if getattr(row, "teacher_id", None):
            access.staff(row.teacher_id, row.branch)
        if isinstance(row, SchoolProfile):
            if row.principal_user_id:
                access.staff(row.principal_user_id, row.branch, principal=True)
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
            try:
                ZoneInfo(row.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                invalid("timezone", "Choose a valid timezone.")
            if row.currency != access.tenant.currency:
                invalid("currency", "School currency must match the tenant accounting currency.")
            if not row.allow_term_overlap:
                terms = AcademicTerm.objects.filter(tenant=access.tenant, branch=row.branch, deleted_at__isnull=True).exclude(status="archived")
                for term in terms:
                    if terms.filter(academic_year=term.academic_year, start_date__lte=term.end_date, end_date__gte=term.start_date).exclude(pk=term.pk).exists():
                        invalid("allow_term_overlap", "Existing terms overlap. Resolve them before disabling overlap.")
        if isinstance(row, (AcademicYear, AcademicTerm)):
            if row.start_date >= row.end_date:
                invalid("end_date", "End date must be after start date.")
        if isinstance(row, AcademicYear):
            if row.pk and AcademicTerm.objects.filter(academic_year=row).filter(Q(start_date__lt=row.start_date) | Q(end_date__gt=row.end_date)).exists():
                invalid("start_date", "Existing terms must remain inside the academic year.")
            from apps.school.models import StudentEnrollment
            if StudentEnrollment.objects.filter(academic_year=row).filter(Q(start_date__lt=row.start_date) | Q(start_date__gt=row.end_date) | Q(end_date__gt=row.end_date)).exists():
                invalid("start_date", "Existing enrollment history must remain inside the academic year.")
        if isinstance(row, AcademicTerm):
            year = row.academic_year
            if row.start_date < year.start_date or row.end_date > year.end_date:
                invalid("start_date", "Term dates must be inside the academic year.")
            if bool(row.exam_start) != bool(row.exam_end):
                invalid("exam_start", "Provide both exam dates or neither.")
            if row.exam_start and not (row.start_date <= row.exam_start <= row.exam_end <= row.end_date):
                invalid("exam_end", "Exam dates must be ordered and within the term.")
            if row.result_publish_date and row.result_publish_date < (row.exam_end or row.end_date):
                invalid("result_publish_date", "Publication must be on or after the exam end (or term end).")
            profile = SchoolProfile.objects.filter(tenant=access.tenant, branch=row.branch, deleted_at__isnull=True).first()
            if not profile or not profile.allow_term_overlap:
                if AcademicTerm.objects.filter(academic_year=year, deleted_at__isnull=True, start_date__lte=row.end_date, end_date__gte=row.start_date).exclude(pk=row.pk).exclude(status="archived").exists():
                    invalid("start_date", "Terms may not overlap under the campus calendar policy.")
        if isinstance(row, Section) and row.capacity > row.school_class.capacity:
            invalid("capacity", "Section capacity cannot exceed class capacity.")
        if isinstance(row, SchoolClass) and row.sections.filter(deleted_at__isnull=True, capacity__gt=row.capacity).exists():
            invalid("capacity", "Existing section capacity exceeds the proposed class capacity.")
        if isinstance(row, SubjectOffering):
            if row.term_id and row.term.academic_year_id != row.academic_year_id:
                invalid("term_id", "Term does not belong to this academic year.")
            if row.section_id and row.section.school_class_id != row.school_class_id:
                invalid("section_id", "Section does not belong to this class.")

    @staticmethod
    def check_archive(row):
        # Protect live dependent structure; archived historical rows remain linked.
        for rel in row._meta.related_objects:
            if rel.related_model._meta.app_label != "school":
                continue
            qs = rel.related_model.objects.filter(**{rel.field.name: row}, deleted_at__isnull=True)
            if any(f.name == "status" for f in rel.related_model._meta.fields):
                qs = qs.exclude(status="archived")
            if qs.exists():
                invalid("status", f"Archive or reassign related {rel.related_model._meta.verbose_name_plural} first.")

    @staticmethod
    def check_close(row):
        """Do not close a calendar while placements still depend on it."""
        from apps.school.models import StudentEnrollment
        field = 'academic_year' if isinstance(row, AcademicYear) else 'term'
        if StudentEnrollment.objects.filter(**{field: row}, deleted_at__isnull=True, status__in=['pending', 'active']).exists():
            invalid("status", "Complete or withdraw active enrollments before closing this period.")
        if isinstance(row, AcademicYear) and row.terms.filter(deleted_at__isnull=True, status__in=["planning", "active"]).exists():
            invalid("status", "Close or archive this year's terms first.")
