from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalesOrderViewSet

router = DefaultRouter()
router.register(r'orders', SalesOrderViewSet, basename='sales-orders')
router.register(r'', SalesOrderViewSet, basename='sales')

urlpatterns = [
    path('', include(router.urls)),
]
