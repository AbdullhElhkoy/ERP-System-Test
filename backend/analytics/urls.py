from django.urls import path, include
from rest_framework.routers import DefaultRouter
from analytics import views

app_name = "analytics"

# HTML views
urlpatterns = [
    path("", views.analytics_dashboard, name="dashboard"),
    path("production/", views.production_analytics, name="production"),
    path("stock/", views.stock_analytics, name="stock"),
    path("spc/", views.spc_analytics, name="spc"),
    path("quality/", views.quality_analytics, name="quality"),
    # JSON API for AJAX charts
    path("api/production-chart/", views.api_production_chart, name="api_production_chart"),
    path("api/stock-snapshot/", views.api_stock_snapshot, name="api_stock_snapshot"),
    path("api/spc-data/", views.api_spc_data, name="api_spc_data"),
]
