import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def normalize(value):
    return unicodedata.normalize("NFKC", value or "").casefold().strip()


class Store(models.Model):
    name = models.CharField(max_length=160)
    normalized_name = models.CharField(max_length=160, db_index=True, editable=False)
    address = models.CharField(max_length=255, blank=True)
    normalized_address = models.CharField(max_length=255, blank=True, editable=False)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_name", "normalized_address", "latitude", "longitude"],
                name="unique_store_location",
                nulls_distinct=False,
            ),
        ]

    def duplicates(self):
        """Stores that already use this name, address and coordinates."""
        found = Store.objects.filter(
            normalized_name=normalize(self.name),
            normalized_address=normalize(self.address),
            latitude=self.latitude,
            longitude=self.longitude,
        )
        return found.exclude(pk=self.pk) if self.pk else found

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError(
                "Latitude and longitude must either both be supplied or both be empty."
            )
        # The constraint covers non-editable fields, which forms skip, so the
        # duplicate has to be reported from here to reach the admin site.
        if self.duplicates().exists():
            raise ValidationError("A store with this name, address and coordinates already exists.")

    def save(self, *args, **kwargs):
        self.normalized_name = normalize(self.name)
        self.normalized_address = normalize(self.address)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class StoreFeedback(models.Model):
    class Vote(models.TextChoices):
        HELPFUL = "helpful", "Helpful"
        NOT_HELPFUL = "not_helpful", "Not helpful"

    store = models.ForeignKey(
        Store,
        related_name="feedback_votes",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="store_feedback_votes",
        on_delete=models.CASCADE,
    )
    vote = models.CharField(max_length=20, choices=Vote.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["store", "user"],
                name="unique_store_feedback_user",
            ),
        ]

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

class UserPoints(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="points",
        on_delete=models.CASCADE,
    )
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.points}p"


class PointHistory(models.Model):
    class ActionType(models.TextChoices):
        CREATE_STORE = "create_store", "New store (+3p)"
        EDIT_STORE = "edit_store", "Edit store (+1p)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="point_history",
        on_delete=models.CASCADE,
    )
    store = models.ForeignKey(Store, related_name="point_histories", on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    points = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} ({self.points}p)"
