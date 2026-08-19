"""
Generic Aggregation Service.

Provides a single ``aggregate()`` entry-point that every analytics report
reuses.  All queries pass through plant-scoped permission filtering before
any aggregation happens.

Design constraints (from execution plan):
- ``model_key`` is a whitelisted key, never a raw model import from the caller.
- ``group_by`` fields are validated against a per-model allow-list.
- ``metric_field`` values are validated against a per-model allow-list.
- Output shape is always chart-ready: {labels, series, meta}.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from django.db.models import (
    Avg,
    Count,
    F,
    Max,
    Min,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import (
    TruncDay,
    TruncMonth,
    TruncWeek,
)
from django.contrib.contenttypes.models import ContentType

from custom_permissions.models import get_viewable_plant_ids

# ---------------------------------------------------------------------------
# REPORTABLE MODELS REGISTRY
# ---------------------------------------------------------------------------
# Each entry maps a ``model_key`` (string the caller sends) to metadata that
# controls what the caller is allowed to do with it.
#
# Keys:
#   model             – Django model class
#   app_label         – e.g. "factory"
#   model_name        – e.g. "Ton"
#   plant_field       – ORM path to the Plant FK (may traverse FKs)
#   date_field        – primary datetime/date field used for date-range filtering
#   group_by_fields   – fields the caller may group by (ORM paths)
#   metric_fields     – numeric fields the caller may aggregate
#   filter_fields     – fields the caller may filter on (simple exact / lookups)

REPORTABLE_MODELS: dict[str, dict[str, Any]] = {}


def _register(key: str, **kwargs):
    REPORTABLE_MODELS[key] = kwargs


# ── Factory ────────────────────────────────────────────────────────────────
_register(
    "ton",
    model=None,  # filled lazily below
    app_label="factory",
    model_name="Ton",
    plant_field="plant__plant_id",
    date_field="production_date",
    group_by_fields=[
        "plant__plant_name",
        "status",
        "production_date",
        "production_shift__name",
        "output_reading__packing_type__name",
    ],
    metric_fields=["weight", "cycle_number", "sequence_number"],
    filter_fields=["plant__plant_id", "status", "production_date"],
)

_register(
    "process_reading",
    model=None,
    app_label="factory",
    model_name="ProcessReading",
    plant_field="plant__plant_id",
    date_field="sampled_at",
    group_by_fields=[
        "plant__plant_name",
        "stage__name",
        "shift__name",
    ],
    metric_fields=[],
    filter_fields=["plant__plant_id", "stage__id"],
)

_register(
    "process_analysis_result",
    model=None,
    app_label="factory",
    model_name="ProcessAnalysisResult",
    plant_field="reading__plant__plant_id",
    date_field="reading__sampled_at",
    group_by_fields=[
        "reading__plant__plant_name",
        "reading__stage__name",
        "test__name",
    ],
    metric_fields=["result"],
    filter_fields=["reading__plant__plant_id", "test__id"],
)

_register(
    "output_reading",
    model=None,
    app_label="factory",
    model_name="OutputReading",
    plant_field="plant__plant_id",
    date_field="sampled_at",
    group_by_fields=[
        "plant__plant_name",
        "output_point__name",
        "packing_type__name",
        "sampling_status",
    ],
    metric_fields=[],
    filter_fields=["plant__plant_id", "output_point__id", "packing_type__id"],
)

_register(
    "output_analysis_result",
    model=None,
    app_label="factory",
    model_name="OutputAnalysisResult",
    plant_field="reading__plant__plant_id",
    date_field="reading__sampled_at",
    group_by_fields=[
        "reading__plant__plant_name",
        "reading__output_point__name",
        "test__name",
    ],
    metric_fields=["result"],
    filter_fields=["reading__plant__plant_id", "test__id"],
)

_register(
    "packing_event",
    model=None,
    app_label="factory",
    model_name="PackingEvent",
    plant_field="plant__plant_id",
    date_field="packed_at",
    group_by_fields=[
        "plant__plant_name",
        "packing_type__name",
    ],
    metric_fields=["quantity"],
    filter_fields=["plant__plant_id", "packing_type__id"],
)

_register(
    "floor_stock_balance",
    model=None,
    app_label="factory",
    model_name="FloorStockBalance",
    plant_field="plant__plant_id",
    date_field=None,
    group_by_fields=[
        "plant__plant_name",
        "grade__code",
        "status",
    ],
    metric_fields=["quantity"],
    filter_fields=["plant__plant_id", "grade__id", "status"],
)

_register(
    "floor_stock_movement",
    model=None,
    app_label="factory",
    model_name="FloorStockMovement",
    plant_field="plant__plant_id",
    date_field="occurred_at",
    group_by_fields=[
        "plant__plant_name",
        "grade__code",
        "movement_type",
        "status",
    ],
    metric_fields=["quantity"],
    filter_fields=["plant__plant_id", "grade__id", "movement_type"],
)

# ── Raw Materials ──────────────────────────────────────────────────────────
_register(
    "raw_material_delivery",
    model=None,
    app_label="raw_materials",
    model_name="RawMaterialDelivery",
    plant_field="plant__plant_id",
    date_field="arrived_at",
    group_by_fields=[
        "plant__plant_name",
        "material__material_name",
        "supplier__supplier_name",
        "decision",
    ],
    metric_fields=["weight_tons", "deduction_percentage"],
    filter_fields=["plant__plant_id", "material__id", "supplier__id", "decision"],
)

_register(
    "inventory_transaction",
    model=None,
    app_label="raw_materials",
    model_name="InventoryTransaction",
    plant_field="plant__plant_id",
    date_field="transaction_date",
    group_by_fields=[
        "plant__plant_name",
        "material__material_name",
        "movement_type",
    ],
    metric_fields=["quantity_tons"],
    filter_fields=["plant__plant_id", "material__id", "movement_type"],
)

# ── Finished Products ──────────────────────────────────────────────────────
_register(
    "finished_stock_balance",
    model=None,
    app_label="finished_products",
    model_name="StockBalance",
    plant_field="plant__plant_id",
    date_field=None,
    group_by_fields=[
        "plant__plant_name",
        "product__product_name",
        "packaging_type__name",
    ],
    metric_fields=["total_stock", "reserved", "available", "under_preparation", "qc_hold"],
    filter_fields=["plant__plant_id", "product__id", "packaging_type__id"],
)

_register(
    "finished_stock_ledger",
    model=None,
    app_label="finished_products",
    model_name="StockLedger",
    plant_field="plant__plant_id",
    date_field="occurred_at",
    group_by_fields=[
        "plant__plant_name",
        "product__product_name",
        "transaction_type",
    ],
    metric_fields=["quantity"],
    filter_fields=["plant__plant_id", "product__id", "transaction_type"],
)

# ── Packaging ──────────────────────────────────────────────────────────────
_register(
    "packaging_stock_balance",
    model=None,
    app_label="packaging",
    model_name="PackagingStockBalance",
    plant_field=None,
    date_field=None,
    group_by_fields=[
        "material__material_name",
        "status",
    ],
    metric_fields=["quantity"],
    filter_fields=["material__id", "status"],
)

_register(
    "factory_packaging_stock",
    model=None,
    app_label="packaging",
    model_name="FactoryPackagingStock",
    plant_field="factory__plant_id",
    date_field=None,
    group_by_fields=[
        "factory__plant_name",
        "material__material_name",
    ],
    metric_fields=["quantity"],
    filter_fields=["factory__plant_id", "material__id"],
)

_register(
    "packing_operation",
    model=None,
    app_label="packaging",
    model_name="PackingOperation",
    plant_field="factory__plant_id",
    date_field="operated_at",
    group_by_fields=[
        "factory__plant_name",
        "material__material_name",
        "product__product_name",
    ],
    metric_fields=["quantity_used", "quantity_waste", "quantity_remaining"],
    filter_fields=["factory__plant_id", "material__id", "product__id"],
)

# ── Spare Parts ────────────────────────────────────────────────────────────
_register(
    "spare_part_stock_transaction",
    model=None,
    app_label="spare_parts",
    model_name="SparePartStockTransaction",
    plant_field="item__plant__plant_id",
    date_field="occurred_at",
    group_by_fields=[
        "item__plant__plant_name",
        "item__item_name",
        "transaction_type",
    ],
    metric_fields=["quantity"],
    filter_fields=["item__plant__plant_id", "item__id", "transaction_type"],
)

# ── Lab ────────────────────────────────────────────────────────────────────
_register(
    "sample_test_result",
    model=None,
    app_label="lab",
    model_name="SampleTestResult",
    plant_field="sample__plant__plant_id",
    date_field="entered_at",
    group_by_fields=[
        "sample__plant__plant_name",
        "test_name",
        "sample__source_type",
    ],
    metric_fields=["result"],
    filter_fields=["sample__plant__plant_id", "test_name", "sample__source_type"],
)

# ── QC ─────────────────────────────────────────────────────────────────────
_register(
    "quality_decision",
    model=None,
    app_label="quality_control",
    model_name="QualityDecision",
    plant_field="sample__plant__plant_id",
    date_field="decided_at",
    group_by_fields=[
        "sample__plant__plant_name",
        "final_decision",
        "suggested_decision",
    ],
    metric_fields=[],
    filter_fields=["sample__plant__plant_id", "final_decision"],
)

# ── HR ─────────────────────────────────────────────────────────────────────
_register(
    "attendance",
    model=None,
    app_label="hr",
    model_name="Attendance",
    plant_field="plant__plant_id",
    date_field="date",
    group_by_fields=[
        "plant__plant_name",
        "is_absent",
        "is_late",
    ],
    metric_fields=["late_minutes", "overtime_hours"],
    filter_fields=["plant__plant_id", "is_absent", "is_late"],
)

_register(
    "leave",
    model=None,
    app_label="hr",
    model_name="Leave",
    plant_field="plant__plant_id",
    date_field="start_date",
    group_by_fields=[
        "plant__plant_name",
        "leave_type",
        "status",
    ],
    metric_fields=["days"],
    filter_fields=["plant__plant_id", "leave_type", "status"],
)


# ---------------------------------------------------------------------------
# Lazy model resolution — avoids circular imports at module load time.
# ---------------------------------------------------------------------------

def _resolve_models():
    """Populate ``model`` class references in REPORTABLE_MODELS on first use."""
    from factory.models import (
        FloorStockBalance,
        FloorStockMovement,
        OutputAnalysisResult,
        OutputReading,
        PackingEvent,
        ProcessAnalysisResult,
        ProcessReading,
        Ton,
    )
    from warehousing.raw_materials.models import (
        InventoryTransaction,
        RawMaterialDelivery,
    )
    from finished_products.models import StockBalance as FPStockBalance
    from finished_products.models import StockLedger as FPStockLedger
    from warehousing.packaging.models import (
        FactoryPackagingStock,
        PackingOperation,
        PackagingStockBalance,
    )
    from warehousing.spare_parts.models import SparePartStockTransaction
    from lab.models import SampleTestResult
    from quality_control.models import QualityDecision
    from hr.models import Attendance, Leave

    _MODEL_MAP = {
        "ton": Ton,
        "process_reading": ProcessReading,
        "process_analysis_result": ProcessAnalysisResult,
        "output_reading": OutputReading,
        "output_analysis_result": OutputAnalysisResult,
        "packing_event": PackingEvent,
        "floor_stock_balance": FloorStockBalance,
        "floor_stock_movement": FloorStockMovement,
        "raw_material_delivery": RawMaterialDelivery,
        "inventory_transaction": InventoryTransaction,
        "finished_stock_balance": FPStockBalance,
        "finished_stock_ledger": FPStockLedger,
        "packaging_stock_balance": PackagingStockBalance,
        "factory_packaging_stock": FactoryPackagingStock,
        "packing_operation": PackingOperation,
        "spare_part_stock_transaction": SparePartStockTransaction,
        "sample_test_result": SampleTestResult,
        "quality_decision": QualityDecision,
        "attendance": Attendance,
        "leave": Leave,
    }

    for key, model_cls in _MODEL_MAP.items():
        if key in REPORTABLE_MODELS:
            REPORTABLE_MODELS[key]["model"] = model_cls


_models_resolved = False


def _ensure_models():
    global _models_resolved
    if not _models_resolved:
        _resolve_models()
        _models_resolved = True


# ---------------------------------------------------------------------------
# Time-bucket helpers
# ---------------------------------------------------------------------------

_TRUNC_MAP = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}


def _trunc_expr(field_name: str, bucket: str):
    cls = _TRUNC_MAP.get(bucket)
    if cls is None:
        return None
    return cls(F(field_name), output_field=Value(""))


# ---------------------------------------------------------------------------
# Aggregation function
# ---------------------------------------------------------------------------

_AGG_MAP = {
    "sum": Sum,
    "avg": Avg,
    "count": Count,
    "min": Min,
    "max": Max,
}


def aggregate(
    model_key: str,
    metric_field: str | None,
    agg_func: str,
    group_by: list[str],
    filters: dict | None = None,
    date_range: tuple | None = None,
    user=None,
) -> dict:
    """
    Generic aggregation engine.

    Returns chart-ready dict: ``{"labels": [...], "series": [...], "meta": {...}}``

    Parameters
    ----------
    model_key : str
        Key into REPORTABLE_MODELS.
    metric_field : str | None
        Field to aggregate. Required for sum/avg/min/max; ignored for count.
    agg_func : str
        One of 'sum', 'avg', 'count', 'min', 'max'.
    group_by : list[str]
        ORM field paths to group by.
    filters : dict | None
        Additional ORM filter kwargs.
    date_range : tuple | None
        ``(date_from, date_to)`` — both inclusive.
    user : settings.AUTH_USER_MODEL
        Required for plant-scoping.
    """
    _ensure_models()

    if model_key not in REPORTABLE_MODELS:
        raise ValueError(f"Unknown model_key: {model_key!r}. Available: {list(REPORTABLE_MODELS)}")

    registry = REPORTABLE_MODELS[model_key]
    model = registry["model"]
    if model is None:
        raise RuntimeError(f"Model for {model_key!r} failed to resolve.")

    # ── Validate inputs ────────────────────────────────────────────────
    allowed_group = set(registry["group_by_fields"])
    for g in group_by:
        if g not in allowed_group:
            raise ValueError(
                f"Field {g!r} not in allowed group_by for {model_key}. "
                f"Allowed: {sorted(allowed_group)}"
            )

    allowed_metrics = set(registry["metric_fields"])
    if agg_func != "count" and metric_field not in allowed_metrics:
        raise ValueError(
            f"Field {metric_field!r} not in allowed metrics for {model_key}. "
            f"Allowed: {sorted(allowed_metrics)}"
        )

    if agg_func not in _AGG_MAP:
        raise ValueError(f"Unknown agg_func: {agg_func!r}. Use one of: {list(_AGG_MAP)}")

    # ── Build queryset ─────────────────────────────────────────────────
    qs = model.objects.all()

    # Plant-scoping via permissions
    if user is not None and not getattr(user, "is_superuser", False):
        plant_ids = get_viewable_plant_ids(user)
        plant_field = registry["plant_field"]
        if plant_field:
            qs = qs.filter(**{f"{plant_field}__in": plant_ids})

    # Date range
    date_field = registry["date_field"]
    if date_range and date_field:
        d_from, d_to = date_range
        lookup = {}
        if d_from:
            lookup[f"{date_field}__gte"] = d_from
        if d_to:
            lookup[f"{date_field}__lte"] = d_to
        qs = qs.filter(**lookup)

    # Caller filters
    if filters:
        allowed_filters = set(registry["filter_fields"])
        for fk, fv in filters.items():
            if fk not in allowed_filters:
                raise ValueError(
                    f"Filter {fk!r} not allowed for {model_key}. "
                    f"Allowed: {sorted(allowed_filters)}"
                )
        qs = qs.filter(**filters)

    # ── Aggregate ──────────────────────────────────────────────────────
    agg_cls = _AGG_MAP[agg_func]
    alias_name = "value"

    if agg_func == "count":
        agg_expr = Count("id")
    else:
        agg_expr = agg_cls(metric_field)

    # Apply date truncation to group_by if bucket detected
    trunc_buckets = {}
    clean_group = []
    for g in group_by:
        if g.endswith("__day") or g.endswith("__week") or g.endswith("__month"):
            parts = g.rsplit("__", 1)
            base_field = parts[0]
            bucket = parts[1]
            trunc_buckets[g] = (base_field, bucket)
            clean_group.append(g)
        else:
            clean_group.append(g)

    # Build annotations for truncated date fields
    annotate_kwargs = {}
    for alias, (base_field, bucket) in trunc_buckets.items():
        annotate_kwargs[alias] = _trunc_expr(base_field, bucket)

    if annotate_kwargs:
        qs = qs.annotate(**annotate_kwargs)

    # Group by
    qs = qs.values(*clean_group).annotate(**{alias_name: agg_expr})

    # Order — prefer date fields first
    order_fields = []
    for g in clean_group:
        if g in trunc_buckets or "date" in g or "at" in g:
            order_fields.append(g)
    order_fields.append(f"-{alias_name}" if agg_func != "count" else f"-{alias_name}")
    qs = qs.order_by(*order_fields)

    # Materialise
    rows = list(qs)

    # ── Shape output ───────────────────────────────────────────────────
    labels = []
    for row in rows:
        parts = []
        for g in clean_group:
            v = row.get(g)
            if hasattr(v, "strftime"):
                parts.append(v.strftime("%Y-%m-%d"))
            elif v is None:
                parts.append("—")
            else:
                parts.append(str(v))
        labels.append(" | ".join(parts))

    values = [float(row[alias_name]) if row[alias_name] is not None else 0 for row in rows]

    meta = {
        "model_key": model_key,
        "agg_func": agg_func,
        "metric_field": metric_field,
        "group_by": group_by,
        "row_count": len(rows),
    }

    return {
        "labels": labels,
        "series": [{"name": f"{agg_func}({metric_field or 'count'})", "data": values}],
        "meta": meta,
    }
