"""Applications are independent of applicant identity and controlled by workflows."""
from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from .sis_identity import SchoolRecord, choices, ref

APPLICATION_STATES = 'draft submitted document_review assessment_pending assessment_completed interview_pending interview_completed under_review accepted waitlisted rejected withdrawn enrolled cancelled'


class AdmissionApplication(SchoolRecord):
    number = models.CharField(max_length=60)
    applicant = ref('school.Applicant', related_name='applications')
    academic_year = ref('school.AcademicYear', related_name='admission_applications')
    school_class = ref('school.SchoolClass', related_name='admission_applications')
    section = ref('school.Section', optional=True, related_name='admission_applications')
    application_date = models.DateField(default=timezone.localdate)
    application_type = models.CharField(max_length=20, choices=choices('new transfer returning'), default='new')
    previous_school = models.CharField(max_length=150, blank=True)
    previous_result = models.TextField(blank=True)
    transfer_student = models.BooleanField(default=False)
    boarding_mode = models.CharField(max_length=20, choices=choices('day boarding unspecified'), default='unspecified')
    transport_required = models.BooleanField(default=False)
    program_interest = models.CharField(max_length=150, blank=True)
    fee_status = models.CharField(max_length=20, choices=choices('not_applicable pending recorded waived'), default='not_applicable')
    status = models.CharField(max_length=30, choices=choices(APPLICATION_STATES), default='draft')
    submitted_by = ref('authentication.User', optional=True)
    assigned_reviewer = ref('authentication.User', optional=True)
    notes = models.TextField(blank=True)
    student = ref('school.Student', optional=True)

    class Meta(SchoolRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'number'], name='school_application_number')]
        indexes = [models.Index(fields=['tenant', 'branch', 'status']), models.Index(fields=['tenant', 'academic_year', 'school_class'])]

    def __str__(self):
        return self.number


class AdmissionDecision(SchoolRecord):
    application = ref(AdmissionApplication, related_name='decisions')
    decision = models.CharField(max_length=20, choices=choices('accepted waitlisted rejected'))
    decision_date = models.DateField(default=timezone.localdate)
    decided_by = ref('authentication.User')
    reason = models.TextField()
    conditions = models.TextField(blank=True)
    offer_expiry = models.DateField(null=True, blank=True)
    approved_class = ref('school.SchoolClass')
    approved_section = ref('school.Section', optional=True)
    notes = models.TextField(blank=True)
    document_override_reason = models.TextField(blank=True)


class AdmissionAssessment(SchoolRecord):
    application = ref(AdmissionApplication, related_name='assessments')
    assessment_type = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    location = models.CharField(max_length=150, blank=True)
    assessor = ref('authentication.User')
    maximum_score = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    result = models.CharField(max_length=20, choices=choices('pass fail review not_required'), default='review')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=choices('scheduled completed cancelled'), default='scheduled')

    class Meta(SchoolRecord.Meta):
        constraints = [models.CheckConstraint(condition=Q(maximum_score__gt=0) & (Q(score__isnull=True) | Q(score__gte=0, score__lte=F('maximum_score'))), name='school_assessment_scores')]


class AdmissionInterview(SchoolRecord):
    application = ref(AdmissionApplication, related_name='interviews')
    date = models.DateField()
    start_time = models.TimeField()
    interviewer = ref('authentication.User')
    applicant_present = models.BooleanField(default=False)
    guardian_present = models.BooleanField(default=False)
    location = models.CharField(max_length=150, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    recommendation = models.CharField(max_length=20, choices=choices('accept reject review'), default='review')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=choices('scheduled completed no_show cancelled rescheduled'), default='scheduled')

    class Meta(SchoolRecord.Meta):
        constraints = [models.CheckConstraint(condition=Q(score__isnull=True) | Q(score__gte=0), name='school_interview_score')]


class SchoolAdmissionPolicy(SchoolRecord):
    require_guardian = models.BooleanField(default=True)
    require_family = models.BooleanField(default=False)
    capacity_policy = models.CharField(max_length=30, choices=choices('warn_only block allow_with_override'), default='block')
    student_prefix = models.CharField(max_length=40, default='STU-{year}-')
    student_padding = models.PositiveSmallIntegerField(default=6)
    number_scope = models.CharField(max_length=20, choices=choices('tenant campus year campus_year'), default='tenant')

    class Meta(SchoolRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'branch'], name='school_admission_policy'), models.CheckConstraint(condition=Q(student_padding__gte=1, student_padding__lte=12), name='school_student_padding')]


class SchoolSequence(SchoolRecord):
    kind = models.CharField(max_length=30)
    scope_key = models.CharField(max_length=100)
    last_value = models.PositiveBigIntegerField(default=0)

    class Meta(SchoolRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'kind', 'scope_key'], name='school_identity_sequence')]
