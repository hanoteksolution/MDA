import secrets
import uuid

from django.db import migrations, models
import django.utils.timezone


def assign_sync_secrets(apps, schema_editor):
    Tenant = apps.get_model("platform", "Tenant")
    for tenant in Tenant.objects.all():
        if not tenant.sync_secret:
            tenant.sync_secret = secrets.token_urlsafe(24)
            tenant.save(update_fields=["sync_secret"])


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0003_subscription_customization"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="sync_secret",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.RunPython(assign_sync_secrets, migrations.RunPython.noop),
        migrations.CreateModel(
            name="ShopSyncSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_id", models.CharField(blank=True, max_length=64)),
                ("synced_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("kpis", models.JSONField(default=dict)),
                ("invoices", models.JSONField(default=list)),
                ("company_name", models.CharField(blank=True, max_length=255)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="sync_snapshots",
                        to="platform.tenant",
                    ),
                ),
            ],
            options={
                "db_table": "shop_sync_snapshots",
                "ordering": ["-synced_at"],
            },
        ),
    ]
