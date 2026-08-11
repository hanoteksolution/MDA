from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProjectSite(TenantScopedModel, BaseModel):
    STATUS_ACTIVE, STATUS_INACTIVE = "active", "inactive"
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="sites")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=[(STATUS_ACTIVE, "Active"), (STATUS_INACTIVE, "Inactive")], default=STATUS_ACTIVE)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_sites"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_site_project_code")]


class ProjectBuilding(TenantScopedModel, BaseModel):
    STATUS_ACTIVE, STATUS_INACTIVE = "active", "inactive"
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="buildings")
    site = models.ForeignKey(ProjectSite, on_delete=models.CASCADE, related_name="buildings")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    floors_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=[(STATUS_ACTIVE, "Active"), (STATUS_INACTIVE, "Inactive")], default=STATUS_ACTIVE)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_buildings"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_building_project_code")]


class ProjectFloor(TenantScopedModel, BaseModel):
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="floors")
    building = models.ForeignKey(ProjectBuilding, on_delete=models.CASCADE, related_name="floors")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    level_number = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_floors"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_floor_project_code")]


class ProjectUnit(TenantScopedModel, BaseModel):
    TYPE_CHOICES = [("apartment", "Apartment"), ("shop", "Shop"), ("office", "Office"), ("other", "Other")]
    STATUS_CHOICES = [("planned", "Planned"), ("in_progress", "In Progress"), ("completed", "Completed")]
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE, related_name="units")
    building = models.ForeignKey(ProjectBuilding, on_delete=models.CASCADE, related_name="units")
    floor = models.ForeignKey(ProjectFloor, on_delete=models.SET_NULL, null=True, blank=True, related_name="units")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    unit_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")
    area_sqm = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_management_units"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_unit_project_code")]
