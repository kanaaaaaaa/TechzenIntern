from django.db.models import Prefetch
from rest_framework import filters, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import issue_token, password_matches
from .models import PaymentMethod, Store, StorePaymentMethod
from .serializers import PaymentMethodSerializer, StoreSerializer


class AppAccessView(APIView):
    """Exchanges the shared app password for the token the app sends back."""

    permission_classes = [AllowAny]

    def post(self, request):
        if not password_matches(request.data.get("password")):
            raise ValidationError({"password": ["That password is not correct."]})
        return Response({"token": issue_token()})


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
