"""Scoped query construction; no caller-supplied tenant IDs."""
from django.db.models import Count
from apps.school.models import AcademicYear, AcademicTerm, SchoolProfile, EducationLevel, SchoolClass, Section, SchoolShift, Subject, SubjectCategory, SubjectOffering, SchoolCampusAccess
from apps.settings_app.models import Branch

MODELS = {"campuses": Branch, "academic-years": AcademicYear, "terms": AcademicTerm, "levels": EducationLevel, "classes": SchoolClass, "sections": Section, "shifts": SchoolShift, "subjects": Subject, "subject-categories": SubjectCategory, "subject-offerings": SubjectOffering, "campus-access": SchoolCampusAccess}


def queryset(resource, access, *, archived=False):
    model = MODELS[resource]
    qs = access.scope(model.objects.all(), include_inactive=archived)
    qs = qs.filter(is_active=not archived) if model is Branch else qs.filter(deleted_at__isnull=not archived)
    relations = [f.name for f in model._meta.fields if f.is_relation and f.name not in ("created_by", "updated_by", "deleted_by", "tenant")]
    qs = qs.select_related(*relations)
    if model is AcademicYear:
        qs = qs.annotate(term_count=Count("terms", distinct=True))
    return qs.order_by("-created_at", "id")
