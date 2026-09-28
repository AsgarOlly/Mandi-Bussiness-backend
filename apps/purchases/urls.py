from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseOrderViewSet, SupplierTruckPaymentViewSet

router = DefaultRouter()
router.register(r'truck-payments', SupplierTruckPaymentViewSet)
router.register(r'', PurchaseOrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
