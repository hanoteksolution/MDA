from django.db import models

from core.models.base import BaseModel


class BusinessType(BaseModel):
    """Industry profile that drives modules, POS behavior, and terminology."""

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_modules = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "business_types"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
