import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0016_demo_tenant_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(db_index=True, max_length=32)),
                ("mode", models.CharField(default="trial", max_length=20)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("subdomain", models.SlugField(db_index=True, max_length=63)),
                ("payload", models.JSONField(default=dict)),
                ("payload_fingerprint", models.CharField(max_length=64)),
                ("idempotency_key_hash", models.CharField(max_length=64, unique=True)),
                ("owner_password_hash", models.CharField(max_length=256)),
                ("failure_category", models.CharField(blank=True, max_length=64)),
                ("failure_message", models.CharField(blank=True, max_length=500)),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registrationrequest_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registrationrequest_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registrationrequest_updated", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registration_request", to="platform.tenant")),
            ],
            options={"db_table": "registration_requests", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="registrationrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("deleted_at__isnull", True), ("status__in", ["pending_email", "verified", "provisioning", "ready"])), fields=("subdomain",), name="uniq_live_registration_subdomain"),
        ),
        migrations.CreateModel(
            name="EmailVerification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("token_hash", models.CharField(max_length=64, unique=True)), ("expires_at", models.DateTimeField(db_index=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)), ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="emailverification_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="emailverification_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="emailverification_updated", to=settings.AUTH_USER_MODEL)),
                ("registration", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="verifications", to="platform.registrationrequest")),
            ], options={"db_table": "registration_email_verifications", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AgreementAcceptance",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("document_type", models.CharField(max_length=32)), ("document_version", models.CharField(max_length=64)),
                ("accepted_at", models.DateTimeField()), ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agreementacceptance_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agreementacceptance_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agreementacceptance_updated", to=settings.AUTH_USER_MODEL)),
                ("registration", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agreements", to="platform.registrationrequest")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="platform.tenant")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ], options={"db_table": "agreement_acceptances"},
        ),
        migrations.AddConstraint(model_name="agreementacceptance", constraint=models.UniqueConstraint(fields=("registration", "document_type", "document_version"), name="uniq_registration_agreement_version")),
        migrations.CreateModel(
            name="ProvisioningJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("stage", models.CharField(db_index=True, max_length=64)), ("status", models.CharField(db_index=True, max_length=20)),
                ("attempt", models.PositiveSmallIntegerField(default=1)), ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)), ("failure_category", models.CharField(blank=True, max_length=64)),
                ("safe_message", models.CharField(blank=True, max_length=500)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="provisioningjob_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="provisioningjob_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="provisioningjob_updated", to=settings.AUTH_USER_MODEL)),
                ("registration", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobs", to="platform.registrationrequest")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="platform.tenant")),
            ], options={"db_table": "provisioning_jobs", "ordering": ["created_at"]},
        ),
    ]
