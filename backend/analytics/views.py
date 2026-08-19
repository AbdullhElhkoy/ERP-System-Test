from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from plants.models import Plant
from analytics.aggregation import aggregate
from analytics.stock_realtime import get_stock_snapshot, get_stock_trend
from analytics.spc import get_available_spc_tests, compute_spc, get_spc_report
from analytics.serializers import (
    AggregateRequestSerializer,
    SPCTestSerializer,
)


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

    # Grade distribution (via quality_decision for now)
    grade_data = aggregate(
        model_key="quality_decision",
        metric_field=None,
        agg_func="count",
        group_by=["sample__plant__plant_name"],
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


# ── DRF ViewSets (used by api_urls.py) ────────────────────────────────────

class AggregateViewSet(viewsets.ViewSet):
    """POST /api/analytics/aggregate/"""

    def create(self, request):
        serializer = AggregateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = aggregate(
                model_key=data["model_key"],
                metric_field=data.get("metric_field"),
                agg_func=data["agg_func"],
                group_by=data["group_by"],
                filters=data.get("filters") or None,
                date_range=(data.get("date_from"), data.get("date_to")),
                user=request.user,
            )
        except (ValueError, RuntimeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class StockRealtimeViewSet(viewsets.ViewSet):
    """GET /api/analytics/stock/stock-realtime/ and stock-trend/"""

    def list(self, request):
        plant = request.query_params.get("plant")
        plant_id = int(plant) if plant else None
        result = get_stock_snapshot(user=request.user, plant=plant_id)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="stock-trend")
    def stock_trend(self, request):
        source = request.query_params.get("source", "finished_products")
        plant = request.query_params.get("plant")
        days = int(request.query_params.get("days", 30))
        plant_id = int(plant) if plant else None
        result = get_stock_trend(user=request.user, source=source, plant=plant_id, days=days)
        return Response(result)


class SPCViewSet(viewsets.ViewSet):
    """GET /api/analytics/spc/available-tests/ and spc-report/"""

    @action(detail=False, methods=["get"], url_path="available-tests")
    def available_tests(self, request):
        plant = request.query_params.get("plant")
        plant_id = int(plant) if plant else None
        tests = get_available_spc_tests(user=request.user, plant=plant_id)
        return Response(tests)

    @action(detail=False, methods=["get"], url_path="spc-report")
    def spc_report(self, request):
        plant_id = request.query_params.get("plant")
        test_name = request.query_params.get("test_name")
        if not plant_id or not test_name:
            return Response({"error": "plant and test_name required"}, status=status.HTTP_400_BAD_REQUEST)
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        from datetime import date as _date
        df = _date.fromisoformat(date_from) if date_from else None
        dt = _date.fromisoformat(date_to) if date_to else None
        result = get_spc_report(plant_id=int(plant_id), test_name=test_name, user=request.user, date_from=df, date_to=dt)
        return Response(result)
