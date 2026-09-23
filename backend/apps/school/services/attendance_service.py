"""Daily/period attendance with locked submission and audited corrections."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from apps.school.models import (AcademicYear, AttendanceSession, AttendanceRecord, AttendanceCorrection, SchoolClass, Section,
                                StudentEnrollment, SubjectOffering, TeacherAssignment, TimetablePeriod)
from apps.school.models.academic_ops import ATTENDANCE_STATUS
from apps.school.serializers.sis import serialize
from .sis_common import get, invalid, lock, persist, event, reason, date_value

STATUSES = ATTENDANCE_STATUS.split()


def roster(access, school_class, section, day):
    """Enrollments that place a student in the class/section on `day`."""
    query = StudentEnrollment.objects.filter(tenant=access.tenant, branch=school_class.branch, school_class=school_class, deleted_at__isnull=True, start_date__lte=day, student__deleted_at__isnull=True) \
        .exclude(status__in=('pending', 'cancelled')).filter(Q(end_date__isnull=True) | Q(end_date__gte=day)).select_related('student')
    if section:
        query = query.filter(section=section)
    return query.order_by('roll_number', 'student__first_name', 'id')


def _year(access, school_class, day):
    year = AcademicYear.objects.filter(tenant=access.tenant, branch=school_class.branch, deleted_at__isnull=True, status='active', start_date__lte=day, end_date__gte=day).first()
    if not year:
        invalid('date', 'The date does not belong to an active academic year for this campus.')
    return year


def _authorize(access, school_class, section, offering, day, mode):
    """`take_any` covers the campus; `take` is limited to the user's own assignments."""
    if access.allows('attendance', 'take_any'):
        return
    access.require('attendance', 'take')
    if mode == 'period' and not offering:
        invalid('subject_offering_id', 'Choose the subject you are teaching.')
    query = TeacherAssignment.objects.filter(tenant=access.tenant, school_class=school_class, status='active', deleted_at__isnull=True, staff__deleted_at__isnull=True,
                                             staff__status='active', staff__employee__user=access.user, staff__employee__status='active', start_date__lte=day).filter(Q(end_date__isnull=True) | Q(end_date__gte=day))
    if section:
        query = query.filter(Q(section__isnull=True) | Q(section=section))
    if mode == 'daily':
        query = query.filter(role='class_teacher')
    elif offering:
        query = query.filter(Q(subject_offering__isnull=True) | Q(subject_offering=offering))
    if not query.exists():
        raise PermissionDenied('You are not assigned to take attendance for this class.')


def _slot(access, data):
    school_class = get(access, SchoolClass, data.get('school_class_id'), 'school_class_id')
    if school_class.status != 'active':
        invalid('school_class_id', 'Choose an active class.')
    section = get(access, Section, data['section_id'], 'section_id') if data.get('section_id') else None
    if section and section.school_class_id != school_class.pk:
        invalid('section_id', 'Section does not belong to the class.')
    day = date_value(data, 'date', timezone.localdate().isoformat())
    if day > timezone.localdate():
        invalid('date', 'Attendance cannot be recorded for a future date.')
    mode = data.get('mode', 'daily')
    if mode not in ('daily', 'period'):
        invalid('mode', 'Choose daily or period attendance.')
    period = offering = None
    if mode == 'period':
        period = get(access, TimetablePeriod, data.get('period_id'), 'period_id')
        if period.branch_id != school_class.branch_id or period.status != 'active' or period.is_break:
            invalid('period_id', 'Choose an active teaching period of this campus.')
        if data.get('subject_offering_id'):
            offering = get(access, SubjectOffering, data['subject_offering_id'], 'subject_offering_id')
            if offering.school_class_id != school_class.pk or (offering.section_id and offering.section_id != (section.pk if section else None)):
                invalid('subject_offering_id', 'The subject offering does not match the class and section.')
    elif data.get('period_id') or data.get('subject_offering_id'):
        invalid('mode', 'Period and subject apply only to period attendance.')
    return school_class, section, day, mode, period, offering


def find_session(access, school_class, section, day, mode, period):
    return AttendanceSession.objects.filter(tenant=access.tenant, branch=school_class.branch, school_class=school_class, section=section, date=day, mode=mode, period=period, deleted_at__isnull=True).first()


def roster_view(access, params):
    school_class, section, day, mode, period, offering = _slot(access, params)
    if not (access.allows('attendance', 'view') or access.allows('attendance', 'take') or access.allows('attendance', 'take_any')):
        access.require('attendance', 'view')
    if not access.allows('attendance', 'view'):
        _authorize(access, school_class, section, offering, day, mode)
    session = find_session(access, school_class, section, day, mode, period)
    marks = {r.student_id: r for r in session.records.filter(deleted_at__isnull=True)} if session else {}
    rows = []
    for enrollment in roster(access, school_class, section, day):
        mark = marks.get(enrollment.student_id)
        rows.append({'student_id': str(enrollment.student_id), 'enrollment_id': str(enrollment.pk), 'student_name': str(enrollment.student), 'roll_number': enrollment.roll_number, 'record_id': str(mark.pk) if mark else None, 'status': mark.status if mark else None, 'remarks': mark.remarks if mark else ''})
    return {'session': serialize(session) if session else None, 'students': rows}


class AttendanceService:
    @staticmethod
    @transaction.atomic
    def take(data, *, access):
        lock(access)
        school_class, section, day, mode, period, offering = _slot(access, data)
        _authorize(access, school_class, section, offering, day, mode)
        year = _year(access, school_class, day)
        session = find_session(access, school_class, section, day, mode, period)
        if session and session.status == 'submitted':
            invalid('status', 'Submitted attendance is locked; request a correction for a mistake.')
        marks = data.get('records')
        if not isinstance(marks, list) or not marks:
            invalid('records', 'Mark at least one student.')
        eligible = {str(e.student_id): e for e in roster(access, school_class, section, day)}
        seen = {}
        for item in marks:
            if not isinstance(item, dict):
                invalid('records', 'Each mark must be an object.')
            student_id = str(item.get('student_id'))
            enrollment = eligible.get(student_id)
            if not enrollment:
                invalid('records', 'A student is not enrolled in this class on that date.')
            if student_id in seen:
                invalid('records', 'A student was marked twice.')
            if item.get('status') not in STATUSES:
                invalid('records', f'Status must be one of: {", ".join(STATUSES)}.')
            seen[student_id] = (enrollment, item)
        submit = bool(data.get('submit'))
        if submit and len(seen) != len(eligible):
            invalid('records', f'Mark every student before submitting ({len(eligible) - len(seen)} unmarked).')
        created = session is None
        if created:
            session = AttendanceSession(tenant=access.tenant, branch=school_class.branch, academic_year=year, school_class=school_class, section=section, date=day, mode=mode, period=period, subject_offering=offering, taken_by=access.user, notes=str(data.get('notes', ''))[:500])
            persist(session, access, 'attendance_session_created')
        existing = {str(r.student_id): r for r in session.records.filter(deleted_at__isnull=True).select_for_update()}
        changed = 0
        for student_id, (enrollment, item) in seen.items():
            row = existing.get(student_id) or AttendanceRecord(tenant=access.tenant, branch=session.branch, session=session, student=enrollment.student, enrollment=enrollment)
            remarks = str(item.get('remarks', ''))[:255]
            if not row._state.adding and row.status == item['status'] and row.remarks == remarks:
                continue
            row.status, row.remarks = item['status'], remarks
            row.created_by = row.created_by or access.user
            row.updated_by = access.user
            row.full_clean(); row.save()
            changed += 1
        counts = {s: session.records.filter(status=s, deleted_at__isnull=True).count() for s in STATUSES}
        if submit:
            session.status, session.submitted_at = 'submitted', timezone.now()
            persist(session, access, 'attendance_submitted')
        event(session, access, 'attendance_saved', submitted=submit, records_changed=changed, counts=counts, session_date=day.isoformat(), mode=mode)
        return session

    @staticmethod
    @transaction.atomic
    def submit(pk, *, access):
        lock(access)
        session = get(access, AttendanceSession, pk)
        _authorize(access, session.school_class, session.section, session.subject_offering, session.date, session.mode)
        if session.status != 'open':
            invalid('status', 'Attendance was already submitted.')
        expected = roster(access, session.school_class, session.section, session.date).count()
        if session.records.filter(deleted_at__isnull=True).count() < expected:
            invalid('records', 'Mark every student before submitting.')
        before = serialize(session, audit=True)
        session.status, session.submitted_at = 'submitted', timezone.now()
        return persist(session, access, 'attendance_submitted', before)

    @staticmethod
    @transaction.atomic
    def request_correction(pk, data, *, access):
        access.require('attendance_correction', 'request'); lock(access)
        record = get(access, AttendanceRecord, pk)
        session = record.session
        _authorize(access, session.school_class, session.section, session.subject_offering, session.date, session.mode)
        if session.status != 'submitted':
            invalid('status', 'The attendance is still open; edit it directly.')
        new_status = data.get('new_status')
        if new_status not in STATUSES:
            invalid('new_status', f'Status must be one of: {", ".join(STATUSES)}.')
        if new_status == record.status:
            invalid('new_status', 'The requested status matches the current status.')
        if AttendanceCorrection.objects.filter(record=record, status='pending', deleted_at__isnull=True).exists():
            invalid('status', 'A correction is already pending for this record.')
        row = AttendanceCorrection(tenant=access.tenant, branch=record.branch, record=record, old_status=record.status, new_status=new_status, reason=reason(data), requested_by=access.user)
        return persist(row, access, 'attendance_correction_requested')

    @staticmethod
    @transaction.atomic
    def decide(pk, approve, data, *, access):
        access.require('attendance_correction', 'approve'); lock(access)
        correction = get(access, AttendanceCorrection, pk)
        if correction.status != 'pending':
            invalid('status', 'This correction was already decided.')
        note = str(data.get('decision_note', '')).strip()
        if not approve and not note:
            invalid('decision_note', 'Explain why the correction is rejected.')
        before = serialize(correction, audit=True)
        correction.status, correction.decided_by, correction.decided_at, correction.decision_note = ('approved' if approve else 'rejected'), access.user, timezone.now(), note
        if approve:
            record = AttendanceRecord.objects.select_for_update().get(pk=correction.record_id)
            if record.status != correction.old_status:
                invalid('status', 'The record changed after this request; reject it and request again.')
            record_before = serialize(record, audit=True)
            record.status, record.updated_by = correction.new_status, access.user
            record.save(update_fields=['status', 'updated_by', 'updated_at'])
            event(record, access, 'attendance_corrected', old_values=record_before, correction_id=str(correction.pk), old_status=correction.old_status, new_status=correction.new_status, reason=correction.reason)
        return persist(correction, access, 'attendance_correction_approved' if approve else 'attendance_correction_rejected', before)
