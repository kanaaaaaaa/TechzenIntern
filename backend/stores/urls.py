from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AppAccessView, PaymentMethodViewSet, StoreViewSet


router = DefaultRouter()
router.register("stores", StoreViewSet, basename="store")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")

urlpatterns = [path("access/", AppAccessView.as_view(), name="app-access")] + router.urls
