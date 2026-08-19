from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from analytics.aggregation import aggregate
from analytics.stock_realtime import get_stock_snapshot, get_stock_trend
from analytics.spc import get_available_spc_tests, compute_spc, get_spc_report
from analytics.serializers import (
    AggregateRequestSerializer,
    AggregateResponseSerializer,
    StockSnapshotResponseSerializer,
    SPCTestSerializer,
    SPCReportSerializer,
)


class AggregateViewSet(viewsets.ViewSet):
    """
    POST /api/analytics/aggregate/

    Generic aggregation engine exposed via API.
    """
    permission_classes = []  # handled by DRF default or custom auth

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
    """
    GET /api/analytics/stock-realtime/
    GET /api/analytics/stock-trend/
    """
    permission_classes = []

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

        result = get_stock_trend(
            user=request.user,
            source=source,
            plant=plant_id,
            days=days,
        )
        return Response(result)


class SPCViewSet(viewsets.ViewSet):
    """
    GET /api/analytics/spc/available-tests/
    GET /api/analytics/spc/{test_id}/
    """
    permission_classes = []

    @action(detail=False, methods=["get"], url_path="available-tests")
    def available_tests(self, request):
        plant = request.query_params.get("plant")
        plant_id = int(plant) if plant else None
        tests = get_available_spc_tests(user=request.user, plant=plant_id)
        serializer = SPCTestSerializer(tests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="spc-report")
    def spc_report(self, request):
        plant_id = request.query_params.get("plant")
        test_name = request.query_params.get("test_name")

        if not plant_id or not test_name:
            return Response(
                {"error": "plant and test_name query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        from datetime import date as _date
        df = _date.fromisoformat(date_from) if date_from else None
        dt = _date.fromisoformat(date_to) if date_to else None

        result = get_spc_report(
            plant_id=int(plant_id),
            test_name=test_name,
            user=request.user,
            date_from=df,
            date_to=dt,
        )
        return Response(result)
