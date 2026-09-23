"""Phase 5 academic cycle and integrity gates."""
import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from tests.unit.test_school_sis import school_catalog, school, sis, direct, Service, Crud
from apps.school.models import Subject
from apps.school.models.learning import Mark, ResultPublication, ReportCardVersion
from apps.school.services import marks_service as marks, result_service as results

pytestmark=pytest.mark.django_db

@pytest.fixture
def learning(sis):
    s=sis;s['student']=direct(s);s['enrollment']=s['student'].enrollments.get()
    s['offering']=Service.save('subject-offerings',dict(name='Math 5',code='M5',branch_id=str(s['a'].pk),academic_year_id=str(s['y'].pk),school_class_id=str(s['k'].pk),subject_id=str(Subject.objects.get(tenant=s['t']).pk),section_id=str(s['sec'].pk)),user=s['owner'])
    def create(resource,**data):return Crud.save(resource,data,access=s['access'])
    s['create']=create
    scheme=create('grade-schemes',branch_id=str(s['a'].pk),name='Standard',code='STD');s['scheme']=scheme
    create('grade-bands',scheme_id=str(scheme.pk),label='Fail',minimum='0',maximum='50',passing=False)
    create('grade-bands',scheme_id=str(scheme.pk),label='Pass',minimum='50',maximum='100',passing=True)
    exam=create('exams',branch_id=str(s['a'].pk),name='Final',academic_year_id=str(s['y'].pk),school_class_id=str(s['k'].pk),section_id=str(s['sec'].pk),scheme_id=str(scheme.pk));s['exam']=exam
    s['assessment']=create('academic-assessments',exam_id=str(exam.pk),subject_offering_id=str(s['offering'].pk),name='Written',date='2026-09-10',maximum_score='100',weight='100')
    exam.refresh_from_db()
    return s

def save(s,score='80',outcome='present'):
    s['exam'].refresh_from_db()
    return marks.save_marks(s['assessment'].pk,{'expected_revision':s['exam'].revision,'records':[{'enrollment_id':str(s['enrollment'].pk),'score':score,'outcome':outcome}]},access=s['access'])

def publish(s):
    for action in ('submit','moderate','publish'):
        s['exam'].refresh_from_db();marks.exam_action(s['exam'].pk,action,{'expected_revision':s['exam'].revision},access=s['access'])
    return ResultPublication.objects.get(exam=s['exam'])

def test_academic_cycle_versions_and_print(learning):
    s=learning;save(s);pub=publish(s);card=ReportCardVersion.objects.get(publication=pub)
    assert card.data['percentage']=='80.00' and card.data['passed']
    with pytest.raises(ValidationError):save(s,'90')
    marks.exam_action(s['exam'].pk,'reopen',{'reason':'Moderation correction'},access=s['access']);save(s,'90')
    for action in ('submit','moderate','publish'):
        s['exam'].refresh_from_db();marks.exam_action(s['exam'].pk,action,{'expected_revision':s['exam'].revision},access=s['access'])
    card.refresh_from_db();assert card.data['percentage']=='80.00'
    assert ResultPublication.objects.filter(exam=s['exam']).count()==2
    response=s['client'].get(f'/api/v1/school/sis/report-cards/{card.pk}/print/')
    assert response.status_code==200 and b'80.00' in response.content
    assert s['client'].patch(f'/api/v1/school/sis/report-cards/{card.pk}/',{'data':{}},format='json').status_code in (400,403)

@pytest.mark.parametrize('score,outcome',[('-1','present'),('101','present'),(None,'present'),('2','absent'),('0','exempt')])
def test_score_bounds(learning,score,outcome):
    with pytest.raises(ValidationError):save(learning,score,outcome)
    assert not Mark.objects.exists()

def test_missing_stale_and_atomic_marks(learning):
    s=learning
    with pytest.raises(ValidationError):results.calculate(s['exam'])
    old=s['exam'].revision;save(s)
    with pytest.raises(ValidationError):marks.save_marks(s['assessment'].pk,{'expected_revision':old,'records':[]},access=s['access'])
    assert Mark.objects.get().score==80
    s['exam'].refresh_from_db()
    with pytest.raises(ValidationError):marks.save_marks(s['assessment'].pk,{'expected_revision':s['exam'].revision,'records':[{'enrollment_id':str(s['enrollment'].pk),'score':'90'},{'enrollment_id':str(s['enrollment'].pk),'score':'20'}]},access=s['access'])
    assert Mark.objects.get().score==80

def test_absent_exempt_weight_and_bands(learning):
    s=learning;save(s,None,'absent');assert results.calculate(s['exam'])['students'][0]['percentage']=='0.00'
    save(s,None,'exempt');row=results.calculate(s['exam'])['students'][0];assert row['percentage'] is None and not row['passed']
    with pytest.raises(ValidationError):s['create']('grade-bands',scheme_id=str(s['scheme'].pk),label='Overlap',minimum='40',maximum='60')
    s['assessment'].weight=Decimal('90');s['assessment'].save()
    with pytest.raises(ValidationError):results.calculate(s['exam'])

def test_assignment_submission(learning):
    s=learning;a=s['create']('assignments',subject_offering_id=str(s['offering'].pk),title='Practice',assigned_date='2026-09-10',due_date='2026-09-20',maximum_score='10')
    marks.assignment_action('assignments',a.pk,'publish',{},access=s['access'])
    sub=s['create']('submissions',assignment_id=str(a.pk),enrollment_id=str(s['enrollment'].pk),content='My work')
    with pytest.raises(ValidationError):marks.assignment_action('submissions',sub.pk,'grade',{'score':'11'},access=s['access'])
    marks.assignment_action('submissions',sub.pk,'grade',{'score':'9','feedback':'Good'},access=s['access'])
    sub.refresh_from_db();assert sub.score==9 and sub.status=='graded'

def test_http_tenant_and_campus(learning):
    s=learning
    for resource in ('exams','academic-assessments','grade-schemes','grade-bands','marks','result-publications','report-cards','promotion-batches'):
        r=s['client'].get(f'/api/v1/school/sis/{resource}/');assert r.status_code==200,r.data
    s['client'].force_authenticate(s['foreign'])
    assert s['client'].get(f"/api/v1/school/sis/exams/{s['exam'].pk}/").status_code in (403,404)

def test_teacher_assignment_scope(learning):
    from apps.authentication.models import User,Role
    s=learning
    teacher=User.objects.create_user(username='teacher',tenant=s['t'],branch=s['a'],role=Role.objects.get(slug='school_teacher'))
    employee=s['create']('employees',branch_id=str(s['a'].pk),user_id=str(teacher.pk),code='T',first_name='Teacher')
    staff=s['create']('staff-profiles',branch_id=str(s['a'].pk),employee_id=str(employee.pk))
    s['client'].force_authenticate(teacher);url=f"/api/v1/school/sis/marks-roster/{s['assessment'].pk}/"
    assert s['client'].get(url).status_code in (403,404)
    s['create']('teacher-assignments',staff_id=str(staff.pk),academic_year_id=str(s['y'].pk),school_class_id=str(s['k'].pk),section_id=str(s['sec'].pk),subject_offering_id=str(s['offering'].pk),start_date='2026-09-01')
    assert s['client'].get(url).status_code==200
    response=s['client'].post(f"/api/v1/school/sis/academic-assessments/{s['assessment'].pk}/marks/",{'expected_revision':s['exam'].revision,'records':[{'enrollment_id':str(s['enrollment'].pk),'score':'70'}]},format='json');assert response.status_code==200,response.data
    assert s['client'].post(f"/api/v1/school/sis/exams/{s['exam'].pk}/publish/",{},format='json').status_code==403
    teacher.branch=s['b'];teacher.save();s['client'].force_authenticate(teacher)
    assert s['client'].get(url).status_code==404

@pytest.mark.parametrize('outcome',['promote','repeat','graduate'])
def test_promotion_history_and_replay(learning,monkeypatch,outcome):
    from datetime import date
    from apps.school.services import promotion_service as p
    s=learning;save(s);pub=publish(s)
    monkeypatch.setattr('django.utils.timezone.localdate',lambda:date(2027,9,2))
    target=Service.save('academic-years',{'branch_id':str(s['a'].pk),'name':'Next','code':'NEXT','start_date':'2027-09-01','end_date':'2028-07-01','enrollment_open':True},user=s['owner'])
    Service.action('academic-years',target.pk,'activate',user=s['owner'])
    klass=s['k'] if outcome=='repeat' else Service.save('classes',{'branch_id':str(s['a'].pk),'education_level_id':str(s['k'].education_level_id),'name':'Grade 6','code':'G6','capacity':30},user=s['owner'])
    data={'publication_id':str(pub.pk),'target_year_id':str(target.pk),'effective_date':'2027-09-01','reason':'Year completion','items':[{'enrollment_id':str(s['enrollment'].pk),'outcome':outcome,'target_class_id':str(klass.pk) if outcome!='graduate' else None}]}
    batch=p.preview(data,access=s['access']);assert s['student'].enrollments.count()==1
    for _ in range(2):p.commit(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    s['enrollment'].refresh_from_db();assert s['enrollment'].status=={'promote':'promoted','repeat':'repeated','graduate':'graduated'}[outcome]
    if outcome!='graduate':
        new=s['student'].enrollments.get(status='active');assert new.promoted_from_id==s['enrollment'].pk and new.academic_year_id==target.pk
        assert s['student'].enrollments.count()==2
    else:
        s['student'].refresh_from_db();assert s['student'].status=='graduated'
    assert ReportCardVersion.objects.get().data['percentage']=='80.00'

def test_stale_promotion_and_failed_graduation(learning):
    from apps.school.services import promotion_service as p
    s=learning;save(s,'40');pub=publish(s)
    data={'publication_id':str(pub.pk),'effective_date':'2026-09-20','reason':'Completion','items':[{'enrollment_id':str(s['enrollment'].pk),'outcome':'graduate'}]}
    with pytest.raises(ValidationError):p.preview(data,access=s['access'])
    marks.exam_action(s['exam'].pk,'reopen',{'reason':'Correction'},access=s['access']);save(s)
    for action in ('submit','moderate','publish'):
        s['exam'].refresh_from_db();marks.exam_action(s['exam'].pk,action,{'expected_revision':s['exam'].revision},access=s['access'])
    data['publication_id']=str(ResultPublication.objects.order_by('-version').first().pk)
    batch=p.preview(data,access=s['access']);s['enrollment'].notes='Changed';s['enrollment'].save()
    with pytest.raises(ValidationError):p.commit(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    s['enrollment'].refresh_from_db();assert s['enrollment'].status=='active'

def test_weighted_decimal_attendance_and_cross_enrollment(learning):
    from apps.school.services.attendance_service import AttendanceService
    s=learning;a=s['assessment'];a.weight=Decimal('40');a.maximum_score=Decimal('3');a.save()
    b=s['create']('academic-assessments',exam_id=str(s['exam'].pk),subject_offering_id=str(s['offering'].pk),name='Coursework',date='2026-09-10',maximum_score='10',weight='60')
    save(s,'2');s['assessment']=b;save(s,'8')
    session=AttendanceService.take({'branch_id':str(s['a'].pk),'academic_year_id':str(s['y'].pk),'school_class_id':str(s['k'].pk),'section_id':str(s['sec'].pk),'date':'2026-09-10','mode':'daily','records':[{'student_id':str(s['student'].pk),'status':'present'}]},access=s['access'])
    AttendanceService.submit(session.pk,access=s['access'])
    result=results.calculate(s['exam'])['students'][0];assert result['percentage']=='74.67' and result['attendance']=={'present':1}
    save(s,None,'exempt');assert results.calculate(s['exam'])['students'][0]['percentage']=='66.67'
    s['exam'].refresh_from_db()
    import uuid
    with pytest.raises(ValidationError):marks.save_marks(b.pk,{'expected_revision':s['exam'].revision,'records':[{'enrollment_id':str(uuid.uuid4()),'score':'5'}]},access=s['access'])

def test_schedule_conflict_and_publication_rollback(learning,monkeypatch):
    s=learning;e=s['create']('employees',branch_id=str(s['a'].pk),code='INV',first_name='Invigilator')
    staff=s['create']('staff-profiles',branch_id=str(s['a'].pk),employee_id=str(e.pk));room=s['create']('classrooms',branch_id=str(s['a'].pk),code='R',name='Room')
    data={'assessment_id':str(s['assessment'].pk),'staff_id':str(staff.pk),'classroom_id':str(room.pk),'start_time':'09:00','end_time':'10:00'}
    s['create']('exam-schedules',**data)
    b=s['create']('academic-assessments',exam_id=str(s['exam'].pk),subject_offering_id=str(s['offering'].pk),name='Other',date='2026-09-10',maximum_score='100',weight='50')
    with pytest.raises(ValidationError):s['create']('exam-schedules',**{**data,'assessment_id':str(b.pk)})
    # Remove a never-used extra draft through the model fixture to test atomic publication.
    b.delete();save(s)
    for action in ('submit','moderate'):
        s['exam'].refresh_from_db();marks.exam_action(s['exam'].pk,action,{'expected_revision':s['exam'].revision},access=s['access'])
    import apps.school.services.result_service as rs
    original=rs.persist
    def broken(row,*args,**kwargs):
        if isinstance(row,ReportCardVersion):raise RuntimeError('audit unavailable')
        return original(row,*args,**kwargs)
    monkeypatch.setattr(rs,'persist',broken)
    with pytest.raises(RuntimeError):marks.exam_action(s['exam'].pk,'publish',{'expected_revision':s['exam'].revision},access=s['access'])
    assert not ResultPublication.objects.exists();s['exam'].refresh_from_db();assert s['exam'].status=='moderated'

def test_promotion_capacity_preview_and_commit_rollback(learning,monkeypatch):
    from datetime import date
    from apps.school.services import promotion_service as p
    s=learning;save(s);pub=publish(s);monkeypatch.setattr('django.utils.timezone.localdate',lambda:date(2027,9,2))
    target=Service.save('academic-years',{'branch_id':str(s['a'].pk),'name':'Next','code':'NEXT','start_date':'2027-09-01','end_date':'2028-07-01','enrollment_open':True},user=s['owner']);Service.action('academic-years',target.pk,'activate',user=s['owner'])
    klass=Service.save('classes',{'branch_id':str(s['a'].pk),'education_level_id':str(s['k'].education_level_id),'name':'Next class','code':'NEXT','capacity':1},user=s['owner'])
    data={'publication_id':str(pub.pk),'target_year_id':str(target.pk),'effective_date':'2027-09-01','reason':'Promotion','items':[{'enrollment_id':str(s['enrollment'].pk),'outcome':'promote','target_class_id':str(klass.pk)}]}
    batch=p.preview(data,access=s['access'])
    original=p.placement
    def broken(*args,**kwargs):raise RuntimeError('Placement unavailable')
    monkeypatch.setattr(p,'placement',broken)
    with pytest.raises(RuntimeError):p.commit(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    s['enrollment'].refresh_from_db();assert s['enrollment'].status=='active' and s['enrollment'].end_date is None
    batch.refresh_from_db();assert batch.status=='preview'
    monkeypatch.setattr(p,'placement',original)
    s['placement']={**s['placement'],'academic_year_id':str(target.pk),'school_class_id':str(klass.pk),'section_id':None,'start_date':'2027-09-01'};direct(s,first_name='Occupied')
    with pytest.raises(ValidationError):p.commit(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])

def test_cross_entity_calendar_and_campus_rejected(learning):
    s=learning
    other=Service.save('classes',{'branch_id':str(s['b'].pk),'education_level_id':str(s['k'].education_level_id),'name':'Foreign campus','code':'B','capacity':10},user=s['owner'])
    with pytest.raises(ValidationError):s['create']('exams',branch_id=str(s['a'].pk),name='Invalid',academic_year_id=str(s['y'].pk),school_class_id=str(other.pk),scheme_id=str(s['scheme'].pk))
    with pytest.raises(ValidationError):s['create']('academic-assessments',exam_id=str(s['exam'].pk),subject_offering_id=str(s['offering'].pk),name='Out of year',date='2028-01-01')
    s['assessment'].date='2026-09-22';s['assessment'].save()
    with pytest.raises(ValidationError):save(s)

@pytest.mark.parametrize('ranking,expected',[('none',[None,None,None]),('competition',[1,1,3]),('dense',[1,1,2])])
def test_rank_configuration_and_ties(learning,ranking,expected):
    s=learning;second=direct(s,first_name='Second');third=direct(s,first_name='Third')
    s['scheme'].ranking=ranking;s['scheme'].save();save(s,'90')
    s['exam'].refresh_from_db()
    marks.save_marks(s['assessment'].pk,{'expected_revision':s['exam'].revision,'records':[{'enrollment_id':str(second.enrollments.get().pk),'score':'90'},{'enrollment_id':str(third.enrollments.get().pk),'score':'70'}]},access=s['access'])
    rows=results.calculate(s['exam'])['students'];ranked=sorted(rows,key=lambda r:Decimal(r['percentage']),reverse=True)
    assert [r['rank'] for r in ranked]==expected
