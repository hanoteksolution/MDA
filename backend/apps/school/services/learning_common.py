"""Academic relationship, teacher-scope and grading rules."""
from decimal import Decimal
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from apps.school.models import TeacherAssignment, StudentEnrollment, SubjectOffering
from apps.school.models.learning import GradeBand
from .sis_common import get, invalid


def teaching_offerings(access, day):
    assignments=TeacherAssignment.objects.filter(tenant=access.tenant,deleted_at__isnull=True,status='active',staff__status='active',staff__deleted_at__isnull=True,staff__employee__user=access.user,staff__employee__status='active',staff__employee__deleted_at__isnull=True,start_date__lte=day).filter(Q(end_date__isnull=True)|Q(end_date__gte=day))
    return assignments


def authorize(access, offering, day):
    access.campus(offering.branch_id)
    if access.allows('mark','enter_any'):return
    assignments=teaching_offerings(access,day).filter(academic_year=offering.academic_year,school_class=offering.school_class,branch=offering.branch)
    if offering.section_id:assignments=assignments.filter(Q(section__isnull=True)|Q(section=offering.section))
    else:assignments=assignments.filter(section__isnull=True)
    assignments=assignments.filter(Q(subject_offering=offering)|Q(subject_offering__isnull=True,role='class_teacher'))
    if not assignments.exists():raise PermissionDenied('You are not assigned to this subject and class.')


def roster(assessment):
    offering=assessment.subject_offering
    qs=StudentEnrollment.objects.filter(tenant=assessment.tenant,branch=assessment.branch,academic_year=offering.academic_year,school_class=offering.school_class,deleted_at__isnull=True,student__deleted_at__isnull=True,start_date__lte=assessment.date).exclude(status__in=['pending','cancelled']).filter(Q(end_date__isnull=True)|Q(end_date__gte=assessment.date))
    section_id=assessment.exam.section_id or offering.section_id
    if section_id:qs=qs.filter(section_id=section_id)
    return qs.select_related('student').order_by('student_id')


def bands(scheme):
    rows=list(GradeBand.objects.filter(scheme=scheme,deleted_at__isnull=True).order_by('minimum'))
    edge=Decimal(0)
    for band in rows:
        if band.minimum!=edge:invalid('scheme_id','Grade bands must cover 0–100 without gaps or overlaps.')
        edge=band.maximum
    if edge!=100:invalid('scheme_id','Grade bands must cover 0–100.')
    return rows


def grade(value, rows):
    for row in rows:
        if row.minimum<=value<row.maximum or value==100==row.maximum:return row.label,row.passing
    invalid('scheme_id','No grade band matches the result.')


def scoped_relation(access, model, pk, branch, field):
    row=get(access,model,pk,field)
    if getattr(row,'branch_id',None)!=branch.pk:invalid(field,'Related record belongs to another campus.')
    return row
