from django.conf import settings
from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProjectScopedModel(TenantScopedModel, BaseModel):
    project = models.ForeignKey("project_management.Project", on_delete=models.CASCADE)

    class Meta:
        abstract = True


class MaterialRequest(ProjectScopedModel):
    STATUS_CHOICES = [(v, v.replace("_", " ").title()) for v in ("draft", "submitted", "approved", "ordered", "received", "cancelled")]
    wbs_node = models.ForeignKey("project_management.WbsNode", null=True, blank=True, on_delete=models.SET_NULL)
    unit = models.ForeignKey("project_management.ProjectUnit", null=True, blank=True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    purchase_order = models.ForeignKey(
        "purchases.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="material_requests",
    )
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_material_requests"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_project_material_request_code")]


class ProjectInventoryAllocation(ProjectScopedModel):
    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("grn", "Goods receipt"),
        ("material_request", "Material request"),
    ]
    wbs_node = models.ForeignKey(
        "project_management.WbsNode", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="inventory_allocations",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, related_name="project_inventory_allocations"
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    allocated_at = models.DateTimeField(auto_now_add=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "project_inventory_allocations"
        ordering = ["-allocated_at", "-created_at"]


class MaterialRequestLine(TenantScopedModel, BaseModel):
    request = models.ForeignKey(MaterialRequest, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_of_measure = models.CharField(max_length=40)
    estimated_unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_material_request_lines"


class ProjectEquipment(ProjectScopedModel):
    STATUS_CHOICES = [(v, v.title()) for v in ("available", "assigned", "maintenance", "retired")]
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    equipment_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    daily_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_equipment"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_project_equipment_code")]


class ProjectExpense(ProjectScopedModel):
    STATUS_CHOICES = [(v, v.title()) for v in ("draft", "submitted", "approved", "rejected", "paid")]
    wbs_node = models.ForeignKey("project_management.WbsNode", null=True, blank=True, on_delete=models.SET_NULL)
    category = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    expense_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_expenses"


class ChangeOrder(ProjectScopedModel):
    STATUS_CHOICES = [(v, v.title()) for v in ("draft", "submitted", "approved", "rejected", "implemented")]
    code = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount_delta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    requested_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_change_orders"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_project_change_order_code")]


class SiteReport(ProjectScopedModel):
    STATUS_CHOICES = [("draft", "Draft"), ("submitted", "Submitted")]
    site = models.ForeignKey("project_management.ProjectSite", null=True, blank=True, on_delete=models.SET_NULL)
    report_date = models.DateField()
    weather = models.CharField(max_length=100, blank=True)
    summary = models.TextField()
    progress_notes = models.TextField(blank=True)
    issues_notes = models.TextField(blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    class Meta:
        db_table = "project_site_reports"


class QualityInspection(ProjectScopedModel):
    RESULT_CHOICES = [(v, v.title()) for v in ("pass", "fail", "conditional")]
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]
    unit = models.ForeignKey("project_management.ProjectUnit", null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200)
    inspection_date = models.DateField()
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    findings = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_quality_inspections"


class SafetyIncident(ProjectScopedModel):
    SEVERITY_CHOICES = [(v, v.title()) for v in ("low", "medium", "high", "critical")]
    STATUS_CHOICES = [(v, v.title()) for v in ("open", "investigating", "closed")]
    incident_date = models.DateField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_safety_incidents"


class ProjectRisk(ProjectScopedModel):
    LEVEL_CHOICES = [(v, v.title()) for v in ("low", "medium", "high", "critical")]
    PROBABILITY_CHOICES = LEVEL_CHOICES[:-1]
    STATUS_CHOICES = [(v, v.title()) for v in ("open", "mitigating", "closed")]
    code = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    probability = models.CharField(max_length=20, choices=PROBABILITY_CHOICES)
    impact = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    mitigation_plan = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_risks"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_project_risk_code")]


class ProjectIssue(ProjectScopedModel):
    PRIORITY_CHOICES = [(v, v.title()) for v in ("low", "medium", "high", "critical")]
    STATUS_CHOICES = [(v, v.replace("_", " ").title()) for v in ("open", "in_progress", "resolved", "closed")]
    task = models.ForeignKey("project_management.ProjectTask", null=True, blank=True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    notes = models.TextField(blank=True)
    class Meta:
        db_table = "project_issues"
        constraints = [models.UniqueConstraint(fields=["project", "code"], name="uniq_project_issue_code")]


class ProjectInvoice(ProjectScopedModel):
    STATUS_CHOICES = [(v, v.title()) for v in ("draft", "issued", "paid", "void")]
    invoice_number = models.CharField(max_length=60)
    invoice_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    journal_entry = models.ForeignKey(
        "finance.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_invoices",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "project_invoices"
        constraints = [models.UniqueConstraint(fields=["project", "invoice_number"], name="uniq_project_invoice_number")]
