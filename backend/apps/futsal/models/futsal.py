from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Court(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, db_index=True)
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="futsal_courts"
    )
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "futsal_courts"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_futsal_court_tenant_branch_code",
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Team(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=120, db_index=True)
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="futsal_teams"
    )
    captain_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "futsal_teams"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "name"], name="idx_futsal_team_tenant"),
        ]

    def __str__(self):
        return self.name


class Player(TenantScopedModel, BaseModel):
    full_name = models.CharField(max_length=120, db_index=True)
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="players"
    )
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="futsal_players"
    )
    phone = models.CharField(max_length=50, blank=True)
    jersey_number = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "futsal_players"
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "full_name"], name="idx_futsal_player_tenant"),
        ]

    def __str__(self):
        return self.full_name


class CourtBooking(TenantScopedModel, BaseModel):
    STATUS_SCHEDULED = "scheduled"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    court = models.ForeignKey(Court, on_delete=models.PROTECT, related_name="bookings")
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="futsal_bookings"
    )
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="futsal_bookings",
    )
    title = models.CharField(max_length=200, blank=True)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "futsal_bookings"
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "start_at"], name="idx_futsal_booking_tenant"),
        ]

    def __str__(self):
        return self.title or f"{self.court.name} {self.start_at:%Y-%m-%d %H:%M}"

    def recalc_amount(self):
        self.amount = Decimal(str(self.hours)) * Decimal(str(self.hourly_rate))


class FutsalLedgerEntry(TenantScopedModel, BaseModel):
    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"
    TYPE_CHOICES = [
        (TYPE_INCOME, "Income"),
        (TYPE_EXPENSE, "Expense"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="futsal_ledger_entries"
    )
    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    category = models.CharField(max_length=80, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    entry_date = models.DateField(default=timezone.localdate, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    booking = models.ForeignKey(
        CourtBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )

    class Meta:
        db_table = "futsal_ledger_entries"
        ordering = ["-entry_date", "-created_at"]
        verbose_name_plural = "futsal ledger entries"
        indexes = [
            models.Index(
                fields=["tenant", "entry_type", "entry_date"],
                name="idx_futsal_ledger_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.entry_type} {self.amount} ({self.category})"
