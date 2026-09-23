"""Admission state machine, appointment outcomes and immutable decisions."""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from apps.school.models import AdmissionApplication, AdmissionAssessment, AdmissionInterview, AdmissionDecision, SchoolClass, Section
from apps.school.serializers.sis import validate_input, serialize
from .sis_common import get, invalid, lock, persist, staff, reason, date_value
from .sis_integrity import validate
from .document_service import require_documents

REVIEWABLE = ('document_review','assessment_completed','interview_completed','under_review')
TERMINAL = ('enrolled','rejected','withdrawn','cancelled')


def schedule(row, access):
    assessment = isinstance(row,AdmissionAssessment)
    access.require('admission','assess' if assessment else 'interview')
    app = get(access,AdmissionApplication,row.application_id)
    if app.status not in REVIEWABLE:invalid('status','Application must be in review before scheduling.')
    if app.assessments.filter(status='scheduled',deleted_at__isnull=True).exists() or app.interviews.filter(status='scheduled',deleted_at__isnull=True).exists():invalid('status','Complete or cancel the existing appointment first.')
    person = row.assessor_id if assessment else row.interviewer_id
    staff(access,person,app.branch,'assess' if assessment else 'interview')
    if row.date < timezone.localdate():invalid('date','Schedule an appointment for today or later.')
    if row.score is not None:invalid('score','Record scores when completing the appointment.')
    row.branch=app.branch;validate(row,access)
    persist(row,access,'assessment_scheduled' if assessment else 'interview_scheduled')
    app.status='assessment_pending' if assessment else 'interview_pending'
    persist(app,access,app.status)
    return row


@transaction.atomic
def appointment(resource, pk, action, data, *, access):
    assessment=resource=='assessments'
    access.require('admission','assess' if assessment else 'interview');lock(access)
    row=get(access,AdmissionAssessment if assessment else AdmissionInterview,pk)
    if row.status!='scheduled':invalid('status','Only scheduled appointments can receive outcomes.')
    app=get(access,AdmissionApplication,row.application_id)
    if app.status!=('assessment_pending' if assessment else 'interview_pending'):invalid('status','Application is no longer awaiting this appointment.')
    if action=='complete':
        allowed={'score','result','notes'} if assessment else {'score','recommendation','applicant_present','guardian_present','notes'}
        if set(data)-allowed:invalid('action','Unsupported outcome field.')
        values=validate_input(resource,data,partial=True)
        for key,value in values.items():setattr(row,key,value)
        if row.date>timezone.localdate():invalid('date','A future appointment cannot be completed.')
        if assessment and row.result!='not_required' and row.score is None:invalid('score','A completed assessment requires a score.')
        row.status='completed';app.status='assessment_completed' if assessment else 'interview_completed'
    elif action in ('cancel','no-show') and (not assessment or action=='cancel'):
        reason(data);row.status='cancelled' if action=='cancel' else 'no_show';app.status='document_review'
    elif action=='reschedule' and not assessment:
        reason(data)
        row.status='rescheduled';persist(row,access,'interview_rescheduled')
        app.status='document_review';persist(app,access,'document_review')
        values=validate_input(resource,{**{k:getattr(row,k) for k in ('application_id','interviewer_id','location')},'date':data.get('date'),'start_time':data.get('start_time')})
        replacement=AdmissionInterview(tenant=access.tenant,**values)
        return schedule(replacement,access)
    else:invalid('action','Unsupported appointment action.')
    persist(row,access,'appointment_'+row.status);persist(app,access,app.status)
    return row


@transaction.atomic
def transition(pk, action, data, *, access):
    permission={'submit':'submit','review':'review','under-review':'review','withdraw':'withdraw','cancel':'withdraw'}.get(action)
    if not permission:invalid('action','Unsupported application action.')
    access.require('admission',permission);lock(access)
    app=get(access,AdmissionApplication,pk)
    before=serialize(app,audit=True)
    allowed={'submit':('draft',),'review':('submitted',),'under-review':REVIEWABLE,'withdraw':tuple(s for s in ('draft','submitted',*REVIEWABLE,'accepted','waitlisted','assessment_pending','interview_pending')),'cancel':('draft',)}
    if app.status not in allowed[action]:invalid('status','This transition is not allowed from the current status.')
    if action=='under-review' and app.status=='under_review':invalid('status','Application is already under review.')
    if action in ('withdraw','cancel'):
        reason(data)
        for model in (AdmissionAssessment,AdmissionInterview):
            for row in model.objects.filter(application=app,status='scheduled',deleted_at__isnull=True):
                row.status='cancelled';persist(row,access,'appointment_cancelled')
    if action=='submit':
        if not app.academic_year.admission_open:invalid('academic_year_id','Admissions are closed for this academic year.')
        validate(app,access);app.submitted_by=access.user
    app.status={'submit':'submitted','review':'document_review','under-review':'under_review','withdraw':'withdrawn','cancel':'cancelled'}[action]
    persist(app,access,app.status,before)
    return app


@transaction.atomic
def decide(pk,data,*,access):
    access.require('admission','decide');lock(access)
    app=get(access,AdmissionApplication,pk)
    if app.status not in ('under_review','waitlisted'):invalid('status','Decisions require an application under review or waitlisted.')
    target=data.get('decision')
    if target not in ('accepted','waitlisted','rejected'):invalid('decision','Choose accepted, waitlisted or rejected.')
    if target==app.status:invalid('decision','Application already has this outcome.')
    branch=access.campus(serializers.UUIDField().run_validation(data.get('branch_id',str(app.branch_id))))
    school_class=get(access,SchoolClass,data.get('approved_class_id',app.school_class_id),'approved_class_id')
    section_id=data.get('approved_section_id',app.section_id if school_class.pk==app.school_class_id else None)
    section=get(access,Section,section_id,'approved_section_id') if section_id else None
    if school_class.branch_id!=branch.pk or school_class.status!='active':invalid('approved_class_id','Choose an active class in the approved campus.')
    if section and (section.school_class_id!=school_class.pk or section.status!='active'):invalid('approved_section_id','Choose an active section in the approved class.')
    # Applications remain scoped to their original campus; cross-campus approval needs a new application.
    if branch.pk!=app.branch_id:invalid('branch_id','Create an application in the target campus before approving placement there.')
    expiry=date_value(data,'offer_expiry') if data.get('offer_expiry') else None
    if expiry and expiry<timezone.localdate():invalid('offer_expiry','Offer expiry cannot be in the past.')
    override=require_documents(app,access,data,school_class=school_class,branch=branch) if target=='accepted' else ''
    row=AdmissionDecision(tenant=access.tenant,branch=branch,application=app,decision=target,decided_by=access.user,reason=reason(data),conditions=data.get('conditions',''),offer_expiry=expiry,approved_class=school_class,approved_section=section,notes=data.get('notes',''),document_override_reason=override)
    persist(row,access,'admission_decision');app.status=target;persist(app,access,'admission_'+target)
    return row
