from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class AcademicYear(TenantScopedModel, BaseModel):
    STATUS_PLANNING = "planning"
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_PLANNING, "Planning"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.PROTECT,
        related_name="school_academic_years",
    )
    code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNING, db_index=True
    )
    is_current = models.BooleanField(default=False, db_index=True)
    description = models.TextField(blank=True)
    admission_open = models.BooleanField(default=False)
    enrollment_open = models.BooleanField(default=False)

    class Meta:
        db_table = "school_academic_years"
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(tenant__isnull=False), name="%(class)s_tenant_required"),
            models.CheckConstraint(condition=models.Q(status__in=["planning", "active", "closed", "archived"]), name="%(class)s_status_valid"),
            models.CheckConstraint(condition=models.Q(end_date__gt=models.F("start_date")), name="school_year_dates"),
            models.CheckConstraint(condition=models.Q(is_current=False) | models.Q(status="active", deleted_at__isnull=True), name="school_year_current_state"),
            models.UniqueConstraint(fields=["tenant", "code"], condition=~models.Q(code=""), name="school_year_code"),
            models.UniqueConstraint(fields=["tenant", "branch"], condition=models.Q(is_current=True, deleted_at__isnull=True), name="school_one_current_year"),
            models.UniqueConstraint(
                fields=["tenant", "branch", "name"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_school_academic_year_name",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "branch", "is_current"], name="idx_school_year_current"),
        ]

    def __str__(self):
        return self.name


class AcademicTerm(TenantScopedModel, BaseModel):
    STATUS_PLANNING = "planning"
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_PLANNING, "Planning"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.PROTECT,
        related_name="school_academic_terms",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="terms",
    )
    code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    result_publish_date = models.DateField(null=True, blank=True)
    exam_start = models.DateField(null=True, blank=True)
    exam_end = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNING, db_index=True
    )
    sort_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "school_academic_terms"
        ordering = ["academic_year", "sort_order", "start_date"]
        constraints = [
            models.CheckConstraint(condition=models.Q(tenant__isnull=False), name="%(class)s_tenant_required"),
            models.CheckConstraint(condition=models.Q(status__in=["planning", "active", "closed", "archived"]), name="%(class)s_status_valid"),
            models.CheckConstraint(condition=models.Q(end_date__gt=models.F("start_date")), name="school_term_dates"),
            models.CheckConstraint(condition=models.Q(sort_order__gte=1), name="school_term_sequence"),
            models.UniqueConstraint(fields=["tenant", "academic_year", "code"], condition=~models.Q(code=""), name="school_term_code"),
            models.UniqueConstraint(
                fields=["tenant", "academic_year", "name"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_school_academic_term_name",
            ),
        ]

    def __str__(self):
        return f"{self.academic_year.name} — {self.name}"
