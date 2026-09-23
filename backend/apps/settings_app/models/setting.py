from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Company(BaseModel):
    tenant = models.ForeignKey(
        "platform.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="companies",
    )
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    logo = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "companies"
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Branch(TenantScopedModel, BaseModel):
    """The canonical ERP branch (decision D1).

    Extended in place rather than replaced: 94 foreign keys across 24 apps already
    point here, and School uses the same row as its Campus. Every field added for
    multi-branch is nullable or defaulted so the migration stays additive.

    ``is_active`` remains the legacy source of truth and is kept in sync with the
    richer ``status`` in both directions by :meth:`save`.
    """

    TYPE_RETAIL = "RETAIL"
    TYPE_WAREHOUSE = "WAREHOUSE"
    TYPE_OUTLET = "OUTLET"
    TYPE_HEAD_OFFICE = "HEAD_OFFICE"
    TYPE_CAMPUS = "CAMPUS"
    TYPE_OTHER = "OTHER"
    TYPE_CHOICES = [
        (TYPE_RETAIL, "Retail Branch"),
        (TYPE_WAREHOUSE, "Warehouse / Depot"),
        (TYPE_OUTLET, "Outlet"),
        (TYPE_HEAD_OFFICE, "Head Office"),
        (TYPE_CAMPUS, "Campus"),
        (TYPE_OTHER, "Other"),
    ]

    STATUS_ACTIVE = "ACTIVE"
    STATUS_INACTIVE = "INACTIVE"
    STATUS_TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"
    STATUS_ARCHIVED = "ARCHIVED"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
        (STATUS_TEMPORARILY_CLOSED, "Temporarily Closed"),
        (STATUS_ARCHIVED, "Archived"),
    ]
    #: Statuses in which the branch may not trade.
    INACTIVE_STATUSES = frozenset(
        {STATUS_INACTIVE, STATUS_TEMPORARILY_CLOSED, STATUS_ARCHIVED}
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # `db_default` (not just `default`) matters here: School's migration test rebuilds
    # a Branch through an *old, frozen* historical model that predates these columns,
    # so the generated INSERT omits them entirely. Without a real database-level
    # default, SQLite enforces NOT NULL against an omitted column and the insert
    # fails — `default=` alone only helps callers going through the *current* model.
    branch_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_RETAIL, db_default=TYPE_RETAIL
    )
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_default=STATUS_ACTIVE,
        db_index=True,
    )
    legal_name = models.CharField(max_length=255, blank=True, db_default="")
    manager = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branches",
    )
    city = models.CharField(max_length=120, blank=True, db_default="")
    region = models.CharField(max_length=120, blank=True, db_default="")
    country = models.CharField(max_length=120, blank=True, db_default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    opening_date = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=64, blank=True, db_default="")
    currency = models.CharField(max_length=8, blank=True, db_default="")
    receipt_prefix = models.CharField(max_length=16, blank=True, db_default="")
    invoice_prefix = models.CharField(max_length=16, blank=True, db_default="")
    order_prefix = models.CharField(max_length=16, blank=True, db_default="")
    transfer_prefix = models.CharField(max_length=16, blank=True, db_default="")
    notes = models.TextField(blank=True, db_default="")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], condition=models.Q(tenant__isnull=False), name="branch_tenant_code_unique")]
        db_table = "branches"
        unique_together = ["company", "code"]
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="branch_tenant_status_idx"),
            models.Index(fields=["company", "is_active"], name="branch_company_active_idx"),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._remember_activity_state()
        return instance

    def refresh_from_db(self, using=None, fields=None, **kwargs):
        super().refresh_from_db(using=using, fields=fields, **kwargs)
        self._remember_activity_state()

    def _remember_activity_state(self):
        self._loaded_is_active = self.is_active
        self._loaded_status = self.status

    def save(self, *args, **kwargs):
        """Keep ``is_active`` and ``status`` consistent, whichever one was changed.

        Callers that predate multi-branch only ever touch ``is_active``; the branch
        screens set ``status``. Neither may silently contradict the other, so the field
        that actually changed drives the other one.
        """
        update_fields = kwargs.get("update_fields")
        touched = set(update_fields) if update_fields is not None else None

        if touched is not None:
            active_changed = "is_active" in touched
            status_changed = "status" in touched
        else:
            loaded_active = getattr(self, "_loaded_is_active", None)
            loaded_status = getattr(self, "_loaded_status", None)
            active_changed = loaded_active is None or self.is_active != loaded_active
            status_changed = loaded_status is None or self.status != loaded_status

        if status_changed and not active_changed:
            self.is_active = self.status == self.STATUS_ACTIVE
            if touched is not None:
                touched.add("is_active")
        elif active_changed and not status_changed:
            self._sync_status_from_is_active()
            if touched is not None:
                touched.add("status")
        else:
            # Both (or neither) moved — e.g. a fresh row. Make them agree without
            # overriding an explicit non-active status.
            if self.status in self.INACTIVE_STATUSES:
                self.is_active = False
            elif not self.is_active:
                self._sync_status_from_is_active()

        if touched is not None:
            kwargs["update_fields"] = list(touched)
        result = super().save(*args, **kwargs)
        self._remember_activity_state()
        return result

    def _sync_status_from_is_active(self):
        if self.is_active:
            self.status = self.STATUS_ACTIVE
        elif self.status not in self.INACTIVE_STATUSES:
            self.status = self.STATUS_INACTIVE


class Setting(TenantScopedModel, BaseModel):
    CATEGORY_CHOICES = [
        ("general", "General"),
        ("company", "Company"),
        ("pos", "POS"),
        ("tax", "Tax"),
        ("security", "Security"),
        ("backup", "Backup"),
        ("notifications", "Notifications"),
    ]

    key = models.CharField(max_length=255, db_index=True)
    value = models.JSONField(default=dict)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="settings"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name="settings"
    )

    class Meta:
        db_table = "settings"
        unique_together = ["key", "branch", "company"]
        ordering = ["category", "key"]

    def __str__(self):
        return self.key
