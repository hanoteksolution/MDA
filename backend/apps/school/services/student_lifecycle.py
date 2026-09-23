"""Reasoned, atomic student transitions with optimistic source-enrollment checks."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from apps.school.models import Student, StudentEnrollment, StudentTransition, StudentGuardian, StudentDocument, StudentNote, EmergencyContact
from .sis_common import get, invalid, lock, persist, reason, date_value
from .enrollment_service import placement
from .student_creation import household

OUTCOMES={'transfer':'transferred','withdraw':'withdrawn','reenroll':'reenrolled','promote':'promoted','repeat':'repeated','graduate':'graduated','suspend':'suspended','reactivate':'reactivated','alumni':'alumni','inactivate':'inactive'}


@transaction.atomic
def transition(pk,action,data,*,access):
    if action in ('promote','repeat'):invalid('action','Promotion and repetition are not available in this phase.')
    if action not in OUTCOMES:invalid('action','Unknown student transition.')
    access.require('student',action if action in ('transfer','withdraw','reenroll','promote','repeat','graduate') else 'change_status');lock(access)
    student=get(access,Student,pk)
    why=reason(data);effective=date_value(data,'effective_date',timezone.localdate())
    if effective>timezone.localdate():invalid('effective_date','Future transitions must be performed when they take effect.')
    previous=student.enrollments.filter(status='active',deleted_at__isnull=True).first()
    if action!='reenroll':
        if not previous:invalid('enrollment_id','An active enrollment is required.')
        if str(data.get('enrollment_id'))!=str(previous.pk):invalid('enrollment_id','Placement has changed. Reload the student before continuing.')
        if effective<previous.start_date:invalid('effective_date','Transition cannot precede enrollment.')
    if action=='reenroll':
        if previous or student.status not in ('withdrawn','transferred','inactive'):invalid('status','Re-enrollment requires an inactive, withdrawn or transferred student without active placement.')
        previous=student.enrollments.order_by('-start_date','-created_at').first()
        if previous and previous.end_date and effective<=previous.end_date:invalid('effective_date','Re-enrollment must follow the previous enrollment.')
    elif action=='reactivate':
        if student.status!='suspended':invalid('status','Only suspended students may be reactivated.')
    elif student.status not in ('active','suspended'):invalid('status','Student is not eligible for this transition.')
    next_row=None
    if action in ('transfer','promote','repeat','reenroll'):
        if not isinstance(data.get('placement',{}),dict):invalid('placement','Expected an object.')
        target=dict(data.get('placement',{}));target['start_date']=effective.isoformat()
        if previous:
            if action=='transfer':
                if str(target.get('academic_year_id'))!=str(previous.academic_year_id) and str(target.get('branch_id'))==str(previous.branch_id):invalid('academic_year_id','A class transfer must remain in the academic year.')
                if all(str(target.get(k) or '')==str(getattr(previous,k) or '') for k in ('branch_id','school_class_id','section_id')):invalid('placement','Choose a different campus, class or section.')
            if action in ('promote','repeat'):
                from apps.school.models import AcademicYear
                year=get(access,AcademicYear,target.get('academic_year_id'),'academic_year_id')
                if year.start_date<=previous.academic_year.start_date:invalid('academic_year_id','Choose a later academic year.')
                if action=='repeat' and str(target.get('school_class_id'))!=str(previous.school_class_id):invalid('school_class_id','Repetition retains the same class in a later year.')
                if action=='promote' and str(target.get('school_class_id'))==str(previous.school_class_id):invalid('school_class_id','Promotion requires a different class.')
            if action!='reenroll':
                if effective<=previous.start_date:invalid('effective_date','New placement must begin after the previous start date.')
                previous.status=OUTCOMES[action];previous.end_date=effective-timedelta(days=1);persist(previous,access,'enrollment_'+previous.status)
        next_row=placement(student,target,access,kind={'transfer':'transfer','promote':'promotion','repeat':'repetition','reenroll':'reenrollment'}[action],previous=previous)
        student.branch=next_row.branch;student.status='active'
        # Supporting records follow current identity access; enrollment/transition history keeps its campus.
        for model in (StudentGuardian,StudentDocument,StudentNote,EmergencyContact):
            model.objects.filter(student=student).update(branch=student.branch)
        household(student,access)
    elif action in ('withdraw','graduate','inactivate'):
        previous.status='graduated' if action=='graduate' else 'withdrawn';previous.end_date=effective;persist(previous,access,'enrollment_'+previous.status)
        student.status={'withdraw':'withdrawn','graduate':'graduated','inactivate':'inactive'}[action]
    elif action=='suspend':
        if student.status!='active':invalid('status','Only active students may be suspended.')
        student.status='suspended'
    elif action=='reactivate':student.status='active'
    elif action=='alumni':invalid('status','Use the alumni command for a graduated student.')
    persist(student,access,'student_'+OUTCOMES[action])
    history=StudentTransition(tenant=access.tenant,branch=previous.branch if previous else student.branch,student=student,from_enrollment=previous,to_enrollment=next_row,outcome=OUTCOMES[action],effective_date=effective,reason=why,destination_school=data.get('destination_school',''),certificate_status=data.get('certificate_status','not_required'),requested_by=access.user,approved_by=access.user,notes=data.get('notes',''))
    persist(history,access,'student_transition')
    return student


@transaction.atomic
def alumni(pk,data,*,access):
    access.require('student','change_status');lock(access)
    student=get(access,Student,pk)
    if student.status!='graduated':invalid('status','Only graduated students may become alumni.')
    why=reason(data);student.status='alumni';persist(student,access,'student_alumni')
    persist(StudentTransition(tenant=access.tenant,branch=student.branch,student=student,outcome='alumni',effective_date=timezone.localdate(),reason=why,requested_by=access.user,approved_by=access.user),access,'student_transition')
    return student
