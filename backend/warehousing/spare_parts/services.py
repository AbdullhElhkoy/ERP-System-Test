"""
Spare Parts service layer — stock transactions and balance updates.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import SparePartItem, SparePartStockTransaction, SparePartStockBalance


@transaction.atomic
def create_spare_part_transaction(item, transaction_type, quantity, user=None, reference="", notes=""):
    """Create a stock transaction and update the balance."""
    tx = SparePartStockTransaction.objects.create(
        item=item,
        transaction_type=transaction_type,
        quantity=quantity,
        reference_text=reference,
        occurred_at=timezone.now(),
        user=user,
        notes=notes,
    )

    balance, _ = SparePartStockBalance.objects.select_for_update().get_or_create(
        item=item,
        defaults={
            "total_stock": Decimal("0"),
            "available": Decimal("0"),
            "on_loan": Decimal("0"),
            "in_maintenance": Decimal("0"),
        },
    )

    if transaction_type == SparePartStockTransaction.TYPE_RECEIVING:
        balance.total_stock += quantity
        balance.available += quantity
    elif transaction_type == SparePartStockTransaction.TYPE_ISSUING:
        balance.available -= quantity
        balance.total_stock -= quantity
    elif transaction_type == SparePartStockTransaction.TYPE_ADJUSTMENT:
        balance.available += quantity
        balance.total_stock += quantity
    elif transaction_type == SparePartStockTransaction.TYPE_TRANSFER:
        balance.available -= quantity
        balance.on_loan += quantity
    elif transaction_type == SparePartStockTransaction.TYPE_COUNT:
        balance.available = quantity
        balance.total_stock = quantity

    balance.save(update_fields=["total_stock", "available", "on_loan", "in_maintenance"])
    return tx
