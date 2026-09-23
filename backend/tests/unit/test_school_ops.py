"""Phase 4: teaching staff, timetable conflicts and daily/period attendance."""
import pytest
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.authentication.models import User, Role
from apps.audit.models import AuditLog
from apps.school.models import AttendanceRecord, AttendanceSession, TimetableEntry, SchoolCampusAccess
from apps.school.repositories.sis import StudentAccess, queryset
from apps.school.services.sis_crud import StudentCrudService as Crud
from apps.school.services.attendance_service import AttendanceService, roster_view
from apps.school.services.timetable_service import TimetableService
from tests.unit.test_school_foundation import create, structure
from tests.unit.test_school_foundation import school_catalog, school  # noqa: F401  (fixtures)
from tests.unit.test_school_sis import sis, direct  # noqa: F401

pytestmark = pytest.mark.django_db
TODAY = '2026-09-21'


def mk(s, resource, **data):
    return Crud.save(resource, data, access=s['access'])


def ids(**kw):
    return {k: str(v.pk) if hasattr(v, 'pk') else v for k, v in kw.items()}


@pytest.fixture
def ops(sis):
    s = sis
    teacher_user = User.objects.create_user(username='teacher1', tenant=s['t'], branch=s['a'], role=Role.objects.get(slug='school_teacher'))
    other_user = User.objects.create_user(username='teacher2', tenant=s['t'], branch=s['a'], role=Role.objects.get(slug='school_teacher'))
    def person(code, user=None, branch='a'):
        e = mk(s, 'employees', **ids(branch_id=s[branch], user_id=user), code=code, first_name=code, last_name='Teacher')
        return mk(s, 'staff-profiles', **ids(branch_id=s[branch], employee_id=e), staff_type='teacher'), e
    p1, e1 = person('T1', teacher_user)
    p2, _ = person('T2', other_user)
    sub2 = create(s, 'subjects', name='Science', code='SCI')
    from apps.school.models import Subject
    math = Subject.objects.get(code='MAT')
    from apps.school.services.foundation_service import FoundationService as F
    def offering(code, subj, sec=None, weekly=2):
        return F.save('subject-offerings', dict(name=code, code=code, branch_id=str(s['a'].pk), academic_year_id=str(s['y'].pk), school_class_id=str(s['k'].pk), subject_id=str(subj.pk), weekly_periods=weekly, **({'section_id': str(sec.pk)} if sec else {})), user=s['owner'])
    s['math'], s['sci'] = offering('M5', math, weekly=4), offering('S5', sub2, weekly=1)
    def period(code, start, end):
        return mk(s, 'periods', branch_id=str(s['a'].pk), code=code, name=code, start_time=start, end_time=end)
    s['p1'], s['p2'], s['p3'] = period('P1', '08:00', '08:45'), period('P2', '08:45', '09:30'), period('P3', '09:30', '10:15')
    s['room1'], s['room2'] = (mk(s, 'classrooms', branch_id=str(s['a'].pk), code=c, name=c) for c in ('R1', 'R2'))
    s['sec2'] = F.save('sections', dict(name='B', code='B', branch_id=str(s['a'].pk), school_class_id=str(s['k'].pk), capacity=20), user=s['owner'])
    def assign(profile, offering, role='subject_teacher', sec=None):
        return mk(s, 'teacher-assignments', **ids(staff_id=profile, academic_year_id=s['y'], school_class_id=s['k'], subject_offering_id=offering), section_id=str(sec.pk) if sec else None, role=role, start_date='2026-09-01')
    s.update(p1_staff=p1, p2_staff=p2, teacher_user=teacher_user, other_user=other_user, assign=assign, e1=e1)
    assign(p1, s['math']); assign(p2, s['sci'])
    s['version'] = mk(s, 'timetable-versions', **ids(branch_id=s['a'], academic_year_id=s['y']), name='Term 1', effective_from='2026-09-01')
    def entry(period, weekday=1, offering=None, staff=None, room=None, section=None, version=None):
        return mk(s, 'timetable-entries', **ids(version_id=version or s['version'], period_id=period, school_class_id=s['k'], subject_offering_id=offering or s['math']), weekday=weekday,
                  staff_id=str((staff or s['p1_staff']).pk) if staff != 0 else None, classroom_id=str(room.pk) if room else None, section_id=str(section.pk) if section else None)
    s['entry'] = entry
    return s


def test_staff_and_assignment_integrity(ops):
    s = ops
    with pytest.raises(ValidationError):  # login from another organisation
        mk(s, 'employees', **ids(branch_id=s['a'], user_id=s['foreign']), code='X', first_name='X')
    with pytest.raises(ValidationError):  # one employee record per login
        mk(s, 'employees', **ids(branch_id=s['a'], user_id=s['teacher_user']), code='X2', first_name='X')
    with pytest.raises(ValidationError):  # duplicate profile on a campus
        mk(s, 'staff-profiles', **ids(branch_id=s['a'], employee_id=s['e1']))
    with pytest.raises(ValidationError):  # subject teachers need an offering
        mk(s, 'teacher-assignments', **ids(staff_id=s['p1_staff'], academic_year_id=s['y'], school_class_id=s['k']), role='subject_teacher', start_date='2026-09-01')
    with pytest.raises(ValidationError):  # duplicate assignment
        s['assign'](s['p1_staff'], s['math'])
    s['assign'](s['p1_staff'], None, role='class_teacher')
    with pytest.raises(ValidationError):  # one class teacher per class
        s['assign'](s['p2_staff'], None, role='class_teacher')
    with pytest.raises(ValidationError):  # assignment outside the year
        mk(s, 'teacher-assignments', **ids(staff_id=s['p2_staff'], academic_year_id=s['y'], school_class_id=s['k'], subject_offering_id=s['sci']), role='subject_teacher', start_date='2025-01-01')


def test_timetable_conflict_detection(ops):
    s = ops
    entry = s['entry']
    first = entry(s['p1'], room=s['room1'])
    with pytest.raises(ValidationError, match='teacher'):
        entry(s['p1'], offering=s['sci'], staff=s['p1_staff'], room=s['room2'], section=s['sec'])  # same teacher, same slot
    s['assign'](s['p1_staff'], s['sci'])
    with pytest.raises(ValidationError, match='teacher'):
        entry(s['p1'], offering=s['sci'], staff=s['p1_staff'], room=s['room2'], section=s['sec'])
    with pytest.raises(ValidationError, match='room'):
        entry(s['p1'], offering=s['sci'], staff=s['p2_staff'], room=s['room1'], section=s['sec'])
    with pytest.raises(ValidationError, match='class or section'):  # class-wide lesson blocks any section
        entry(s['p1'], offering=s['sci'], staff=s['p2_staff'], room=s['room2'], section=s['sec'])
    # valid: different period, different weekday
    entry(s['p2'], room=s['room1'])
    entry(s['p1'], weekday=2, room=s['room1'])
    assert TimetableEntry.objects.filter(version=s['version']).count() == 3
    # overlapping (not identical) periods conflict on time, not on id
    overlap = mk(s, 'periods', branch_id=str(s['a'].pk), code='X', name='X', start_time='10:15', end_time='11:00')
    entry(overlap, room=s['room1'])
    with pytest.raises(ValidationError):
        mk(s, 'periods', branch_id=str(s['a'].pk), code='Y', name='Y', start_time='10:30', end_time='11:30')
    with pytest.raises(ValidationError, match='weekly'):  # a fifth lesson exceeds the offering's four weekly periods
        entry(s['p3'], room=s['room2'], weekday=4)
    assert first.status == 'active'


def test_section_lessons_coexist_and_unassigned_teacher_rejected(ops):
    s = ops
    entry = s['entry']
    one = entry(s['p1'], section=s['sec'], room=s['room1'])
    entry(s['p1'], section=s['sec2'], room=s['room2'], staff=0)  # two sections, no teacher yet
    with pytest.raises(ValidationError, match='class or section'):
        entry(s['p1'], section=s['sec'], room=None, staff=0)
    with pytest.raises(ValidationError, match='assignment'):  # T2 is not assigned to Math
        entry(s['p2'], section=s['sec'], staff=s['p2_staff'])
    assert one.section_id == s['sec'].pk


def test_publish_recheck_supersede_and_immutability(ops):
    s = ops
    entry = s['entry']
    with pytest.raises(ValidationError):
        TimetableService.publish(s['version'].pk, {}, access=s['access'])  # empty
    mine = entry(s['p1'], room=s['room1'])
    published = TimetableService.publish(s['version'].pk, {}, access=s['access'])
    assert published.status == 'published' and published.published_by_id == s['owner'].pk
    with pytest.raises(ValidationError):
        Crud.save('timetable-entries', {'status': 'inactive'}, pk=mine.pk, access=s['access'])
    with pytest.raises(ValidationError):
        Crud.archive('timetable-entries', mine.pk, access=s['access'])
    with pytest.raises(ValidationError):
        Crud.archive('timetable-versions', s['version'].pk, access=s['access'])
    draft = TimetableService.clone(s['version'].pk, {'name': 'Revised'}, access=s['access'])
    assert TimetableEntry.objects.filter(version=draft, deleted_at__isnull=True).count() == 1
    TimetableService.publish(draft.pk, {}, access=s['access'])
    s['version'].refresh_from_db()
    assert s['version'].status == 'archived'
    actions = set(AuditLog.objects.filter(module='school', entity_id__in=[s['version'].pk, draft.pk]).values_list('action', flat=True))
    assert {'timetable_published', 'timetable_superseded', 'timetable_cloned'} <= actions


def test_cross_campus_teacher_conflict(ops):
    s = ops
    from apps.school.services.foundation_service import FoundationService as F
    entry = s['entry']
    entry(s['p1'])
    TimetableService.publish(s['version'].pk, {}, access=s['access'])
    # The same employee holds a profile at campus B and cannot be scheduled there at the same time.
    e = s['e1']
    b = str(s['b'].pk)
    SchoolCampusAccess.objects.get_or_create(tenant=s['t'], user=s['owner'], branch=s['b'])
    yb = create(s, 'academic-years', name='BY', code='BY', branch_id=b, start_date='2026-09-01', end_date='2027-07-01')
    F.save('academic-years', {'enrollment_open': True}, pk=yb.pk, user=s['owner'])
    F.action('academic-years', yb.pk, 'activate', user=s['owner'])
    level = s['k'].education_level
    kb = create(s, 'classes', name='Grade 6', code='G6', branch_id=b, education_level_id=str(level.pk))
    from apps.school.models import Subject
    ob = F.save('subject-offerings', dict(name='MB', code='MB', branch_id=b, academic_year_id=str(yb.pk), school_class_id=str(kb.pk), subject_id=str(Subject.objects.get(code='MAT').pk)), user=s['owner'])
    pb = mk(s, 'periods', branch_id=b, code='PB', name='PB', start_time='08:15', end_time='09:00')
    profile_b = mk(s, 'staff-profiles', branch_id=b, employee_id=str(e.pk))
    mk(s, 'teacher-assignments', staff_id=str(profile_b.pk), academic_year_id=str(yb.pk), school_class_id=str(kb.pk), subject_offering_id=str(ob.pk), start_date='2026-09-01')
    vb = mk(s, 'timetable-versions', branch_id=b, academic_year_id=str(yb.pk), name='B', effective_from='2026-09-01')
    with pytest.raises(ValidationError, match='another campus'):
        mk(s, 'timetable-entries', version_id=str(vb.pk), period_id=str(pb.pk), weekday=1, school_class_id=str(kb.pk), subject_offering_id=str(ob.pk), staff_id=str(profile_b.pk))


def test_bulk_attendance_lock_and_errors(ops):
    s = ops
    a = direct(s)
    b = direct(s, first_name='Bilal', date_of_birth='2015-05-05')
    base = {'school_class_id': str(s['k'].pk), 'section_id': str(s['sec'].pk), 'date': TODAY}
    marks = [{'student_id': str(a.pk), 'status': 'present'}, {'student_id': str(b.pk), 'status': 'absent', 'remarks': 'sick'}]
    with pytest.raises(ValidationError):  # incomplete submit
        AttendanceService.take({**base, 'records': marks[:1], 'submit': True}, access=s['access'])
    session = AttendanceService.take({**base, 'records': marks[:1]}, access=s['access'])
    assert session.status == 'open' and session.records.count() == 1
    AttendanceService.take({**base, 'records': marks}, access=s['access'])  # idempotent upsert into one session
    assert AttendanceSession.objects.count() == 1 and session.records.count() == 2
    for bad in ({'records': [{'student_id': '00000000-0000-0000-0000-000000000000', 'status': 'present'}]}, {'records': [{'student_id': str(a.pk), 'status': 'sleeping'}]},
                {'records': [marks[0], marks[0]]}, {'records': marks, 'date': '2027-08-01'}, {'records': marks, 'date': '2025-01-01'}, {'records': marks, 'mode': 'period'}):
        with pytest.raises(ValidationError):
            AttendanceService.take({**base, **bad}, access=s['access'])
    submitted = AttendanceService.take({**base, 'records': marks, 'submit': True}, access=s['access'])
    assert submitted.status == 'submitted'
    with pytest.raises(ValidationError, match='locked'):
        AttendanceService.take({**base, 'records': marks}, access=s['access'])
    view = roster_view(s['access'], base)
    assert [r['status'] for r in view['students']] == ['present', 'absent']
    assert queryset('attendance-sessions', s['access']).get().absent_count == 1


def test_period_attendance_is_separate_from_daily(ops):
    s = ops
    a = direct(s)
    base = {'school_class_id': str(s['k'].pk), 'section_id': str(s['sec'].pk), 'date': TODAY, 'records': [{'student_id': str(a.pk), 'status': 'present'}]}
    AttendanceService.take(base, access=s['access'])
    AttendanceService.take({**base, 'mode': 'period', 'period_id': str(s['p1'].pk), 'subject_offering_id': str(s['math'].pk)}, access=s['access'])
    AttendanceService.take({**base, 'mode': 'period', 'period_id': str(s['p2'].pk)}, access=s['access'])
    assert AttendanceSession.objects.count() == 3 and AttendanceRecord.objects.count() == 3


def test_teacher_scope_and_no_wrong_year(ops):
    s = ops
    a = direct(s)
    base = {'school_class_id': str(s['k'].pk), 'section_id': str(s['sec'].pk), 'date': TODAY, 'records': [{'student_id': str(a.pk), 'status': 'present'}]}
    mine, theirs = StudentAccess(user=s['teacher_user']), StudentAccess(user=s['other_user'])
    with pytest.raises(PermissionDenied):  # daily attendance needs a class-teacher assignment
        AttendanceService.take(base, access=mine)
    s['assign'](s['p1_staff'], None, role='class_teacher')
    AttendanceService.take(base, access=mine)
    with pytest.raises(ValidationError, match='subject'):  # teachers must name the subject they teach
        AttendanceService.take({**base, 'mode': 'period', 'period_id': str(s['p1'].pk)}, access=theirs)
    AttendanceService.take({**base, 'mode': 'period', 'period_id': str(s['p1'].pk), 'subject_offering_id': str(s['sci'].pk)}, access=theirs)
    with pytest.raises(PermissionDenied):
        AttendanceService.take({**base, 'mode': 'period', 'period_id': str(s['p2'].pk), 'subject_offering_id': str(s['math'].pk)}, access=theirs)
    with pytest.raises(ValidationError):  # date outside the active year
        AttendanceService.take({**base, 'date': '2026-08-01'}, access=s['access'])


def test_correction_workflow_and_audit(ops):
    s = ops
    a = direct(s)
    base = {'school_class_id': str(s['k'].pk), 'section_id': str(s['sec'].pk), 'date': TODAY, 'records': [{'student_id': str(a.pk), 'status': 'absent'}]}
    s['assign'](s['p1_staff'], None, role='class_teacher')
    mine = StudentAccess(user=s['teacher_user'])
    session = AttendanceService.take(base, access=mine)
    record = session.records.get()
    with pytest.raises(ValidationError, match='still open'):
        AttendanceService.request_correction(record.pk, {'new_status': 'present', 'reason': 'x'}, access=mine)
    AttendanceService.submit(session.pk, access=mine)
    with pytest.raises(ValidationError):
        AttendanceService.request_correction(record.pk, {'new_status': 'present', 'reason': ' '}, access=mine)
    with pytest.raises(ValidationError):
        AttendanceService.request_correction(record.pk, {'new_status': 'absent', 'reason': 'same'}, access=mine)
    correction = AttendanceService.request_correction(record.pk, {'new_status': 'present', 'reason': 'Arrived late, missed at roll call'}, access=mine)
    with pytest.raises(ValidationError, match='pending'):
        AttendanceService.request_correction(record.pk, {'new_status': 'late', 'reason': 'again'}, access=mine)
    with pytest.raises(PermissionDenied):  # teachers request; they cannot approve
        AttendanceService.decide(correction.pk, True, {}, access=mine)
    record.refresh_from_db(); assert record.status == 'absent'
    AttendanceService.decide(correction.pk, True, {'decision_note': 'Confirmed by parent'}, access=s['access'])
    record.refresh_from_db(); assert record.status == 'present'
    with pytest.raises(ValidationError, match='already'):
        AttendanceService.decide(correction.pk, True, {}, access=s['access'])
    log = AuditLog.objects.get(entity_id=record.pk, action='attendance_corrected')
    assert log.new_values['old_status'] == 'absent' and log.new_values['new_status'] == 'present' and 'roll call' in log.new_values['reason']
    rejected = AttendanceService.request_correction(record.pk, {'new_status': 'excused', 'reason': 'Note supplied'}, access=mine)
    with pytest.raises(ValidationError):
        AttendanceService.decide(rejected.pk, False, {}, access=s['access'])  # rejection needs a reason
    AttendanceService.decide(rejected.pk, False, {'decision_note': 'No evidence'}, access=s['access'])
    record.refresh_from_db(); assert record.status == 'present'


def test_http_authorization_and_scope(ops):
    s = ops
    c = s['client']
    other = s['client'].__class__(); other.force_authenticate(s['teacher_user'])
    assert other.post('/api/v1/school/sis/timetable-versions/', {}, format='json').status_code == 403
    assert other.get('/api/v1/school/sis/timetable-versions/').status_code == 200
    assert other.post(f'/api/v1/school/sis/timetable-versions/{s["version"].pk}/publish/', {}, format='json').status_code == 403
    assert other.post('/api/v1/school/sis/employees/', {}, format='json').status_code == 403
    r = c.post('/api/v1/school/sis/attendance-sessions/', {'records': []}, format='json'); assert r.status_code == 400
    assert c.patch('/api/v1/school/sis/attendance-records/00000000-0000-0000-0000-000000000000/', {}, format='json').status_code in (403, 404)
    caps = other.get('/api/v1/school/sis/capabilities/').data['data']
    assert 'school.attendance.take' in caps and 'school.timetable.publish' not in caps
    # a campus-B-only reader cannot see campus-A rows
    outsider = User.objects.create_user(username='outsider', tenant=s['t'], branch=s['b'], role=Role.objects.get(slug='school_principal'))
    o = s['client'].__class__(); o.force_authenticate(outsider)
    assert o.get('/api/v1/school/sis/employees/').data['data']['count'] == 0
    assert o.get(f'/api/v1/school/sis/timetable-versions/{s["version"].pk}/').status_code == 404
    assert o.get(f'/api/v1/school/sis/attendance-roster/?school_class_id={s["k"].pk}&date={TODAY}').status_code in (403, 404)
