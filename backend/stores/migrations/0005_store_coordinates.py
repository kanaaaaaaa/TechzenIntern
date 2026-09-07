from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("stores", "0004_unique_store_name_address")]

    operations = [
        migrations.AddField(
            model_name="store",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(-90),
                    django.core.validators.MaxValueValidator(90),
                ],
            ),
        ),
        migrations.AddField(
            model_name="store",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(-180),
                    django.core.validators.MaxValueValidator(180),
                ],
            ),
        ),
        migrations.RemoveConstraint(
            model_name="store",
            name="unique_store_name_address",
        ),
        migrations.AddConstraint(
            model_name="store",
            constraint=models.UniqueConstraint(
                fields=("normalized_name", "normalized_address", "latitude", "longitude"),
                name="unique_store_location",
                nulls_distinct=False,
            ),
        ),
    ]
