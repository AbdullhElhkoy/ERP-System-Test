import types
from django.contrib import admin
from django.urls import reverse
from plants.models import Plant


VIEW_PERMS = {"add": False, "change": False, "delete": False, "view": True}

HIDDEN_APP_LABELS = {"raw_materials", "spare_parts", "packaging", "finished_products"}


def _admin_link(app_label, model_name, title):
    return {
        "name": title,
        "object_name": model_name,
        "perms": VIEW_PERMS,
        "admin_url": reverse(f"admin:{app_label}_{model_name}_changelist"),
        "add_url": None,
        "view_only": True,
    }


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
        _admin_link("spare_parts", "sparepartitem", "Spare Part Items"),
        _admin_link("spare_parts", "sparepartstocktransaction", "Stock Transactions"),
        _admin_link("spare_parts", "receivingvoucher", "Receiving Vouchers"),
        _admin_link("spare_parts", "issuevoucher", "Issue Vouchers"),
        _admin_link("spare_parts", "sparepartstockbalance", "Stock Balances"),
        _admin_link("spare_parts", "stockcount", "Stock Counts"),
        _admin_link("finished_products", "product", "Products"),
        _admin_link("finished_products", "stockledger", "Stock Ledger"),
        _admin_link("finished_products", "stockbalance", "Stock Balances"),
        _admin_link("packaging", "packagingmaterial", "Packaging Materials"),
        _admin_link("packaging", "packagingsupplier", "Packaging Suppliers"),
        _admin_link("packaging", "packagingreceiving", "Receiving Records"),
        _admin_link("packaging", "packagingstockledger", "Stock Ledger"),
        _admin_link("packaging", "packagingstockbalance", "Stock Balances"),
        _admin_link("packaging", "factorypackagingstock", "Factory Packaging Stock"),
        _admin_link("packaging", "packingoperation", "Packing Operations"),
        _admin_link("packaging", "packagingreconciliation", "Reconciliation"),
        _admin_link("packaging", "supplierevaluation", "Supplier Evaluation"),
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
