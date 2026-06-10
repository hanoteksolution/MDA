from django.db import models

from core.models.base import BaseModel


class Customer(BaseModel):
    CUSTOMER_TYPES = [
        ("retail", "Retail"),
        ("wholesale", "Wholesale"),
        ("corporate", "Corporate"),
    ]

    customer_code = models.CharField(max_length=50, unique=True, db_index=True)
    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True, db_index=True)
    address = models.TextField(blank=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default="retail")
    credit_limit = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    outstanding_balance = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.SET_NULL, null=True, blank=True, related_name="customers"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "customers"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name
