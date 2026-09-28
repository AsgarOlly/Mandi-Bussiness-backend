from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerLedgerViewSet, SupplierLedgerViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'customer-ledger', CustomerLedgerViewSet, basename='customer-ledger')
router.register(r'supplier-ledger', SupplierLedgerViewSet, basename='supplier-ledger')
router.register(r'payments', PaymentViewSet, basename='payments-list')
router.register(r'', PaymentViewSet, basename='payments-root')

urlpatterns = [
    path('', include(router.urls)),
]

