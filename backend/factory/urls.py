from django.urls import path

from .views import process_reading_grid, final_product_entry_grid

app_name = "factory"

urlpatterns = [
    path("process-reading/", process_reading_grid, name="process_reading_grid"),
    path(
        "final-product/<int:plant_id>/<slug:packing_slug>/",
        final_product_entry_grid,
        name="final_product_entry_grid",
    ),
]
