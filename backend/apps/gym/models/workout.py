from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Exercise(TenantScopedModel, BaseModel):
    """Reusable exercise library entry."""

    code = models.SlugField(max_length=50, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True)
    muscle_group = models.CharField(max_length=50, blank=True, db_index=True)
    equipment = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "gym_exercises"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_exercise_tenant_code",
            ),
        ]

    def __str__(self):
        return self.name


class WorkoutPlan(TenantScopedModel, BaseModel):
    """Multi-day workout template."""

    GOAL_STRENGTH = "strength"
    GOAL_HYPERTROPHY = "hypertrophy"
    GOAL_WEIGHT_LOSS = "weight_loss"
    GOAL_GENERAL = "general"
    GOAL_CHOICES = [
        (GOAL_STRENGTH, "Strength"),
        (GOAL_HYPERTROPHY, "Hypertrophy"),
        (GOAL_WEIGHT_LOSS, "Weight loss"),
        (GOAL_GENERAL, "General fitness"),
    ]

    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True)
    goal = models.CharField(
        max_length=30, choices=GOAL_CHOICES, default=GOAL_GENERAL, db_index=True
    )
    duration_weeks = models.PositiveIntegerField(default=4)
    is_active = models.BooleanField(default=True, db_index=True)
    trainer = models.ForeignKey(
        "gym.Trainer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workout_plans",
    )

    class Meta:
        db_table = "gym_workout_plans"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_gym_workout_plan_tenant_code",
            ),
        ]

    def __str__(self):
        return self.name


class WorkoutDay(BaseModel):
    """Single day within a workout plan."""

    workout_plan = models.ForeignKey(
        WorkoutPlan, on_delete=models.CASCADE, related_name="days"
    )
    day_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_workout_days"
        ordering = ["day_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["workout_plan", "day_number"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_gym_workout_day_plan_number",
            ),
        ]

    def __str__(self):
        return f"{self.workout_plan_id} D{self.day_number}"


class WorkoutExercise(BaseModel):
    """Exercise prescription within a workout day."""

    workout_day = models.ForeignKey(
        WorkoutDay, on_delete=models.CASCADE, related_name="exercises"
    )
    exercise = models.ForeignKey(
        Exercise, on_delete=models.PROTECT, related_name="workout_entries"
    )
    sort_order = models.PositiveSmallIntegerField(default=1)
    sets = models.PositiveSmallIntegerField(default=3)
    reps = models.CharField(max_length=30, default="10")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    rest_seconds = models.PositiveIntegerField(default=60)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_workout_exercises"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.workout_day_id} #{self.sort_order}"


class MemberWorkoutAssignment(TenantScopedModel, BaseModel):
    """Assign a workout plan to a member."""

    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    member = models.ForeignKey(
        "gym.Member", on_delete=models.CASCADE, related_name="workout_assignments"
    )
    workout_plan = models.ForeignKey(
        WorkoutPlan, on_delete=models.PROTECT, related_name="assignments"
    )
    trainer = models.ForeignKey(
        "gym.Trainer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workout_assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_member_workout_assignments"
        ordering = ["-start_date"]
        indexes = [
            models.Index(
                fields=["tenant", "member", "status"],
                name="idx_gym_mwa_tenant_member",
            ),
        ]

    def __str__(self):
        return f"{self.member_id} → {self.workout_plan_id}"


class WorkoutProgress(TenantScopedModel, BaseModel):
    """Logged completion of a workout session."""

    member = models.ForeignKey(
        "gym.Member", on_delete=models.CASCADE, related_name="workout_progress"
    )
    assignment = models.ForeignKey(
        MemberWorkoutAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_logs",
    )
    workout_day = models.ForeignKey(
        WorkoutDay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_logs",
    )
    completed_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_workout_progress"
        ordering = ["-completed_at"]

    def __str__(self):
        return f"Progress {self.member_id} @ {self.completed_at}"


class WorkoutProgressSet(BaseModel):
    """Per-exercise set log within a progress entry."""

    progress = models.ForeignKey(
        WorkoutProgress, on_delete=models.CASCADE, related_name="sets"
    )
    exercise = models.ForeignKey(
        Exercise, on_delete=models.PROTECT, related_name="progress_sets"
    )
    set_number = models.PositiveSmallIntegerField(default=1)
    reps = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_workout_progress_sets"
        ordering = ["set_number"]

    def __str__(self):
        return f"Set {self.set_number} on {self.progress_id}"


class BodyMeasurement(TenantScopedModel, BaseModel):
    """Member body composition / circumference snapshot."""

    member = models.ForeignKey(
        "gym.Member", on_delete=models.CASCADE, related_name="body_measurements"
    )
    measured_at = models.DateTimeField(db_index=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    body_fat_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    chest_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    waist_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    hips_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    arms_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    thighs_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_body_measurements"
        ordering = ["-measured_at"]
        indexes = [
            models.Index(
                fields=["tenant", "member", "measured_at"],
                name="idx_gym_bmeas_tenant_mem",
            ),
        ]

    def __str__(self):
        return f"{self.member_id} @ {self.measured_at}"
