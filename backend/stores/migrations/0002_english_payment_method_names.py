from django.db import migrations, models


RENAMES = {
    "cash": ("Cash", "現金"),
    "rakuten-pay": ("Rakuten Pay", "楽天ペイ"),
    "d-payment": ("d Payment", "d払い"),
}


def to_english(apps, schema_editor):
    PaymentMethod = apps.get_model("stores", "PaymentMethod")
    for code, (english, _japanese) in RENAMES.items():
        PaymentMethod.objects.filter(code=code).update(name=english)


def to_japanese(apps, schema_editor):
    PaymentMethod = apps.get_model("stores", "PaymentMethod")
    for code, (_english, japanese) in RENAMES.items():
        PaymentMethod.objects.filter(code=code).update(name=japanese)


class Migration(migrations.Migration):
    dependencies = [("stores", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="paymentmethod",
            name="category",
            field=models.CharField(
                choices=[
                    ("cash", "Cash"),
                    ("card", "Credit card"),
                    ("qr", "QR code payment"),
                    ("e_money", "E-money"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="storepaymentmethod",
            name="status",
            field=models.CharField(
                choices=[
                    ("accepted", "Accepted"),
                    ("not_accepted", "Not accepted"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.RunPython(to_english, to_japanese),
    ]
