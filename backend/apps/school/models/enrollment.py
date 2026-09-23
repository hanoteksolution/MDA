"""Placement history and immutable administrative lifecycle records."""
from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from .sis_identity import SchoolRecord, choices, ref


class StudentEnrollment(SchoolRecord):
    student = ref('school.Student', related_name='enrollments')
    academic_year = ref('school.AcademicYear', related_name='student_enrollments')
    term = ref('school.AcademicTerm', optional=True, related_name='student_enrollments')
    school_class = ref('school.SchoolClass', related_name='student_enrollments')
    section = ref('school.Section', optional=True, related_name='student_enrollments')
    roll_number = models.CharField(max_length=40, blank=True)
    enrollment_type = models.CharField(max_length=20, choices=choices('admission direct transfer reenrollment promotion repetition'), default='direct')
    enrollment_date = models.DateField(default=timezone.localdate)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=choices('pending active completed transferred withdrawn repeated promoted graduated cancelled'), default='active')
    promoted_from = ref('self', optional=True)
    transferred_from = ref('self', optional=True)
    notes = models.TextField(blank=True)

    class Meta(SchoolRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=['student'], condition=Q(status='active', deleted_at__isnull=True), name='school_one_active_enrollment'),
            models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')), name='school_enrollment_dates'),
            models.UniqueConstraint(fields=['tenant', 'academic_year', 'branch', 'school_class', 'section', 'roll_number'], condition=~Q(roll_number='') & Q(status='active', section__isnull=False, deleted_at__isnull=True), name='school_roll_section'),
            models.UniqueConstraint(fields=['tenant', 'academic_year', 'branch', 'school_class', 'roll_number'], condition=~Q(roll_number='') & Q(status='active', section__isnull=True, deleted_at__isnull=True), name='school_roll_class'),
        ]
        indexes = [models.Index(fields=['tenant', 'branch', 'academic_year', 'status']), models.Index(fields=['student', 'status', 'start_date'])]

    def __str__(self):
        return f'{self.student} — {self.academic_year}'


class StudentTransition(SchoolRecord):
    student = ref('school.Student', related_name='transitions')
    from_enrollment = ref(StudentEnrollment, optional=True)
    to_enrollment = ref(StudentEnrollment, optional=True)
    outcome = models.CharField(max_length=20, choices=choices('transferred withdrawn reenrolled promoted repeated graduated suspended reactivated alumni inactive'))
    effective_date = models.DateField()
    reason = models.TextField()
    destination_school = models.CharField(max_length=150, blank=True)
    certificate_status = models.CharField(max_length=20, choices=choices('not_required required issued'), default='not_required')
    requested_by = ref('authentication.User')
    approved_by = ref('authentication.User')
    notes = models.TextField(blank=True)
