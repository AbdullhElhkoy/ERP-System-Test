from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from .models import StockLedger, StockBalance


@transaction.atomic
def create_stock_transaction(product, packaging_type, transaction_type, quantity, user=None, reference="", notes=""):
    """Create a StockLedger entry and update StockBalance."""
    ledger = StockLedger.objects.create(
        product=product,
        packaging_type=packaging_type,
        transaction_type=transaction_type,
        quantity=quantity,
        reference_text=reference,
        occurred_at=timezone.now(),
        user=user,
        notes=notes,
    )

    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        product=product,
        packaging_type=packaging_type,
        defaults={
            "total_stock": Decimal("0"),
            "reserved": Decimal("0"),
            "available": Decimal("0"),
            "under_preparation": Decimal("0"),
            "qc_hold": Decimal("0"),
        },
    )

    if transaction_type == StockLedger.TYPE_PRODUCTION_IN:
        balance.total_stock += quantity
        balance.available += quantity
    elif transaction_type == StockLedger.TYPE_RESERVED:
        balance.available -= quantity
        balance.reserved += quantity
    elif transaction_type == StockLedger.TYPE_RELEASED:
        balance.reserved -= quantity
        balance.available += quantity
    elif transaction_type == StockLedger.TYPE_ISSUED:
        balance.reserved -= quantity
        balance.total_stock -= quantity
    elif transaction_type == StockLedger.TYPE_ADJUSTMENT_IN:
        balance.total_stock += quantity
        balance.available += quantity
    elif transaction_type == StockLedger.TYPE_ADJUSTMENT_OUT:
        balance.total_stock -= quantity
        balance.available -= quantity
    elif transaction_type == StockLedger.TYPE_REJECTED:
        balance.available -= quantity
        balance.qc_hold += quantity

    balance.save(update_fields=["total_stock", "reserved", "available", "under_preparation", "qc_hold"])
    return ledger


@transaction.atomic
def reserve_stock(product, packaging_type, quantity, user=None, reference=""):
    """Reserve stock — fails if available < quantity."""
    balance = StockBalance.objects.select_for_update().filter(
        product=product, packaging_type=packaging_type
    ).first()

    if not balance:
        raise ValueError("No stock balance found for this product/packaging combination.")

    if balance.available < quantity:
        raise ValueError(
            f"Insufficient stock: available={balance.available}, requested={quantity}"
        )

    if balance.qc_hold > 0:
        raise ValueError("Stock is under QC hold and cannot be reserved.")

    return create_stock_transaction(
        product, packaging_type, StockLedger.TYPE_RESERVED,
        quantity, user=user, reference=reference,
    )


@transaction.atomic
def release_stock(product, packaging_type, quantity, user=None, reference=""):
    """Release a reservation (reserved → available)."""
    balance = StockBalance.objects.select_for_update().filter(
        product=product, packaging_type=packaging_type
    ).first()

    if not balance or balance.reserved < quantity:
        raise ValueError("Insufficient reserved stock to release.")

    return create_stock_transaction(
        product, packaging_type, StockLedger.TYPE_RELEASED,
        quantity, user=user, reference=reference,
    )


@transaction.atomic
def issue_stock(product, packaging_type, quantity, user=None, reference=""):
    """Issue stock for delivery (reserved → out)."""
    balance = StockBalance.objects.select_for_update().filter(
        product=product, packaging_type=packaging_type
    ).first()

    if not balance or balance.reserved < quantity:
        raise ValueError("Insufficient reserved stock to issue.")

    return create_stock_transaction(
        product, packaging_type, StockLedger.TYPE_ISSUED,
        quantity, user=user, reference=reference,
    )
