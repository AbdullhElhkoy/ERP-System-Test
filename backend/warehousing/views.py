import json

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from django.utils.translation import gettext_lazy as _

from plants.models import Plant

from warehousing.raw_materials.models import (
    Material,
    Supplier,
    MaterialStorage,
    RawMaterialDelivery,
)
from warehousing.spare_parts.models import SparePartItem, SparePartStockBalance
from warehousing.packaging.models import PackagingMaterial, PackagingStockBalance
from finished_products.models import Product as FinishedProduct, StockBalance as FinishedStockBalance
from .services import (
    save_delivery_rows,
    save_delivery_edits,
    delivery_row_data,
)


def _admin_context(request, **extra):
    context = admin.site.each_context(request)
    context.update(extra)
    return context


def _current_plant(request):
    plant_id = request.session.get("raw_materials_current_plant_id")
    if not plant_id:
        return None
    return Plant.objects.filter(pk=plant_id).first()


def _set_current_plant(request, plant):
    request.session["raw_materials_current_plant_id"] = plant.pk


@staff_member_required
def warehousing_hub(request):
    """Main Warehousing hub — 4 sections: Raw Materials, Spare Parts, Final Products, Packaging."""
    context = _admin_context(
        request,
        title=_("Warehousing"),
        raw_materials_url=reverse("warehousing:raw_materials_hub"),
        spare_parts_url=reverse("warehousing:spare_parts"),
        final_products_url=reverse("warehousing:final_product"),
        packaging_url=reverse("warehousing:packaging_materials"),
    )
    return render(request, "warehousing/warehousing_hub.html", context)


@staff_member_required
def raw_materials_hub(request):
    """Raw Materials hub — 5-card layout matching Factory dashboard."""
    plant = _current_plant(request)

    selected = request.GET.get("select_plant")
    if selected:
        chosen = Plant.objects.filter(pk=selected).first()
        if chosen:
            _set_current_plant(request, chosen)
            plant = chosen

    context = _admin_context(
        request,
        title="Raw Materials",
        plant=plant,
        plants=Plant.objects.all().order_by("plant_name"),
        settings_url=reverse("warehousing:warehousing_settings"),
        data_entry_url=reverse("warehousing:delivery_entry"),
        data_url=reverse("warehousing:deliveries_data"),
        reports_url=reverse("warehousing:deliveries_reports"),
        data_analysis_url=reverse("warehousing:deliveries_analysis"),
    )
    return render(request, "warehousing/raw_materials_hub.html", context)


@staff_member_required
def warehousing_settings(request):
    """Settings page — grouped admin links for managing materials, suppliers, tests, etc."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")

    def _link(model, title):
        return {"url": reverse(f"admin:raw_materials_{model}_changelist"), "title": title}

    context = _admin_context(
        request,
        title="Warehousing Settings",
        plant=plant,
        hub_url=reverse("warehousing:raw_materials_hub"),
        materials_groups=[
            _link("material", "Materials"),
            _link("supplier", "Suppliers"),
        ],
        tests_groups=[
            _link("materialtest", "Material Tests"),
            _link("materialspecification", "Material Specifications"),
        ],
        storage_groups=[
            _link("materialstorage", "Material Storages"),
            _link("inventorytransaction", "Inventory Transactions"),
            _link("rawmateriallot", "Raw Material Lots"),
            _link("rawmaterialsample", "Raw Material Samples"),
            _link("rawmaterialanalysis", "Raw Material Analysis"),
        ],
        company_groups=[],
    )
    return render(request, "warehousing/warehousing_settings.html", context)


@staff_member_required
def select_plant(request, plant_id):
    plant = Plant.objects.filter(pk=plant_id).first()
    if plant:
        _set_current_plant(request, plant)
    return redirect("warehousing:raw_materials_hub")


@staff_member_required
def coming_soon(request, section_name):
    context = _admin_context(
        request,
        title=section_name,
        section_name=section_name,
    )
    return render(request, "warehousing/coming_soon.html", context)


@staff_member_required
def delivery_entry(request):
    """Delivery entry sheet (Excel-like grid, same as final_product_entry in Factory)."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")

    if request.method == "POST":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid data"}, status=400)
        saved, errors = save_delivery_rows(plant, payload.get("rows", []), request.user)
        if errors:
            return JsonResponse({"status": "error", "message": "; ".join(errors)}, status=400)
        return JsonResponse({"status": "ok", "rows_saved": saved})

    materials = Material.objects.filter(is_active=True).order_by("material_name")
    suppliers = Supplier.objects.filter(is_active=True).order_by("supplier_name")
    storages = MaterialStorage.objects.filter(plant=plant, is_active=True)

    context = _admin_context(
        request,
        title="Delivery Entry - " + plant.plant_name,
        plant=plant,
        materials_json=json.dumps(
            list(materials.values("id", "material_name")), ensure_ascii=False
        ),
        suppliers_json=json.dumps(
            list(suppliers.values("id", "supplier_name")), ensure_ascii=False
        ),
        storages_json=json.dumps(
            list(storages.values("id", "material_id", "storage_name")),
            ensure_ascii=False,
        ),
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/delivery_entry.html", context)


@staff_member_required
def deliveries_data(request):
    """List of previous deliveries for the current plant (same layout as Factory data page)."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")

    deliveries = (
        RawMaterialDelivery.objects.filter(plant=plant)
        .select_related("material", "supplier", "storage")
        .order_by("-arrived_at")
    )
    context = _admin_context(
        request,
        title="Deliveries Data - " + plant.plant_name,
        plant=plant,
        deliveries=deliveries,
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/data.html", context)


@staff_member_required
def delivery_edit(request, delivery_id):
    """View/edit a single delivery (no creation from here)."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")

    delivery = RawMaterialDelivery.objects.filter(pk=delivery_id, plant=plant).first()
    if not delivery:
        return redirect("warehousing:deliveries_data")

    if request.method == "POST":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid data"}, status=400)
        errors = save_delivery_edits(plant, payload.get("rows", []), request.user)
        if errors:
            return JsonResponse({"status": "error", "message": "; ".join(errors)}, status=400)
        return JsonResponse({"status": "ok"})

    materials = Material.objects.filter(is_active=True).order_by("material_name")
    suppliers = Supplier.objects.filter(is_active=True).order_by("supplier_name")
    storages = MaterialStorage.objects.filter(plant=plant, is_active=True)

    context = _admin_context(
        request,
        title="Edit Delivery - " + delivery.material.material_name,
        plant=plant,
        row=delivery_row_data(delivery),
        materials_json=json.dumps(
            list(materials.values("id", "material_name")), ensure_ascii=False
        ),
        suppliers_json=json.dumps(
            list(suppliers.values("id", "supplier_name")), ensure_ascii=False
        ),
        storages_json=json.dumps(
            list(storages.values("id", "material_id", "storage_name")),
            ensure_ascii=False,
        ),
        data_url=reverse("warehousing:deliveries_data"),
    )
    return render(request, "warehousing/delivery_edit.html", context)


@staff_member_required
def deliveries_reports(request):
    """Reports — ready for future implementation."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")
    context = _admin_context(
        request,
        title="Delivery Reports - " + plant.plant_name,
        plant=plant,
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


@staff_member_required
def deliveries_analysis(request):
    """Data Analysis — ready for future implementation."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")
    context = _admin_context(
        request,
        title="Delivery Data Analysis - " + plant.plant_name,
        plant=plant,
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


# ── Spare Parts ──────────────────────────────────────────────

@staff_member_required
def spare_parts_hub(request):
    context = _admin_context(
        request,
        title=_("Spare Parts"),
        settings_url=reverse("warehousing:spare_parts_settings"),
        data_url=reverse("warehousing:spare_parts_data"),
        reports_url=reverse("warehousing:spare_parts_reports"),
        data_analysis_url=reverse("warehousing:spare_parts_analysis"),
    )
    return render(request, "warehousing/spare_parts_hub.html", context)


@staff_member_required
def spare_parts_settings(request):
    def _link(model, title):
        return {"url": reverse(f"admin:spare_parts_{model}_changelist"), "title": title}

    context = _admin_context(
        request,
        title=_("Spare Parts Settings"),
        hub_url=reverse("warehousing:spare_parts_hub"),
        items_groups=[
            _link("sparepartitem", _("Spare Part Items")),
        ],
        transactions_groups=[
            _link("sparepartstocktransaction", _("Stock Transactions")),
            _link("receivingvoucher", _("Receiving Vouchers")),
            _link("issuevoucher", _("Issue Vouchers")),
        ],
        stock_groups=[
            _link("sparepartstockbalance", _("Stock Balances")),
            _link("stockcount", _("Stock Counts")),
        ],
    )
    return render(request, "warehousing/warehousing_settings.html", context)


@staff_member_required
def spare_parts_data(request):
    items = SparePartItem.objects.all().order_by("item_name")
    balances = {
        b.item_id: b for b in SparePartStockBalance.objects.select_related("item").all()
    }
    rows = []
    for item in items:
        bal = balances.get(item.pk)
        rows.append({
            "item": item,
            "total_stock": bal.total_stock if bal else 0,
            "available": bal.available if bal else 0,
            "on_loan": bal.on_loan if bal else 0,
            "in_maintenance": bal.in_maintenance if bal else 0,
        })
    context = _admin_context(
        request,
        title=_("Spare Parts Data"),
        rows=rows,
        hub_url=reverse("warehousing:spare_parts_hub"),
    )
    return render(request, "warehousing/spare_parts_data.html", context)


@staff_member_required
def spare_parts_reports(request):
    context = _admin_context(
        request,
        title=_("Spare Parts Reports"),
        hub_url=reverse("warehousing:spare_parts_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


@staff_member_required
def spare_parts_analysis(request):
    context = _admin_context(
        request,
        title=_("Spare Parts Analysis"),
        hub_url=reverse("warehousing:spare_parts_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


# ── Packaging Materials ──────────────────────────────────────

@staff_member_required
def packaging_hub(request):
    context = _admin_context(
        request,
        title=_("Packaging Materials"),
        settings_url=reverse("warehousing:packaging_settings"),
        data_url=reverse("warehousing:packaging_data"),
        reports_url=reverse("warehousing:packaging_reports"),
        data_analysis_url=reverse("warehousing:packaging_analysis"),
    )
    return render(request, "warehousing/packaging_hub.html", context)


@staff_member_required
def packaging_settings(request):
    def _link(model, title):
        return {"url": reverse(f"admin:packaging_{model}_changelist"), "title": title}

    context = _admin_context(
        request,
        title=_("Packaging Settings"),
        hub_url=reverse("warehousing:packaging_hub"),
        materials_groups=[
            _link("packagingmaterial", _("Packaging Materials")),
            _link("packagingsupplier", _("Packaging Suppliers")),
        ],
        transactions_groups=[
            _link("packagingreceiving", _("Receiving Records")),
            _link("packagingstockledger", _("Stock Ledger")),
        ],
        stock_groups=[
            _link("packagingstockbalance", _("Stock Balances")),
            _link("factorypackagingstock", _("Factory Packaging Stock")),
            _link("packingoperation", _("Packing Operations")),
            _link("packagingreconciliation", _("Reconciliation")),
            _link("supplierevaluation", _("Supplier Evaluation")),
        ],
    )
    return render(request, "warehousing/warehousing_settings.html", context)


@staff_member_required
def packaging_data(request):
    materials = PackagingMaterial.objects.all().order_by("material_name")
    balances = {
        b.material_id: b for b in PackagingStockBalance.objects.select_related("material").all()
    }
    rows = []
    for mat in materials:
        bal = balances.get(mat.pk)
        rows.append({
            "material": mat,
            "qty": bal.quantity if bal else 0,
        })
    context = _admin_context(
        request,
        title=_("Packaging Data"),
        rows=rows,
        hub_url=reverse("warehousing:packaging_hub"),
    )
    return render(request, "warehousing/packaging_data.html", context)


@staff_member_required
def packaging_reports(request):
    context = _admin_context(
        request,
        title=_("Packaging Reports"),
        hub_url=reverse("warehousing:packaging_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


@staff_member_required
def packaging_analysis(request):
    context = _admin_context(
        request,
        title=_("Packaging Analysis"),
        hub_url=reverse("warehousing:packaging_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


# ── Final Products ───────────────────────────────────────────

@staff_member_required
def final_products_hub(request):
    context = _admin_context(
        request,
        title=_("Final Products"),
        settings_url=reverse("warehousing:final_products_settings"),
        data_url=reverse("warehousing:final_products_data"),
        reports_url=reverse("warehousing:final_products_reports"),
        data_analysis_url=reverse("warehousing:final_products_analysis"),
    )
    return render(request, "warehousing/final_products_hub.html", context)


@staff_member_required
def final_products_settings(request):
    def _link(model, title):
        return {"url": reverse(f"admin:finished_products_{model}_changelist"), "title": title}

    context = _admin_context(
        request,
        title=_("Final Products Settings"),
        hub_url=reverse("warehousing:final_products_hub"),
        materials_groups=[
            _link("product", _("Products")),
        ],
        transactions_groups=[
            _link("stockledger", _("Stock Ledger")),
        ],
        stock_groups=[
            _link("stockbalance", _("Stock Balances")),
        ],
    )
    return render(request, "warehousing/warehousing_settings.html", context)


@staff_member_required
def final_products_data(request):
    products = FinishedProduct.objects.all().order_by("product_name")
    balances = FinishedStockBalance.objects.select_related("product", "plant").all()
    product_map = {}
    for b in balances:
        key = b.product_id
        if key not in product_map:
            product_map[key] = {"total": 0, "reserved": 0, "available": 0}
        product_map[key]["total"] += b.total_stock
        product_map[key]["reserved"] += b.reserved
        product_map[key]["available"] += b.available
    rows = []
    for p in products:
        agg = product_map.get(p.pk, {"total": 0, "reserved": 0, "available": 0})
        rows.append({"product": p, **agg})
    context = _admin_context(
        request,
        title=_("Final Products Data"),
        rows=rows,
        hub_url=reverse("warehousing:final_products_hub"),
    )
    return render(request, "warehousing/final_products_data.html", context)


@staff_member_required
def final_products_reports(request):
    context = _admin_context(
        request,
        title=_("Final Products Reports"),
        hub_url=reverse("warehousing:final_products_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


@staff_member_required
def final_products_analysis(request):
    context = _admin_context(
        request,
        title=_("Final Products Analysis"),
        hub_url=reverse("warehousing:final_products_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)
