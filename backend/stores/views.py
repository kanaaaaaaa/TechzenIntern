from django.db.models import Prefetch
from rest_framework import filters, viewsets

from .models import PaymentMethod, Store, StorePaymentMethod
from .serializers import PaymentMethodSerializer, StoreSerializer


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "normalized_name", "address"]
    ordering_fields = ["name", "updated_at", "created_at"]
    ordering = ["name", "id"]

    def get_queryset(self):
        statuses = StorePaymentMethod.objects.select_related("payment_method")
        return Store.objects.prefetch_related(Prefetch("payment_methods", queryset=statuses))


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentMethodSerializer
    pagination_class = None

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)

