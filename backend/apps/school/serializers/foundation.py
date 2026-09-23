"""Explicit input contracts; shared domain service owns relational integrity."""
from rest_framework import serializers
from apps.school.repositories.foundation import MODELS
from apps.school.models import SchoolProfile

FIELDS = {
    "campuses": "name code company_id address phone email is_active is_default",
    "academic-years": "name code branch_id start_date end_date description admission_open enrollment_open",
    "terms": "name code branch_id academic_year_id start_date end_date exam_start exam_end result_publish_date sort_order",
    "levels": "name code sequence description status",
    "classes": "name code branch_id education_level_id sequence capacity room teacher_id description status",
    "sections": "name code branch_id school_class_id capacity room teacher_id shift_id description status",
    "shifts": "name code branch_id start_time end_time description status",
    "subject-categories": "name code description status",
    "subjects": "name code short_name category_id description maximum_marks pass_mark weight mandatory teaching_mode status",
    "subject-offerings": "name code branch_id academic_year_id term_id school_class_id section_id subject_id teacher_id maximum_marks pass_mark weight weekly_periods mandatory description status",
    "campus-access": "user_id branch_id is_active",
    "profile": "branch_id school_name display_name legal_name school_code registration_number authority_reference tax_number logo_url phone email website address country city timezone currency language date_format academic_calendar_type school_type principal_name principal_user_id contact_phone contact_email settings grading_scheme attendance_mode status allow_term_overlap term_label",
}


def validate_input(resource, data, *, partial=False):
    model = SchoolProfile if resource == "profile" else MODELS[resource]
    fields = FIELDS[resource].split()
    if not isinstance(data, dict):
        raise serializers.ValidationError({"detail": "Expected a JSON object."})
    unknown = set(data) - set(fields)
    # Keep legacy planning/default fields accepted, but never lifecycle mutations.
    if resource in ("academic-years", "terms"):
        unknown -= {"status", "is_current"}
        if data.get("status", "planning") != "planning" or data.get("is_current", False) not in (False, None):
            raise serializers.ValidationError({"status": "Use the dedicated activate, close, archive or restore action."})
    if unknown:
        raise serializers.ValidationError({key: "This field cannot be written." for key in unknown})
    attrs = {}
    for name in fields:
        if name.endswith("_id"):
            f = model._meta.get_field(name[:-3])
            attrs[name] = serializers.UUIDField(required=not (f.null or f.blank or (resource == "terms" and name == "branch_id")), allow_null=f.null)
    Meta = type("Meta", (), {"model": model, "fields": fields, "validators": [], "extra_kwargs": {f: {"validators": []} for f in fields if not f.endswith("_id")}})
    cls = type("FoundationInput", (serializers.ModelSerializer,), {**attrs, "Meta": Meta})
    serializer = cls(data={k:v for k,v in data.items() if k in fields}, partial=partial)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)


def serialize(row):
    data = {}
    for f in row._meta.fields:
        if f.name in ("tenant", "created_by", "updated_by", "deleted_by"):
            continue
        value = getattr(row, f.attname)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif value is not None and not isinstance(value, (str, int, float, bool, dict, list)):
            value = str(value)
        data[f.attname] = value
        if f.is_relation and value:
            related = getattr(row, f.name)
            data[f"{f.name}_name"] = str(related)
            if f.name in ("teacher", "principal_user"):
                data[f"{f.name}_active"] = bool(related.is_active and not related.deleted_at)
    if hasattr(row, "term_count"):
        data["term_count"] = row.term_count
    return data
