from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import PaymentMethod, Store, StorePaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = PaymentMethod
        fields = ["id", "code", "name", "category", "category_label", "display_order"]


class StorePaymentMethodSerializer(serializers.ModelSerializer):
    payment_method = PaymentMethodSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = StorePaymentMethod
        fields = ["payment_method", "status", "status_label", "confirmed_at"]


class PaymentStatusInputSerializer(serializers.Serializer):
    payment_method_id = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=StorePaymentMethod.Status.choices)


class StoreSerializer(serializers.ModelSerializer):
    payment_methods = StorePaymentMethodSerializer(many=True, read_only=True)
    payment_statuses = PaymentStatusInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "address",
            "payment_methods",
            "payment_statuses",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        candidate = Store(
            pk=self.instance.pk if self.instance else None,
            name=attrs.get("name", getattr(self.instance, "name", "")),
            address=attrs.get("address", getattr(self.instance, "address", "")),
        )
        if candidate.duplicates().exists():
            raise serializers.ValidationError("A store with this name and address already exists.")
        return attrs

    def validate_payment_statuses(self, values):
        method_ids = [value["payment_method_id"] for value in values]
        if len(method_ids) != len(set(method_ids)):
            raise serializers.ValidationError("A payment method cannot be specified more than once.")

        existing_ids = set(
            PaymentMethod.objects.filter(id__in=method_ids, is_active=True).values_list("id", flat=True)
        )
        missing_ids = sorted(set(method_ids) - existing_ids)
        if missing_ids:
            raise serializers.ValidationError(f"Unavailable payment method IDs: {missing_ids}")
        return values

    @staticmethod
    def _save_statuses(store, statuses):
        for value in statuses:
            status = value["status"]
            StorePaymentMethod.objects.update_or_create(
                store=store,
                payment_method_id=value["payment_method_id"],
                defaults={
                    "status": status,
                    "confirmed_at": None if status == StorePaymentMethod.Status.UNKNOWN else timezone.now(),
                },
            )

    @transaction.atomic
    def create(self, validated_data):
        statuses = validated_data.pop("payment_statuses", [])
        store = Store.objects.create(**validated_data)
        supplied = {value["payment_method_id"] for value in statuses}
        StorePaymentMethod.objects.bulk_create([
            StorePaymentMethod(store=store, payment_method=method)
            for method in PaymentMethod.objects.filter(is_active=True)
            if method.id not in supplied
        ])
        self._save_statuses(store, statuses)
        return store

    @transaction.atomic
    def update(self, instance, validated_data):
        statuses = validated_data.pop("payment_statuses", None)
        instance = super().update(instance, validated_data)
        if statuses is not None:
            self._save_statuses(instance, statuses)
        return instance

