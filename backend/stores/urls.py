from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AppAccessView,
    LoginView,
    LogoutView,
    PaymentMethodViewSet,
    RegisterView,
    StoreViewSet,
)

router = DefaultRouter()
router.register("stores", StoreViewSet, basename="store")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
] + router.urls