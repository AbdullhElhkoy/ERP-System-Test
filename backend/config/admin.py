import types
from django.contrib import admin
from django.urls import reverse
from plants.models import Plant


REACTION_MODELS = {
    "ProcessStage",
    "ProcessStageTest",
    "ProcessReading",
    "ProcessAnalysisResult",
}

FINAL_PRODUCT_MODELS = {
    "OutputPoint",
    "OutputPointTest",
    "OutputReading",
    "OutputAnalysisResult",
    "QualityConformityResult",
    "PackingEvent",
    "PackingConversion",
    "PlantLotSetting",
    "Ton",
    "RepresentativeSample",
    "TonPhysicalResult",
    "SampleChemicalResult",
    "TonGradeAssignment",
    "GradeReason",
    "RepresentativeGroupSize",
    "FieldDefinition",
    "PackingTypeField",
    "FloorStockBalance",
    "FloorStockMovement",
}


def get_app_list(self, request, app_label=None):
    app_list = admin.AdminSite.get_app_list(self, request, app_label)
    new_list = []

    for app in app_list:
        if app["app_label"] != "factory":
            new_list.append(app)
            continue

        plant_models = [
            m for m in app["models"]
            if m["object_name"] == "FactoryPlant"
        ]

        if plant_models:
            base_perms = plant_models[0]["perms"]
            add_url = plant_models[0].get("add_url")

            entries = [{
                "name": "+ New Factory",
                "object_name": "FactoryPlant",
                "perms": base_perms,
                "admin_url": add_url,
                "add_url": add_url,
                "view_only": False,
            }]
            for plant in Plant.objects.all().order_by("plant_name"):
                entries.append({
                    "name": plant.plant_name,
                    "object_name": "Plant",
                    "perms": base_perms,
                    "admin_url": reverse("admin:factory_enter_plant", args=[plant.pk]),
                    "add_url": None,
                    "view_only": False,
                })

            # بقية الموديلات (الإعدادات والبيانات) تظهر تحت قسم "Factory Data"
            data_models = [m for m in app["models"] if m["object_name"] != "FactoryPlant"]
            for entry in data_models:
                entry["name"] = f"⚙ {entry['name']}"
                entries.append(entry)

            new_list.append({**app, "name": "Factory", "app_label": "factory", "models": entries})

    return new_list


admin.site.get_app_list = types.MethodType(
    get_app_list,
    admin.site
)