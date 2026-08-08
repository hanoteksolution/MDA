# Generated manually for PHASE 10 demo tenant fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0015_module_preset_dependencies"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="demo_converted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="demo_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="demo_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ACTIVE", "Active"),
                    ("EXPIRED", "Expired"),
                    ("SUSPENDED", "Suspended"),
                    ("CONVERTED", "Converted"),
                ],
                db_index=True,
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="is_demo",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
