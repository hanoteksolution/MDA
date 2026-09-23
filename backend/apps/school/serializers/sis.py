"""Explicit writable contracts; lifecycle and audit fields are server-owned."""
from rest_framework import serializers
from apps.school.repositories.sis import MODELS

PERSON = 'first_name middle_name last_name preferred_name phone email address city country language'
CHILD = PERSON + ' gender date_of_birth place_of_birth nationality photo_id family_id notes'
RELATION = 'guardian_id relationship_id is_primary lives_with_student financially_responsible emergency_contact pickup_authorized receives_academic receives_finance receives_attendance display_order start_date end_date status'
PLACEMENT = 'academic_year_id term_id school_class_id section_id roll_number start_date end_date notes'
FIELDS = {
    'applicants': 'branch_id '+CHILD+' previous_school previous_grade source referral_source desired_year_id desired_class_id desired_section_id status',
    'applications': 'branch_id applicant_id academic_year_id school_class_id section_id application_date application_type previous_school previous_result transfer_student boarding_mode transport_required program_interest fee_status assigned_reviewer_id notes',
    'assessments': 'application_id assessment_type date start_time location assessor_id maximum_score score result notes',
    'interviews': 'application_id date start_time interviewer_id applicant_present guardian_present location score recommendation notes',
    'decisions': '',
    'students': CHILD+' admission_number',
    'families': 'branch_id code name primary_guardian_id secondary_guardian_id address city country phone email language communication_preference notes status',
    'guardians': 'branch_id '+PERSON+' secondary_phone national_id occupation employer portal_eligible financially_responsible emergency_contact status',
    'relationship-types': 'name code status',
    'student-guardians': 'student_id '+RELATION,
    'applicant-guardians': 'applicant_id '+RELATION,
    'enrollments': 'student_id branch_id '+PLACEMENT,
    'transitions': '',
    'document-types': 'branch_id name code required education_level_id school_class_id expiry_required allowed_types max_size_mb status',
    'applicant-documents': 'application_id document_type_id file_id document_number issue_date expiry_date notes',
    'student-documents': 'student_id document_type_id file_id document_number issue_date expiry_date notes category',
    'emergency-contacts': 'student_id name relationship phone alternative_phone priority notes',
    'notes': 'student_id title body category',
    'employees': 'branch_id user_id code first_name last_name phone email job_title employment_type hire_date termination_date status',
    'staff-profiles': 'branch_id employee_id staff_type qualification specialization max_weekly_periods status',
    'teacher-assignments': 'staff_id academic_year_id school_class_id section_id subject_offering_id role start_date end_date status notes',
    'classrooms': 'branch_id code name capacity room_type status',
    'periods': 'branch_id code name shift_id start_time end_time is_break status',
    'timetable-versions': 'branch_id academic_year_id name effective_from effective_to notes',
    'timetable-entries': 'version_id period_id weekday school_class_id section_id subject_offering_id staff_id classroom_id status',
    'attendance-sessions': '', 'attendance-records': '', 'attendance-corrections': '',
    'admission-policies': 'branch_id require_guardian require_family capacity_policy student_prefix student_padding number_scope',
}


from apps.school.learning_contracts import FIELDS as LEARNING_FIELDS
FIELDS.update(LEARNING_FIELDS)
from apps.school.fee_contracts import FIELDS as FEE_FIELDS
FIELDS.update(FEE_FIELDS)

def validate_input(resource, data, *, partial=False, extra_fields=None):
    if not isinstance(data, dict):
        raise serializers.ValidationError({'detail':'Expected a JSON object.'})
    fields = (FIELDS[resource] + (' '+extra_fields if extra_fields else '')).split()
    if set(data)-set(fields):
        raise serializers.ValidationError({f:'This field cannot be written.' for f in set(data)-set(fields)})
    model = MODELS[resource]
    attrs = {}
    for name in fields:
        field = model._meta.get_field(name)
        if field.is_relation:
            attrs[name] = serializers.UUIDField(required=not(field.null or field.blank), allow_null=field.null)
    meta = type('Meta', (), {'model':model,'fields':fields,'validators':[], 'extra_kwargs':{f:{'validators':[]} for f in fields if not f.endswith('_id')}})
    cls = type('StudentInput', (serializers.ModelSerializer,), {**attrs,'Meta':meta})
    obj = cls(data=data, partial=partial);obj.is_valid(raise_exception=True)
    return dict(obj.validated_data)


def serialize(row, *, audit=False):
    from apps.school.models import StudentNote, SchoolFile
    data = {}
    hidden = {'tenant','created_by','updated_by','deleted_by','storage_key'}
    for field in row._meta.fields:
        if field.name in hidden or (audit and (field.name in ('national_id','notes','body','document_number','previous_result') or isinstance(row, StudentNote)) and field.name not in ('id','student','branch','category','created_at','updated_at')):
            continue
        value = getattr(row,field.attname)
        if hasattr(value,'isoformat'):value=value.isoformat()
        elif value is not None and not isinstance(value,(str,int,float,bool,dict,list)):value=str(value)
        data[field.attname]=value
        # Avoid exposing parent identities from another campus through historical links.
        if field.is_relation and field.name in ('branch','academic_year','school_class','section','guardian','applicant','student','relationship','document_type','employee','staff','period','classroom','version','subject_offering','session','record','shift','scheme','exam','assessment','assignment','enrollment','publication','batch','target_class','target_section') and value:
            related=getattr(row,field.name)
            data[f'{field.name}_name']=str(related)
    data['name'] = getattr(row,'name',None) or (str(row) if hasattr(row,'first_name') else getattr(row,'number',None) or getattr(row,'title',None) or row._meta.verbose_name.title())
    from apps.school.models.learning import ResultPublication, ReportCardVersion
    if isinstance(row,ResultPublication):data['name']=f'{row.exam.name} · Version {row.version}'
    if isinstance(row,ReportCardVersion):data['name']=f'{row.data.get("name", "Student")} · {row.data.get("exam", "Exam")} · Version {row.data.get("version")}'
    from apps.school.models import StudentEnrollment
    if isinstance(row,StudentEnrollment):data['name']=f'{row.student} · {row.academic_year.name} · {row.school_class.name}'
    from apps.school.fee_contracts import MODELS as FEE_MODELS
    if type(row) in FEE_MODELS.values():
        from apps.school.services.fee_serialization import augment
        augment(row,data)
    for key in ('current_enrollment_id','current_class','current_section','current_year','primary_guardian_name','guardian_phone','student_count','missing_documents','record_count','absent_count'):
        if hasattr(row,key):
            value=getattr(row,key);data[key]=str(value) if key.endswith('_id') and value else value
    if isinstance(row,SchoolFile):data['download_url']=f'/api/v1/school/sis/files/{row.pk}/'
    return data
