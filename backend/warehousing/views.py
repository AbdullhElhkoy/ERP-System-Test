import json

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from plants.models import Plant

from warehousing.raw_materials.models import (
    Material,
    Supplier,
    MaterialStorage,
    RawMaterialDelivery,
)
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
def raw_materials_hub(request):
    """بوابة الرو ماتيريال: روابط لشاشات الأدمن الحالية + الشيتات الجدولية."""
    admin_urls = [
        {
            "title": "المواد (Materials)",
            "url": reverse("admin:raw_materials_material_changelist"),
        },
        {
            "title": "الموردين (Suppliers)",
            "url": reverse("admin:raw_materials_supplier_changelist"),
        },
        {
            "title": "اختبارات المواد (Material Tests)",
            "url": reverse("admin:raw_materials_materialtest_changelist"),
        },
        {
            "title": "مواصفات المواد (Material Specifications)",
            "url": reverse("admin:raw_materials_materialspecification_changelist"),
        },
        {
            "title": "مخازن الخام (Material Storages)",
            "url": reverse("admin:raw_materials_materialstorage_changelist"),
        },
        {
            "title": "حركات المخزون (Inventory Transactions)",
            "url": reverse("admin:raw_materials_inventorytransaction_changelist"),
        },
        {
            "title": "التشغيلات (Raw Material Lots)",
            "url": reverse("admin:raw_materials_rawmateriallot_changelist"),
        },
        {
            "title": "العينات (Raw Material Samples)",
            "url": reverse("admin:raw_materials_rawmaterialsample_changelist"),
        },
        {
            "title": "نتائج التحاليل (Raw Material Analysis)",
            "url": reverse("admin:raw_materials_rawmaterialanalysis_changelist"),
        },
    ]

    plant = _current_plant(request)

    selected = request.GET.get("select_plant")
    if selected:
        chosen = Plant.objects.filter(pk=selected).first()
        if chosen:
            _set_current_plant(request, chosen)
            plant = chosen

    context = _admin_context(
        request,
        title="الرو ماتيريال (Raw Materials)",
        admin_links=admin_urls,
        plant=plant,
        plants=Plant.objects.all().order_by("plant_name"),
        sheet_urls={
            "delivery_entry": reverse("warehousing:delivery_entry"),
            "data": reverse("warehousing:deliveries_data"),
            "reports": reverse("warehousing:deliveries_reports"),
            "analysis": reverse("warehousing:deliveries_analysis"),
        },
    )
    return render(request, "warehousing/raw_materials_hub.html", context)


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
    """شيت إدخال الشحنات الجدولي (مثل final_product_entry في الفاكتوري)."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")

    if request.method == "POST":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "بيانات غير صالحة"}, status=400)
        saved, errors = save_delivery_rows(plant, payload.get("rows", []), request.user)
        if errors:
            return JsonResponse({"status": "error", "message": "; ".join(errors)}, status=400)
        return JsonResponse({"status": "ok", "rows_saved": saved})

    materials = Material.objects.filter(is_active=True).order_by("material_name")
    suppliers = Supplier.objects.filter(is_active=True).order_by("supplier_name")
    storages = MaterialStorage.objects.filter(plant=plant, is_active=True)

    context = _admin_context(
        request,
        title="شيت استلام الشحنات - " + plant.plant_name,
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
    """قائمة الشحنات السابقة للمصنع الحالي (بنفس تقسيم صفحة الداتا في الفاكتوري)."""
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
        title="عرض بيانات الشحنات - " + plant.plant_name,
        plant=plant,
        deliveries=deliveries,
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/data.html", context)


@staff_member_required
def delivery_edit(request, delivery_id):
    """عرض/تعديل شحنة واحدة (لا إضافة من هنا)."""
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
            return JsonResponse({"status": "error", "message": "بيانات غير صالحة"}, status=400)
        errors = save_delivery_edits(plant, payload.get("rows", []), request.user)
        if errors:
            return JsonResponse({"status": "error", "message": "; ".join(errors)}, status=400)
        return JsonResponse({"status": "ok"})

    materials = Material.objects.filter(is_active=True).order_by("material_name")
    suppliers = Supplier.objects.filter(is_active=True).order_by("supplier_name")
    storages = MaterialStorage.objects.filter(plant=plant, is_active=True)

    context = _admin_context(
        request,
        title="تعديل شحنة - " + delivery.material.material_name,
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
    """التقارير — جاهز للإضافة لاحقاً."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")
    context = _admin_context(
        request,
        title="تقارير الشحنات - " + plant.plant_name,
        plant=plant,
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)


@staff_member_required
def deliveries_analysis(request):
    """تحليل البيانات — جاهز للإضافة لاحقاً."""
    plant = _current_plant(request)
    if not plant:
        return redirect("warehousing:raw_materials_hub")
    context = _admin_context(
        request,
        title="تحليل بيانات الشحنات - " + plant.plant_name,
        plant=plant,
        hub_url=reverse("warehousing:raw_materials_hub"),
    )
    return render(request, "warehousing/coming_soon.html", context)
