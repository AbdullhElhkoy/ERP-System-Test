from django.conf import settings
from django.db import models


class SparePartItem(models.Model):
    item_code = models.CharField(max_length=30, unique=True)
    item_name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, blank=True)
    subcategory = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    maximum_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    reorder_point = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="spare_parts")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "spare_part_items"
        ordering = ["item_name"]

    def __str__(self):
        return f"{self.item_code} — {self.item_name}"


class SparePartStockTransaction(models.Model):
    TYPE_RECEIVING = "receiving"
    TYPE_ISSUING = "issuing"
    TYPE_ADJUSTMENT = "adjustment"
    TYPE_TRANSFER = "transfer"
    TYPE_COUNT = "count"
    TYPE_CHOICES = [
        (TYPE_RECEIVING, "Receiving"),
        (TYPE_ISSUING, "Issuing"),
        (TYPE_ADJUSTMENT, "Adjustment"),
        (TYPE_TRANSFER, "Transfer"),
        (TYPE_COUNT, "Physical Count"),
    ]

    item = models.ForeignKey(SparePartItem, on_delete=models.PROTECT, related_name="stock_transactions")
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    reference_text = models.CharField(max_length=200, blank=True)
    occurred_at = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spare_part_stock_transactions"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.item} — {self.transaction_type} — {self.quantity}"


class SparePartStockBalance(models.Model):
    item = models.OneToOneField(SparePartItem, on_delete=models.PROTECT, related_name="stock_balance")
    total_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    available = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    on_loan = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    in_maintenance = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "spare_part_stock_balances"

    def __str__(self):
        return f"{self.item}: {self.available} available"


class ReceivingVoucher(models.Model):
    voucher_number = models.CharField(max_length=30, unique=True)
    date = models.DateField()
    supplier_name = models.CharField(max_length=150, blank=True)
    item = models.ForeignKey(SparePartItem, on_delete=models.PROTECT, related_name="receiving_vouchers")
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spare_part_receiving_vouchers"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.voucher_number} — {self.item.item_name}"


class IssueVoucher(models.Model):
    voucher_number = models.CharField(max_length=30, unique=True)
    date = models.DateField()
    issued_to = models.CharField(max_length=150, blank=True)
    item = models.ForeignKey(SparePartItem, on_delete=models.PROTECT, related_name="issue_vouchers")
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="issued")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spare_part_issue_vouchers"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.voucher_number} — {self.item.item_name}"


class StockCount(models.Model):
    count_date = models.DateField()
    item = models.ForeignKey(SparePartItem, on_delete=models.PROTECT, related_name="stock_counts")
    system_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    physical_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    variance = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    counted_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spare_part_stock_counts"
        ordering = ["-count_date"]

    def save(self, *args, **kwargs):
        self.variance = self.physical_quantity - self.system_quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item} — {self.count_date}: Δ {self.variance}"
