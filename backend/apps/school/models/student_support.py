"""Private attachments, document requirements, emergency contacts and notes."""
from django.db import models
from django.db.models import Q, F
from core.models.base import BaseModel
from .sis_identity import SchoolRecord, choices, ref


class SchoolFile(SchoolRecord):
    original_name = models.CharField(max_length=200)
    storage_key = models.CharField(max_length=200, unique=True)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)


class AdmissionDocumentType(BaseModel):
    tenant = ref('platform.Tenant')
    branch = ref('settings_app.Branch', optional=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    required = models.BooleanField(default=False)
    education_level = ref('school.EducationLevel', optional=True)
    school_class = ref('school.SchoolClass', optional=True)
    expiry_required = models.BooleanField(default=False)
    allowed_types = models.JSONField(default=list, blank=True)
    max_size_mb = models.PositiveSmallIntegerField(default=5)
    status = models.CharField(max_length=20, choices=choices('active inactive archived'), default='active')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tenant', 'code'], name='school_document_type_code'), models.CheckConstraint(condition=Q(max_size_mb__gte=1, max_size_mb__lte=10), name='school_document_size')]

    def __str__(self):
        return self.name


class SchoolDocument(SchoolRecord):
    document_type = ref(AdmissionDocumentType)
    file = ref(SchoolFile)
    document_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    verification_status = models.CharField(max_length=25, choices=choices('pending verified rejected expired requires_reupload'), default='pending')
    verified_by = ref('authentication.User', optional=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta(SchoolRecord.Meta):
        abstract = True
        constraints = [models.CheckConstraint(condition=Q(expiry_date__isnull=True) | Q(issue_date__isnull=True) | Q(expiry_date__gte=F('issue_date')), name='%(class)s_dates')]


class ApplicantDocument(SchoolDocument):
    application = ref('school.AdmissionApplication', related_name='documents')


class StudentDocument(SchoolDocument):
    student = ref('school.Student', related_name='documents')
    source_document = ref(ApplicantDocument, optional=True)
    category = models.CharField(max_length=20, choices=choices('admission identity academic transfer guardian administrative other'), default='other')

    class Meta(SchoolDocument.Meta):
        constraints = SchoolDocument.Meta.constraints + [models.UniqueConstraint(fields=['student', 'source_document'], condition=Q(source_document__isnull=False), name='school_converted_document')]


class EmergencyContact(SchoolRecord):
    student = ref('school.Student', related_name='emergency_contacts')
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50)
    alternative_phone = models.CharField(max_length=50, blank=True)
    priority = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True)


class StudentNote(SchoolRecord):
    student = ref('school.Student', related_name='student_notes')
    title = models.CharField(max_length=150)
    body = models.TextField()
    category = models.CharField(max_length=20, choices=choices('general academic administrative admission transfer confidential'), default='general')
