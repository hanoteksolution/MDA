"""Authoritative rules for staff assignments, timetable entries and periods.

Conflict detection is a pure function of two entries plus a time-overlap test, so
the same rules serve single-entry edits and the full re-check on publication.
"""
from django.db.models import Q
from apps.school.models import (Classroom, SchoolStaffProfile, TeacherAssignment, TimetablePeriod, TimetableVersion, TimetableEntry)
from apps.hr.models import Employee
from .sis_common import get, invalid

OPEN_YEAR = ('planning', 'active')


def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def window_overlaps(a_start, a_end, b_start, b_end):
    return (a_end is None or a_end >= b_start) and (b_end is None or b_end >= a_start)


def prepare(row, access):
    """Derive server-owned campus from the parent before generic validation."""
    if isinstance(row, TimetableEntry):
        row.branch = get(access, TimetableVersion, row.version_id, 'version_id').branch
    elif isinstance(row, TeacherAssignment):
        row.branch = get(access, SchoolStaffProfile, row.staff_id, 'staff_id').branch


def entry_conflict(a, b):
    """Message when two active entries of one version cannot coexist, else None."""
    if a.weekday != b.weekday or a.pk == b.pk:
        return None
    pa, pb = a.period, b.period
    if not overlaps(pa.start_time, pa.end_time, pb.start_time, pb.end_time):
        return None
    if a.staff_id and a.staff_id == b.staff_id:
        return 'The teacher is already teaching another class in an overlapping period.'
    if a.classroom_id and a.classroom_id == b.classroom_id:
        return 'The room is already booked in an overlapping period.'
    if a.school_class_id == b.school_class_id and (not a.section_id or not b.section_id or a.section_id == b.section_id):
        return 'The class or section already has a lesson in an overlapping period.'
    return None


def _entries(version):
    return TimetableEntry.objects.filter(version=version, status='active', deleted_at__isnull=True).select_related('period')


def check_entry(entry):
    """Full conflict check for one entry against its version and other campuses."""
    for other in _entries(entry.version).filter(weekday=entry.weekday).exclude(pk=entry.pk):
        message = entry_conflict(entry, other)
        if message:
            invalid('period_id', message)
    if entry.staff_id:
        version = entry.version
        # The same person may hold profiles on several campuses; never let them be in two rooms at once.
        elsewhere = TimetableEntry.objects.filter(tenant=entry.tenant, status='active', deleted_at__isnull=True, weekday=entry.weekday, staff__employee_id=entry.staff.employee_id, version__status='published', version__deleted_at__isnull=True).exclude(version__branch_id=version.branch_id).select_related('period', 'version')
        for other in elsewhere:
            if window_overlaps(version.effective_from, version.effective_to, other.version.effective_from, other.version.effective_to) and overlaps(entry.period.start_time, entry.period.end_time, other.period.start_time, other.period.end_time):
                invalid('staff_id', 'The teacher is scheduled at another campus in an overlapping period.')


def _assigned(entry):
    query = TeacherAssignment.objects.filter(staff=entry.staff, academic_year=entry.version.academic_year, school_class=entry.school_class, status='active', deleted_at__isnull=True)
    if entry.section_id:
        query = query.filter(Q(section__isnull=True) | Q(section_id=entry.section_id))
    query = query.filter(Q(subject_offering__isnull=True) | Q(subject_offering_id=entry.subject_offering_id))
    return query.exists()


def validate_ops(row, access):
    if isinstance(row, Employee):
        if row.user_id:
            if row.user.tenant_id != access.tenant.pk or not row.user.is_active or row.user.deleted_at:
                invalid('user_id', 'Choose an active login belonging to this organisation.')
        return
    if not isinstance(row, (Classroom, SchoolStaffProfile, TeacherAssignment, TimetablePeriod, TimetableVersion, TimetableEntry)):
        return  # SIS records keep their own (Phase 3) relation rules; e.g. campus-wide document types
    for field in row._meta.fields:
        related = getattr(row, field.name, None) if field.is_relation and field.related_model._meta.app_label in ('school',) else None
        if related is not None and getattr(related, 'branch_id', row.branch_id) != row.branch_id and field.name not in ('tenant',):
            invalid(field.attname, 'Related record belongs to another campus.')
    if isinstance(row, SchoolStaffProfile):
        if row.employee.status != 'active':
            invalid('employee_id', 'Choose an active employee.')
    elif isinstance(row, TeacherAssignment):
        year = row.academic_year
        if row.staff.status != 'active':
            invalid('staff_id', 'Choose active teaching staff.')
        if year.status not in OPEN_YEAR:
            invalid('academic_year_id', 'The academic year is closed.')
        if row.start_date < year.start_date or row.start_date > year.end_date or (row.end_date and row.end_date > year.end_date):
            invalid('start_date', 'The assignment must fall within the academic year.')
        if row.section_id and row.section.school_class_id != row.school_class_id:
            invalid('section_id', 'Section does not belong to the class.')
        offering = row.subject_offering
        if offering:
            if offering.academic_year_id != row.academic_year_id or offering.school_class_id != row.school_class_id or (offering.section_id and offering.section_id != row.section_id):
                invalid('subject_offering_id', 'The subject offering does not match the year, class and section.')
        if row.role == 'subject_teacher' and not offering:
            invalid('subject_offering_id', 'A subject teacher assignment needs a subject offering.')
        rivals = TeacherAssignment.objects.filter(tenant=row.tenant, academic_year=year, school_class=row.school_class, status='active', deleted_at__isnull=True).exclude(pk=row.pk)
        for other in rivals:
            same_scope = other.section_id == row.section_id and other.subject_offering_id == row.subject_offering_id
            if not window_overlaps(row.start_date, row.end_date, other.start_date, other.end_date):
                continue
            if row.status == 'active' and other.staff_id == row.staff_id and other.role == row.role and same_scope:
                invalid('staff_id', 'This assignment already exists for the period.')
            if row.status == 'active' and row.role == 'class_teacher' and other.role == 'class_teacher' and other.section_id == row.section_id:
                invalid('role', 'The class already has a class teacher for the period.')
    elif isinstance(row, TimetablePeriod):
        if row.shift_id and not (row.shift.start_time <= row.start_time and row.end_time <= row.shift.end_time):
            invalid('start_time', 'The period must fall within its shift.')
        for other in TimetablePeriod.objects.filter(tenant=row.tenant, branch=row.branch, shift_id=row.shift_id, status='active', deleted_at__isnull=True).exclude(pk=row.pk):
            if row.status == 'active' and overlaps(row.start_time, row.end_time, other.start_time, other.end_time):
                invalid('start_time', f'Overlaps the period "{other.name}".')
    elif isinstance(row, TimetableVersion):
        year = row.academic_year
        if year.status not in OPEN_YEAR:
            invalid('academic_year_id', 'The academic year is closed.')
        if row.effective_from < year.start_date or (row.effective_to and row.effective_to > year.end_date):
            invalid('effective_from', 'The timetable must fall within the academic year.')
        if not row._state.adding and row.status != 'draft':
            invalid('status', 'Only draft timetables can be edited; clone the version instead.')
    elif isinstance(row, TimetableEntry):
        version, period = row.version, row.period
        if version.status != 'draft':
            invalid('version_id', 'Only draft timetables can be edited; clone the published version instead.')
        if period.status != 'active' or period.is_break:
            invalid('period_id', 'Choose an active teaching period.')
        if row.section_id and row.section.school_class_id != row.school_class_id:
            invalid('section_id', 'Section does not belong to the class.')
        offering = row.subject_offering
        if offering.academic_year_id != version.academic_year_id or offering.school_class_id != row.school_class_id or (offering.section_id and offering.section_id != row.section_id) or offering.status != 'active':
            invalid('subject_offering_id', 'The subject offering must be active and match the timetable year, class and section.')
        if row.staff_id:
            if row.staff.status != 'active':
                invalid('staff_id', 'Choose active teaching staff.')
            if not _assigned(row):
                invalid('staff_id', 'The teacher has no active assignment for this class and subject.')
        if row.classroom_id and row.classroom.status != 'active':
            invalid('classroom_id', 'Choose an active room.')
        if row.status == 'active':
            check_entry(row)
            quota = TimetableEntry.objects.filter(version=version, subject_offering=offering, section_id=row.section_id, status='active', deleted_at__isnull=True).exclude(pk=row.pk).count()
            if quota + 1 > offering.weekly_periods:
                invalid('subject_offering_id', f'The subject is limited to {offering.weekly_periods} weekly period(s) for this class.')
            if row.staff_id and row.staff.max_weekly_periods:
                load = TimetableEntry.objects.filter(version=version, staff=row.staff, status='active', deleted_at__isnull=True).exclude(pk=row.pk).count()
                if load + 1 > row.staff.max_weekly_periods:
                    invalid('staff_id', f'The teacher is limited to {row.staff.max_weekly_periods} weekly period(s).')


def can_archive_ops(row):
    if isinstance(row, TimetableEntry) and row.version.status != 'draft':
        invalid('status', 'Only draft timetables can be edited; clone the published version instead.')
    if isinstance(row, TimetableVersion) and row.status == 'published':
        invalid('status', 'Publish a replacement version instead of archiving the live timetable.')
