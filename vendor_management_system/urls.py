from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, PurchaseOrderViewSet, HistoricalPerformanceViewSet, RegisterUser

router = DefaultRouter()
router.register(r'vendors', VendorViewSet)
router.register(r'purchase_orders', PurchaseOrderViewSet)
router.register(r'historical_performance', HistoricalPerformanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # path('register/', RegisterUser.as_view(), name='register_user'),
]
