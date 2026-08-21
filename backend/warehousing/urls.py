from django.urls import path

from .views import (
    warehousing_hub,
    raw_materials_hub,
    warehousing_settings,
    coming_soon,
    select_plant,
    delivery_entry,
    deliveries_data,
    delivery_edit,
    deliveries_reports,
    deliveries_analysis,
    analysis1_entry,
    chemical_analysis,
    weighing_entry,
    issue_entry,
    analysis2_entry,
    spare_parts_hub,
    spare_parts_settings,
    spare_parts_data,
    spare_parts_reports,
    spare_parts_analysis,
    packaging_hub,
    packaging_settings,
    packaging_data,
    packaging_reports,
    packaging_analysis,
    final_products_hub,
    final_products_settings,
    final_products_data,
    final_products_reports,
    final_products_analysis,
)

app_name = "warehousing"

urlpatterns = [
    path("", warehousing_hub, name="warehousing_hub"),

    # ── Raw Materials ────────────────────────────────────────
    path("raw-materials/", raw_materials_hub, name="raw_materials_hub"),
    path("raw-materials/settings/", warehousing_settings, name="warehousing_settings"),
    path("raw-materials/select-plant/<int:plant_id>/", select_plant, name="select_plant"),
    path("raw-materials/delivery-entry/", delivery_entry, name="delivery_entry"),
    path("raw-materials/data/", deliveries_data, name="deliveries_data"),
    path("raw-materials/data/delivery/<int:delivery_id>/", delivery_edit, name="delivery_edit"),
    path("raw-materials/reports/", deliveries_reports, name="deliveries_reports"),
    path("raw-materials/analysis/", deliveries_analysis, name="deliveries_analysis"),
    path("raw-materials/analysis1/", analysis1_entry, name="analysis1_entry"),
    path("raw-materials/chemical-analysis/", chemical_analysis, name="chemical_analysis"),
    path("raw-materials/chemical-analysis/<int:sample_id>/", chemical_analysis, name="chemical_analysis_detail"),
    path("raw-materials/weighing/", weighing_entry, name="weighing_entry"),
    path("raw-materials/issue/", issue_entry, name="issue_entry"),
    path("raw-materials/analysis2/", analysis2_entry, name="analysis2_entry"),

    # ── Spare Parts ──────────────────────────────────────────
    path("spare-parts/", spare_parts_hub, name="spare_parts"),
    path("spare-parts/settings/", spare_parts_settings, name="spare_parts_settings"),
    path("spare-parts/data/", spare_parts_data, name="spare_parts_data"),
    path("spare-parts/reports/", spare_parts_reports, name="spare_parts_reports"),
    path("spare-parts/analysis/", spare_parts_analysis, name="spare_parts_analysis"),

    # ── Packaging Materials ──────────────────────────────────
    path("packaging-materials/", packaging_hub, name="packaging_materials"),
    path("packaging-materials/settings/", packaging_settings, name="packaging_settings"),
    path("packaging-materials/data/", packaging_data, name="packaging_data"),
    path("packaging-materials/reports/", packaging_reports, name="packaging_reports"),
    path("packaging-materials/analysis/", packaging_analysis, name="packaging_analysis"),

    # ── Final Products ───────────────────────────────────────
    path("final-product/", final_products_hub, name="final_product"),
    path("final-product/settings/", final_products_settings, name="final_products_settings"),
    path("final-product/data/", final_products_data, name="final_products_data"),
    path("final-product/reports/", final_products_reports, name="final_products_reports"),
    path("final-product/analysis/", final_products_analysis, name="final_products_analysis"),
]
