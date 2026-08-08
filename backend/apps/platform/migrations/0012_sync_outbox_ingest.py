# STEP 29 — sync outbox (shop) + idempotent ingest receipts (cloud)

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0011_planmodule"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncOutboxEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "resource_type",
                    models.CharField(
                        choices=[
                            ("invoice", "Invoice"),
                            ("customer", "Customer"),
                            ("inventory", "Inventory"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("resource_id", models.CharField(db_index=True, max_length=64)),
                ("idempotency_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("synced", "Synced"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("synced_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "sync_outbox_entries",
            },
        ),
        migrations.CreateModel(
            name="SyncIngestReceipt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_id", models.CharField(blank=True, max_length=64)),
                ("idempotency_key", models.CharField(db_index=True, max_length=64)),
                (
                    "resource_type",
                    models.CharField(
                        choices=[("invoice", "Invoice"), ("customer", "Customer")],
                        default="invoice",
                        max_length=30,
                    ),
                ),
                ("resource_id", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sync_ingest_receipts",
                        to="platform.tenant",
                    ),
                ),
            ],
            options={
                "db_table": "sync_ingest_receipts",
            },
        ),
        migrations.AddIndex(
            model_name="syncoutboxentry",
            index=models.Index(fields=["status", "created_at"], name="idx_sync_outbox_status_created"),
        ),
        migrations.AddIndex(
            model_name="syncingestreceipt",
            index=models.Index(fields=["tenant", "created_at"], name="idx_sync_ingest_tenant_created"),
        ),
        migrations.AddConstraint(
            model_name="syncingestreceipt",
            constraint=models.UniqueConstraint(
                fields=("tenant", "idempotency_key"),
                name="uniq_sync_ingest_tenant_idempotency",
            ),
        ),
    ]
