import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("settings_app", "0003_tenant_isolation"),
        ("sales", "0007_payment_and_idempotency"),
    ]

    operations = [
        migrations.CreateModel(
            name="CashierSession",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("opened_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("opening_float", models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18)),
                ("closing_cash_counted", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("expected_cash", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("cash_variance", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("total_sales", models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18)),
                ("total_refunds", models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18)),
                ("status", models.CharField(choices=[("open", "Open"), ("closed", "Closed")], db_index=True, default="open", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cashier_sessions", to="settings_app.branch")),
                ("cashier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cashier_sessions", to="authentication.user")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to="authentication.user")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to="authentication.user")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="platform.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to="authentication.user")),
            ],
            options={
                "db_table": "cashier_sessions",
                "ordering": ["-opened_at"],
            },
        ),
        migrations.AddIndex(
            model_name="cashiersession",
            index=models.Index(fields=["branch", "cashier", "status"], name="idx_cashier_sess_branch"),
        ),
        migrations.AddField(
            model_name="invoice",
            name="amount_refunded",
            field=models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18),
        ),
        migrations.AddField(
            model_name="invoice",
            name="cashier_session",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="invoices", to="sales.cashiersession"),
        ),
        migrations.CreateModel(
            name="SaleRefund",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("refund_number", models.CharField(db_index=True, max_length=50)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("total_amount", models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sale_refunds", to="settings_app.branch")),
                ("cashier_session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="refunds", to="sales.cashiersession")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to="authentication.user")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to="authentication.user")),
                ("original_invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refunds", to="sales.invoice")),
                ("processed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="processed_refunds", to="authentication.user")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="platform.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to="authentication.user")),
            ],
            options={
                "db_table": "sale_refunds",
                "ordering": ["-created_at"],
                "unique_together": {("branch", "refund_number")},
            },
        ),
        migrations.CreateModel(
            name="SaleRefundItem",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("quantity", models.DecimalField(decimal_places=4, max_digits=18)),
                ("unit_price", models.DecimalField(decimal_places=4, max_digits=18)),
                ("line_total", models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to="authentication.user")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to="authentication.user")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refund_items", to="products.product")),
                ("refund", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="sales.salerefund")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to="authentication.user")),
            ],
            options={
                "db_table": "sale_refund_items",
            },
        ),
    ]
