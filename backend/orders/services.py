"""
Orders service layer — reservation, delivery, and status transitions.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import SalesOrder, SalesOrderLine, OrderPlantAllocation


@transaction.atomic
def reserve_stock_for_order(order, user=None):
    """
    Reserve finished-product stock for all confirmed order lines.
    Calls finished_products.services.reserve_stock per line.
    Returns list of (line, error) tuples — empty list means success.
    """
    from finished_products.services import reserve_stock

    errors = []
    lines = order.lines.select_related("product", "packaging_type").all()

    for line in lines:
        try:
            reserve_stock(
                product=line.product,
                packaging_type=line.packaging_type,
                quantity=line.quantity,
                user=user,
                reference=f"Order {order.order_number}",
            )
        except (ValueError, Exception) as exc:
            errors.append((line, str(exc)))

    if not errors:
        order.status = SalesOrder.STATUS_STOCK_RESERVED
        order.save(update_fields=["status"])

    return errors


@transaction.atomic
def issue_stock_for_order(order, product, packaging_type, quantity, user=None):
    """
    Issue (ship) stock previously reserved for this order.
    Decrements reserved → out; transitions order status to partially/fully delivered.
    """
    from finished_products.services import issue_stock

    try:
        issue_stock(
            product=product,
            packaging_type=packaging_type,
            quantity=quantity,
            user=user,
            reference=f"Delivery — {order.order_number}",
        )
    except (ValueError, Exception) as exc:
        return str(exc)

    total_reserved = sum(
        line.quantity for line in order.lines.all()
        if line.product_id == product.pk and line.packaging_type_id == packaging_type.pk
    )
    total_issued = sum(
        order.movements.filter(
            movement_type="handover",
            grade__isnull=True,
        ).values_list("quantity", flat=True),
        Decimal("0"),
    ) if order.movements.exists() else Decimal("0")

    if total_issued >= order.total_quantity:
        order.status = SalesOrder.STATUS_FULL_DELIVERY
    else:
        order.status = SalesOrder.STATUS_PARTIAL_DELIVERY

    order.save(update_fields=["status"])
    return None


@transaction.atomic
def allocate_plant(order, plant, quantity):
    """
    Allocate a portion of the order to a specific plant.
    """
    allocation, created = OrderPlantAllocation.objects.get_or_create(
        order=order, plant=plant,
        defaults={"allocated_quantity": quantity},
    )
    if not created:
        allocation.allocated_quantity = quantity
        allocation.save(update_fields=["allocated_quantity"])
    return allocation


@transaction.atomic
def close_order(order):
    """Mark order as fully closed — no further movements allowed."""
    order.status = SalesOrder.STATUS_CLOSED
    order.save(update_fields=["status"])
