from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.dateparse import parse_datetime

from plants.models import Plant
from .models import ProcessStage, TestDefinition, ProcessReading, ProcessAnalysisResult


@staff_member_required
def process_reading_grid(request):
    plant_id = request.GET.get("plant") or request.POST.get("plant")
    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None

    stages = ProcessStage.objects.filter(plant=plant) if plant else ProcessStage.objects.none()
    tests = TestDefinition.objects.filter(plant=plant) if plant else TestDefinition.objects.none()

    raw_stage_ids = request.GET.getlist("stages") or request.POST.getlist("stages")
    selected_stage_ids = [int(s) for s in raw_stage_ids if s.isdigit()]
    selected_stages = stages.filter(id__in=selected_stage_ids) if selected_stage_ids else ProcessStage.objects.none()

    if request.method == "POST" and selected_stage_ids:
        sampled_at_raw = request.POST.get("sampled_at")
        sampled_at = parse_datetime(sampled_at_raw) if sampled_at_raw else None

        if not sampled_at:
            messages.error(request, "لازم تحدد التاريخ والوقت")
        else:
            created_readings = 0
            created_results = 0
            for stage in selected_stages:
                reading = ProcessReading.objects.create(
                    plant=plant, stage=stage, sampled_at=sampled_at
                )
                created_readings += 1
                for test in tests:
                    field_name = f"cell_{stage.id}_{test.id}"
                    value = request.POST.get(field_name, "").strip()
                    if value:
                        ProcessAnalysisResult.objects.create(
                            reading=reading, test=test, result=value
                        )
                        created_results += 1

            messages.success(request, f"تم حفظ {created_readings} قراءة و {created_results} نتيجة بنجاح")
            return redirect(f"{request.path}?plant={plant_id}")

    context = {
        "plants": Plant.objects.all(),
        "plant": plant,
        "stages": stages,
        "tests": tests,
        "selected_stages": selected_stages,
        "selected_stage_ids": selected_stage_ids,
        "title": "إدخال قراءات التفاعل - جدول",
    }
    return render(request, "factory/process_reading_grid.html", context)