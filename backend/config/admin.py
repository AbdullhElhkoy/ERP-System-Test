import types
from django.contrib import admin

REACTION_MODELS = {"ProcessStage", "ProcessStageTest", "ProcessReading", "ProcessAnalysisResult"}
FINAL_PRODUCT_MODELS = {
    "OutputPoint", "OutputPointTest", "OutputReading", "OutputAnalysisResult",
    "QualityConformityResult", "PackingEvent", "PackingConversion", "PlantLotSetting",
    "Ton", "RepresentativeSample", "TonPhysicalResult", "SampleChemicalResult", "TonGradeAssignment",
}


def get_app_list(self, request, app_label=None):
    app_list = admin.AdminSite.get_app_list(self, request, app_label)
    new_list = []
    for app in app_list:
        if app["app_label"] != "factory":
            new_list.append(app)
            continue

        plant_models = [m for m in app["models"] if m["object_name"] == "FactoryPlant"]
        reaction_models = [m for m in app["models"] if m["object_name"] in REACTION_MODELS]
        final_models = [m for m in app["models"] if m["object_name"] in FINAL_PRODUCT_MODELS]
        used = REACTION_MODELS | FINAL_PRODUCT_MODELS | {"FactoryPlant"}
        shared_models = [m for m in app["models"] if m["object_name"] not in used]

        if plant_models:
            new_list.append({**app, "name": "Factory", "app_label": "factory", "models": plant_models})
        if shared_models:
            new_list.append({**app, "name": "Factory - Shared Definitions", "app_label": "factory_shared", "models": shared_models})
        if reaction_models:
            new_list.append({**app, "name": "Factory - Reaction", "app_label": "factory_reaction", "models": reaction_models})
        if final_models:
            new_list.append({**app, "name": "Factory - Final Product", "app_label": "factory_final", "models": final_models})
    return new_list


admin.site.get_app_list = types.MethodType(get_app_list, admin.site)
