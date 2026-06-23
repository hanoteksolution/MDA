# Generated migration for subscription customization fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("platform", "0002_subscription_standalone"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantsubscription",
            name="monthly_fee",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="alert_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="alert_message_template",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="contact_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="managed_subscriptions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
