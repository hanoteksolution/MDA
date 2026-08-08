# Generated for STEP 30 — login lockout audit

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0007_user_created_by"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(db_index=True, max_length=150)),
                ("ip_address", models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ("succeeded", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "login_attempts",
            },
        ),
        migrations.AddIndex(
            model_name="loginattempt",
            index=models.Index(fields=["username", "created_at"], name="idx_login_attempt_user_at"),
        ),
    ]
