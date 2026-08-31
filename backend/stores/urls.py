from rest_framework.routers import DefaultRouter

from .views import PaymentMethodViewSet, StoreViewSet


router = DefaultRouter()
router.register("stores", StoreViewSet, basename="store")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")

urlpatterns = router.urls

