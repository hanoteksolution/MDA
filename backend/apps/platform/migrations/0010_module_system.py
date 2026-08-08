# Generated for STEP 08 module system

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


MODULE_SEEDS = [
    ("pos", "Point of Sale", "core", "Checkout, holds, and receipts", 10),
    ("inventory", "Inventory", "core", "Stock, warehouses, products, categories", 20),
    ("sales", "Sales", "core", "Invoices, quotations, customers, daily ops", 30),
    ("purchases", "Purchases", "core", "Purchase orders and suppliers", 40),
    ("pharmacy", "Pharmacy", "industry", "Prescription and batch controls", 100),
    ("restaurant", "Restaurant", "industry", "Floor / kitchen flows", 110),
    ("gym", "Gym", "industry", "Memberships and attendance", 120),
    ("futsal", "Futsal", "industry", "Courts, bookings, and teams", 130),
]


def seed_modules_and_tenant_links(apps, schema_editor):
    Module = apps.get_model("platform", "Module")
    Tenant = apps.get_model("platform", "Tenant")
    TenantModule = apps.get_model("platform", "TenantModule")
    BusinessType = apps.get_model("platform", "BusinessType")

    for code, name, category, description, sort_order in MODULE_SEEDS:
        Module.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "category": category,
                "description": description,
                "sort_order": sort_order,
                "is_active": True,
            },
        )

    modules = {m.code: m for m in Module.objects.filter(deleted_at__isnull=True)}
    for tenant in Tenant.objects.filter(deleted_at__isnull=True):
        bt = None
        if tenant.business_type_id:
            bt = BusinessType.objects.filter(pk=tenant.business_type_id).first()
        codes = list(bt.default_modules or []) if bt else []
        if not codes:
            codes = ["pos", "inventory", "sales", "purchases"]
        wanted = {str(c).strip().lower() for c in codes}
        for code, module in modules.items():
            TenantModule.objects.get_or_create(
                tenant_id=tenant.pk,
                module_id=module.pk,
                defaults={"enabled": code in wanted},
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0009_backfill_tenant_isolation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Module",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        choices=[("core", "Core"), ("industry", "Industry"), ("addon", "Add-on")],
                        db_index=True,
                        default="core",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=100)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "modules",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="TenantModule",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "module",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tenant_links",
                        to="platform.module",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tenant_modules",
                        to="platform.tenant",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "tenant_modules",
                "ordering": ["module__sort_order", "module__code"],
            },
        ),
        migrations.AddConstraint(
            model_name="tenantmodule",
            constraint=models.UniqueConstraint(fields=("tenant", "module"), name="uniq_tenant_module"),
        ),
        migrations.RunPython(seed_modules_and_tenant_links, noop_reverse),
    ]
