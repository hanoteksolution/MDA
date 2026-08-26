from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0006_requires_prescription"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="module_code",
            field=models.SlugField(
                blank=True,
                db_index=True,
                default="",
                help_text="Owning industry/module (gym, restaurant, pharmacy, retail, …). Blank = shared retail.",
                max_length=40,
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["tenant", "module_code", "is_active"],
                name="idx_prod_tenant_module_active",
            ),
        ),
    ]
