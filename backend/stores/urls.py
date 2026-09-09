from django.urls import path
from rest_framework.routers import DefaultRouter

from .ocr import OcrView
from .views import (
    AccountView,
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
    path("auth/me/", AccountView.as_view(), name="account"),
    path("ocr/", OcrView.as_view(), name="ocr"),
] + router.urls