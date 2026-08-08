from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class TrainerSpecialty(TenantScopedModel, BaseModel):
    """Reusable specialty label (strength, cardio, yoga, …)."""

    code = models.SlugField(max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gym_trainer_specialties"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_specialty_tenant_code",
            ),
        ]

    def __str__(self):
        return self.name


class Trainer(TenantScopedModel, BaseModel):
    """Gym trainer profile."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    code = models.CharField(max_length=50, db_index=True)
    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True, db_index=True)
    bio = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_trainer_profiles",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_trainers",
    )
    specialties = models.ManyToManyField(
        TrainerSpecialty,
        blank=True,
        related_name="trainers",
    )
    hourly_rate = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_trainers"
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_trainer_tenant_code",
            ),
        ]

    def __str__(self):
        return self.full_name


class TrainerSchedule(BaseModel):
    """Weekly availability slot for a trainer."""

    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    trainer = models.ForeignKey(
        Trainer, on_delete=models.CASCADE, related_name="schedules"
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gym_trainer_schedules"
        ordering = ["day_of_week", "start_time"]

    def __str__(self):
        return f"{self.trainer_id} D{self.day_of_week} {self.start_time}-{self.end_time}"


class MemberTrainerAssignment(TenantScopedModel, BaseModel):
    """Link a member to a trainer (ongoing coaching)."""

    STATUS_ACTIVE = "active"
    STATUS_ENDED = "ended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ENDED, "Ended"),
    ]

    member = models.ForeignKey(
        "gym.Member",
        on_delete=models.CASCADE,
        related_name="trainer_assignments",
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name="member_assignments",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_member_trainer_assignments"
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["tenant", "member", "status"],
                name="idx_gym_mta_tenant_member",
            ),
        ]

    def __str__(self):
        return f"{self.member_id}→{self.trainer_id}"


class PersonalTrainingSession(TenantScopedModel, BaseModel):
    """Scheduled or completed PT session."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_NO_SHOW, "No-show"),
    ]

    member = models.ForeignKey(
        "gym.Member",
        on_delete=models.CASCADE,
        related_name="pt_sessions",
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name="pt_sessions",
    )
    assignment = models.ForeignKey(
        MemberTrainerAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )
    scheduled_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True
    )
    amount_charged = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    invoice = models.ForeignKey(
        "sales.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_pt_sessions",
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_pt_sessions"
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"PT {self.member_id}/{self.trainer_id} @ {self.scheduled_at}"
