from django.urls import path
from . import views

app_name = "hr"

urlpatterns = [
    path("dashboard/", views.hr_dashboard, name="dashboard"),
]
