"""Serialized placement creation; enrollment rows remain the historical truth."""
from django.db import transaction
from django.utils import timezone
from apps.school.models import StudentEnrollment
from apps.school.serializers.sis import validate_input
from .sis_common import get, invalid, lock, persist, policy, reason
from .sis_integrity import validate


def placement(student, data, access, *, kind='direct', previous=None):
    values = validate_input('enrollments', {**data, 'student_id':str(student.pk)})
    row = StudentEnrollment(tenant=access.tenant, enrollment_type=kind, **values)
    validate(row, access)
    today = timezone.localdate()
    year = row.academic_year
    if not year.enrollment_open:
        invalid('academic_year_id', 'Enrollment is disabled for this academic year.')
    if year.status != 'active':invalid('academic_year_id', 'Enrollment requires an active academic year.')
    if not year.start_date <= row.start_date <= year.end_date:invalid('start_date', 'Start date must fall within the academic year.')
    if row.start_date > today:invalid('start_date', 'Future enrollment is not supported by this workflow.')
    if row.end_date and (row.end_date < today or row.end_date > year.end_date):invalid('end_date', 'Active enrollment must cover today and end within the year.')
    if not year.start_date <= today <= year.end_date:invalid('academic_year_id', 'The academic year must cover today.')
    if row.school_class.status != 'active' or (row.section_id and row.section.status != 'active'):invalid('school_class_id', 'Placement must be active.')
    if row.section_id and row.section.school_class_id != row.school_class_id:invalid('section_id', 'Section does not belong to the class.')
    if row.term_id and (row.term.status != 'active' or row.term.academic_year_id != year.pk or not row.term.start_date <= row.start_date <= row.term.end_date):invalid('term_id', 'Term must be active, belong to the year and cover the start date.')
    if StudentEnrollment.objects.filter(student=student, status='active', deleted_at__isnull=True).exists():invalid('student_id', 'Student already has an active enrollment.')
    occupied = StudentEnrollment.objects.filter(tenant=access.tenant, branch=row.branch, academic_year=year, school_class=row.school_class, status='active', deleted_at__isnull=True)
    full = occupied.count() >= row.school_class.capacity
    if row.section_id:full = full or occupied.filter(section=row.section).count() >= row.section.capacity
    if full:
        config = policy(access, row.branch)
        if config.capacity_policy == 'block':invalid('school_class_id', 'Placement has reached its capacity.')
        if config.capacity_policy == 'allow_with_override':
            access.require('student', 'override_capacity')
            # The containing workflow supplies its audited reason through notes.
            if not row.notes.strip():invalid('notes', 'A capacity override reason is required.')
        row._capacity_warning = 'Placement exceeds configured capacity.'
    if previous:
        if kind == 'transfer':row.transferred_from = previous
        elif kind in ('promotion', 'repetition'):row.promoted_from = previous
    return persist(row, access, 'enrollment_created')


class EnrollmentService:
    @staticmethod
    @transaction.atomic
    def create(student_id, data, *, access):
        from apps.school.models import Student
        access.require('enrollment', 'create');lock(access)
        student = get(access, Student, student_id)
        if student.status != 'active':invalid('student_id', 'Use re-enrollment for an inactive student.')
        if str(data.get('branch_id')) != str(student.branch_id):invalid('branch_id', 'Use transfer to change campus.')
        return placement(student, data, access)

    @staticmethod
    @transaction.atomic
    def update(pk, data, *, access):
        access.require('enrollment', 'update');lock(access)
        row = get(access, StudentEnrollment, pk)
        if row.status != 'active':invalid('status', 'Historical enrollment is immutable.')
        if set(data) - {'roll_number','notes'}:invalid('action', 'Use a lifecycle command to change placement or dates.')
        values = validate_input('enrollments', data, partial=True)
        for key, value in values.items():setattr(row, key, value)
        return persist(row, access, 'enrollment_updated')
