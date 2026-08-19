from django.urls import path
from . import views

app_name = "it"

urlpatterns = [
    path("dashboard/", views.it_dashboard, name="dashboard"),
]
