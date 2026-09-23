import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("platform", "0018_alter_agreementacceptance_created_by_and_more"),
        ("settings_app", "0003_tenant_isolation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SchoolProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("school_name", models.CharField(max_length=255)),
                ("legal_name", models.CharField(blank=True, max_length=255)),
                ("school_code", models.CharField(blank=True, db_index=True, max_length=50)),
                ("registration_number", models.CharField(blank=True, max_length=100)),
                ("tax_number", models.CharField(blank=True, max_length=100)),
                ("logo_url", models.CharField(blank=True, max_length=500)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("website", models.CharField(blank=True, max_length=255)),
                ("address", models.TextField(blank=True)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("currency", models.CharField(default="USD", max_length=8)),
                ("language", models.CharField(default="en", max_length=16)),
                ("date_format", models.CharField(default="YYYY-MM-DD", max_length=32)),
                (
                    "academic_calendar_type",
                    models.CharField(
                        choices=[("terms", "Terms"), ("semesters", "Semesters"), ("custom", "Custom")],
                        default="terms",
                        max_length=20,
                    ),
                ),
                (
                    "school_type",
                    models.CharField(
                        choices=[
                            ("primary", "Primary"),
                            ("secondary", "Secondary"),
                            ("k12", "K-12"),
                            ("training", "Training Institution"),
                            ("other", "Other"),
                        ],
                        default="k12",
                        max_length=20,
                    ),
                ),
                ("principal_name", models.CharField(blank=True, max_length=255)),
                ("contact_phone", models.CharField(blank=True, max_length=50)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("settings", models.JSONField(blank=True, default=dict)),
                (
                    "branch",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="school_profile",
                        to="settings_app.branch",
                    ),
                ),
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
                    "principal_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="school_principal_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_set",
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
                "db_table": "school_profiles",
                "ordering": ["school_name"],
            },
        ),
        migrations.CreateModel(
            name="AcademicYear",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planning", "Planning"),
                            ("active", "Active"),
                            ("closed", "Closed"),
                            ("archived", "Archived"),
                        ],
                        db_index=True,
                        default="planning",
                        max_length=20,
                    ),
                ),
                ("is_current", models.BooleanField(db_index=True, default=False)),
                ("description", models.TextField(blank=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="school_academic_years",
                        to="settings_app.branch",
                    ),
                ),
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
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_set",
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
                "db_table": "school_academic_years",
                "ordering": ["-start_date", "name"],
            },
        ),
        migrations.CreateModel(
            name="AcademicTerm",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("exam_start", models.DateField(blank=True, null=True)),
                ("exam_end", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("planning", "Planning"), ("active", "Active"), ("closed", "Closed")],
                        db_index=True,
                        default="planning",
                        max_length=20,
                    ),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "academic_year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="terms",
                        to="school.academicyear",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="school_academic_terms",
                        to="settings_app.branch",
                    ),
                ),
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
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_set",
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
                "db_table": "school_academic_terms",
                "ordering": ["academic_year", "sort_order", "start_date"],
            },
        ),
        migrations.AddConstraint(
            model_name="schoolprofile",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("tenant__isnull", False)),
                fields=("tenant", "branch"),
                name="uniq_school_profile_tenant_branch",
            ),
        ),
        migrations.AddIndex(
            model_name="academicyear",
            index=models.Index(fields=["tenant", "branch", "is_current"], name="idx_school_year_current"),
        ),
        migrations.AddConstraint(
            model_name="academicyear",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("tenant__isnull", False)),
                fields=("tenant", "branch", "name"),
                name="uniq_school_academic_year_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="academicterm",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("tenant__isnull", False)),
                fields=("tenant", "academic_year", "name"),
                name="uniq_school_academic_term_name",
            ),
        ),
    ]
