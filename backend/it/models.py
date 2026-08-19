from django.conf import settings
from django.db import models


ASSET_STATUS_CHOICES = [
    ("available", "Available"),
    ("assigned", "Assigned"),
    ("in_maintenance", "In Maintenance"),
    ("retired", "Retired"),
    ("lost", "Lost"),
]

ACCOUNT_STATUS_CHOICES = [
    ("active", "Active"),
    ("disabled", "Disabled"),
    ("locked", "Locked"),
    ("pending", "Pending Setup"),
]

LOGIN_METHOD_CHOICES = [
    ("password", "Password"),
    ("sso", "SSO"),
    ("ldap", "LDAP"),
]


class AssetCategory(models.Model):
    """IT asset categories (Computer, Laptop, Printer, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "it_asset_categories"
        verbose_name_plural = "Asset Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ITAsset(models.Model):
    """Individual IT asset/equipment."""
    asset_code = models.CharField(max_length=30, unique=True)
    category = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, related_name="assets",
    )
    brand = models.CharField(max_length=100, blank=True, default="")
    model_name = models.CharField(max_length=100, blank=True, default="")
    serial_number = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES, default="available")
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="it_assets",
    )
    department = models.ForeignKey(
        "plants.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_assets",
    )
    location = models.CharField(max_length=100, blank=True, default="")
    assigned_to = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_assets", db_column="assigned_to_id",
    )
    delivery_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "it_assets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset_code} — {self.category.name}"


class EmployeeAccount(models.Model):
    """IT-managed login account linked to an employee."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="it_accounts",
        db_column="employee_id",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="it_employee_link",
        null=True, blank=True,
    )
    username = models.CharField(max_length=150, unique=True)
    login_method = models.CharField(max_length=20, choices=LOGIN_METHOD_CHOICES, default="password")
    status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default="pending")
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_accounts",
    )
    department = models.ForeignKey(
        "plants.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_accounts",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_accounts_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "it_employee_accounts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} — {self.employee}"


class AssetHandover(models.Model):
    """Tracks asset assignment to / return from employees."""
    TYPE_HANDOVER = "handover"
    TYPE_RETURN = "return"
    TYPE_CHOICES = [
        (TYPE_HANDOVER, "Handover"),
        (TYPE_RETURN, "Return"),
    ]

    asset = models.ForeignKey(
        ITAsset, on_delete=models.CASCADE, related_name="handovers",
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="it_handovers",
        db_column="employee_id",
    )
    handover_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    handover_date = models.DateField()
    condition_at_handover = models.CharField(max_length=100, blank=True, default="")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_handovers_performed",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "it_asset_handovers"
        ordering = ["-handover_date"]

    def __str__(self):
        return f"{self.asset.asset_code} — {self.get_handover_type_display()} — {self.employee}"


class ITClearance(models.Model):
    """IT clearance record when an employee departs."""
    STATUS_PENDING = "pending"
    STATUS_CLEARED = "cleared"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CLEARED, "Cleared"),
    ]

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="it_clearances",
        db_column="employee_id",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    accounts_disabled = models.BooleanField(default=False)
    assets_returned = models.BooleanField(default=False)
    clearance_date = models.DateField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="it_clearances_performed",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "it_clearances"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Clearance — {self.employee} — {self.get_status_display()}"
