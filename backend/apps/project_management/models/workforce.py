from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProjectWorker(TenantScopedModel, BaseModel):
    TYPE_CHOICES = [("employee", "Employee"), ("daily_wage", "Daily wage"), ("contractor", "Contractor"), ("subcontractor", "Subcontractor"), ("consultant", "Consultant")]
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="workers")
    employee_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="project_worker_records")
    worker_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="daily_wage")
    code = models.CharField(max_length=40)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    trade = models.CharField(max_length=120, blank=True)
    daily_rate = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_workers"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_worker_project_code")]


class WorkerRateHistory(TenantScopedModel, BaseModel):
    worker = models.ForeignKey(ProjectWorker, on_delete=models.CASCADE, related_name="rate_history")
    rate = models.DecimalField(max_digits=16, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_worker_rate_history"
        ordering = ["-effective_from"]


class WorkerAttendance(TenantScopedModel, BaseModel):
    STATUS_CHOICES = [("present", "Present"), ("absent", "Absent"), ("half_day", "Half day")]
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="attendance")
    worker = models.ForeignKey(ProjectWorker, on_delete=models.CASCADE, related_name="attendance")
    work_date = models.DateField()
    hours_worked = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="present")
    wbs_node = models.ForeignKey("project_management.WbsNode", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance")
    task = models.ForeignKey("project_management.ProjectTask", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance")
    rate_applied = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_worker_attendance"
        constraints = [models.UniqueConstraint(fields=["worker", "work_date"], name="uniq_worker_attendance_date")]


class DailyWageEntry(TenantScopedModel, BaseModel):
    STATUS_CHOICES = [("draft", "Draft"), ("approved", "Approved"), ("paid", "Paid")]
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="daily_wages")
    worker = models.ForeignKey(ProjectWorker, on_delete=models.CASCADE, related_name="daily_wages")
    attendance = models.OneToOneField(WorkerAttendance, on_delete=models.SET_NULL, null=True, blank=True, related_name="daily_wage")
    work_date = models.DateField()
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_daily_wages"
