from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class AttributeDefinition(TenantScopedModel, BaseModel):
    """Dynamic product attribute schema (EAV definition).

    ``tenant`` null = platform/system definition shared across tenants.
    Do not store batch/expiry/serial/money integrity fields here.
    """

    TYPE_TEXT = "text"
    TYPE_INT = "int"
    TYPE_DECIMAL = "decimal"
    TYPE_BOOL = "bool"
    TYPE_DATE = "date"
    TYPE_DATETIME = "datetime"
    TYPE_SELECT = "select"
    TYPE_MULTI_SELECT = "multi_select"
    TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_INT, "Integer"),
        (TYPE_DECIMAL, "Decimal"),
        (TYPE_BOOL, "Boolean"),
        (TYPE_DATE, "Date"),
        (TYPE_DATETIME, "DateTime"),
        (TYPE_SELECT, "Select"),
        (TYPE_MULTI_SELECT, "Multi-select"),
    ]

    code = models.SlugField(max_length=80, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_TEXT)
    is_required = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=False)
    is_pos_visible = models.BooleanField(default=False)
    is_reportable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "attribute_definitions"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(tenant__isnull=False, deleted_at__isnull=True),
                name="uniq_attr_def_tenant_code",
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(tenant__isnull=True, deleted_at__isnull=True),
                name="uniq_attr_def_system_code",
            ),
        ]

    def __str__(self):
        scope = self.tenant_id or "system"
        return f"{scope}:{self.code}"


class AttributeOption(BaseModel):
    """Allowed value for select / multi-select definitions."""

    definition = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.CASCADE,
        related_name="options",
    )
    value = models.CharField(max_length=150)
    label = models.CharField(max_length=150)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "attribute_options"
        ordering = ["sort_order", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "value"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_attr_option_def_value",
            ),
        ]

    def __str__(self):
        return f"{self.definition_id}:{self.value}"


class BusinessTypeAttribute(BaseModel):
    """Assign an attribute definition to a business type profile."""

    business_type = models.ForeignKey(
        "platform.BusinessType",
        on_delete=models.CASCADE,
        related_name="attribute_assignments",
    )
    definition = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.CASCADE,
        related_name="business_type_assignments",
    )
    is_required = models.BooleanField(
        null=True,
        blank=True,
        help_text="Override definition.is_required when set.",
    )
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "business_type_attributes"
        ordering = ["sort_order", "definition__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business_type", "definition"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_bt_attribute",
            ),
        ]

    def __str__(self):
        return f"{self.business_type_id}:{self.definition_id}"


class CategoryAttribute(BaseModel):
    """Assign an attribute definition to a product category."""

    category = models.ForeignKey(
        "products.Category",
        on_delete=models.CASCADE,
        related_name="attribute_assignments",
    )
    definition = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.CASCADE,
        related_name="category_assignments",
    )
    is_required = models.BooleanField(
        null=True,
        blank=True,
        help_text="Override definition.is_required when set.",
    )
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "category_attributes"
        ordering = ["sort_order", "definition__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "definition"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_category_attribute",
            ),
        ]

    def __str__(self):
        return f"{self.category_id}:{self.definition_id}"


class ProductAttributeValue(BaseModel):
    """Typed EAV value for a product attribute."""

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="attribute_values",
    )
    definition = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.CASCADE,
        related_name="product_values",
    )
    value_text = models.TextField(blank=True, default="")
    value_int = models.BigIntegerField(null=True, blank=True)
    value_decimal = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    value_json = models.JSONField(default=list, blank=True)
    option = models.ForeignKey(
        AttributeOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_values",
    )

    class Meta:
        db_table = "product_attribute_values"
        ordering = ["definition__sort_order", "definition__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "definition"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_product_attr_value",
            ),
        ]

    def __str__(self):
        return f"{self.product_id}:{self.definition_id}"
