"""Atomic direct creation and accepted-application conversion."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.school.models import Student, ApplicantGuardian, StudentGuardian, AdmissionApplication, StudentDocument, AcademicYear
from apps.school.serializers.sis import validate_input, CHILD, RELATION
from .sis_common import get, invalid, lock, persist, number, policy, reason, event
from .sis_integrity import validate
from .sis_crud import StudentCrudService
from .enrollment_service import placement
from .document_service import require_documents


def household(student, access):
    config=policy(access,student.branch)
    if config.require_family and not student.family_id:invalid('family_id','School policy requires a family.')
    today=timezone.localdate()
    links=student.guardian_links.filter(status='active',deleted_at__isnull=True,guardian__status='active',guardian__deleted_at__isnull=True).filter(Q(start_date__isnull=True)|Q(start_date__lte=today)).filter(Q(end_date__isnull=True)|Q(end_date__gte=today))
    if config.require_guardian and not links.exists():invalid('guardians','School policy requires an active guardian relationship.')


def duplicate_candidates(data, access):
    qs=access.scope(Student.objects.filter(deleted_at__isnull=True))
    indicators=Q(pk__isnull=True)
    if data.get('first_name') and data.get('last_name') and data.get('date_of_birth'):
        indicators |= Q(first_name__iexact=data['first_name'],last_name__iexact=data['last_name'],date_of_birth=data['date_of_birth'])
    if data.get('admission_number'):indicators |= Q(admission_number=data['admission_number'])
    if data.get('guardian_phone'):indicators |= Q(guardian_links__guardian__phone=data['guardian_phone'],guardian_links__status='active',guardian_links__deleted_at__isnull=True)
    return qs.filter(indicators).distinct()[:20]


@transaction.atomic
def direct(data,*,access):
    access.require('student','create_direct');access.require('student','create');access.require('enrollment','create');lock(access)
    bypass_reason=reason(data)
    identity_data=data.get('student',{})
    if not isinstance(identity_data,dict):invalid('student','Expected an object.')
    if not isinstance(data.get('placement',{}),dict):invalid('placement','Expected an object.')
    for field in ('guardians','emergency_contacts','documents'):
        values=data.get(field,[])
        if not isinstance(values,list) or any(not isinstance(value,dict) for value in values):
            invalid(field,'Expected a list of objects.')
    identity=validate_input('students',{'admission_date': timezone.localdate(), **identity_data},extra_fields='branch_id admission_date')
    branch=access.campus(identity['branch_id'])
    year=get(access,AcademicYear,data.get('placement',{}).get('academic_year_id'),'academic_year_id')
    student=Student(tenant=access.tenant,number=number(access,'student',branch,year),**identity)
    if student.admission_date>timezone.localdate():invalid('admission_date','Admission date cannot be in the future.')
    validate(student,access);persist(student,access,'student_created')
    for link in data.get('guardians',[]):StudentCrudService.save('student-guardians',{**link,'student_id':str(student.pk)},access=access)
    household(student,access)
    if str(data.get('placement',{}).get('branch_id'))!=str(branch.pk):invalid('branch_id','Student and enrollment campus must match.')
    placement(student,data.get('placement',{}),access)
    for contact in data.get('emergency_contacts',[]):StudentCrudService.save('emergency-contacts',{**contact,'student_id':str(student.pk)},access=access)
    for document in data.get('documents',[]):StudentCrudService.save('student-documents',{**document,'student_id':str(student.pk)},access=access)
    event(student,access,'admissions_bypassed',reason=bypass_reason)
    return student


@transaction.atomic
def convert(pk,data,*,access):
    access.require('admission','enroll');access.require('student','create');access.require('enrollment','create');lock(access)
    app=get(access,AdmissionApplication,pk)
    if app.status == 'enrolled' and app.student_id:
        return get(access, Student, app.student_id)
    if app.status!='accepted' or app.student_id:invalid('status','Only an accepted, unconverted application may enroll.')
    if Student.objects.filter(applicant=app.applicant).exists():invalid('applicant_id','This applicant already has a student identity; use re-enrollment.')
    decision=app.decisions.filter(decision='accepted',deleted_at__isnull=True).order_by('-created_at').first()
    if not decision:invalid('decision','An acceptance decision is required.')
    if decision.offer_expiry and decision.offer_expiry<timezone.localdate():invalid('offer_expiry','The acceptance offer has expired.')
    branch=access.campus(decision.branch_id)
    require_documents(app,access,data,school_class=decision.approved_class,branch=branch)
    supplied=data.get('placement',{})
    if not isinstance(supplied,dict):invalid('placement','Expected an object.')
    fixed={'branch_id':str(branch.pk),'academic_year_id':str(app.academic_year_id),'school_class_id':str(decision.approved_class_id),'section_id':str(decision.approved_section_id) if decision.approved_section_id else None}
    for key,value in fixed.items():
        if key in supplied and str(supplied[key])!=str(value):invalid(key,'Enrollment must use the accepted placement.')
    identity={key:getattr(app.applicant,key) for key in CHILD.split()}
    student=Student(tenant=access.tenant,branch=branch,number=number(access,'student',branch,app.academic_year),admission_date=timezone.localdate(),admission_number=app.number,applicant=app.applicant,original_application=app,**identity)
    validate(student,access);persist(student,access,'student_created')
    for source in app.applicant.guardian_links.filter(status='active',deleted_at__isnull=True):
        values={key:getattr(source,key) for key in RELATION.split()}
        row=StudentGuardian(tenant=access.tenant,branch=branch,student=student,**values)
        validate(row,access);persist(row,access,'guardian_linked')
    household(student,access)
    placement(student,{**supplied,**fixed},access,kind='admission')
    for source in app.documents.filter(verification_status='verified',deleted_at__isnull=True).filter(Q(expiry_date__isnull=True)|Q(expiry_date__gte=timezone.localdate())):
        values={key:getattr(source,key) for key in ('document_type_id','file_id','document_number','issue_date','expiry_date','verification_status','verified_by_id','verified_at','notes')}
        row=StudentDocument(tenant=access.tenant,branch=branch,student=student,source_document=source,category='admission',**values)
        persist(row,access,'admission_document_copied')
    app.student=student;app.status='enrolled';persist(app,access,'admission_enrolled')
    return student
