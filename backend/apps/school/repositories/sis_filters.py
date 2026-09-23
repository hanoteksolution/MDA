"""Validated, reusable list/export filters without loading related histories."""
from django.db.models import Q, Exists, OuterRef
from rest_framework import serializers
from apps.school.models import Student, AdmissionApplication, AdmissionDocumentType, ApplicantDocument
from django.utils import timezone


def missing_annotation(qs):
    valid=ApplicantDocument.objects.filter(application_id=OuterRef(OuterRef('pk')),document_type_id=OuterRef('pk'),verification_status='verified',deleted_at__isnull=True,file__deleted_at__isnull=True).filter(Q(expiry_date__isnull=True)|Q(expiry_date__gte=timezone.localdate()))
    requirements=AdmissionDocumentType.objects.filter(tenant_id=OuterRef('tenant_id'),status='active',required=True,deleted_at__isnull=True).filter(Q(branch__isnull=True)|Q(branch_id=OuterRef('branch_id'))).filter(Q(school_class__isnull=True)|Q(school_class_id=OuterRef('school_class_id'))).filter(Q(education_level__isnull=True)|Q(education_level_id=OuterRef('school_class__education_level_id'))).annotate(satisfied=Exists(valid)).filter(satisfied=False)
    return qs.annotate(missing_documents=Exists(requirements))


def filters(qs, params):
    fields={f.attname for f in qs.model._meta.fields}
    for key in ('branch_id','academic_year_id','school_class_id','section_id','family_id','guardian_id','student_id','applicant_id','application_id','assigned_reviewer_id','version_id','period_id','staff_id','employee_id','classroom_id','session_id','record_id','subject_offering_id','structure_id','category_id','line_id','customer_id','receipt_id','invoice_id','batch_id'):
        if not params.get(key):continue
        value=serializers.UUIDField().run_validation(params[key])
        if qs.model is Student and key in ('academic_year_id','school_class_id','section_id'):
            from .sis import current_enrollments
            qs=qs.filter(pk__in=current_enrollments().filter(**{key:value}).values('student_id'))
        elif key in fields:qs=qs.filter(**{key:value})
    for key in ('status','verification_status','category','weekday','mode','role'):
        if params.get(key) and key in fields:qs=qs.filter(**{key:params[key]})
    for key in ('admission_date','application_date','date'):
        for suffix in ('gte','lte'):
            value=params.get(key+'__'+suffix)
            if value and key in fields:qs=qs.filter(**{key+'__'+suffix:serializers.DateField().run_validation(value)})
    if qs.model is AdmissionApplication:
        qs=missing_annotation(qs)
        if params.get('missing_documents') is not None:qs=qs.filter(missing_documents=serializers.BooleanField().run_validation(params['missing_documents']))
    search=params.get('search','').strip()[:100]
    if search:
        condition=Q()
        for key in ('name','number','first_name','middle_name','last_name','phone','email','code','admission_number','title'):
            if key in fields:condition|=Q(**{key+'__icontains':search})
        if qs.model is Student:
            condition|=Q(guardian_links__guardian__first_name__icontains=search)|Q(guardian_links__guardian__last_name__icontains=search)|Q(guardian_links__guardian__phone__icontains=search)
        if qs.model is AdmissionApplication:
            for key in ('first_name','last_name','phone'):condition|=Q(**{'applicant__'+key+'__icontains':search})
            condition|=Q(applicant__guardian_links__guardian__phone__icontains=search)|Q(applicant__guardian_links__guardian__first_name__icontains=search)
        if condition:qs=qs.filter(condition).distinct()
    ordering=params.get('ordering','-created_at')
    if ordering.lstrip('-') not in fields & {'name','number','first_name','last_name','full_name','customer_code','code','created_at','status','admission_date','application_date','date','start_date'}:raise serializers.ValidationError({'ordering':'Unsupported sort field.'})
    return qs.order_by(ordering,'pk')
