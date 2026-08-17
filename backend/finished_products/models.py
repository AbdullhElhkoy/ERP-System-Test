from django.conf import settings
from django.db import models


class Product(models.Model):
    product_code = models.CharField(max_length=30, unique=True)
    product_name = models.CharField(max_length=150)
    product_type = models.CharField(max_length=50, blank=True)
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="finished_products")
    unit_of_measure = models.CharField(max_length=20, default="tons")
    packing_types = models.ManyToManyField("factory.PackingType", blank=True)
    traceability_level = models.PositiveSmallIntegerField(default=1)
    batch_required = models.BooleanField(default=True)
    chemical_tests_required = models.BooleanField(default=True)
    physical_tests_required = models.BooleanField(default=True)
    stock_product = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finished_products_products"
        ordering = ["product_name"]

    def __str__(self):
        return f"{self.product_code} — {self.product_name}"


class StockLedger(models.Model):
    TYPE_PRODUCTION_IN = "production_in"
    TYPE_RESERVED = "reserved"
    TYPE_RELEASED = "released"
    TYPE_ISSUED = "issued"
    TYPE_ADJUSTMENT_IN = "adjustment_in"
    TYPE_ADJUSTMENT_OUT = "adjustment_out"
    TYPE_REJECTED = "rejected"
    TYPE_CHOICES = [
        (TYPE_PRODUCTION_IN, "Production In"),
        (TYPE_RESERVED, "Reserved"),
        (TYPE_RELEASED, "Released"),
        (TYPE_ISSUED, "Issued"),
        (TYPE_ADJUSTMENT_IN, "Adjustment In"),
        (TYPE_ADJUSTMENT_OUT, "Adjustment Out"),
        (TYPE_REJECTED, "Rejected"),
    ]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movements")
    packaging_type = models.ForeignKey("factory.PackingType", on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reference_text = models.CharField(max_length=200, blank=True)
    occurred_at = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finished_products_stock_ledger"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.product} — {self.transaction_type} — {self.quantity}"


class StockBalance(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="balances")
    packaging_type = models.ForeignKey("factory.PackingType", on_delete=models.PROTECT)
    total_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reserved = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    available = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    under_preparation = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    qc_hold = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finished_products_stock_balances"
        unique_together = (("product", "packaging_type"),)

    def __str__(self):
        return f"{self.product} / {self.packaging_type}: {self.available} available"
