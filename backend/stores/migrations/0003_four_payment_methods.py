from django.db import migrations


# The four payment methods the app supports. Brand level entries (Visa, PayPay,
# Suica, ...) are collapsed into these.
CANONICAL = [
    # canonical code, old codes to absorb, name, category, display_order
    ("cash", ["cash"], "Cash", "cash", 10),
    ("credit-card", ["credit", "credit-card"], "Credit card", "card", 20),
    ("e-money", ["e-money", "e_money"], "E-money", "e_money", 30),
    ("qr", ["QR", "qr"], "QR code payment", "qr", 40),
]

RETIRED_SEED = [
    ("visa", "Visa", "card"),
    ("mastercard", "Mastercard", "card"),
    ("jcb", "JCB", "card"),
    ("paypay", "PayPay", "qr"),
    ("rakuten-pay", "Rakuten Pay", "qr"),
    ("d-payment", "d Payment", "qr"),
    ("au-pay", "au PAY", "qr"),
    ("suica", "Suica", "e_money"),
    ("pasmo", "PASMO", "e_money"),
]


def collapse(apps, schema_editor):
    PaymentMethod = apps.get_model("stores", "PaymentMethod")
    StorePaymentMethod = apps.get_model("stores", "StorePaymentMethod")

    keep_ids = []
    for code, old_codes, name, category, order in CANONICAL:
        method = PaymentMethod.objects.filter(code__in=old_codes).order_by("id").first()
        if method is None:
            method = PaymentMethod(code=code)
        method.code = code
        method.name = name
        method.category = category
        method.display_order = order
        method.is_active = True
        method.save()
        keep_ids.append(method.id)

        # A duplicate row for the same category would break the unique code, so
        # fold any leftovers into the row we just kept.
        duplicates = PaymentMethod.objects.filter(code__in=old_codes).exclude(id=method.id)
        for duplicate in duplicates:
            StorePaymentMethod.objects.filter(payment_method=duplicate).update(payment_method=method)
        duplicates.delete()

    obsolete = PaymentMethod.objects.exclude(id__in=keep_ids)
    referenced_ids = set(
        StorePaymentMethod.objects.filter(payment_method__in=obsolete).values_list("payment_method_id", flat=True)
    )
    # Rows still attached to a store are protected by the FK, so retire them
    # instead of deleting; the rest go away.
    obsolete.filter(id__in=referenced_ids).update(is_active=False)
    obsolete.exclude(id__in=referenced_ids).delete()


def restore(apps, schema_editor):
    PaymentMethod = apps.get_model("stores", "PaymentMethod")
    for index, (code, name, category) in enumerate(RETIRED_SEED, start=2):
        PaymentMethod.objects.update_or_create(
            code=code,
            defaults={"name": name, "category": category, "display_order": index * 10, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [("stores", "0002_english_payment_method_names")]
    operations = [migrations.RunPython(collapse, restore)]
