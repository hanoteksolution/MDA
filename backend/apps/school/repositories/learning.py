"""Additional assignment scoping for academic data; campus scope still applies."""
from django.db.models import Q, F
from django.utils import timezone
from apps.school.models import SubjectOffering
from apps.school.models.learning import LearningAssignment, LearningSubmission, Exam, Assessment, ExamSchedule, Mark, ResultPublication, ReportCardVersion, PromotionBatch, PromotionItem


def scope(qs,access):
    if access.allows('mark','enter_any'):return qs
    from apps.school.services.learning_common import teaching_offerings
    grants=teaching_offerings(access,timezone.localdate())
    offerings=SubjectOffering.objects.filter(tenant=access.tenant,deleted_at__isnull=True)
    permitted=Q(pk__in=grants.exclude(subject_offering__isnull=True).filter(Q(section__isnull=True)|Q(section_id=F('subject_offering__section_id'))).values('subject_offering_id'))
    # Class-wide teacher grants apply only to the assigned class/year/section.
    for grant in grants.filter(role='class_teacher',subject_offering__isnull=True):
        condition=Q(school_class=grant.school_class,academic_year=grant.academic_year)
        if grant.section_id:condition &= Q(section=grant.section)
        permitted |= condition
    ids=offerings.filter(permitted).values('pk')
    field={LearningAssignment:'subject_offering_id',LearningSubmission:'assignment__subject_offering_id',Assessment:'subject_offering_id',ExamSchedule:'assessment__subject_offering_id',Mark:'assessment__subject_offering_id'}.get(qs.model)
    if field:return qs.filter(**{field+'__in':ids})
    if qs.model is Exam:return qs.filter(assessments__subject_offering_id__in=ids).distinct()
    if qs.model in (ResultPublication,ReportCardVersion,PromotionBatch,PromotionItem):return qs.none()
    return qs
