from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, UnitViewSet, ProductViewSet, ProductVarietyViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'units', UnitViewSet)
router.register(r'varieties', ProductVarietyViewSet)
router.register(r'', ProductViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
