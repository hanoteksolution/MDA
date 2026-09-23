"""Revision-checked mark entry and moderation commands."""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from apps.school.models.learning import Assessment, Exam, Mark, LearningAssignment, LearningSubmission
from .sis_common import get, invalid, lock, persist, reason, event
from .learning_common import authorize, roster
from .learning_crud import draft, bump


def revision(exam,data):
    expected=serializers.IntegerField(min_value=0).run_validation(data.get('expected_revision'))
    if expected!=exam.revision:invalid('expected_revision','The draft changed. Reload before saving.')


def roster_view(pk,access):
    access.require('mark','view');assessment=get(access,Assessment,pk)
    authorize(access,assessment.subject_offering,assessment.date)
    marks={m.enrollment_id:m for m in assessment.marks.all()}
    return {'exam_id':str(assessment.exam_id),'revision':assessment.exam.revision,'status':assessment.exam.status,'maximum_score':str(assessment.maximum_score),'students':[{'enrollment_id':str(e.pk),'student_id':str(e.student_id),'name':str(e.student),'score':str(marks[e.pk].score) if e.pk in marks and marks[e.pk].score is not None else None,'outcome':marks[e.pk].outcome if e.pk in marks else 'present','remarks':marks[e.pk].remarks if e.pk in marks else ''} for e in roster(assessment)]}


@transaction.atomic
def save_marks(pk,data,*,access):
    access.require('mark','enter');lock(access)
    assessment=get(access,Assessment,pk);exam=assessment.exam;draft(exam);revision(exam,data)
    authorize(access,assessment.subject_offering,assessment.date)
    if assessment.date>timezone.localdate():invalid('date','Future assessments cannot receive marks.')
    records=data.get('records')
    if not isinstance(records,list) or not records or len(records)>1000:invalid('records','Provide 1–1000 mark rows.')
    eligible={str(e.pk):e for e in roster(assessment)};seen=set()
    for item in records:
        if not isinstance(item,dict) or set(item)-{'enrollment_id','score','outcome','remarks'}:invalid('records','Unsupported mark row.')
        key=str(item.get('enrollment_id'))
        if key not in eligible or key in seen:invalid('enrollment_id','Student is not enrolled for this assessment, or appears twice.')
        seen.add(key);outcome=item.get('outcome','present')
        if outcome not in ('present','absent','exempt'):invalid('outcome','Choose present, absent or exempt.')
        score=None
        if outcome=='present':score=serializers.DecimalField(max_digits=8,decimal_places=2,min_value=0,max_value=assessment.maximum_score).run_validation(item.get('score'))
        elif item.get('score') not in (None,''):invalid('score','Absent/exempt marks cannot include a score.')
        row=Mark.objects.filter(assessment=assessment,enrollment=eligible[key]).first() or Mark(tenant=access.tenant,branch=assessment.branch,assessment=assessment,enrollment=eligible[key])
        row.score=score;row.outcome=outcome;row.remarks=serializers.CharField(allow_blank=True,max_length=2000).run_validation(item.get('remarks',''))
        persist(row,access,'mark_saved')
    bump(exam,access)
    return exam


@transaction.atomic
def assignment_action(resource,pk,action,data,*,access):
    lock(access)
    if resource=='assignments':
        access.require('assignment',action);row=get(access,LearningAssignment,pk)
        authorize(access,row.subject_offering,row.assigned_date)
        expected={'publish':'draft','close':'published'}
        if action not in expected or row.status!=expected[action]:invalid('status','This assignment transition is not allowed.')
        row.status='published' if action=='publish' else 'closed'
    else:
        access.require('submission','grade');row=get(access,LearningSubmission,pk)
        authorize(access,row.assignment.subject_offering,row.assignment.assigned_date)
        if action!='grade':invalid('action','Unknown submission command.')
        row.score=serializers.DecimalField(max_digits=8,decimal_places=2,min_value=0,max_value=row.assignment.maximum_score).run_validation(data.get('score'))
        row.feedback=serializers.CharField(allow_blank=True,max_length=4000).run_validation(data.get('feedback',''));row.status='graded'
    return persist(row,access,'learning_'+action)


@transaction.atomic
def exam_action(pk,action,data,*,access):
    access.require('exam',action);lock(access);exam=get(access,Exam,pk)
    if action=='reopen':
        if exam.status=='draft':invalid('status','Exam is already a draft.')
        why=reason(data);exam.status='draft';exam.revision+=1;event(exam,access,'exam_reopen_reason',reason=why)
    else:
        revision(exam,data)
        from .result_service import calculate, publish
        if action=='submit' and exam.status=='draft':calculate(exam);exam.status='submitted'
        elif action=='moderate' and exam.status=='submitted':calculate(exam);exam.status='moderated'
        elif action=='publish' and exam.status in ('moderated','published'):return publish(exam,access)
        else:invalid('status','Use draft → submit → moderate → publish; reopen requires a reason.')
    return persist(exam,access,'exam_'+action)
