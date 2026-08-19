"""
Real-Time Stock Dashboard.

Provides:
- ``get_stock_snapshot()`` — current-state balances from all 5 stock sources.
- ``get_stock_trend()`` — time-series movement from ledger/transaction models.
"""

from __future__ import annotations

import datetime
from typing import Any

from django.db.models import Q

from custom_permissions.models import get_viewable_plant_ids


# ---------------------------------------------------------------------------
# Stock Snapshot
# ---------------------------------------------------------------------------

def get_stock_snapshot(user=None, plant: int | None = None) -> dict:
    """
    Returns a unified stock snapshot across all 5 sources, grouped by plant.

    Returns::

        {
          "plants": {
            "<plant_name>": {
              "floor_stock": [...],
              "finished_products": [...],
              "raw_materials": [...],
              "packaging": {...},
              "spare_parts": [...],
            },
            ...
          },
          "summary": { ... totals ... }
        }
    """
    from factory.models import FloorStockBalance
    from finished_products.models import StockBalance as FPStockBalance
    from warehousing.raw_materials.models import MaterialStorage
    from warehousing.packaging.models import PackagingStockBalance, FactoryPackagingStock
    from warehousing.spare_parts.models import SparePartStockBalance

    plant_ids = _allowed_plant_ids(user)
    result: dict[str, dict[str, Any]] = {}
    summary = {
        "floor_stock": 0,
        "finished_products": {"total_stock": 0, "available": 0, "reserved": 0, "under_preparation": 0, "qc_hold": 0},
        "raw_materials": 0,
        "packaging_warehouse": 0,
        "packaging_factory": 0,
        "spare_parts": {"total_stock": 0, "available": 0, "on_loan": 0, "in_maintenance": 0},
    }

    def _plant_key(obj, field="plant"):
        p = getattr(obj, field, None)
        if p is None:
            return "Unassigned"
        return getattr(p, "plant_name", str(p))

    def _ensure_plant(plant_name):
        if plant_name not in result:
            result[plant_name] = {
                "floor_stock": [],
                "finished_products": [],
                "raw_materials": [],
                "packaging": {"warehouse": [], "factory": []},
                "spare_parts": [],
            }

    # ── 1. Floor Stock ─────────────────────────────────────────────────
    floor_qs = FloorStockBalance.objects.select_related("plant", "grade").filter(quantity__gt=0)
    if plant_ids is not None:
        floor_qs = floor_qs.filter(plant_id__in=plant_ids)
    if plant:
        floor_qs = floor_qs.filter(plant_id=plant)

    for fsb in floor_qs:
        pk = _plant_key(fsb)
        _ensure_plant(pk)
        entry = {
            "grade": str(fsb.grade.code if fsb.grade else "—"),
            "status": fsb.status,
            "quantity": float(fsb.quantity),
        }
        result[pk]["floor_stock"].append(entry)
        summary["floor_stock"] += float(fsb.quantity)

    # ── 2. Finished Products ───────────────────────────────────────────
    fp_qs = FPStockBalance.objects.select_related("plant", "product", "packaging_type").filter(total_stock__gt=0)
    if plant_ids is not None:
        fp_qs = fp_qs.filter(plant_id__in=plant_ids)
    if plant:
        fp_qs = fp_qs.filter(plant_id=plant)

    for fpb in fp_qs:
        pk = _plant_key(fpb)
        _ensure_plant(pk)
        entry = {
            "product": str(fpb.product.product_name if fpb.product else "—"),
            "packaging_type": str(fpb.packaging_type.name if fpb.packaging_type else "—"),
            "total_stock": float(fpb.total_stock),
            "available": float(fpb.available),
            "reserved": float(fpb.reserved),
            "under_preparation": float(fpb.under_preparation),
            "qc_hold": float(fpb.qc_hold),
        }
        result[pk]["finished_products"].append(entry)
        summary["finished_products"]["total_stock"] += float(fpb.total_stock)
        summary["finished_products"]["available"] += float(fpb.available)
        summary["finished_products"]["reserved"] += float(fpb.reserved)
        summary["finished_products"]["under_preparation"] += float(fpb.under_preparation)
        summary["finished_products"]["qc_hold"] += float(fpb.qc_hold)

    # ── 3. Raw Materials ───────────────────────────────────────────────
    rm_qs = MaterialStorage.objects.select_related("plant", "material").filter(is_active=True)
    if plant_ids is not None:
        rm_qs = rm_qs.filter(plant_id__in=plant_ids)
    if plant:
        rm_qs = rm_qs.filter(plant_id=plant)

    for ms in rm_qs:
        pk = _plant_key(ms)
        _ensure_plant(pk)
        entry = {
            "material": str(ms.material.material_name if ms.material else "—"),
            "balance": float(ms.current_balance),
        }
        result[pk]["raw_materials"].append(entry)
        summary["raw_materials"] += float(ms.current_balance)

    # ── 4. Packaging ───────────────────────────────────────────────────
    # Warehouse side
    pkg_wh_qs = PackagingStockBalance.objects.select_related("material").filter(quantity__gt=0)
    _ensure_plant("Warehouse")
    for psb in pkg_wh_qs:
        entry = {
            "material": str(psb.material.material_name if psb.material else "—"),
            "status": psb.status,
            "quantity": float(psb.quantity),
        }
        result["Warehouse"]["packaging"]["warehouse"].append(entry)
        summary["packaging_warehouse"] += float(psb.quantity)

    # Factory side
    fps_qs = FactoryPackagingStock.objects.select_related("factory", "material").filter(quantity__gt=0)
    if plant_ids is not None:
        fps_qs = fps_qs.filter(factory_id__in=plant_ids)
    if plant:
        fps_qs = fps_qs.filter(factory_id=plant)

    for fps in fps_qs:
        pk = _plant_key(fps, field="factory")
        _ensure_plant(pk)
        entry = {
            "material": str(fps.material.material_name if fps.material else "—"),
            "quantity": float(fps.quantity),
        }
        result[pk]["packaging"]["factory"].append(entry)
        summary["packaging_factory"] += float(fps.quantity)

    # ── 5. Spare Parts ─────────────────────────────────────────────────
    sp_qs = SparePartStockBalance.objects.select_related("item", "item__plant").filter(total_stock__gt=0)
    if plant_ids is not None:
        sp_qs = sp_qs.filter(item__plant_id__in=plant_ids)
    if plant:
        sp_qs = sp_qs.filter(item__plant_id=plant)

    for spb in sp_qs:
        pk = _plant_key(spb.item, field="plant")
        _ensure_plant(pk)
        entry = {
            "item": str(spb.item.item_name if spb.item else "—"),
            "total_stock": float(spb.total_stock),
            "available": float(spb.available),
            "on_loan": float(spb.on_loan),
            "in_maintenance": float(spb.in_maintenance),
        }
        result[pk]["spare_parts"].append(entry)
        summary["spare_parts"]["total_stock"] += float(spb.total_stock)
        summary["spare_parts"]["available"] += float(spb.available)
        summary["spare_parts"]["on_loan"] += float(spb.on_loan)
        summary["spare_parts"]["in_maintenance"] += float(spb.in_maintenance)

    return {"plants": result, "summary": summary}


def _ensure_plant_wh(result):
    """Helper to ensure 'Warehouse' key exists."""
    if "Warehouse" not in result:
        result["Warehouse"] = {
            "floor_stock": [],
            "finished_products": [],
            "raw_materials": [],
            "packaging": {"warehouse": [], "factory": []},
            "spare_parts": [],
        }
    return result["Warehouse"]


# ---------------------------------------------------------------------------
# Stock Trend
# ---------------------------------------------------------------------------

# Mapping from user-friendly source key to (model, date_field, qty_field, plant_field)
_TREND_SOURCES = {
    "floor_stock": (
        "factory.FloorStockMovement", "occurred_at", "quantity", "plant__plant_id",
    ),
    "finished_products": (
        "finished_products.StockLedger", "occurred_at", "quantity", "plant__plant_id",
    ),
    "raw_materials": (
        "raw_materials.InventoryTransaction", "transaction_date", "quantity_tons", "plant__plant_id",
    ),
    "spare_parts": (
        "spare_parts.SparePartStockTransaction", "occurred_at", "quantity", "item__plant__plant_id",
    ),
    "packaging": (
        "packaging.PackagingStockLedger", "occurred_at", "quantity", None,
    ),
}


def get_stock_trend(
    user=None,
    source: str = "finished_products",
    plant: int | None = None,
    days: int = 30,
) -> dict:
    """
    Returns in/out trend over time for a given stock source.

    Uses the aggregation engine for consistency.
    """
    from django.utils import timezone
    from analytics.aggregation import aggregate

    date_to = timezone.now().date()
    date_from = date_to - datetime.timedelta(days=days)

    agg_key_map = {
        "floor_stock": "floor_stock_movement",
        "finished_products": "finished_stock_ledger",
        "raw_materials": "inventory_transaction",
        "spare_parts": "spare_part_stock_transaction",
    }

    model_key = agg_key_map.get(source)
    if model_key is None:
        return {"error": f"Unknown source: {source!r}"}

    filters = {}
    if plant:
        # Determine the right filter field
        if source == "spare_parts":
            filters["item__plant__plant_id"] = plant
        else:
            filters["plant__plant_id"] = plant

    return aggregate(
        model_key=model_key,
        metric_field="quantity" if source != "raw_materials" else "quantity_tons",
        agg_func="sum",
        group_by=["plant__plant_name"],
        filters=filters or None,
        date_range=(date_from, date_to),
        user=user,
    )


def _allowed_plant_ids(user):
    """Return plant ID set for scoping, or None for superuser (no filter)."""
    if user is None or getattr(user, "is_superuser", False):
        return None
    return get_viewable_plant_ids(user)
