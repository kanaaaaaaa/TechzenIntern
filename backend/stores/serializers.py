from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import PaymentMethod, Store, StoreComment, StoreFeedback, StorePaymentMethod, UserPoints

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


class StoreCommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = StoreComment
        fields = [
            "id",
            "username",
            "text",
            "is_mine",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "is_mine",
            "created_at",
            "updated_at",
        ]

    def get_is_mine(self, obj):
        request = self.context.get("request")

        return bool(
            request
            and request.user.is_authenticated
            and obj.user_id == request.user.id
        )

class StoreSerializer(serializers.ModelSerializer):
    payment_methods = StorePaymentMethodSerializer(many=True, read_only=True)
    payment_statuses = PaymentStatusInputSerializer(many=True, write_only=True, required=False)

    helpful_count = serializers.SerializerMethodField()
    not_helpful_count = serializers.SerializerMethodField()
    my_feedback = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "category",
            "category_label",
            "payment_methods",
            "payment_statuses",
            "helpful_count",
            "not_helpful_count",
            "my_feedback",
            "comment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_helpful_count(self, obj):
        # StoreViewSet.get_queryset() annotates these in one aggregate query
        # per page; fall back to a live query for instances that bypass it
        # (e.g. the object create() just built, before it's re-fetched).
        annotated = getattr(obj, "annotated_helpful_count", None)
        if annotated is not None:
            return annotated
        return obj.feedback_votes.filter(
            vote=StoreFeedback.Vote.HELPFUL
        ).count()

    def get_not_helpful_count(self, obj):
        annotated = getattr(obj, "annotated_not_helpful_count", None)
        if annotated is not None:
            return annotated
        return obj.feedback_votes.filter(
            vote=StoreFeedback.Vote.NOT_HELPFUL
        ).count()

    def get_my_feedback(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        prefetched = getattr(obj, "my_feedback_votes", None)
        if prefetched is not None:
            return prefetched[0].vote if prefetched else None

        return (
            obj.feedback_votes
            .filter(user=request.user)
            .values_list("vote", flat=True)
            .first()
        )

    def get_comment_count(self, obj):
        annotated = getattr(obj, "annotated_comment_count", None)
        if annotated is not None:
            return annotated
        return obj.comments.count()

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

    def _award_points(self, points_to_add):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user_points, _ = UserPoints.objects.get_or_create(user=request.user)
            user_points.total_points += points_to_add
            user_points.save(update_fields=["total_points", "updated_at"])

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
        self._award_points(3)
        return store

    @transaction.atomic
    def update(self, instance, validated_data):
        statuses = validated_data.pop("payment_statuses", None)
        instance = super().update(instance, validated_data)
        if statuses is not None:
            self._save_statuses(instance, statuses)
        self._award_points(1)
        return instance
