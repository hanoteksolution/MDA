"""Long-lived student, prospective identity and shared household contacts."""
from django.db import models
from django.db.models import Q, F
from core.models.base import BaseModel


def choices(values):
    return [(value, value.replace('_', ' ').title()) for value in values.split()]


def ref(model, *, optional=False, related_name='+', one=False):
    field = models.OneToOneField if one else models.ForeignKey
    return field(model, on_delete=models.PROTECT, null=optional, blank=optional, related_name=related_name)


class SchoolRecord(BaseModel):
    tenant = ref('platform.Tenant')
    branch = ref('settings_app.Branch')

    class Meta:
        abstract = True
        ordering = ['-created_at', 'id']


class SchoolPerson(SchoolRecord):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=30, default='en')

    class Meta(SchoolRecord.Meta):
        abstract = True

    def __str__(self):
        return ' '.join(filter(None, [self.first_name, self.middle_name, self.last_name]))


class Family(SchoolRecord):
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=150)
    primary_guardian = ref('school.Guardian', optional=True)
    secondary_guardian = ref('school.Guardian', optional=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    language = models.CharField(max_length=30, default='en')
    communication_preference = models.CharField(max_length=20, choices=choices('phone email none'), default='phone')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(SchoolRecord.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'code'], name='school_family_code')]

    def __str__(self):
        return self.name


class Guardian(SchoolPerson):
    number = models.CharField(max_length=60)
    secondary_phone = models.CharField(max_length=50, blank=True)
    national_id = models.CharField(max_length=100, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=150, blank=True)
    portal_eligible = models.BooleanField(default=False)
    financially_responsible = models.BooleanField(default=False)
    emergency_contact = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(SchoolPerson.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'number'], name='school_guardian_number')]
        indexes = [models.Index(fields=['tenant', 'phone']), models.Index(fields=['tenant', 'email'])]


class ChildIdentity(SchoolPerson):
    gender = models.CharField(max_length=20, choices=choices('unspecified female male other'), default='unspecified')
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=150, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    photo = ref('school.SchoolFile', optional=True)
    family = ref(Family, optional=True, related_name='%(class)s_records')
    notes = models.TextField(blank=True)

    class Meta(SchoolPerson.Meta):
        abstract = True


class Applicant(ChildIdentity):
    number = models.CharField(max_length=60)
    previous_school = models.CharField(max_length=150, blank=True)
    previous_grade = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=100, blank=True)
    referral_source = models.CharField(max_length=150, blank=True)
    desired_year = ref('school.AcademicYear', optional=True)
    desired_class = ref('school.SchoolClass', optional=True)
    desired_section = ref('school.Section', optional=True)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(ChildIdentity.Meta):
        constraints = [models.UniqueConstraint(fields=['tenant', 'number'], name='school_applicant_number')]
        indexes = [models.Index(fields=['tenant', 'branch', 'status'])]


class Student(ChildIdentity):
    number = models.CharField(max_length=60)
    admission_number = models.CharField(max_length=60, blank=True)
    admission_date = models.DateField()
    applicant = ref(Applicant, optional=True, one=True, related_name='student')
    original_application = ref('school.AdmissionApplication', optional=True, one=True)
    status = models.CharField(max_length=20, choices=choices('active suspended transferred withdrawn graduated alumni inactive archived'), default='active')

    class Meta(ChildIdentity.Meta):
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'number'], name='school_student_number'),
            models.UniqueConstraint(fields=['tenant', 'admission_number'], condition=~Q(admission_number=''), name='school_admission_number'),
        ]
        indexes = [models.Index(fields=['tenant', 'branch', 'status']), models.Index(fields=['tenant', 'last_name', 'date_of_birth'])]


class RelationshipType(BaseModel):
    tenant = ref('platform.Tenant')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tenant', 'code'], name='school_relationship_code')]

    def __str__(self):
        return self.name


class GuardianRelationship(SchoolRecord):
    guardian = ref(Guardian, related_name='%(class)s_records')
    relationship = ref(RelationshipType)
    is_primary = models.BooleanField(default=False)
    lives_with_student = models.BooleanField(default=False)
    financially_responsible = models.BooleanField(default=False)
    emergency_contact = models.BooleanField(default=False)
    pickup_authorized = models.BooleanField(default=False)
    receives_academic = models.BooleanField(default=True)
    receives_finance = models.BooleanField(default=False)
    receives_attendance = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta(SchoolRecord.Meta):
        abstract = True
        constraints = [models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')), name='%(class)s_dates')]


class StudentGuardian(GuardianRelationship):
    student = ref(Student, related_name='guardian_links')

    class Meta(GuardianRelationship.Meta):
        constraints = GuardianRelationship.Meta.constraints + [
            models.UniqueConstraint(fields=['student', 'guardian'], name='school_student_guardian'),
            models.UniqueConstraint(fields=['student'], condition=Q(is_primary=True, status='active', deleted_at__isnull=True), name='school_primary_guardian'),
        ]


class ApplicantGuardian(GuardianRelationship):
    applicant = ref(Applicant, related_name='guardian_links')

    class Meta(GuardianRelationship.Meta):
        constraints = GuardianRelationship.Meta.constraints + [
            models.UniqueConstraint(fields=['applicant', 'guardian'], name='school_applicant_guardian'),
            models.UniqueConstraint(fields=['applicant'], condition=Q(is_primary=True, status='active', deleted_at__isnull=True), name='school_applicant_primary_guardian'),
        ]
