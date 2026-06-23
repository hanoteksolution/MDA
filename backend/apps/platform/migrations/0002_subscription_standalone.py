import secrets

from django.db import migrations, models
import django.db.models.deletion


def generate_reference_codes(apps, schema_editor):
    TenantSubscription = apps.get_model("platform", "TenantSubscription")
    for sub in TenantSubscription.objects.all():
        sub.reference_code = f"SUB-{secrets.token_hex(3).upper()}"
        sub.save(update_fields=["reference_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0001_platform_cloud"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantsubscription",
            name="billing_period_days",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="grace_period_days",
            field=models.PositiveIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="warning_days",
            field=models.PositiveIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="reference_code",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.RunPython(generate_reference_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="tenantsubscription",
            name="reference_code",
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="tenantsubscription",
            name="tenant",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscription",
                to="platform.tenant",
            ),
        ),
    ]
