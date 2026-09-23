"""Phase 4 concurrent HTTP commands on real PostgreSQL."""
import pytest
from apps.authentication.models import User, Role
from apps.school.models import AttendanceSession, AttendanceRecord, AttendanceCorrection, TimetableEntry, TimetableVersion, SchoolAdmissionPolicy
from apps.school.repositories.sis import StudentAccess
from apps.school.services import student_creation
from apps.school.services.attendance_service import AttendanceService
from apps.school.services.sis_crud import StudentCrudService as Crud
from apps.school.services.foundation_service import FoundationService as Service
from tests.unit.test_school_postgresql import setup_school, race  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)
API = '/api/v1/school/sis/'


@pytest.fixture
def ready(setup_school):
    s = setup_school
    Service.save('academic-years', {'enrollment_open': True}, pk=s['year'].pk, user=s['owner'])
    Service.action('academic-years', s['year'].pk, 'activate', user=s['owner'])
    SchoolAdmissionPolicy.objects.create(tenant=s['tenant'], branch=s['branch'], require_guardian=False)
    s['access'] = StudentAccess(user=s['owner'])
    b = str(s['branch'].pk)
    def mk(resource, **data):
        return Crud.save(resource, data, access=s['access'])
    s['mk'] = mk
    teacher = User.objects.create_user(username='teacher', tenant=s['tenant'], branch=s['branch'], role=Role.objects.get(slug='school_teacher'))
    emp = mk('employees', branch_id=b, user_id=str(teacher.pk), code='E1', first_name='Tee')
    s['staff'] = mk('staff-profiles', branch_id=b, employee_id=str(emp.pk))
    s['section2'] = s['create']('sections', name='Stream B', code='SB', branch_id=b, school_class_id=str(s['klass'].pk))
    s['offering'] = s['create']('subject-offerings', name='M', code='M', branch_id=b, academic_year_id=str(s['year'].pk), school_class_id=str(s['klass'].pk), subject_id=str(s['subject'].pk), weekly_periods=5)
    mk('teacher-assignments', staff_id=str(s['staff'].pk), academic_year_id=str(s['year'].pk), school_class_id=str(s['klass'].pk), subject_offering_id=str(s['offering'].pk), start_date='2026-01-01')
    s['period'] = mk('periods', branch_id=b, code='P1', name='P1', start_time='08:00', end_time='08:45')
    s['version'] = mk('timetable-versions', branch_id=b, academic_year_id=str(s['year'].pk), name='T', effective_from='2026-01-01')
    return s


def enroll(s, name):
    placement = {'branch_id': str(s['branch'].pk), 'academic_year_id': str(s['year'].pk), 'school_class_id': str(s['klass'].pk), 'section_id': str(s['section'].pk), 'start_date': '2026-01-01'}
    return student_creation.direct({'student': {'branch_id': str(s['branch'].pk), 'first_name': name, 'date_of_birth': '2015-02-02'}, 'placement': placement, 'reason': 'Registration'}, access=s['access'])


def test_concurrent_teacher_double_booking_yields_one_lesson(ready):
    s = ready
    def lesson(section):
        return (API + 'timetable-entries/', {'version_id': str(s['version'].pk), 'period_id': str(s['period'].pk), 'weekday': 1, 'school_class_id': str(s['klass'].pk), 'section_id': str(section.pk), 'subject_offering_id': str(s['offering'].pk), 'staff_id': str(s['staff'].pk)})
    results = race(s['owner'], [lesson(s['section']), lesson(s['section2'])])
    assert sorted(code for code, _ in results) == [201, 400], results
    assert TimetableEntry.objects.filter(version=s['version']).count() == 1


def test_concurrent_attendance_saves_share_one_session(ready):
    s = ready
    a, b = enroll(s, 'Amina'), enroll(s, 'Bilal')
    marks = [{'student_id': str(a.pk), 'status': 'present'}, {'student_id': str(b.pk), 'status': 'absent'}]
    body = {'school_class_id': str(s['klass'].pk), 'section_id': str(s['section'].pk), 'date': '2026-09-21', 'records': marks}
    results = race(s['owner'], [(API + 'attendance-sessions/', body)] * 2)
    assert [code for code, _ in results] == [201, 201], results
    assert AttendanceSession.objects.count() == 1 and AttendanceRecord.objects.count() == 2


def test_concurrent_publish_leaves_one_live_timetable(ready):
    s = ready
    entry = {'period_id': str(s['period'].pk), 'weekday': 1, 'school_class_id': str(s['klass'].pk), 'subject_offering_id': str(s['offering'].pk)}
    other = s['mk']('timetable-versions', branch_id=str(s['branch'].pk), academic_year_id=str(s['year'].pk), name='T2', effective_from='2026-01-01')
    for version in (s['version'], other):
        s['mk']('timetable-entries', version_id=str(version.pk), **entry)
    results = race(s['owner'], [(f'{API}timetable-versions/{v.pk}/publish/', {}) for v in (s['version'], other)])
    assert all(code == 200 for code, _ in results), results
    assert TimetableVersion.objects.filter(status='published').count() == 1
    assert TimetableVersion.objects.filter(status='archived').count() == 1


def test_concurrent_correction_decisions_apply_once(ready):
    s = ready
    a = enroll(s, 'Amina')
    body = {'school_class_id': str(s['klass'].pk), 'section_id': str(s['section'].pk), 'date': '2026-09-21', 'records': [{'student_id': str(a.pk), 'status': 'absent'}], 'submit': True}
    session = AttendanceService.take(body, access=s['access'])
    record = session.records.get()
    correction = AttendanceService.request_correction(record.pk, {'new_status': 'present', 'reason': 'Was present'}, access=s['access'])
    results = race(s['owner'], [(f'{API}attendance-corrections/{correction.pk}/approve/', {})] * 2)
    assert sorted(code for code, _ in results) == [200, 400], results
    record.refresh_from_db()
    assert record.status == 'present' and AttendanceCorrection.objects.filter(status='approved').count() == 1
