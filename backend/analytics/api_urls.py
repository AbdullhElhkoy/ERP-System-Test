from django.urls import path, include
from rest_framework.routers import DefaultRouter
from analytics import views

router = DefaultRouter()
router.register(r"aggregate", views.AggregateViewSet, basename="aggregate")
router.register(r"stock", views.StockRealtimeViewSet, basename="stock")
router.register(r"spc", views.SPCViewSet, basename="spc")

urlpatterns = [
    path("", include(router.urls)),
]
