from django.conf import settings
from django.db import models


class PackagingMaterial(models.Model):
    material_code = models.CharField(max_length=30, unique=True)
    material_name = models.CharField(max_length=150)
    category = models.CharField(max_length=50)
    subcategory = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    maximum_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    reorder_point = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    inspection_required = models.BooleanField(default=True)
    inspection_template = models.JSONField(default=dict, blank=True)
    products = models.ManyToManyField("finished_products.Product", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "packaging_materials"
        ordering = ["material_name"]

    def __str__(self):
        return f"{self.material_code} — {self.material_name}"


class PackagingSupplier(models.Model):
    supplier_code = models.CharField(max_length=30, unique=True)
    supplier_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    materials_supplied = models.ManyToManyField(PackagingMaterial, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "packaging_suppliers"
        ordering = ["supplier_name"]

    def __str__(self):
        return self.supplier_name


class PackagingReceiving(models.Model):
    STATUS_QUARANTINE = "quarantine"
    STATUS_AVAILABLE = "available"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_QUARANTINE, "Quarantine"),
        (STATUS_AVAILABLE, "Available"),
        (STATUS_REJECTED, "Rejected"),
    ]

    receiving_number = models.CharField(max_length=30, unique=True)
    date = models.DateField()
    supplier = models.ForeignKey(PackagingSupplier, on_delete=models.PROTECT, related_name="receiving_records")
    material = models.ForeignKey(PackagingMaterial, on_delete=models.PROTECT, related_name="receiving_records")
    product = models.ForeignKey("finished_products.Product", on_delete=models.PROTECT, related_name="packaging_receiving")
    quantity_received = models.DecimalField(max_digits=10, decimal_places=3)
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUARANTINE)
    lab_sample = models.ForeignKey("lab.Sample", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "packaging_receiving"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.receiving_number} — {self.material.material_name}"


class PackagingStockLedger(models.Model):
    material = models.ForeignKey(PackagingMaterial, on_delete=models.PROTECT, related_name="stock_movements")
    transaction_type = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    status = models.CharField(max_length=20)
    reference_text = models.CharField(max_length=200, blank=True)
    occurred_at = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "packaging_stock_ledger"
        ordering = ["-occurred_at"]


class PackagingStockBalance(models.Model):
    material = models.ForeignKey(PackagingMaterial, on_delete=models.PROTECT, related_name="balances")
    status = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "packaging_stock_balances"
        unique_together = (("material", "status"),)


class FactoryPackagingStock(models.Model):
    factory = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, related_name="packaging_stock")
    material = models.ForeignKey(PackagingMaterial, on_delete=models.PROTECT, related_name="factory_stocks")
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "factory_packaging_stock"
        unique_together = (("factory", "material"),)


class PackingOperation(models.Model):
    factory = models.ForeignKey("plants.Plant", on_delete=models.PROTECT)
    material = models.ForeignKey(PackagingMaterial, on_delete=models.PROTECT)
    product = models.ForeignKey("finished_products.Product", on_delete=models.PROTECT)
    quantity_used = models.DecimalField(max_digits=10, decimal_places=3)
    quantity_waste = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    quantity_remaining = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    operated_at = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "packing_operations"
        ordering = ["-operated_at"]


class PackagingReconciliation(models.Model):
    STATUS_MATCHED = "matched"
    STATUS_VARIANCE = "variance"
    STATUS_CHOICES = [
        (STATUS_MATCHED, "Matched"),
        (STATUS_VARIANCE, "Variance"),
    ]

    material = models.ForeignKey(PackagingMaterial, on_delete=models.PROTECT)
    warehouse_qty = models.DecimalField(max_digits=10, decimal_places=3)
    factory_qty = models.DecimalField(max_digits=10, decimal_places=3)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    reconciled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "packaging_reconciliation"
        ordering = ["-reconciled_at"]


class SupplierEvaluation(models.Model):
    supplier = models.ForeignKey(PackagingSupplier, on_delete=models.PROTECT, related_name="evaluations")
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2)
    rejection_rate = models.DecimalField(max_digits=5, decimal_places=2)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "packaging_supplier_evaluations"
        ordering = ["-evaluated_at"]
