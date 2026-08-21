from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import InventoryTransaction, MaterialStorage


@transaction.atomic
def record_inventory_movement(user, material, plant, storage, movement_type, quantity_tons,
                              accuracy_type=InventoryTransaction.ACCURACY_EXACT,
                              notes="", reference_delivery=None):
    if quantity_tons <= Decimal("0"):
        raise ValueError("الكمية لازم تكون أكبر من صفر")

    if movement_type == InventoryTransaction.MOVEMENT_OUT:
        balance = storage.current_balance
        if balance < quantity_tons:
            raise ValueError(f"الرصيد غير كافي. الرصيد الحالي: {balance} طن")

    return InventoryTransaction.objects.create(
        material           = material,
        plant              = plant,
        storage            = storage,
        movement_type      = movement_type,
        accuracy_type      = accuracy_type,
        quantity_tons      = quantity_tons,
        transaction_date   = timezone.now(),
        user               = user,
        notes              = notes,
        reference_delivery = reference_delivery,
    )


@transaction.atomic
def issue_inventory(user, material, plant, storage, quantity_tons, notes=""):
    return record_inventory_movement(
        user=user,
        material=material,
        plant=plant,
        storage=storage,
        movement_type=InventoryTransaction.MOVEMENT_OUT,
        quantity_tons=quantity_tons,
        notes=notes,
    )


@transaction.atomic
def adjust_inventory(user, material, plant, storage, quantity_tons, notes=""):
    if not notes or not notes.strip():
        raise ValueError("التسوية لازم يكون فيها ملاحظات تفصيلية")

    return record_inventory_movement(
        user=user,
        material=material,
        plant=plant,
        storage=storage,
        movement_type=InventoryTransaction.MOVEMENT_ADJUSTMENT,
        quantity_tons=quantity_tons,
        notes=notes,
    )
