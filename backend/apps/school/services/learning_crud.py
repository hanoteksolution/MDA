"""Draft academic CRUD with immutable publication boundaries."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.school.models import AcademicYear, AcademicTerm, SubjectOffering, SchoolClass, Section, Classroom, SchoolStaffProfile, StudentEnrollment
from apps.school.models.learning import *
from apps.school.learning_contracts import MODELS, RESOURCES, READ_ONLY
from apps.school.serializers.sis import validate_input
from .sis_common import get, invalid, lock, persist
from .learning_common import authorize, scoped_relation


def draft(exam):
    if exam.status!='draft':invalid('status','Reopen this exam before changing its draft.')


def bump(exam,access):
    exam.revision+=1;persist(exam,access,'exam_draft_changed')


class LearningCrud:
    @staticmethod
    @transaction.atomic
    def save(resource,data,*,access,pk=None):
        access.require(RESOURCES[resource],'update' if pk else 'create');lock(access)
        if resource in READ_ONLY:invalid('action','Use the dedicated workflow.')
        row=get(access,MODELS[resource],pk) if pk else MODELS[resource](tenant=access.tenant)
        values=validate_input(resource,data,partial=bool(pk))
        for key,value in values.items():
            if pk and key.endswith('_id') and str(value)!=str(getattr(row,key)):invalid(key,'Relationships are immutable; create a new draft record.')
            setattr(row,key,value)
        exam=None
        if isinstance(row,GradeScheme):
            row.branch=access.campus(row.branch_id)
            if pk and Exam.objects.filter(scheme=row).exclude(status='draft').exists():invalid('scheme_id','This scheme is used by a locked exam.')
        elif isinstance(row,GradeBand):
            row.scheme=get(access,GradeScheme,row.scheme_id);row.branch=row.scheme.branch
            if Exam.objects.filter(scheme=row.scheme).exclude(status='draft').exists() or ResultPublication.objects.filter(exam__scheme=row.scheme).exists():invalid('scheme_id','Published or locked schemes are immutable; create a new scheme.')
            if GradeBand.objects.filter(scheme=row.scheme,deleted_at__isnull=True,minimum__lt=row.maximum,maximum__gt=row.minimum).exclude(pk=row.pk).exists():invalid('minimum','Grade bands overlap.')
        elif isinstance(row,LearningAssignment):
            if pk and row.status!='draft':invalid('status','Published assignments are immutable.')
            row.subject_offering=get(access,SubjectOffering,row.subject_offering_id);row.branch=row.subject_offering.branch
            authorize(access,row.subject_offering,row.assigned_date)
            year=row.subject_offering.academic_year
            if row.subject_offering.status!='active' or year.status!='active' or not year.start_date<=row.assigned_date<=row.due_date<=year.end_date:invalid('due_date','Assignment dates must be within an active offering year.')
        elif isinstance(row,LearningSubmission):
            row.assignment=get(access,LearningAssignment,row.assignment_id);row.branch=row.assignment.branch
            authorize(access,row.assignment.subject_offering,row.assignment.assigned_date)
            if row.assignment.status!='published' or row.status=='graded':invalid('status','Only ungraded submissions to published assignments can be edited.')
            e=get(access,StudentEnrollment,row.enrollment_id);o=row.assignment.subject_offering
            if e.branch_id!=row.branch_id or e.academic_year_id!=o.academic_year_id or e.school_class_id!=o.school_class_id or (o.section_id and e.section_id!=o.section_id) or e.start_date>row.assignment.assigned_date or (e.end_date and e.end_date<row.assignment.assigned_date) or e.status in ('pending','cancelled'):invalid('enrollment_id','Student was not enrolled for this assignment.')
            if timezone.localdate()<row.assignment.assigned_date:invalid('assignment_id','The assignment has not started.')
            if not pk:row.submitted_at=timezone.now()
        elif isinstance(row,Exam):
            draft(row);row.branch=access.campus(row.branch_id)
            for field,model in [('academic_year',AcademicYear),('school_class',SchoolClass),('scheme',GradeScheme)]:setattr(row,field,scoped_relation(access,model,getattr(row,field+'_id'),row.branch,field+'_id'))
            if row.academic_year.status!='active' or row.school_class.status!='active':invalid('academic_year_id','An active calendar and class are required.')
            if row.term_id:
                row.term=scoped_relation(access,AcademicTerm,row.term_id,row.branch,'term_id')
                if row.term.academic_year_id!=row.academic_year_id or row.term.status!='active':invalid('term_id','Choose an active term in this year.')
            if row.section_id:
                row.section=scoped_relation(access,Section,row.section_id,row.branch,'section_id')
                if row.section.school_class_id!=row.school_class_id or row.section.status!='active':invalid('section_id','Choose an active section of this class.')
            row.revision+=1
        elif isinstance(row,Assessment):
            exam=get(access,Exam,row.exam_id);draft(exam);row.branch=exam.branch
            o=scoped_relation(access,SubjectOffering,row.subject_offering_id,row.branch,'subject_offering_id');row.subject_offering=o
            if o.status!='active' or o.academic_year_id!=exam.academic_year_id or o.school_class_id!=exam.school_class_id or (o.section_id and o.section_id!=exam.section_id) or (o.term_id and o.term_id!=exam.term_id):invalid('subject_offering_id','Offering must match the exam year, term, class and section.')
            start,end=(exam.term.start_date,exam.term.end_date) if exam.term_id else (exam.academic_year.start_date,exam.academic_year.end_date)
            if not start<=row.date<=end:invalid('date','Assessment date is outside the calendar.')
            if pk and row.marks.exists():invalid('assessment','An assessment with marks is immutable; reopen marks or create another assessment.')
            if row.assignment_id:
                assignment=get(access,LearningAssignment,row.assignment_id)
                if assignment.subject_offering_id!=o.pk:invalid('assignment_id','Assignment does not match the assessed offering.')
        elif isinstance(row,ExamSchedule):
            row.assessment=get(access,Assessment,row.assessment_id);exam=row.assessment.exam;draft(exam);row.branch=exam.branch
            row.classroom=scoped_relation(access,Classroom,row.classroom_id,row.branch,'classroom_id')
            row.staff=scoped_relation(access,SchoolStaffProfile,row.staff_id,row.branch,'staff_id')
            if row.classroom.status!='active' or row.staff.status!='active' or row.staff.employee.status!='active' or row.staff.employee.deleted_at:invalid('staff_id','Room and staff must be active.')
            peers=ExamSchedule.objects.filter(tenant=access.tenant,assessment__date=row.assessment.date,deleted_at__isnull=True,start_time__lt=row.end_time,end_time__gt=row.start_time).exclude(pk=row.pk).select_related('assessment__exam','staff')
            for peer in peers:
                same_class=peer.assessment.exam.school_class_id==exam.school_class_id and (not peer.assessment.exam.section_id or not exam.section_id or peer.assessment.exam.section_id==exam.section_id)
                if peer.classroom_id==row.classroom_id or peer.staff.employee_id==row.staff.employee_id or same_class:invalid('start_time','Exam schedule conflicts with a room, staff member or class.')
        result=persist(row,access,'learning_updated' if pk else 'learning_created')
        if exam:bump(exam,access)
        return result
