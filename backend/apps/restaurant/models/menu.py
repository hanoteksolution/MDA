from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class MenuCategory(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=120, db_index=True)
    code = models.CharField(max_length=40, blank=True, db_index=True)
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    color_accent = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_menu_categories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    kitchen_station = models.ForeignKey(
        "restaurant.KitchenStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="menu_categories",
    )
    tax_group = models.CharField(max_length=40, blank=True)
    pos_visible = models.BooleanField(default=True)
    mobile_visible = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_menu_categories"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "sort_order"], name="idx_rest_cat_tenant"),
        ]

    def __str__(self):
        return self.name


class MenuItem(TenantScopedModel, BaseModel):
    category = models.ForeignKey(
        MenuCategory, on_delete=models.CASCADE, related_name="items"
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_menu_items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_menu_items",
    )
    kitchen_station = models.ForeignKey(
        "restaurant.KitchenStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="menu_items",
    )
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=50, blank=True, db_index=True)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    base_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preparation_time_minutes = models.PositiveSmallIntegerField(default=5)
    is_available = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    pos_visible = models.BooleanField(default=True)
    mobile_visible = models.BooleanField(default=True)
    track_inventory = models.BooleanField(default=True)
    allow_modifiers = models.BooleanField(default=True)
    allow_notes = models.BooleanField(default=True)
    available_dine_in = models.BooleanField(default=True)
    available_takeaway = models.BooleanField(default=True)
    available_delivery = models.BooleanField(default=False)
    availability_start = models.TimeField(null=True, blank=True)
    availability_end = models.TimeField(null=True, blank=True)
    coffee_attrs = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "restaurant_menu_items"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["tenant", "is_available", "name"], name="idx_rest_item_tenant"),
        ]

    def __str__(self):
        return self.name


class DiningTable(TenantScopedModel, BaseModel):
    STATUS_FREE = "free"
    STATUS_OCCUPIED = "occupied"
    STATUS_RESERVED = "reserved"
    STATUS_CLEANING = "cleaning"
    STATUS_BLOCKED = "blocked"
    STATUS_OUT_OF_SERVICE = "out_of_service"
    STATUS_CHOICES = [
        (STATUS_FREE, "Free"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_CLEANING, "Cleaning"),
        (STATUS_BLOCKED, "Blocked"),
        (STATUS_OUT_OF_SERVICE, "Out of service"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_tables",
    )
    code = models.CharField(max_length=30, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    capacity = models.PositiveSmallIntegerField(default=4)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_FREE, db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)
    floor = models.ForeignKey(
        "restaurant.RestaurantFloor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tables",
    )

    class Meta:
        db_table = "restaurant_dining_tables"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_table_tenant_branch_code",
            ),
        ]

    def __str__(self):
        return self.label or self.code


class RestaurantOrder(TenantScopedModel, BaseModel):
    """Open floor ticket — payment via Universal POS later (not Invoice yet)."""

    STATUS_DRAFT = "draft"
    STATUS_OPEN = "open"
    STATUS_SUBMITTED = "submitted"
    STATUS_PREPARING = "preparing"
    STATUS_SENT = "sent"
    STATUS_READY = "ready"
    STATUS_SERVED = "served"
    STATUS_COMPLETED = "completed"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    STATUS_VOIDED = "voided"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_OPEN, "Open"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_PREPARING, "Preparing"),
        (STATUS_SENT, "Sent to kitchen"),
        (STATUS_READY, "Ready"),
        (STATUS_SERVED, "Served"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_VOIDED, "Voided"),
    ]

    SERVICE_DINE_IN = "dine_in"
    SERVICE_TAKEAWAY = "takeaway"
    SERVICE_DELIVERY = "delivery"
    SERVICE_QUICK_SALE = "quick_sale"
    SERVICE_CHOICES = [
        (SERVICE_DINE_IN, "Dine in"),
        (SERVICE_TAKEAWAY, "Takeaway"),
        (SERVICE_DELIVERY, "Delivery"),
        (SERVICE_QUICK_SALE, "Quick sale"),
    ]

    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_RUSH = "rush"
    PRIORITY_CHOICES = [
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_RUSH, "Rush"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_orders",
    )
    table = models.ForeignKey(
        DiningTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    order_number = models.CharField(max_length=40, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    service_type = models.CharField(
        max_length=20, choices=SERVICE_CHOICES, default=SERVICE_DINE_IN
    )
    waiter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_orders",
    )
    waiter_name = models.CharField(max_length=120, blank=True)
    barista_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_barista_orders",
    )
    queue_number = models.CharField(max_length=20, blank=True, db_index=True)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL
    )
    guest_count = models.PositiveSmallIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tip_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_charge_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(default=timezone.now, db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "restaurant_orders"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "opened_at"], name="idx_rest_ord_tenant"),
        ]

    def __str__(self):
        return self.order_number

    def recalc_subtotal(self):
        total = Decimal("0")
        for line in self.lines.filter(deleted_at__isnull=True):
            total += Decimal(str(line.line_total or 0))
        self.subtotal = total
        self.save(update_fields=["subtotal", "updated_at"])


class OrderLine(TenantScopedModel, BaseModel):
    STATUS_QUEUED = "queued"
    STATUS_PREP = "prep"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PREP, "Preparing"),
        (STATUS_DONE, "Done"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    order = models.ForeignKey(RestaurantOrder, on_delete=models.CASCADE, related_name="lines")
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.PROTECT, related_name="order_lines"
    )
    variant = models.ForeignKey(
        "restaurant.MenuItemVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_lines",
    )
    kitchen_station = models.ForeignKey(
        "restaurant.KitchenStation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_lines",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_order_lines",
    )
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_order_lines"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} x{self.quantity}"


class RestaurantFloor(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_floors",
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_floors"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_floor_tenant_branch_code",
            )
        ]

    def __str__(self):
        return self.name


class KitchenStation(TenantScopedModel, BaseModel):
    TYPE_COFFEE_BAR = "coffee_bar"
    TYPE_COLD_DRINKS = "cold_drinks"
    TYPE_KITCHEN = "kitchen"
    TYPE_BAKERY = "bakery"
    TYPE_DESSERT = "dessert"
    TYPE_JUICE = "juice"
    TYPE_GRILL = "grill"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_COFFEE_BAR, "Coffee bar"),
        (TYPE_COLD_DRINKS, "Cold drinks"),
        (TYPE_KITCHEN, "Kitchen"),
        (TYPE_BAKERY, "Bakery"),
        (TYPE_DESSERT, "Dessert"),
        (TYPE_JUICE, "Juice"),
        (TYPE_GRILL, "Grill"),
        (TYPE_OTHER, "Other"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_kitchen_stations",
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, db_index=True)
    station_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_KITCHEN, db_index=True
    )
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_kitchen_stations"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_station_tenant_branch_code",
            )
        ]

    def __str__(self):
        return self.name


class ModifierGroup(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_modifier_groups",
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40, db_index=True)
    required = models.BooleanField(default=False)
    min_select = models.PositiveSmallIntegerField(default=0)
    max_select = models.PositiveSmallIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_modifier_groups"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_mod_group_tenant_branch_code",
            )
        ]

    def __str__(self):
        return self.name


class Modifier(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_modifiers",
    )
    group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name="modifiers",
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40, db_index=True)
    price_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_modifiers"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "group", "code"],
                name="uniq_rest_modifier_tenant_branch_group_code",
            )
        ]

    def __str__(self):
        return self.name


class Ingredient(TenantScopedModel, BaseModel):
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_ingredients",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_ingredients",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=40, db_index=True)
    unit = models.CharField(max_length=30, default="unit")
    purchase_unit = models.CharField(max_length=30, blank=True)
    consumption_unit = models.CharField(max_length=30, blank=True)
    # Consumption units contained in one purchase unit (e.g. 1000 g per kg).
    conversion_rate = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    average_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    last_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    min_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    max_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    expiry_tracking = models.BooleanField(default=False)
    batch_tracking = models.BooleanField(default=False)
    storage_location = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_ingredients"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_ingredient_tenant_branch_code",
            )
        ]

    def __str__(self):
        return self.name


class Recipe(TenantScopedModel, BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_recipes",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=20, default="v1")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    yield_qty = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    waste_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_recipes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "menu_item", "status"], name="idx_rest_recipe_active"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.version})"

    def total_cost(self) -> Decimal:
        total = Decimal("0")
        for row in self.ingredients.filter(deleted_at__isnull=True):
            total += Decimal(str(row.quantity or 0)) * Decimal(str(row.unit_cost or 0))
        if self.waste_percent:
            total *= Decimal("1") + (Decimal(str(self.waste_percent)) / Decimal("100"))
        return total


class RecipeIngredient(TenantScopedModel, BaseModel):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name="recipe_uses",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    unit = models.CharField(max_length=30, default="unit")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_recipe_ingredients"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "recipe", "ingredient"],
                name="uniq_rest_recipe_ingredient",
            )
        ]
