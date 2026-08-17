"""
Unified service layer for raw material delivery sheets.

All save/display logic for deliveries is handled here, following the same
pattern as factory/services.py — any future screen or API calls these functions.
"""

from datetime import datetime, time as dt_time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from .raw_materials.models import (
    Material,
    Supplier,
    MaterialStorage,
    RawMaterialDelivery,
)


def _as_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _combine_datetime(date_str, time_str):
    if not date_str:
        return None
    d = parse_date(date_str)
    if not d:
        return None
    t = dt_time(0, 0)
    if time_str:
        try:
            t = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            pass
    naive = datetime.combine(d, t)
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


def _resolve_material(material_id):
    if not material_id:
        return None
    try:
        return Material.objects.get(pk=material_id)
    except (Material.DoesNotExist, ValueError):
        return None


def _resolve_supplier(supplier_id):
    if not supplier_id:
        return None
    try:
        return Supplier.objects.get(pk=supplier_id)
    except (Supplier.DoesNotExist, ValueError):
        return None


def _resolve_storage(storage_id, plant):
    if not storage_id:
        return None
    try:
        return MaterialStorage.objects.get(pk=storage_id, plant=plant, is_active=True)
    except (MaterialStorage.DoesNotExist, ValueError):
        return None


@transaction.atomic
def save_delivery_rows(plant, rows, user=None):
    """
    Unified save for delivery entry sheet.

    rows: list of dicts as sent by the template:
        {
            "material_id": ..,
            "supplier_id": ..,
            "storage_id": ..,
            "vehicle_number": ..,
            "weight_tons": ..,
            "arrived_date": "YYYY-MM-DD",
            "arrived_time": "HH:MM",
            "decision": "accepted|rejected|accepted_with_deduction",
            "deduction_percentage": ..,
            "notes": ..,
        }

    Accepted / accepted_with_deduction deliveries auto-create an InventoryTransaction.
    Returns (saved_count, errors).
    """
    saved = 0
    errors = []

    for row in rows:
        material = _resolve_material(row.get("material_id"))
        if not material:
            errors.append("Invalid material in one of the rows")
            continue

        supplier = _resolve_supplier(row.get("supplier_id"))
        if not supplier:
            errors.append(f"Invalid supplier for material: {material.material_name}")
            continue

        weight = _as_decimal(row.get("weight_tons"))
        if weight is None:
            errors.append(f"Invalid weight for material: {material.material_name}")
            continue

        decision = row.get("decision") or RawMaterialDelivery.DECISION_ACCEPTED
        deduction = _as_decimal(row.get("deduction_percentage"))
        storage = _resolve_storage(row.get("storage_id"), plant)

        if decision in (
            RawMaterialDelivery.DECISION_ACCEPTED,
            RawMaterialDelivery.DECISION_ACCEPTED_WITH_DEDUCTION,
        ) and not storage:
            errors.append(f"Storage is required for accepted delivery: {material.material_name}")
            continue

        if (
            decision == RawMaterialDelivery.DECISION_ACCEPTED_WITH_DEDUCTION
            and deduction is None
        ):
            deduction = Decimal("0")

        arrived_at = _combine_datetime(
            row.get("arrived_date"), row.get("arrived_time")
        ) or timezone.now()

        try:
            delivery = RawMaterialDelivery.objects.create(
                plant=plant,
                material=material,
                supplier=supplier,
                storage=storage,
                vehicle_number=row.get("vehicle_number", "") or "",
                weight_tons=weight,
                arrived_at=arrived_at,
                decision=decision,
                deduction_percentage=deduction,
                notes=row.get("notes", "") or "",
            )
            saved += 1
        except Exception as e:
            errors.append(f"Failed to save delivery {material.material_name}: {e}")

    return saved, errors


def delivery_row_data(delivery):
    """Prepare a delivery row for display/edit in the data grid."""
    return {
        "delivery_id": delivery.pk,
        "material_id": delivery.material_id,
        "material_name": delivery.material.material_name,
        "supplier_id": delivery.supplier_id,
        "supplier_name": delivery.supplier.supplier_name,
        "storage_id": delivery.storage_id,
        "storage_name": delivery.storage.storage_name if delivery.storage_id else "",
        "vehicle_number": delivery.vehicle_number,
        "weight_tons": str(delivery.weight_tons),
        "arrived_date": delivery.arrived_at.strftime("%Y-%m-%d"),
        "arrived_time": delivery.arrived_at.strftime("%H:%M"),
        "decision": delivery.decision,
        "deduction_percentage": (
            str(delivery.deduction_percentage)
            if delivery.deduction_percentage is not None
            else ""
        ),
        "notes": delivery.notes,
    }


@transaction.atomic
def save_delivery_edits(plant, rows, user=None):
    """
    Save edits to existing deliveries (data page). Does not create new deliveries.
    Updates values on the current delivery only.
    """
    errors = []

    for row in rows:
        delivery = None
        try:
            delivery = RawMaterialDelivery.objects.get(
                pk=row.get("delivery_id"), plant=plant
            )
        except (RawMaterialDelivery.DoesNotExist, ValueError, KeyError):
            errors.append(f"Delivery not found: {row.get('delivery_id')}")
            continue

        material = _resolve_material(row.get("material_id"))
        if not material:
            errors.append(f"Invalid material for delivery #{delivery.pk}")
            continue
        supplier = _resolve_supplier(row.get("supplier_id"))
        if not supplier:
            errors.append(f"Invalid supplier for delivery #{delivery.pk}")
            continue

        weight = _as_decimal(row.get("weight_tons"))
        if weight is None:
            errors.append(f"Invalid weight for delivery #{delivery.pk}")
            continue

        decision = row.get("decision") or delivery.decision
        storage = _resolve_storage(row.get("storage_id"), plant)

        if decision in (
            RawMaterialDelivery.DECISION_ACCEPTED,
            RawMaterialDelivery.DECISION_ACCEPTED_WITH_DEDUCTION,
        ) and not storage:
            errors.append(f"Storage is required for accepted delivery #{delivery.pk}")
            continue

        arrived_at = _combine_datetime(
            row.get("arrived_date"), row.get("arrived_time")
        ) or delivery.arrived_at

        delivery.material = material
        delivery.supplier = supplier
        delivery.storage = storage
        delivery.vehicle_number = row.get("vehicle_number", "") or delivery.vehicle_number
        delivery.weight_tons = weight
        delivery.arrived_at = arrived_at
        delivery.decision = decision
        delivery.deduction_percentage = _as_decimal(row.get("deduction_percentage"))
        delivery.notes = row.get("notes", delivery.notes)
        delivery.save(update_fields=[
            "material", "supplier", "storage", "vehicle_number", "weight_tons",
            "arrived_at", "decision", "deduction_percentage", "notes",
        ])

    return errors
