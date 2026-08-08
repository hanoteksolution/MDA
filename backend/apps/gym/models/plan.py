from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class MembershipPlan(TenantScopedModel, BaseModel):
    """Sellable gym membership product (duration + price)."""

    code = models.SlugField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    duration_days = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    visit_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Null = unlimited visits during the period.",
    )
    freeze_allowed = models.BooleanField(default=True)
    max_freeze_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "gym_membership_plans"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_plan_tenant_code",
            ),
        ]

    def __str__(self):
        return self.name


class MembershipSubscription(TenantScopedModel, BaseModel):
    """Member ↔ plan subscription with lifecycle."""

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_FROZEN = "frozen"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending payment"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_FROZEN, "Frozen"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    member = models.ForeignKey(
        "gym.Member",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    visits_allowed = models.PositiveIntegerField(null=True, blank=True)
    visits_used = models.PositiveIntegerField(default=0)
    price_paid = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    freeze_days_used = models.PositiveIntegerField(default=0)
    frozen_at = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    invoice = models.ForeignKey(
        "sales.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_subscriptions",
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_membership_subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "status", "end_date"],
                name="idx_gym_sub_tenant_status_end",
            ),
        ]

    def __str__(self):
        return f"{self.member_id}:{self.plan_id}:{self.status}"
