from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class GymClass(TenantScopedModel, BaseModel):
    """Class template (Yoga, HIIT, …)."""

    code = models.SlugField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    default_capacity = models.PositiveIntegerField(default=20)
    duration_minutes = models.PositiveIntegerField(default=60)
    drop_in_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    default_trainer = models.ForeignKey(
        "gym.Trainer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_classes",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "gym_classes"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_class_tenant_code",
            ),
        ]

    def __str__(self):
        return self.name


class ClassSchedule(TenantScopedModel, BaseModel):
    """A specific session occurrence of a GymClass."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]

    gym_class = models.ForeignKey(
        GymClass, on_delete=models.CASCADE, related_name="schedules"
    )
    trainer = models.ForeignKey(
        "gym.Trainer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_schedules",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_class_schedules",
    )
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_class_schedules"
        ordering = ["starts_at"]
        indexes = [
            models.Index(
                fields=["tenant", "starts_at", "status"],
                name="idx_gym_sched_tenant_start",
            ),
        ]

    def __str__(self):
        return f"{self.gym_class_id} @ {self.starts_at}"


class ClassBooking(TenantScopedModel, BaseModel):
    """Member booking for a class schedule (confirmed or waitlisted)."""

    STATUS_CONFIRMED = "confirmed"
    STATUS_WAITLISTED = "waitlisted"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_WAITLISTED, "Waitlisted"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    schedule = models.ForeignKey(
        ClassSchedule, on_delete=models.CASCADE, related_name="bookings"
    )
    member = models.ForeignKey(
        "gym.Member", on_delete=models.CASCADE, related_name="class_bookings"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED, db_index=True
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    amount_charged = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    invoice = models.ForeignKey(
        "sales.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_class_bookings",
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_class_bookings"
        ordering = ["booked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "member"],
                condition=models.Q(
                    deleted_at__isnull=True,
                    status__in=["confirmed", "waitlisted"],
                ),
                name="uniq_gym_booking_schedule_member_active",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "schedule", "status"],
                name="idx_gym_book_tenant_sched_st",
            ),
        ]

    def __str__(self):
        return f"{self.member_id}→{self.schedule_id}:{self.status}"
