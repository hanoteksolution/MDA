"""Academic masters. Branch is the shared campus; User owns staff identity."""
from django.db import models
from django.db.models import Q, F
from core.models.base import BaseModel


class SchoolMaster(BaseModel):
    tenant = models.ForeignKey("platform.Tenant", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    status = models.CharField(max_length=16, choices=[("active", "Active"), ("inactive", "Inactive"), ("archived", "Archived")], default="active")
    description = models.TextField(blank=True)

    class Meta:
        abstract = True
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class EducationLevel(SchoolMaster):
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="school_level_code")]


class SchoolShift(SchoolMaster):
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "branch", "code"], name="school_shift_code"), models.CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="school_shift_dates")]


class SchoolClass(SchoolMaster):
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT)
    education_level = models.ForeignKey(EducationLevel, on_delete=models.PROTECT, related_name="classes")
    sequence = models.PositiveSmallIntegerField(default=1)
    capacity = models.PositiveIntegerField(default=30)
    room = models.CharField(max_length=100, blank=True)
    teacher = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="school_classes")

    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "branch", "code"], name="school_class_code"), models.CheckConstraint(condition=Q(capacity__gt=0), name="school_class_capacity")]
        indexes = [models.Index(fields=["tenant", "branch", "status"])]


class Section(SchoolMaster):
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="sections")
    capacity = models.PositiveIntegerField(default=30)
    room = models.CharField(max_length=100, blank=True)
    teacher = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="school_sections")
    shift = models.ForeignKey(SchoolShift, on_delete=models.PROTECT, null=True, blank=True)

    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "school_class", "code"], name="school_section_code"), models.UniqueConstraint(fields=["tenant", "school_class", "name"], name="school_section_name"), models.CheckConstraint(condition=Q(capacity__gt=0), name="school_section_capacity")]


class SubjectCategory(SchoolMaster):
    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="school_subject_category_code")]


class Subject(SchoolMaster):
    short_name = models.CharField(max_length=30, blank=True)
    category = models.ForeignKey(SubjectCategory, on_delete=models.PROTECT, null=True, blank=True)
    maximum_marks = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    pass_mark = models.DecimalField(max_digits=8, decimal_places=2, default=50)
    weight = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    mandatory = models.BooleanField(default=True)
    teaching_mode = models.CharField(max_length=16, choices=[("theory", "Theory"), ("practical", "Practical"), ("mixed", "Mixed")], default="theory")

    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="school_subject_code"), models.CheckConstraint(condition=Q(maximum_marks__gt=0, pass_mark__gte=0, pass_mark__lte=F("maximum_marks"), weight__gt=0), name="school_subject_marks")]


class SubjectOffering(SchoolMaster):
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT)
    academic_year = models.ForeignKey("school.AcademicYear", on_delete=models.PROTECT, related_name="offerings")
    term = models.ForeignKey("school.AcademicTerm", on_delete=models.PROTECT, null=True, blank=True, related_name="offerings")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="offerings")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, null=True, blank=True, related_name="offerings")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="offerings")
    teacher = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="school_offerings")
    maximum_marks = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    pass_mark = models.DecimalField(max_digits=8, decimal_places=2, default=50)
    weight = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    weekly_periods = models.PositiveSmallIntegerField(default=1)
    mandatory = models.BooleanField(default=True)

    class Meta(SchoolMaster.Meta):
        constraints = [models.UniqueConstraint(fields=["tenant", "branch", "code"], name="school_offering_code"), models.CheckConstraint(condition=Q(maximum_marks__gt=0, pass_mark__gte=0, pass_mark__lte=F("maximum_marks"), weight__gt=0, weekly_periods__gt=0), name="school_offering_marks")]
        # Four partial indexes enforce nullable scope on both PostgreSQL and SQLite.
        constraints += [models.UniqueConstraint(fields=["tenant", "academic_year", "branch", "school_class", "subject"] + (["term"] if t else []) + (["section"] if s else []), condition=Q(status="active", deleted_at__isnull=True, term__isnull=not t, section__isnull=not s), name=f"school_offering_scope_{int(t)}{int(s)}") for t in (False, True) for s in (False, True)]
        indexes = [models.Index(fields=["tenant", "branch", "academic_year", "status"])]


class SchoolCampusAccess(BaseModel):
    tenant = models.ForeignKey("platform.Tenant", on_delete=models.PROTECT)
    user = models.ForeignKey("authentication.User", on_delete=models.CASCADE, related_name="school_campus_access")
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "user", "branch"], name="school_campus_access_unique")]
