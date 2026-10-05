from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerLedgerViewSet, SupplierLedgerViewSet

router = DefaultRouter()
router.register(r'customer-ledger', CustomerLedgerViewSet, basename='customer-ledger')
router.register(r'supplier-ledger', SupplierLedgerViewSet, basename='supplier-ledger')

urlpatterns = [
    path('', include(router.urls)),
]
