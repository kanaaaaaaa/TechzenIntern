import unicodedata

from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=160)
    normalized_name = models.CharField(max_length=160, db_index=True, editable=False)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def save(self, *args, **kwargs):
        self.normalized_name = unicodedata.normalize("NFKC", self.name).casefold().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    class Category(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Credit card"
        QR = "qr", "QR code payment"
        E_MONEY = "e_money", "E-money"

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.name


class StorePaymentMethod(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        NOT_ACCEPTED = "not_accepted", "Not accepted"
        UNKNOWN = "unknown", "Unknown"

    store = models.ForeignKey(Store, related_name="payment_methods", on_delete=models.CASCADE)
    payment_method = models.ForeignKey(PaymentMethod, related_name="stores", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNKNOWN)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payment_method__display_order", "payment_method_id"]
        constraints = [
            models.UniqueConstraint(fields=["store", "payment_method"], name="unique_store_payment_method"),
        ]

    def __str__(self):
        return f"{self.store} - {self.payment_method}: {self.get_status_display()}"

