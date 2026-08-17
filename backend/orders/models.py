from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

class Customer(models.Model):
    customer_code = models.CharField(max_length=30, unique=True)
    customer_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, default="active")

    class Meta:
        db_table = "orders_customers"
        ordering = ["customer_name"]

    def __str__(self):
        return f"{self.customer_code} — {self.customer_name}"


# ---------------------------------------------------------------------------
# Sales Price List
# ---------------------------------------------------------------------------

class SalesPriceList(models.Model):
    product = models.ForeignKey("finished_products.Product", on_delete=models.PROTECT)
    packaging_type = models.ForeignKey("factory.PackingType", on_delete=models.PROTECT)
    customer_type = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EGP")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "orders_price_lists"


# ---------------------------------------------------------------------------
# Quotation
# ---------------------------------------------------------------------------

class Quotation(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXPIRED, "Expired"),
    ]

    quotation_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    valid_until = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders_quotations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.quotation_number} — {self.customer.customer_name}"


class QuotationLine(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("finished_products.Product", on_delete=models.PROTECT)
    packaging_type = models.ForeignKey("factory.PackingType", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "orders_quotation_lines"


# ---------------------------------------------------------------------------
# Sales Order (existing, expanded)
# ---------------------------------------------------------------------------

class SalesOrder(models.Model):
    GRADE_POLICY_ANY = "any"
    GRADE_POLICY_FIXED = "fixed"
    GRADE_POLICY_OPEN_AT_PACKING = "open_at_packing"
    GRADE_POLICY_CHOICES = [
        (GRADE_POLICY_ANY, "Open — any grade within same classification"),
        (GRADE_POLICY_FIXED, "Fixed on specific grade"),
        (GRADE_POLICY_OPEN_AT_PACKING, "Determined at packing time"),
    ]

    BATCH_SOURCE_PRODUCTION = "production"
    BATCH_SOURCE_WAREHOUSE = "warehouse"
    BATCH_SOURCE_CHOICES = [
        (BATCH_SOURCE_PRODUCTION, "From Production"),
        (BATCH_SOURCE_WAREHOUSE, "From Warehouse"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_STOCK_RESERVED = "stock_reserved"
    STATUS_PARTIAL_DELIVERY = "partially_delivered"
    STATUS_FULL_DELIVERY = "fully_delivered"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_STOCK_RESERVED, "Stock Reserved"),
        (STATUS_PARTIAL_DELIVERY, "Partially Delivered"),
        (STATUS_FULL_DELIVERY, "Fully Delivered"),
        (STATUS_CLOSED, "Closed"),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, null=True, blank=True, related_name="sales_orders"
    )
    customer_name = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    product_classification = models.ForeignKey(
        "shared_definitions.QualityGrade", on_delete=models.PROTECT, related_name="sales_orders"
    )
    fixed_grade = models.ForeignKey(
        "factory.Grade", on_delete=models.PROTECT, null=True, blank=True, related_name="fixed_sales_orders"
    )
    grade_policy = models.CharField(max_length=20, choices=GRADE_POLICY_CHOICES)
    batch_source = models.CharField(max_length=20, choices=BATCH_SOURCE_CHOICES)
    total_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20, default="tons")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_orders"

    def __str__(self):
        return f"{self.order_number} - {self.customer_name}"


class SalesOrderLine(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("finished_products.Product", on_delete=models.PROTECT)
    packaging_type = models.ForeignKey("factory.PackingType", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "orders_sales_order_lines"


class OrderPlantAllocation(models.Model):
    """توزيع الطلبية الحالي على مصنع أو أكتر - الحالة النشطة دلوقتي"""
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="plant_allocations")
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="order_allocations")
    allocated_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_plant_allocations"
        unique_together = (("order", "plant"),)

    def __str__(self):
        return f"{self.order.order_number} → {self.plant.plant_name}: {self.allocated_quantity}"


class OrderPlantAllocationChangeLog(models.Model):
    """سجل كل عملية إعادة توزيع بين المصانع - للتتبع الكامل"""
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="allocation_logs")
    from_plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True, related_name="allocation_logs_from"
    )
    to_plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, related_name="allocation_logs_to"
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="order_reallocations"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_plant_allocation_change_log"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.from_plant} → {self.to_plant} ({self.quantity})"


class OrderMovement(models.Model):
    MOVEMENT_PRODUCTION = "production"
    MOVEMENT_HANDOVER = "handover"
    MOVEMENT_STAGING = "staging"
    MOVEMENT_LOADING = "loading"
    MOVEMENT_TYPE_CHOICES = [
        (MOVEMENT_PRODUCTION, "إنتاج"),
        (MOVEMENT_HANDOVER, "تسليم للمخزن"),
        (MOVEMENT_STAGING, "تجهيز"),
        (MOVEMENT_LOADING, "تحميل"),
    ]

    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    grade = models.ForeignKey("factory.Grade", on_delete=models.PROTECT, null=True, blank=True, related_name="order_movements")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    source_plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="order_movements_out")
    occurred_at = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "order_movements"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.order.order_number} - {self.get_movement_type_display()} - {self.quantity}"