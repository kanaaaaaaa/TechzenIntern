from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import PaymentMethod, Store, StoreFeedback, StorePaymentMethod

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

    helpful_count = serializers.SerializerMethodField()
    not_helpful_count = serializers.SerializerMethodField()
    my_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "payment_methods",
            "payment_statuses",
            "helpful_count",
            "not_helpful_count",
            "my_feedback",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_helpful_count(self, obj):
        return obj.feedback_votes.filter(
            vote=StoreFeedback.Vote.HELPFUL
        ).count()

    def get_not_helpful_count(self, obj):
        return obj.feedback_votes.filter(
            vote=StoreFeedback.Vote.NOT_HELPFUL
        ).count()

    def get_my_feedback(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        return (
            obj.feedback_votes
            .filter(user=request.user)
            .values_list("vote", flat=True)
            .first()
        )

    def validate(self, attrs):
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                "Latitude and longitude must either both be supplied or both be empty."
            )
        candidate = Store(
            pk=self.instance.pk if self.instance else None,
            name=attrs.get("name", getattr(self.instance, "name", "")),
            address=attrs.get("address", getattr(self.instance, "address", "")),
            latitude=latitude,
            longitude=longitude,
        )
        if candidate.duplicates().exists():
            raise serializers.ValidationError(
                "A store with this name, address and coordinates already exists."
            )
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

    #以下変更点
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Store
        fields = [
            # ... 既存フィールド ...
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]
