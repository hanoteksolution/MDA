from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Supplier(TenantScopedModel, BaseModel):
    supplier_code = models.CharField(max_length=50, db_index=True)
    company_name = models.CharField(max_length=255, db_index=True)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    payment_terms = models.PositiveIntegerField(default=30)
    outstanding_balance = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "suppliers"
        ordering = ["company_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "supplier_code"],
                name="uniq_supplier_tenant_code",
            ),
        ]

    def __str__(self):
        return self.company_name
