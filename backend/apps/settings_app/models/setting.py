from django.db import models

from core.models.base import BaseModel


class Company(BaseModel):
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    logo = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "companies"
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Branch(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "branches"
        unique_together = ["company", "code"]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Setting(BaseModel):
    CATEGORY_CHOICES = [
        ("general", "General"),
        ("company", "Company"),
        ("pos", "POS"),
        ("tax", "Tax"),
        ("security", "Security"),
        ("backup", "Backup"),
        ("notifications", "Notifications"),
    ]

    key = models.CharField(max_length=255, db_index=True)
    value = models.JSONField(default=dict)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="settings"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True, related_name="settings"
    )

    class Meta:
        db_table = "settings"
        unique_together = ["key", "branch", "company"]
        ordering = ["category", "key"]

    def __str__(self):
        return self.key
