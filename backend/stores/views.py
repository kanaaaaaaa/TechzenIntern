from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from rest_framework import filters, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import issue_token, password_matches, IsAuthenticatedOrHasAppAccess
from .models import PaymentMethod, Store, StoreComment, StoreFeedback, StorePaymentMethod, UserPoints, PointHistory
from .serializers import PaymentMethodSerializer, StoreCommentSerializer, StoreSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_points(request):
    user_points, _ = UserPoints.objects.get_or_create(user=request.user)
    history = PointHistory.objects.filter(user=request.user).order_by("-created_at")[:10]

    return Response({
        "total_points": user_points.points,
        "recent_history": [
            {
                "action": item.get_action_type_display(),
                "points": item.points,
                "store_name": item.store.name,
                "created_at": item.created_at,
            }
            for item in history
        ],
    })


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


class AccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username": request.user.username,
            "date_joined": request.user.date_joined,
        })


class AppAccessView(APIView):
    """Exchanges the shared app password for the token the app sends back."""

    permission_classes = [AllowAny]
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
    permission_classes = [IsAuthenticatedOrHasAppAccess]

    def get_queryset(self):
        statuses = StorePaymentMethod.objects.select_related("payment_method")
        return Store.objects.prefetch_related(Prefetch("payment_methods", queryset=statuses))

    @action(detail=True, methods=["post"])
    def feedback(self, request, pk=None):
        store = self.get_object()
        vote = request.data.get("vote")

        if vote is None:
            StoreFeedback.objects.filter(
                store=store,
                user=request.user,
            ).delete()
            current_vote = None

        elif vote in [
            StoreFeedback.Vote.HELPFUL,
            StoreFeedback.Vote.NOT_HELPFUL,
        ]:
            StoreFeedback.objects.update_or_create(
                store=store,
                user=request.user,
                defaults={"vote": vote},
            )
            current_vote = vote

        else:
            raise ValidationError(
                {"vote": ["Vote must be helpful, not_helpful, or null."]}
            )

        return Response({
            "helpful_count": store.feedback_votes.filter(
                vote=StoreFeedback.Vote.HELPFUL
            ).count(),
            "not_helpful_count": store.feedback_votes.filter(
                vote=StoreFeedback.Vote.NOT_HELPFUL
            ).count(),
            "my_feedback": current_vote,
        })

    def perform_create(self, serializer):
        with transaction.atomic():
            extra = {}
            if self.request.user.is_authenticated:
                extra["created_by"] = self.request.user
            store = serializer.save(**extra)
            self._award_points(
                user=self.request.user,
                store=store,
                action_type=PointHistory.ActionType.CREATE_STORE,
                points=3,
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            store = serializer.save()
            self._award_points(
                user=self.request.user,
                store=store,
                action_type=PointHistory.ActionType.EDIT_STORE,
                points=1,
            )

    def _award_points(self, user, store, action_type, points):
        if not user.is_authenticated:
            return
        user_points, _ = UserPoints.objects.get_or_create(user=user)
        user_points.points += points
        user_points.save(update_fields=["points", "updated_at"])

        PointHistory.objects.create(
            user=user,
            store=store,
            action_type=action_type,
            points=points,
        )

    @action(detail=True, methods=["get", "post", "patch"])
    def comments(self, request, pk=None):
        store = self.get_object()

        if request.method == "GET":
            comments = StoreComment.objects.filter(
                store=store
            ).select_related("user")

            serializer = StoreCommentSerializer(
                comments,
                many=True,
                context={"request": request},
            )
            return Response(serializer.data)

        if request.method == "POST":
            if StoreComment.objects.filter(
                store=store,
                user=request.user,
            ).exists():
                raise ValidationError({
                    "text": ["You can only post one comment per store."]
                })

            serializer = StoreCommentSerializer(
                data=request.data,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)

            comment = serializer.save(
                store=store,
                user=request.user,
            )

            return Response(
                StoreCommentSerializer(
                    comment,
                    context={"request": request},
                ).data,
                status=status.HTTP_201_CREATED,
            )

        try:
            comment = StoreComment.objects.get(
                store=store,
                user=request.user,
            )
        except StoreComment.DoesNotExist:
            raise ValidationError({
                "text": ["You have not posted a comment yet."]
            })

        serializer = StoreCommentSerializer(
            comment,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PaymentMethodSerializer
    pagination_class = None

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)
