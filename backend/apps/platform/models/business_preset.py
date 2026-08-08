"""Business presets — onboarding templates (not modules)."""

from django.db import models

from core.models.base import BaseModel


class BusinessPreset(BaseModel):
    """Reusable module pack recommended at onboarding."""

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default="")
    business_type = models.ForeignKey(
        "platform.BusinessType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="presets",
    )
    version = models.PositiveSmallIntegerField(default=1)
    is_system = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "business_presets"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.code


class BusinessPresetModule(BaseModel):
    """Module membership inside a preset."""

    preset = models.ForeignKey(
        BusinessPreset,
        on_delete=models.CASCADE,
        related_name="preset_modules",
    )
    module = models.ForeignKey(
        "platform.Module",
        on_delete=models.CASCADE,
        related_name="preset_links",
    )
    is_required = models.BooleanField(default=False)
    is_default = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=100)
    default_configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "business_preset_modules"
        ordering = ["display_order", "module__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["preset", "module"],
                name="uniq_business_preset_module",
            ),
        ]

    def __str__(self):
        return f"{self.preset.code}:{self.module.code}"
