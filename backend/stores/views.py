import json
import math
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch, Q
from rest_framework import filters, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import issue_token, password_matches
from .models import PaymentMethod, Store, StoreComment, StoreFeedback, StorePaymentMethod, UserPoints
from .serializers import PaymentMethodSerializer, StoreCommentSerializer, StoreSerializer
from rest_framework.decorators import action

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


class AccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username": request.user.username,
            "date_joined": request.user.date_joined,
        })


class UserPointsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        points, _ = UserPoints.objects.get_or_create(user=request.user)
        return Response({"total_points": points.total_points})
class NearbyPlacesView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            latitude = float(
                request.data.get("latitude")
            )
            longitude = float(
                request.data.get("longitude")
            )
            radius = float(
                request.data.get("radius", 1000)
            )
        except (TypeError, ValueError):
            raise ValidationError({
                "location": [
                    "Valid latitude and longitude are required."
                ]
            })

        if not -90 <= latitude <= 90:
            raise ValidationError({
                "latitude": ["Invalid latitude."]
            })

        if not -180 <= longitude <= 180:
            raise ValidationError({
                "longitude": ["Invalid longitude."]
            })

        if radius <= 0 or radius > 2000:
            raise ValidationError({
                "radius": [
                    "Radius must be between 1 and 2000 meters."
                ]
            })

        if not settings.GOOGLE_PLACES_API_KEY:
            return Response(
                {
                    "detail":
                    "GOOGLE_PLACES_API_KEY is not set."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payload = {
            "includedTypes": [
                "restaurant",
                "cafe",
                "coffee_shop",
                "bakery",
                "bar",
                "meal_takeaway",
                "food_court",
                "dessert_shop",
                "ice_cream_shop",

                "convenience_store",
                "supermarket",
                "grocery_store",
                "department_store",
                "shopping_mall",
                "store",
                "market",

                "pharmacy",
                "drugstore",

                "gas_station",
                "parking",

                "hotel",
                "lodging",

                "movie_theater",

                "beauty_salon",
                "hair_salon",
                "barber_shop",
                "nail_salon",
                "laundry",
                "spa",

                "gym",
            ],
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius,
                }
            },
        }

        google_request = urllib_request.Request(
            "https://places.googleapis.com/v1/places:searchNearby",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key":
                    settings.GOOGLE_PLACES_API_KEY,
                "X-Goog-FieldMask": (
                    "places.id,"
                    "places.displayName,"
                    "places.formattedAddress,"
                    "places.location"
                ),
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(
                google_request,
                timeout=10,
            ) as response:
                data = json.load(response)

        except urllib_error.HTTPError as exc:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            return Response(
                {
                    "detail":
                    f"Google Places API error: {detail}"
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except urllib_error.URLError:
            return Response(
                {
                    "detail":
                    "Could not reach Google Places API."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        places = []

        for place in data.get("places", []):
            location = place.get("location") or {}

            places.append({
                "place_id": place.get("id"),
                "name": (
                    place.get("displayName") or {}
                ).get("text", ""),
                "address":
                    place.get("formattedAddress", ""),
                "latitude":
                    location.get("latitude"),
                "longitude":
                    location.get("longitude"),
            })

        return Response(places)


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

    def get_permissions(self):
        # Searching, viewing, and adding store info stay open to everyone.
        # Voting Good/Bad and posting/editing comments require an account.
        if self.action == "feedback":
            return [IsAuthenticated()]
        if self.action == "comments" and self.request.method in ("POST", "PATCH"):
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        statuses = StorePaymentMethod.objects.select_related("payment_method")
        queryset = Store.objects.prefetch_related(
            Prefetch("payment_methods", queryset=statuses)
        ).annotate(
            # One aggregate query for the whole page instead of three (or,
            # with my_feedback below, four) queries per row -- with a few
            # thousand stores that difference is the gap between a normal
            # response and the worker running out of memory.
            annotated_helpful_count=Count(
                "feedback_votes",
                filter=Q(feedback_votes__vote=StoreFeedback.Vote.HELPFUL),
                distinct=True,
            ),
            annotated_not_helpful_count=Count(
                "feedback_votes",
                filter=Q(feedback_votes__vote=StoreFeedback.Vote.NOT_HELPFUL),
                distinct=True,
            ),
            annotated_comment_count=Count("comments", distinct=True),
        )

        # Filter by payment methods (OR logic - store must have AT LEAST ONE
        # selected method with the given status).
        payment_methods_param = self.request.query_params.get("payment_methods")
        payment_method_status = self.request.query_params.get("payment_method_status")

        if payment_methods_param:
            method_ids = [int(id_str) for id_str in payment_methods_param.split(",") if id_str.isdigit()]
            if method_ids:
                filter_status = payment_method_status or "accepted"
                queryset = queryset.filter(
                    payment_methods__payment_method_id__in=method_ids,
                    payment_methods__status=filter_status,
                ).distinct()

        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch(
                    "feedback_votes",
                    queryset=StoreFeedback.objects.filter(user=user),
                    to_attr="my_feedback_votes",
                )
            )
        return queryset

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        try:
            latitude = float(request.query_params["latitude"])
            longitude = float(request.query_params["longitude"])
            radius = float(request.query_params.get("radius", 1000))
        except (KeyError, TypeError, ValueError):
            raise ValidationError(
                {"detail": "latitude, longitude, and radius must be valid numbers."}
            )

        radius = min(max(radius, 1), 5000)
        lat_delta = radius / 111320
        lng_delta = radius / (
            111320 * max(math.cos(math.radians(latitude)), 0.01)
        )

        candidates = Store.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=latitude - lat_delta,
            latitude__lte=latitude + lat_delta,
            longitude__gte=longitude - lng_delta,
            longitude__lte=longitude + lng_delta,
        )

        payment_methods_param = request.query_params.get("payment_methods")

        if payment_methods_param:
            method_ids = [
                int(value)
                for value in payment_methods_param.split(",")
                if value.isdigit()
            ]

            if method_ids:
                candidates = candidates.filter(
                    payment_methods__payment_method_id__in=method_ids,
                    payment_methods__status="accepted",
                ).distinct()

        stores = []
        for store in candidates:
            store_latitude = float(store.latitude)
            store_longitude = float(store.longitude)

            lat1 = math.radians(latitude)
            lat2 = math.radians(store_latitude)
            delta_lat = math.radians(store_latitude - latitude)
            delta_lng = math.radians(store_longitude - longitude)

            a = (
                math.sin(delta_lat / 2) ** 2
                + math.cos(lat1)
                * math.cos(lat2)
                * math.sin(delta_lng / 2) ** 2
            )

            distance = 6371000 * 2 * math.atan2(
                math.sqrt(a),
                math.sqrt(max(0, 1 - a)),
            )

            if distance <= radius:
                stores.append({
                    "id": store.id,
                    "name": store.name,
                    "address": store.address,
                    "latitude": str(store.latitude),
                    "longitude": str(store.longitude),
                })

        return Response(stores)

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
