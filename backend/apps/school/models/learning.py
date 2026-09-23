"""Assessment drafts and immutable academic publication/promotion snapshots."""
from django.db import models
from django.db.models import Q, F
from .sis_identity import SchoolRecord, ref, choices


class GradeScheme(SchoolRecord):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    ranking = models.CharField(max_length=20,choices=choices('none competition dense'),default='none')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['tenant','branch','code'],name='school_grade_scheme_code')]
    def __str__(self): return self.name


class GradeBand(SchoolRecord):
    scheme = ref(GradeScheme, related_name='bands')
    label = models.CharField(max_length=30)
    minimum = models.DecimalField(max_digits=5,decimal_places=2)
    maximum = models.DecimalField(max_digits=5,decimal_places=2)
    passing = models.BooleanField(default=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(minimum__gte=0,maximum__lte=100,maximum__gt=F('minimum')),name='school_grade_band_range')]
    def __str__(self): return self.label


class LearningAssignment(SchoolRecord):
    title = models.CharField(max_length=150)
    subject_offering = ref('school.SubjectOffering')
    assigned_date = models.DateField()
    due_date = models.DateField()
    instructions = models.TextField(blank=True)
    maximum_score = models.DecimalField(max_digits=8,decimal_places=2,default=100)
    status = models.CharField(max_length=20,choices=choices('draft published closed'),default='draft')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(due_date__gte=F('assigned_date'),maximum_score__gt=0),name='school_assignment_bounds')]
    def __str__(self): return self.title


class LearningSubmission(SchoolRecord):
    assignment = ref(LearningAssignment,related_name='submissions')
    enrollment = ref('school.StudentEnrollment')
    content = models.TextField()
    submitted_at = models.DateTimeField()
    score = models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20,choices=choices('submitted graded'),default='submitted')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['assignment','enrollment'],name='school_one_submission'),models.CheckConstraint(condition=Q(score__isnull=True)|Q(score__gte=0),name='school_submission_score')]


class Exam(SchoolRecord):
    name = models.CharField(max_length=150)
    academic_year = ref('school.AcademicYear')
    term = ref('school.AcademicTerm',optional=True)
    school_class = ref('school.SchoolClass')
    section = ref('school.Section',optional=True)
    scheme = ref(GradeScheme)
    status = models.CharField(max_length=20,choices=choices('draft submitted moderated published'),default='draft')
    revision = models.PositiveIntegerField(default=0)
    def __str__(self): return self.name


class Assessment(SchoolRecord):
    exam = ref(Exam,related_name='assessments')
    subject_offering = ref('school.SubjectOffering')
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20,choices=choices('exam coursework practical quiz'),default='exam')
    assignment = ref(LearningAssignment,optional=True)
    date = models.DateField()
    maximum_score = models.DecimalField(max_digits=8,decimal_places=2,default=100)
    weight = models.DecimalField(max_digits=5,decimal_places=2,default=100)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['exam','subject_offering','name'],name='school_assessment_name'),models.CheckConstraint(condition=Q(maximum_score__gt=0,weight__gt=0,weight__lte=100),name='school_assessment_weight')]
    def __str__(self): return self.name


class ExamSchedule(SchoolRecord):
    assessment = ref(Assessment,one=True,related_name='schedule')
    classroom = ref('school.Classroom')
    staff = ref('school.SchoolStaffProfile')
    start_time = models.TimeField()
    end_time = models.TimeField()
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(end_time__gt=F('start_time')),name='school_exam_schedule_time')]


class Mark(SchoolRecord):
    assessment = ref(Assessment,related_name='marks')
    enrollment = ref('school.StudentEnrollment')
    score = models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True)
    outcome = models.CharField(max_length=20,choices=choices('present absent exempt'),default='present')
    remarks = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['assessment','enrollment'],name='school_mark_unique'),models.CheckConstraint(condition=(Q(outcome='present',score__isnull=False,score__gte=0)|Q(outcome__in=['absent','exempt'],score__isnull=True)),name='school_mark_score_outcome')]


class ResultPublication(SchoolRecord):
    exam = ref(Exam,related_name='publications')
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['exam','version'],name='school_result_version')]


class ReportCardVersion(SchoolRecord):
    publication = ref(ResultPublication,related_name='report_cards')
    student = ref('school.Student')
    data = models.JSONField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['publication','student'],name='school_report_version')]


class PromotionBatch(SchoolRecord):
    publication = ref(ResultPublication)
    target_year = ref('school.AcademicYear',optional=True)
    effective_date = models.DateField()
    reason = models.TextField()
    fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=20,choices=choices('preview committed'),default='preview')


class PromotionItem(SchoolRecord):
    batch = ref(PromotionBatch,related_name='items')
    enrollment = ref('school.StudentEnrollment')
    target_class = ref('school.SchoolClass',optional=True)
    target_section = ref('school.Section',optional=True)
    outcome = models.CharField(max_length=20,choices=choices('promote repeat graduate'))
    result_enrollment = ref('school.StudentEnrollment',optional=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['batch','enrollment'],name='school_promotion_item')]
