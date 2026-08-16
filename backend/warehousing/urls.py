from django.urls import path

from .views import (
    raw_materials_hub,
    coming_soon,
    select_plant,
    delivery_entry,
    deliveries_data,
    delivery_edit,
    deliveries_reports,
    deliveries_analysis,
)

app_name = "warehousing"

urlpatterns = [
    path("raw-materials/", raw_materials_hub, name="raw_materials_hub"),
    path("raw-materials/select-plant/<int:plant_id>/", select_plant, name="select_plant"),
    path("raw-materials/delivery-entry/", delivery_entry, name="delivery_entry"),
    path("raw-materials/data/", deliveries_data, name="deliveries_data"),
    path("raw-materials/data/delivery/<int:delivery_id>/", delivery_edit, name="delivery_edit"),
    path("raw-materials/reports/", deliveries_reports, name="deliveries_reports"),
    path("raw-materials/analysis/", deliveries_analysis, name="deliveries_analysis"),
    path(
        "spare-parts/",
        coming_soon,
        {"section_name": "قطع الغيار (Spare Parts)"},
        name="spare_parts",
    ),
    path(
        "final-product/",
        coming_soon,
        {"section_name": "المنتج النهائي (Final Products)"},
        name="final_product",
    ),
]
