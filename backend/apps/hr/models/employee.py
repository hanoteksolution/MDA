"""Minimal shared employee contract.

Deliberately small: identity, home branch, optional login and employment window.
Leave, payroll and contracts extend this master in a later HR phase; industry
apps (School teachers today) attach their own extension rows to it instead of
owning a private staff master. A login is optional: many employees never sign in.
"""
from django.db import models
from django.db.models import Q, F
from core.models.base import BaseModel


class Employee(BaseModel):
    STATUS = [("active", "Active"), ("inactive", "Inactive"), ("archived", "Archived")]
    TYPES = [(v, v.replace("_", " ").title()) for v in ("full_time", "part_time", "contract", "volunteer")]

    tenant = models.ForeignKey("platform.Tenant", on_delete=models.PROTECT, related_name="employees")
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT, related_name="employees")
    user = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_records")
    code = models.CharField(max_length=60)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    employment_type = models.CharField(max_length=20, choices=TYPES, default="full_time")
    hire_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="active")

    class Meta:
        ordering = ["first_name", "last_name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="hr_employee_code"),
            models.UniqueConstraint(fields=["tenant", "user"], condition=Q(user__isnull=False, deleted_at__isnull=True), name="hr_employee_one_per_user"),
            models.CheckConstraint(condition=Q(hire_date__isnull=True) | Q(termination_date__isnull=True) | Q(termination_date__gte=F("hire_date")), name="hr_employee_dates"),
        ]
        indexes = [models.Index(fields=["tenant", "branch", "status"])]

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.name
