from django.conf import settings
from django.db import models


CONTRACT_TYPE_CHOICES = [
    ("permanent", "Permanent"),
    ("fixed_term", "Fixed Term"),
    ("daily", "Daily"),
    ("internship", "Internship"),
]

EMPLOYEE_STATUS_CHOICES = [
    ("active", "Active"),
    ("on_leave", "On Leave"),
    ("terminated", "Terminated"),
]

LEAVE_TYPE_CHOICES = [
    ("annual", "Annual Leave"),
    ("sick", "Sick Leave"),
    ("casual", "Casual Leave"),
    ("maternity", "Maternity Leave"),
    ("unpaid", "Unpaid Leave"),
    ("other", "Other"),
]

LEAVE_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]

DISCIPLINE_TYPE_CHOICES = [
    ("verbal_warning", "Verbal Warning"),
    ("written_warning", "Written Warning"),
    ("suspension", "Suspension"),
    ("demotion", "Demotion"),
    ("termination", "Termination"),
    ("other", "Other"),
]


class HREmployeeProfile(models.Model):
    """HR-specific data on top of the existing employees.Employee."""
    employee = models.OneToOneField(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_profile",
        db_column="employee_id", primary_key=True,
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hr_employees",
    )
    department = models.ForeignKey(
        "plants.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hr_employees",
    )
    section = models.CharField(max_length=100, blank=True, default="")
    job_title = models.CharField(max_length=100, blank=True, default="")
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, default="permanent")
    direct_manager = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hr_subordinates", db_column="direct_manager_id",
    )
    shift = models.ForeignKey(
        "employees.ShiftType", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hr_employees",
    )
    status = models.CharField(max_length=20, choices=EMPLOYEE_STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hr_employee_profiles"
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employee Profiles"

    def __str__(self):
        emp = self.employee
        return f"{emp.full_name} — {self.job_title or 'No Title'}"


class Attendance(models.Model):
    """Daily attendance record per employee."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_attendance",
        db_column="employee_id",
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hr_attendance",
    )
    date = models.DateField()
    shift = models.ForeignKey(
        "employees.ShiftType", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hr_attendance",
    )
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_absent = models.BooleanField(default=False)
    is_late = models.BooleanField(default=False)
    late_minutes = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hr_attendance"
        unique_together = (("employee", "date"),)
        ordering = ["-date", "employee"]

    def __str__(self):
        return f"{self.employee} — {self.date}"


class Leave(models.Model):
    """Leave request and tracking."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_leaves",
        db_column="employee_id",
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hr_leaves",
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField(default=1)
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=LEAVE_STATUS_CHOICES, default="pending")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hr_approved_leaves",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hr_leaves"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee} — {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"


class LeaveBalance(models.Model):
    """Annual leave balance per employee per type."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_leave_balances",
        db_column="employee_id",
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    year = models.PositiveIntegerField()
    entitled = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    taken = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    remaining = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        db_table = "hr_leave_balances"
        unique_together = (("employee", "leave_type", "year"),)

    def __str__(self):
        return f"{self.employee} — {self.get_leave_type_display()} {self.year}: {self.remaining} remaining"


class Contract(models.Model):
    """Employment contract tracking."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_contracts",
        db_column="employee_id",
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hr_contracts",
    )
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("expired", "Expired"), ("terminated", "Terminated")], default="active")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hr_contracts"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.employee} — {self.get_contract_type_display()} ({self.start_date})"


class Discipline(models.Model):
    """Disciplinary actions."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_disciplines",
        db_column="employee_id",
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hr_disciplines",
    )
    violation_type = models.CharField(max_length=50, blank=True, default="")
    action_type = models.CharField(max_length=20, choices=DISCIPLINE_TYPE_CHOICES)
    date = models.DateField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hr_disciplines_issued",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hr_disciplines"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} — {self.get_action_type_display()} ({self.date})"


class Training(models.Model):
    """Training and certification records."""
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="hr_trainings",
        db_column="employee_id",
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="hr_trainings",
    )
    training_name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200, blank=True, default="")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    has_certificate = models.BooleanField(default=False)
    certificate_number = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hr_trainings"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.employee} — {self.training_name}"
