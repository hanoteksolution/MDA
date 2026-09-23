"""Teaching staff, conflict-safe timetable and daily/period attendance.

Employee identity is the shared ``hr.Employee``; School only adds a campus-scoped
extension (`SchoolStaffProfile`) and effective-dated assignments. Attendance rows
are locked after submission and change only through audited corrections.
"""
from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from .sis_identity import SchoolRecord, choices, ref

WEEKDAYS = [(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')]
LIVE = Q(deleted_at__isnull=True)


class Classroom(SchoolRecord):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(default=30)
    room_type = models.CharField(max_length=20, choices=choices('classroom laboratory hall library other'), default='classroom')
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(SchoolRecord.Meta):
        ordering = ['name', 'id']
        constraints = [models.UniqueConstraint(fields=['tenant', 'branch', 'code'], name='school_classroom_code'), models.CheckConstraint(condition=Q(capacity__gt=0), name='school_classroom_capacity')]

    def __str__(self):
        return self.name


class SchoolStaffProfile(SchoolRecord):
    employee = ref('hr.Employee', related_name='school_profiles')
    staff_type = models.CharField(max_length=30, choices=choices('teacher head_of_department counselor support'), default='teacher')
    qualification = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    max_weekly_periods = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(SchoolRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'branch', 'employee'], condition=LIVE, name='school_staff_profile_once')]

    @property
    def name(self):
        return self.employee.name

    def __str__(self):
        return self.employee.name


class TeacherAssignment(SchoolRecord):
    staff = ref(SchoolStaffProfile, related_name='assignments')
    academic_year = ref('school.AcademicYear', related_name='teacher_assignments')
    school_class = ref('school.SchoolClass', related_name='teacher_assignments')
    section = ref('school.Section', optional=True, related_name='teacher_assignments')
    subject_offering = ref('school.SubjectOffering', optional=True, related_name='teacher_assignments')
    role = models.CharField(max_length=20, choices=choices('subject_teacher class_teacher assistant'), default='subject_teacher')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')
    notes = models.TextField(blank=True)

    class Meta(SchoolRecord.Meta):
        constraints = [models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')), name='school_assignment_dates')]
        indexes = [models.Index(fields=['tenant', 'branch', 'academic_year', 'status'])]

    @property
    def name(self):
        return f'{self.staff} — {self.school_class}'

    def __str__(self):
        return self.name


class TimetablePeriod(SchoolRecord):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    shift = ref('school.SchoolShift', optional=True, related_name='periods')
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(SchoolRecord.Meta):
        ordering = ['start_time', 'id']
        constraints = [models.UniqueConstraint(fields=['tenant', 'branch', 'code'], name='school_period_code'), models.CheckConstraint(condition=Q(end_time__gt=F('start_time')), name='school_period_times')]

    def __str__(self):
        return self.name


class TimetableVersion(SchoolRecord):
    academic_year = ref('school.AcademicYear', related_name='timetable_versions')
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=choices('draft published archived'), default='draft')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = ref('authentication.User', optional=True)
    notes = models.TextField(blank=True)

    class Meta(SchoolRecord.Meta):
        constraints = [
            models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gte=F('effective_from')), name='school_timetable_dates'),
            models.UniqueConstraint(fields=['tenant', 'branch', 'academic_year'], condition=Q(status='published', deleted_at__isnull=True), name='school_one_published_timetable'),
        ]

    def __str__(self):
        return self.name


def _entry_unique(name, fields, condition):
    return models.UniqueConstraint(fields=['version', 'weekday', 'period', *fields], condition=condition & Q(status='active') & LIVE, name=name)


class TimetableEntry(SchoolRecord):
    version = ref(TimetableVersion, related_name='entries')
    period = ref(TimetablePeriod, related_name='entries')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    school_class = ref('school.SchoolClass', related_name='timetable_entries')
    section = ref('school.Section', optional=True, related_name='timetable_entries')
    subject_offering = ref('school.SubjectOffering', related_name='timetable_entries')
    staff = ref(SchoolStaffProfile, optional=True, related_name='timetable_entries')
    classroom = ref(Classroom, optional=True, related_name='timetable_entries')
    status = models.CharField(max_length=20, choices=choices('active inactive'), default='active')

    class Meta(SchoolRecord.Meta):
        ordering = ['weekday', 'period__start_time', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(weekday__gte=1, weekday__lte=7), name='school_entry_weekday'),
            # Exact-slot guards hold on every database; class-wide vs section overlap and
            # time-overlapping periods are enforced by the service under the tenant lock.
            _entry_unique('school_entry_teacher_slot', ['staff'], Q(staff__isnull=False)),
            _entry_unique('school_entry_room_slot', ['classroom'], Q(classroom__isnull=False)),
            _entry_unique('school_entry_section_slot', ['school_class', 'section'], Q(section__isnull=False)),
            _entry_unique('school_entry_class_slot', ['school_class'], Q(section__isnull=True)),
        ]
        indexes = [models.Index(fields=['version', 'weekday', 'period'])]

    @property
    def name(self):
        return f'{self.school_class} {self.get_weekday_display()} {self.period}'

    def __str__(self):
        return self.name


ATTENDANCE_STATUS = 'present absent late excused half_day'


class AttendanceSession(SchoolRecord):
    academic_year = ref('school.AcademicYear', related_name='attendance_sessions')
    school_class = ref('school.SchoolClass', related_name='attendance_sessions')
    section = ref('school.Section', optional=True, related_name='attendance_sessions')
    date = models.DateField(default=timezone.localdate)
    mode = models.CharField(max_length=10, choices=choices('daily period'), default='daily')
    period = ref(TimetablePeriod, optional=True, related_name='attendance_sessions')
    subject_offering = ref('school.SubjectOffering', optional=True, related_name='attendance_sessions')
    status = models.CharField(max_length=20, choices=choices('open submitted'), default='open')
    taken_by = ref('authentication.User', related_name='school_attendance_sessions')
    submitted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta(SchoolRecord.Meta):
        ordering = ['-date', 'id']
        constraints = [
            models.CheckConstraint(condition=(Q(mode='daily', period__isnull=True) | Q(mode='period', period__isnull=False)), name='school_attendance_mode'),
            *[models.UniqueConstraint(fields=['tenant', 'branch', 'school_class', 'date'] + (['section'] if s else []) + (['period'] if p else []), condition=Q(mode='period' if p else 'daily', section__isnull=not s, deleted_at__isnull=True), name=f'school_attendance_slot_{int(p)}{int(s)}') for p in (False, True) for s in (False, True)],
        ]
        indexes = [models.Index(fields=['tenant', 'branch', 'date', 'status'])]

    @property
    def name(self):
        return f'{self.school_class} {self.date}'

    def __str__(self):
        return self.name


class AttendanceRecord(SchoolRecord):
    session = ref(AttendanceSession, related_name='records')
    student = ref('school.Student', related_name='attendance_records')
    enrollment = ref('school.StudentEnrollment', related_name='attendance_records')
    status = models.CharField(max_length=20, choices=choices(ATTENDANCE_STATUS), default='present')
    remarks = models.CharField(max_length=255, blank=True)

    class Meta(SchoolRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['session', 'student'], condition=LIVE, name='school_attendance_student_once')]
        indexes = [models.Index(fields=['student', 'status'])]

    @property
    def name(self):
        return f'{self.student} — {self.status}'

    def __str__(self):
        return self.name


class AttendanceCorrection(SchoolRecord):
    record = ref(AttendanceRecord, related_name='corrections')
    old_status = models.CharField(max_length=20, choices=choices(ATTENDANCE_STATUS))
    new_status = models.CharField(max_length=20, choices=choices(ATTENDANCE_STATUS))
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=choices('pending approved rejected'), default='pending')
    requested_by = ref('authentication.User', related_name='school_attendance_corrections')
    decided_by = ref('authentication.User', optional=True, related_name='school_attendance_decisions')
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta(SchoolRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=['record'], condition=Q(status='pending', deleted_at__isnull=True), name='school_one_pending_correction'),
            models.CheckConstraint(condition=~Q(old_status=F('new_status')), name='school_correction_changes_status'),
        ]

    @property
    def name(self):
        return f'{self.record} → {self.new_status}'

    def __str__(self):
        return self.name
