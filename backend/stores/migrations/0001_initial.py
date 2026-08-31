from django.db import migrations, models
import django.db.models.deletion


def seed_payment_methods(apps, schema_editor):
    PaymentMethod = apps.get_model("stores", "PaymentMethod")
    methods = [
        ("cash", "Cash", "cash"),
        ("credit-card", "Credit card", "card"),
        ("e-money", "E-money", "e_money"),
        ("qr", "QR code payment", "qr"),
    ]
    PaymentMethod.objects.bulk_create([
        PaymentMethod(code=code, name=name, category=category, display_order=index * 10)
        for index, (code, name, category) in enumerate(methods, start=1)
    ])


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="PaymentMethod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("category", models.CharField(choices=[("cash", "Cash"), ("card", "Credit card"), ("qr", "QR code payment"), ("e_money", "E-money")], max_length=20)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["display_order", "id"]},
        ),
        migrations.CreateModel(
            name="Store",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("normalized_name", models.CharField(db_index=True, editable=False, max_length=160)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="StorePaymentMethod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("accepted", "Accepted"), ("not_accepted", "Not accepted"), ("unknown", "Unknown")], default="unknown", max_length=20)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("payment_method", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stores", to="stores.paymentmethod")),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_methods", to="stores.store")),
            ],
            options={"ordering": ["payment_method__display_order", "payment_method_id"]},
        ),
        migrations.AddConstraint(
            model_name="storepaymentmethod",
            constraint=models.UniqueConstraint(fields=("store", "payment_method"), name="unique_store_payment_method"),
        ),
        migrations.RunPython(seed_payment_methods, migrations.RunPython.noop),
    ]

