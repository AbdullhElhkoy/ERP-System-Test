import types
from django.contrib import admin
from django.urls import reverse
from plants.models import Plant


VIEW_PERMS = {"add": False, "change": False, "delete": False, "view": True}

HIDDEN_APP_LABELS = {"raw_materials", "spare_parts", "packaging", "finished_products"}


def _warehouse_section():
    entries = [
        {
            "name": "Raw Materials",
            "object_name": "RawMaterials",
            "perms": VIEW_PERMS,
            "admin_url": reverse("warehousing:raw_materials_hub"),
            "add_url": None,
            "view_only": True,
        },
        {
            "name": "Spare Parts",
            "object_name": "SpareParts",
            "perms": VIEW_PERMS,
            "admin_url": reverse("warehousing:spare_parts"),
            "add_url": None,
            "view_only": True,
        },
        {
            "name": "Final Products",
            "object_name": "FinalProduct",
            "perms": VIEW_PERMS,
            "admin_url": reverse("warehousing:final_product"),
            "add_url": None,
            "view_only": True,
        },
        {
            "name": "Packaging Materials",
            "object_name": "PackagingMaterials",
            "perms": VIEW_PERMS,
            "admin_url": reverse("warehousing:packaging_materials"),
            "add_url": None,
            "view_only": True,
        },
    ]
    return {
        "name": "Warehousing",
        "app_label": "warehousing",
        "app_url": reverse("warehousing:warehousing_hub"),
        "models": entries,
    }


def get_app_list(self, request, app_label=None):
    app_list = admin.AdminSite.get_app_list(self, request, app_label)
    new_list = []

    for app in app_list:
        if app["app_label"] in HIDDEN_APP_LABELS:
            continue

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

            new_list.append({**app, "name": "Factory", "app_label": "factory", "models": entries})

    new_list.append(_warehouse_section())

    return new_list


admin.site.get_app_list = types.MethodType(
    get_app_list,
    admin.site
)
