from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from rest_framework import filters, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import issue_token, password_matches
from .models import PaymentMethod, Store, StorePaymentMethod
from .serializers import PaymentMethodSerializer, StoreSerializer

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get("username") or "").strip()

        if not username:
            raise ValidationError({"username": ["Username is required."]})

        if User.objects.filter(username=username).exists():
            raise ValidationError(
                {"username": ["This username is already in use."]}
            )

        user = User.objects.create_user(username=username)
        token = Token.objects.create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get("username") or "").strip()

        if not username:
            raise ValidationError({"username": ["Username is required."]})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValidationError(
                {"username": ["This username does not exist."]}
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.username,
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class AppAccessView(APIView):
    """Exchanges the shared app password for the token the app sends back."""

    permission_classes = [AllowAny]
    # The only endpoint that can be guessed at, and there is a single password
    # for everyone to guess, so cap the attempts. Rate: DEFAULT_THROTTLE_RATES.
    throttle_scope = "app-access"

    def post(self, request):
        if not password_matches(request.data.get("password")):
            raise ValidationError({"password": ["That password is not correct."]})
        return Response({"token": issue_token()})


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "normalized_name", "address"]
    ordering_fields = ["name", "latitude", "longitude", "updated_at", "created_at"]
    ordering = ["name", "id"]

    def get_queryset(self):
        statuses = StorePaymentMethod.objects.select_related("payment_method")
        return Store.objects.prefetch_related(Prefetch("payment_methods", queryset=statuses))


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentMethodSerializer
    pagination_class = None

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)
