"""Decimal result calculation and immutable publication/report versions."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Count
from apps.school.models import AttendanceRecord
from apps.school.models.learning import ResultPublication, ReportCardVersion
from .learning_common import roster,bands,grade
from .sis_common import invalid,persist


def calculate(exam):
    grade_bands=bands(exam.scheme)
    assessments=list(exam.assessments.filter(deleted_at__isnull=True).select_related('subject_offering__subject','subject_offering__academic_year','exam__term'))
    if not assessments:invalid('assessments','Add at least one assessment.')
    weights=defaultdict(Decimal)
    for a in assessments:weights[a.subject_offering_id]+=a.weight
    if any(value!=100 for value in weights.values()):invalid('weight','Assessment weights must total 100 per offering.')
    students={};cohort=None
    for a in assessments:
        eligible={e.pk:e for e in roster(a)}
        student_ids={e.student_id for e in eligible.values()}
        if not student_ids:invalid('enrollment','Assessment has no eligible students.')
        if cohort is None:cohort=student_ids
        if student_ids!=cohort:invalid('enrollment','Assessment rosters differ; separate exams are required for different cohorts.')
        marks={m.enrollment_id:m for m in a.marks.select_related('enrollment__student')}
        if set(marks)!=set(eligible):invalid('marks','Every eligible student needs a mark, absent or exempt outcome.')
        for eid,e in eligible.items():
            m=marks[eid]
            student=students.setdefault(str(e.student_id),{'student_id':str(e.student_id),'name':str(e.student),'enrollment_id':str(e.pk),'subjects':{}})
            subject=student['subjects'].setdefault(str(a.subject_offering_id),{'name':a.subject_offering.subject.name,'weighted':Decimal(0),'weight':Decimal(0),'subject_weight':a.subject_offering.weight,'assessments':[]})
            if m.outcome!='exempt':
                subject['weight']+=a.weight
                subject['weighted']+=(m.score if m.outcome=='present' else Decimal(0))/a.maximum_score*a.weight
            subject['assessments'].append({'assessment_id':str(a.pk),'name':a.name,'score':str(m.score) if m.score is not None else None,'maximum_score':str(a.maximum_score),'weight':str(a.weight),'outcome':m.outcome})
    start,end=(exam.term.start_date,exam.term.end_date) if exam.term_id else (exam.academic_year.start_date,exam.academic_year.end_date)
    for sid,student in students.items():
        total=Decimal(0);weight=Decimal(0);passed=True
        for subject in student['subjects'].values():
            sw=subject.pop('subject_weight');denominator=subject.pop('weight');numerator=subject.pop('weighted')
            value=(numerator/denominator*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if denominator else None
            label,ok=grade(value,grade_bands) if value is not None else ('Exempt',True)
            subject.update(percentage=str(value) if value is not None else None,grade=label,passed=ok)
            if value is not None:total+=value*sw;weight+=sw
            passed=passed and ok
        value=(total/weight).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if weight else None
        student.update(percentage=str(value) if value is not None else None,passed=passed and weight>0)
        attendance=AttendanceRecord.objects.filter(tenant=exam.tenant,branch=exam.branch,enrollment__student_id=sid,session__academic_year=exam.academic_year,session__status='submitted',session__mode='daily',session__date__range=(start,end),deleted_at__isnull=True)
        student['attendance']=dict(attendance.values_list('status').annotate(n=Count('pk')))
    ranked=sorted((s for s in students.values() if s['percentage'] is not None),key=lambda s:Decimal(s['percentage']),reverse=True)
    previous=None;rank=0
    for position,student in enumerate(ranked,1):
        if student['percentage']!=previous:rank=rank+1 if exam.scheme.ranking=='dense' else position
        student['rank']=rank if exam.scheme.ranking!='none' else None
        previous=student['percentage']
    return {'exam_id' :str(exam.pk),'name':exam.name,'academic_year_id':str(exam.academic_year_id),'term_id':str(exam.term_id) if exam.term_id else None,'revision':exam.revision,'policy':{'missing':'blocks publication','absent':'zero','exempt':'excluded and remaining weights normalized','rounding':'decimal half up, 2 places','overall':'offering-weighted mean; every assessed subject must pass','ranking':exam.scheme.ranking},'grade_bands':[{'label':b.label,'minimum':str(b.minimum),'maximum':str(b.maximum),'passing':b.passing} for b in grade_bands],'students':list(students.values())}


def publish(exam,access):
    if exam.status=='published':return exam
    snapshot=calculate(exam)
    latest=exam.publications.order_by('-version').first()
    publication=persist(ResultPublication(tenant=access.tenant,branch=exam.branch,exam=exam,version=latest.version+1 if latest else 1,snapshot=snapshot),access,'results_published')
    for student in snapshot['students']:
        persist(ReportCardVersion(tenant=access.tenant,branch=exam.branch,publication=publication,student_id=student['student_id'],data={**student,'exam':exam.name,'version':publication.version,'academic_year':exam.academic_year.name}),access,'report_card_published')
    exam.status='published'
    return persist(exam,access,'exam_published')
