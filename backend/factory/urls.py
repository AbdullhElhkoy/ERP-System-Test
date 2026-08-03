from django.urls import path
from . import views

app_name = "factory"

urlpatterns = [
    path("process-reading-grid/", views.process_reading_grid, name="process_reading_grid"),
]