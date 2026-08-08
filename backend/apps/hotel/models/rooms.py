"""Hotel front-desk models (PHASE 17 skeleton)."""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class RoomType(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="hotel_room_types",
    )
    name = models.CharField(max_length=120, db_index=True)
    code = models.CharField(max_length=30, blank=True, db_index=True)
    base_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    capacity = models.PositiveSmallIntegerField(default=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "hotel_room_types"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "sort_order"], name="idx_hotel_rtype_tenant"),
        ]

    def __str__(self):
        return self.name


class Room(TenantScopedModel, BaseModel):
    STATUS_VACANT = "vacant"
    STATUS_OCCUPIED = "occupied"
    STATUS_DIRTY = "dirty"
    STATUS_OOO = "ooo"
    STATUS_RESERVED = "reserved"
    STATUS_CHOICES = [
        (STATUS_VACANT, "Vacant"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_DIRTY, "Dirty"),
        (STATUS_OOO, "Out of order"),
        (STATUS_RESERVED, "Reserved"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="hotel_rooms",
    )
    room_type = models.ForeignKey(
        RoomType, on_delete=models.PROTECT, related_name="rooms"
    )
    code = models.CharField(max_length=30, db_index=True)
    floor = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_VACANT, db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hotel_rooms"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_hotel_room_tenant_branch_code",
            ),
        ]

    def __str__(self):
        return self.code


class Guest(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="hotel_guests",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=200, db_index=True)
    phone = models.CharField(max_length=40, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "hotel_guests"
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "full_name"], name="idx_hotel_guest_tenant"),
        ]

    def __str__(self):
        return self.full_name


class Reservation(TenantScopedModel, BaseModel):
    STATUS_BOOKED = "booked"
    STATUS_CHECKED_IN = "checked_in"
    STATUS_CHECKED_OUT = "checked_out"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (STATUS_BOOKED, "Booked"),
        (STATUS_CHECKED_IN, "Checked in"),
        (STATUS_CHECKED_OUT, "Checked out"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_NO_SHOW, "No show"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="hotel_reservations",
    )
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="reservations")
    room_type = models.ForeignKey(
        RoomType, on_delete=models.PROTECT, related_name="reservations"
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    reservation_number = models.CharField(max_length=40, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_BOOKED, db_index=True
    )
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    rate_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hotel_reservations"
        ordering = ["-check_in_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "status", "check_in_date"],
                name="idx_hotel_res_tenant",
            ),
        ]

    def __str__(self):
        return self.reservation_number

    @property
    def nights(self) -> int:
        if not self.check_in_date or not self.check_out_date:
            return 0
        delta = (self.check_out_date - self.check_in_date).days
        return max(delta, 1)


class Folio(TenantScopedModel, BaseModel):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="hotel_folios",
    )
    reservation = models.OneToOneField(
        Reservation, on_delete=models.CASCADE, related_name="folio"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=30, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hotel_folios"
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Folio {self.reservation.reservation_number}"

    @property
    def outstanding(self):
        return (self.balance or Decimal("0")) - (self.amount_paid or Decimal("0"))

    def recalc_balance(self):
        total = Decimal("0")
        for line in self.lines.filter(deleted_at__isnull=True):
            total += Decimal(str(line.amount or 0))
        self.balance = total
        self.save(update_fields=["balance", "updated_at"])


class FolioLine(TenantScopedModel, BaseModel):
    TYPE_ROOM = "room"
    TYPE_SERVICE = "service"
    TYPE_FNB = "fnb"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_ROOM, "Room"),
        (TYPE_SERVICE, "Service"),
        (TYPE_FNB, "Food & Beverage"),
        (TYPE_OTHER, "Other"),
    ]

    folio = models.ForeignKey(Folio, on_delete=models.CASCADE, related_name="lines")
    line_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER, db_index=True
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    posted_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hotel_folio_lines"
        ordering = ["posted_at", "created_at"]

    def __str__(self):
        return self.description
