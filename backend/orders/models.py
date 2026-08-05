from django.conf import settings
from django.db import models


class SalesOrder(models.Model):
    GRADE_POLICY_ANY = "any"
    GRADE_POLICY_FIXED = "fixed"
    GRADE_POLICY_OPEN_AT_PACKING = "open_at_packing"
    GRADE_POLICY_CHOICES = [
        (GRADE_POLICY_ANY, "مفتوحة - أي جريد داخل نفس التصنيف"),
        (GRADE_POLICY_FIXED, "مقفولة على جريد واحد بالتحديد"),
        (GRADE_POLICY_OPEN_AT_PACKING, "بتتحدد لحظة التعبئة"),
    ]

    BATCH_SOURCE_PRODUCTION = "production"
    BATCH_SOURCE_WAREHOUSE = "warehouse"
    BATCH_SOURCE_CHOICES = [
        (BATCH_SOURCE_PRODUCTION, "من الإنتاج"),
        (BATCH_SOURCE_WAREHOUSE, "من المخزن"),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=150)
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
        return f"{self.order.order_number} → {self.plant.plant_code}: {self.allocated_quantity}"


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