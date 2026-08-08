# Data seed/backfill for STEP 04 tenant foundation

from django.conf import settings
from django.db import migrations


def seed_and_backfill(apps, schema_editor):
    BusinessType = apps.get_model("platform", "BusinessType")
    Tenant = apps.get_model("platform", "Tenant")
    TenantSettings = apps.get_model("platform", "TenantSettings")
    TenantDomain = apps.get_model("platform", "TenantDomain")

    seeds = [
        ("retail", "General Retail", ["pos", "inventory", "sales", "purchases"], 10),
        ("supermarket", "Supermarket", ["pos", "inventory", "sales", "purchases"], 20),
        ("pharmacy", "Pharmacy", ["pos", "inventory", "sales", "purchases", "pharmacy"], 30),
        ("cafeteria", "Cafeteria", ["pos", "inventory", "sales", "restaurant"], 40),
        ("restaurant", "Restaurant", ["pos", "inventory", "sales", "restaurant"], 50),
        ("electronics", "Electronics", ["pos", "inventory", "sales", "purchases"], 60),
        ("fashion", "Fashion", ["pos", "inventory", "sales", "purchases"], 70),
        ("hardware", "Hardware", ["pos", "inventory", "sales", "purchases"], 80),
        ("wholesale", "Wholesale", ["pos", "inventory", "sales", "purchases"], 90),
        ("gym", "Gym / Fitness Center", ["pos", "inventory", "sales", "gym"], 100),
        ("salon", "Salon / Spa", ["pos", "inventory", "sales"], 110),
        ("futsal", "Futsal", ["pos", "inventory", "sales", "futsal"], 120),
        ("other", "Other", ["pos", "inventory", "sales"], 200),
    ]
    for code, name, modules, sort_order in seeds:
        BusinessType.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "default_modules": modules,
                "sort_order": sort_order,
                "is_active": True,
            },
        )

    retail = BusinessType.objects.filter(code="retail").first()
    base = getattr(settings, "TENANT_BASE_DOMAIN", None) or "erp.safaritechno.com"

    for tenant in Tenant.objects.all():
        if tenant.is_active:
            if tenant.status not in ("active", "trial"):
                tenant.status = "trial"
        else:
            tenant.status = "suspended"
        if retail and getattr(tenant, "business_type_id", None) is None:
            tenant.business_type_id = retail.id
        tenant.save()

        TenantSettings.objects.get_or_create(tenant_id=tenant.id, defaults={})
        if not TenantDomain.objects.filter(tenant_id=tenant.id, deleted_at__isnull=True).exists():
            TenantDomain.objects.create(
                tenant_id=tenant.id,
                domain=f"{tenant.slug}.{base}".lower(),
                subdomain=tenant.slug,
                is_primary=True,
                is_custom=False,
                is_verified=True,
                is_active=True,
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0007_tenant_foundation"),
    ]

    operations = [
        migrations.RunPython(seed_and_backfill, noop_reverse),
    ]
