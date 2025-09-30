# Generated migration to make the price field nullable to fix inconsistency
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_add_unit_price_field"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
            ),
        ),
    ]
