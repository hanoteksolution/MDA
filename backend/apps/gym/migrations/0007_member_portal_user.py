# Generated manually for STEP 28 — link gym members to portal user accounts.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0001_initial"),
        ("gym", "0006_workouts"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="gym_member_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
