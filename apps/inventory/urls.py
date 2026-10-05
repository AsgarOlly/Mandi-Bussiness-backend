from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InventoryLotViewSet,
    InventoryTransactionViewSet
)

router = DefaultRouter()
router.register(r'lots', InventoryLotViewSet)
router.register(r'transactions', InventoryTransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
