# Generated manually — STEP 06 tenant isolation backfill

from django.db import migrations

from apps.platform.services.tenant_backfill import backfill_tenant_isolation, noop_reverse


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0008_tenant_foundation_data"),
        ("authentication", "0003_platform_cloud"),
        ("settings_app", "0003_tenant_isolation"),
        ("products", "0002_tenant_isolation"),
        ("customers", "0002_tenant_isolation"),
        ("suppliers", "0002_tenant_isolation"),
        ("inventory", "0002_tenant_isolation"),
        ("sales", "0006_tenant_isolation"),
        ("purchases", "0002_tenant_isolation"),
        ("audit", "0003_tenant_isolation"),
    ]

    operations = [
        migrations.RunPython(backfill_tenant_isolation, noop_reverse),
    ]
