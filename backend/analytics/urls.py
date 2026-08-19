from django.urls import path, include
from rest_framework.routers import DefaultRouter
from analytics.views import AggregateViewSet, StockRealtimeViewSet, SPCViewSet

router = DefaultRouter()
router.register(r"aggregate", AggregateViewSet, basename="aggregate")
router.register(r"stock", StockRealtimeViewSet, basename="stock")
router.register(r"spc", SPCViewSet, basename="spc")

app_name = "analytics"

urlpatterns = [
    path("", include(router.urls)),
]
