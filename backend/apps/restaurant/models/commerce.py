"""Cafeteria commercial overlays: combos, promotions, loyalty, reservations, shifts."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class MenuCombo(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_combos",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=40, db_index=True)
    description = models.TextField(blank=True)
    combo_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    pos_visible = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_menu_combos"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_combo_tenant_branch_code",
            )
        ]


class MenuComboItem(TenantScopedModel, BaseModel):
    combo = models.ForeignKey(MenuCombo, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "restaurant.MenuItem",
        on_delete=models.PROTECT,
        related_name="combo_uses",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "restaurant_menu_combo_items"
        ordering = ["sort_order", "created_at"]


class Promotion(TenantScopedModel, BaseModel):
    TYPE_PERCENT = "percent"
    TYPE_FIXED = "fixed"
    TYPE_BOGO = "bogo"
    TYPE_COMBO = "combo"
    TYPE_HAPPY_HOUR = "happy_hour"
    TYPE_CATEGORY = "category"
    TYPE_PRODUCT = "product"
    TYPE_COUPON = "coupon"
    TYPE_CHOICES = [
        (TYPE_PERCENT, "Percentage"),
        (TYPE_FIXED, "Fixed amount"),
        (TYPE_BOGO, "Buy one get one"),
        (TYPE_COMBO, "Combo deal"),
        (TYPE_HAPPY_HOUR, "Happy hour"),
        (TYPE_CATEGORY, "Category"),
        (TYPE_PRODUCT, "Product"),
        (TYPE_COUPON, "Coupon"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_promotions",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=40, db_index=True)
    promotion_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_PERCENT
    )
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount_off = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=40, blank=True, db_index=True)
    stackable = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=100)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    days_of_week = models.CharField(
        max_length=32, blank=True, help_text="Comma days 0-6 (Mon=0)"
    )
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    menu_item = models.ForeignKey(
        "restaurant.MenuItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promotions",
    )
    category = models.ForeignKey(
        "restaurant.MenuCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promotions",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_promotions"
        ordering = ["priority", "name"]


class LoyaltyProgram(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_loyalty_programs",
    )
    name = models.CharField(max_length=120, default="Café Rewards")
    points_per_currency = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    redemption_points = models.PositiveIntegerField(default=100)
    redemption_value = models.DecimalField(max_digits=12, decimal_places=2, default=5)
    birthday_bonus_points = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "restaurant_loyalty_programs"
        ordering = ["name"]


class LoyaltyTier(TenantScopedModel, BaseModel):
    program = models.ForeignKey(
        LoyaltyProgram, on_delete=models.CASCADE, related_name="tiers"
    )
    name = models.CharField(max_length=60)
    code = models.CharField(max_length=20)
    min_points = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "restaurant_loyalty_tiers"
        ordering = ["sort_order", "min_points"]


class LoyaltyMember(TenantScopedModel, BaseModel):
    program = models.ForeignKey(
        LoyaltyProgram, on_delete=models.CASCADE, related_name="members"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="cafeteria_loyalty_memberships",
    )
    tier = models.ForeignKey(
        LoyaltyTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    points_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lifetime_points = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    visit_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "restaurant_loyalty_members"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "program", "customer"],
                name="uniq_rest_loyalty_member",
            )
        ]


class TableReservation(TenantScopedModel, BaseModel):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_SEATED = "seated"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_SEATED, "Seated"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_NO_SHOW, "No show"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_reservations",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_reservations",
    )
    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=50, blank=True)
    reserved_for = models.DateTimeField(db_index=True)
    guests = models.PositiveSmallIntegerField(default=2)
    table = models.ForeignKey(
        "restaurant.DiningTable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_table_reservations"
        ordering = ["reserved_for"]


class StaffShift(TenantScopedModel, BaseModel):
    ROLE_BARISTA = "barista"
    ROLE_CASHIER = "cashier"
    ROLE_KITCHEN = "kitchen"
    ROLE_WAITER = "waiter"
    ROLE_CHOICES = [
        (ROLE_BARISTA, "Barista"),
        (ROLE_CASHIER, "Cashier"),
        (ROLE_KITCHEN, "Kitchen"),
        (ROLE_WAITER, "Waiter"),
    ]

    STATUS_SCHEDULED = "scheduled"
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_staff_shifts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurant_staff_shifts",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_BARISTA)
    station = models.ForeignKey(
        "restaurant.KitchenStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_shifts",
    )
    planned_start = models.DateTimeField()
    planned_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    break_minutes = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_staff_shifts"
        ordering = ["-planned_start"]
