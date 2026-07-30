from django.urls import path
from .views import next_sequence_preview

app_name = "dcp"

urlpatterns = [
    path("next-sequence-preview/", next_sequence_preview, name="next_sequence_preview"),
]
