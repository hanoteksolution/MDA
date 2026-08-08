from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0004_seed_system_attributes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["tenant", "is_active", "name"],
                name="idx_prod_tenant_active_name",
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["tenant", "is_active", "barcode"],
                name="idx_prod_tenant_active_barcode",
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["tenant", "category", "is_active"],
                name="idx_prod_tenant_cat_active",
            ),
        ),
        migrations.AddIndex(
            model_name="category",
            index=models.Index(
                fields=["tenant", "is_active", "name"],
                name="idx_cat_tenant_active_name",
            ),
        ),
    ]
