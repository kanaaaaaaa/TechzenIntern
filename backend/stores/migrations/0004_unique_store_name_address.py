import unicodedata

from django.db import migrations, models


def fill_normalized_address(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    for store in Store.objects.all():
        store.normalized_address = unicodedata.normalize("NFKC", store.address or "").casefold().strip()
        store.save(update_fields=["normalized_address"])


class Migration(migrations.Migration):
    dependencies = [("stores", "0003_four_payment_methods")]
    operations = [
        migrations.AddField(
            model_name="store",
            name="normalized_address",
            field=models.CharField(blank=True, editable=False, max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.RunPython(fill_normalized_address, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="store",
            constraint=models.UniqueConstraint(
                fields=("normalized_name", "normalized_address"),
                name="unique_store_name_address",
            ),
        ),
    ]
