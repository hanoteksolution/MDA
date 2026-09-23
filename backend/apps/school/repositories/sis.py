"""Scoped, bounded student lifecycle queries and current-placement annotations."""
from django.db.models import Q, OuterRef, Subquery, Count
from django.utils import timezone
from apps.school.models import (
    Applicant, AdmissionApplication, AdmissionAssessment, AdmissionInterview, AdmissionDecision,
    AdmissionDocumentType, ApplicantDocument, Student, Family, Guardian, RelationshipType,
    StudentGuardian, ApplicantGuardian, StudentEnrollment, StudentTransition, StudentDocument,
    EmergencyContact, StudentNote, SchoolAdmissionPolicy,
    Classroom, SchoolStaffProfile, TeacherAssignment, TimetablePeriod, TimetableVersion, TimetableEntry,
    AttendanceSession, AttendanceRecord, AttendanceCorrection,
)
from apps.hr.models import Employee
from apps.school.policies.access import SchoolAccess

MODELS = dict(zip(
    ['applicants','applications','assessments','interviews','decisions','document-types','applicant-documents',
     'students','families','guardians','relationship-types','student-guardians','applicant-guardians',
     'enrollments','transitions','student-documents','emergency-contacts','notes','admission-policies'],
    [Applicant,AdmissionApplication,AdmissionAssessment,AdmissionInterview,AdmissionDecision,AdmissionDocumentType,
     ApplicantDocument,Student,Family,Guardian,RelationshipType,StudentGuardian,ApplicantGuardian,StudentEnrollment,
     StudentTransition,StudentDocument,EmergencyContact,StudentNote,SchoolAdmissionPolicy]))

MODELS.update({'employees': Employee, 'staff-profiles': SchoolStaffProfile, 'teacher-assignments': TeacherAssignment, 'classrooms': Classroom, 'periods': TimetablePeriod, 'timetable-versions': TimetableVersion, 'timetable-entries': TimetableEntry, 'attendance-sessions': AttendanceSession, 'attendance-records': AttendanceRecord, 'attendance-corrections': AttendanceCorrection})

from apps.school.learning_contracts import MODELS as LEARNING_MODELS
MODELS.update(LEARNING_MODELS)

from apps.school.fee_contracts import MODELS as FEE_MODELS
MODELS.update(FEE_MODELS)

class StudentAccess(SchoolAccess):
    def scope(self, qs, *, include_inactive=False):
        qs = qs.filter(tenant=self.tenant)
        campuses = self.campuses(include_inactive=include_inactive).values('pk')
        if qs.model is Family:
            return qs.filter(Q(branch_id__in=campuses) | Q(student_records__branch_id__in=campuses, student_records__deleted_at__isnull=True) | Q(applicant_records__branch_id__in=campuses, applicant_records__deleted_at__isnull=True)).distinct()
        if qs.model is Guardian:
            return qs.filter(Q(branch_id__in=campuses) | Q(studentguardian_records__student__branch_id__in=campuses, studentguardian_records__deleted_at__isnull=True, studentguardian_records__status='active', studentguardian_records__student__deleted_at__isnull=True) | Q(applicantguardian_records__applicant__branch_id__in=campuses, applicantguardian_records__deleted_at__isnull=True, applicantguardian_records__status='active', applicantguardian_records__applicant__deleted_at__isnull=True)).distinct()
        if qs.model is AdmissionDocumentType:
            return qs.filter(Q(branch__isnull=True) | Q(branch_id__in=campuses))
        if qs.model is StudentNote and not self.allows('student_note_confidential', 'view'):
            qs = qs.exclude(category='confidential')
        qs=super().scope(qs, include_inactive=include_inactive)
        from apps.sales.models import Invoice
        if qs.model is Invoice:qs=qs.filter(service_billing__source_module='school')
        if qs.model in LEARNING_MODELS.values():
            from .learning import scope
            qs=scope(qs,self)
        return qs


def current_enrollments():
    today = timezone.localdate()
    return StudentEnrollment.objects.filter(status='active', deleted_at__isnull=True, academic_year__status='active', academic_year__deleted_at__isnull=True, start_date__lte=today).filter(Q(end_date__isnull=True) | Q(end_date__gte=today)).filter(academic_year__start_date__lte=today, academic_year__end_date__gte=today)


def queryset(resource, access, *, archived=False):
    model = MODELS[resource]
    qs = access.scope(model.objects.all()).filter(deleted_at__isnull=not archived)
    relations = [f.name for f in model._meta.fields if f.is_relation and f.name not in ('tenant','created_by','updated_by','deleted_by','file','photo')]
    qs = qs.select_related(*relations)
    if model is Student:
        current = current_enrollments().filter(student=OuterRef('pk')).order_by('id')
        for label, field in {'current_enrollment_id':'pk','current_class':'school_class__name','current_section':'section__name','current_year':'academic_year__name'}.items():
            qs = qs.annotate(**{label:Subquery(current.values(field)[:1])})
        primary = StudentGuardian.objects.filter(student=OuterRef('pk'), is_primary=True, status='active', deleted_at__isnull=True).order_by('id')
        qs = qs.annotate(primary_guardian_name=Subquery(primary.values('guardian__first_name')[:1]), guardian_phone=Subquery(primary.values('guardian__phone')[:1]))
    if model is Family:
        qs = qs.annotate(student_count=Count('student_records', filter=Q(student_records__branch_id__in=access.campuses().values('pk'), student_records__deleted_at__isnull=True), distinct=True))
    if model is Guardian:
        qs = qs.annotate(student_count=Count('studentguardian_records__student', filter=Q(studentguardian_records__student__branch_id__in=access.campuses().values('pk'), studentguardian_records__deleted_at__isnull=True), distinct=True))
    if model is StudentEnrollment:
        qs = qs.select_related('term__academic_year')
    if 'staff' in relations:
        qs = qs.select_related('staff__employee')
    if model is AttendanceSession:
        qs = qs.annotate(record_count=Count('records', filter=Q(records__deleted_at__isnull=True)), absent_count=Count('records', filter=Q(records__status='absent', records__deleted_at__isnull=True)))
    if model is AttendanceRecord:
        qs = qs.select_related('session__school_class')
    return qs.order_by('-created_at','pk')
