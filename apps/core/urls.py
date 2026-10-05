from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import health_check, reset_all_data, AuditLogViewSet

router = DefaultRouter()
router.register(r'audit-logs', AuditLogViewSet)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('reset-all-data/', reset_all_data, name='reset_all_data'),
    path('', include(router.urls)),
]
