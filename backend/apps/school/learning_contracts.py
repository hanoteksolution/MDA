"""Phase 5 resource and writable-field contracts."""
from apps.school.models.learning import (GradeScheme, GradeBand, LearningAssignment, LearningSubmission, Exam, Assessment, ExamSchedule, Mark, ResultPublication, ReportCardVersion, PromotionBatch, PromotionItem)
MODELS = dict(zip(['grade-schemes','grade-bands','assignments','submissions','exams','academic-assessments','exam-schedules','marks','result-publications','report-cards','promotion-batches','promotion-items'],[GradeScheme,GradeBand,LearningAssignment,LearningSubmission,Exam,Assessment,ExamSchedule,Mark,ResultPublication,ReportCardVersion,PromotionBatch,PromotionItem]))
RESOURCES = {key: {'academic-assessments':'academic_assessment','grade-schemes':'grade_scheme','grade-bands':'grade_band','exam-schedules':'exam_schedule','result-publications':'result_publication','report-cards':'report_card','promotion-batches':'promotion','promotion-items':'promotion_item'}.get(key,key.rstrip('s')) for key in MODELS}
FIELDS = {
 'grade-schemes':'branch_id name code ranking', 'grade-bands':'scheme_id label minimum maximum passing',
 'assignments':'subject_offering_id title assigned_date due_date instructions maximum_score',
 'submissions':'assignment_id enrollment_id content',
 'exams':'branch_id name academic_year_id term_id school_class_id section_id scheme_id',
 'academic-assessments':'exam_id subject_offering_id name kind assignment_id date maximum_score weight',
 'exam-schedules':'assessment_id classroom_id staff_id start_time end_time',
 'marks':'', 'result-publications':'', 'report-cards':'', 'promotion-batches':'', 'promotion-items':'',
}
READ_ONLY = ('marks','result-publications','report-cards','promotion-batches','promotion-items')
PERMISSIONS = [(f'school.{r}.{a}',f'School {r}: {a}','school') for key,r in RESOURCES.items() for a in (('view',) if key in READ_ONLY else ('view','create','update'))]
PERMISSIONS += [(f'school.{r}.{a}',f'School {r}: {a}','school') for r,actions in {'assignment':('publish','close'),'submission':('grade',),'exam':('submit','moderate','publish','reopen'),'mark':('enter','enter_any'),'promotion':('preview','commit')}.items() for a in actions]
