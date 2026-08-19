from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from plants.models import Plant
from analytics.aggregation import aggregate
from analytics.stock_realtime import get_stock_snapshot
from analytics.spc import get_available_spc_tests, compute_spc


def analytics_dashboard(request):
    """Main analytics dashboard — overview of all factories."""
    plants = Plant.objects.all()
    plant_id = request.GET.get("plant")
    p = int(plant_id) if plant_id else None

    context = {
        "plants": plants,
        "selected_plant": p,
    }
    return render(request, "analytics/dashboard.html", context)


def production_analytics(request):
    """Production analytics: Ton output, grade distribution, packing events."""
    plants = Plant.objects.all()
    plant_id = request.GET.get("plant")
    days = int(request.GET.get("days", 30))
    p = int(plant_id) if plant_id else None

    date_to = timezone.now().date()
    date_from = date_to - timedelta(days=days)

    # Ton production by plant
    ton_data = aggregate(
        model_key="ton",
        metric_field="weight",
        agg_func="sum",
        group_by=["plant__plant_name"],
        date_range=(date_from, date_to),
        user=request.user,
    )

    # Ton count by plant
    ton_count = aggregate(
        model_key="ton",
        metric_field=None,
        agg_func="count",
        group_by=["plant__plant_name"],
        date_range=(date_from, date_to),
        user=request.user,
    )

    # Grade distribution
    grade_data = aggregate(
        model_key="ton_grade_assignment",
        metric_field=None,
        agg_func="count",
        group_by=["primary_grade__code"],
        date_range=(date_from, date_to),
        user=request.user,
    )

    # Packing events by plant
    packing_data = aggregate(
        model_key="packing_event",
        metric_field="quantity",
        agg_func="sum",
        group_by=["plant__plant_name", "packing_type__name"],
        date_range=(date_from, date_to),
        user=request.user,
    )

    context = {
        "plants": plants,
        "selected_plant": p,
        "days": days,
        "ton_data": ton_data,
        "ton_count": ton_count,
        "grade_data": grade_data,
        "packing_data": packing_data,
    }
    return render(request, "analytics/production.html", context)


def stock_analytics(request):
    """Stock analytics: current snapshot across all sources."""
    plants = Plant.objects.all()
    plant_id = request.GET.get("plant")
    p = int(plant_id) if plant_id else None

    snapshot = get_stock_snapshot(user=request.user, plant=p)

    context = {
        "plants": plants,
        "selected_plant": p,
        "snapshot": snapshot,
    }
    return render(request, "analytics/stock.html", context)


def spc_analytics(request):
    """SPC analytics: capability indices and Nelson Rules."""
    plants = Plant.objects.all()
    plant_id = request.GET.get("plant")
    test_name = request.GET.get("test_name")
    days = int(request.GET.get("days", 90))
    p = int(plant_id) if plant_id else None

    available_tests = get_available_spc_tests(user=request.user, plant=p)

    spc_data = None
    if p and test_name:
        date_to = timezone.now().date()
        date_from = date_to - timedelta(days=days)
        spc_data = compute_spc(p, test_name, date_from, date_to)

    context = {
        "plants": plants,
        "selected_plant": p,
        "selected_test": test_name,
        "days": days,
        "available_tests": available_tests,
        "spc_data": spc_data,
    }
    return render(request, "analytics/spc.html", context)


def quality_analytics(request):
    """Quality analytics: decisions, rejection rates, lab turnaround."""
    plants = Plant.objects.all()
    plant_id = request.GET.get("plant")
    days = int(request.GET.get("days", 30))
    p = int(plant_id) if plant_id else None

    date_to = timezone.now().date()
    date_from = date_to - timedelta(days=days)

    # QC decisions by plant
    qc_data = aggregate(
        model_key="quality_decision",
        metric_field=None,
        agg_func="count",
        group_by=["sample__plant__plant_name", "final_decision"],
        date_range=(date_from, date_to),
        user=request.user,
    )

    # Lab test results
    lab_data = aggregate(
        model_key="sample_test_result",
        metric_field="result",
        agg_func="avg",
        group_by=["sample__plant__plant_name", "test_name"],
        date_range=(date_from, date_to),
        user=request.user,
    )

    context = {
        "plants": plants,
        "selected_plant": p,
        "days": days,
        "qc_data": qc_data,
        "lab_data": lab_data,
    }
    return render(request, "analytics/quality.html", context)


# ── API endpoints for chart data (JSON) ───────────────────────────────────

def api_production_chart(request):
    """JSON endpoint for production charts (AJAX)."""
    plant_id = request.GET.get("plant")
    days = int(request.GET.get("days", 30))
    date_to = timezone.now().date()
    date_from = date_to - timedelta(days=days)

    data = aggregate(
        model_key="ton",
        metric_field="weight",
        agg_func="sum",
        group_by=["plant__plant_name"],
        date_range=(date_from, date_to),
        user=request.user,
    )
    return JsonResponse(data)


def api_stock_snapshot(request):
    """JSON endpoint for stock snapshot (AJAX)."""
    plant_id = request.GET.get("plant")
    p = int(plant_id) if plant_id else None
    snapshot = get_stock_snapshot(user=request.user, plant=p)
    return JsonResponse(snapshot)


def api_spc_data(request):
    """JSON endpoint for SPC chart data (AJAX)."""
    plant_id = request.GET.get("plant")
    test_name = request.GET.get("test_name")
    days = int(request.GET.get("days", 90))

    if not plant_id or not test_name:
        return JsonResponse({"error": "plant and test_name required"}, status=400)

    date_to = timezone.now().date()
    date_from = date_to - timedelta(days=days)
    spc = compute_spc(int(plant_id), test_name, date_from, date_to)
    return JsonResponse(spc)
