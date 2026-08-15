from django.db import models
from plants.models import OrgPosition

class ShiftType(models.Model):
    """
    أنواع الورديات: أولى (8ص-4ع)، ثانية (4ع-12ص)، ثالثة (12ص-8ص)، إجازة
    """
    shift_type_id = models.AutoField(primary_key=True)
    shift_type_name = models.CharField(max_length=20, unique=True)
    start_time = models.TimeField(null=True, blank=True)  # NULL للإجازة
    end_time = models.TimeField(null=True, blank=True)    # NULL للإجازة

    class Meta:
        managed = False
        db_table = 'shift_types'

    def __str__(self):
        return self.shift_type_name


class ShiftGroup(models.Model):
    """
    مجموعات التدوير: A, B, C, D
    """
    group_id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=5, unique=True)

    class Meta:
        managed = False
        db_table = 'shift_groups'

    def __str__(self):
        return self.group_name


class ShiftRotationPattern(models.Model):
    """
    دورة الـ 8 أيام: أنهي مجموعة شغالة أنهي وردية في أنهي يوم من الدورة
    day_offset من 0 لـ 7
    """
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(ShiftGroup, on_delete=models.CASCADE, db_column='group_id')
    day_offset = models.IntegerField()
    shift_type = models.ForeignKey(ShiftType, on_delete=models.CASCADE, db_column='shift_type_id')

    class Meta:
        managed = False
        db_table = 'shift_rotation_pattern'
        unique_together = (('group', 'day_offset'),)

    def __str__(self):
        return f"{self.group.group_name} - يوم {self.day_offset} - {self.shift_type.shift_type_name}"


class RotationReference(models.Model):
    """
    تاريخ "يوم صفر" المرجعي لحساب الدورة - سطر واحد بس للشركة كلها
    """
    id = models.BigAutoField(primary_key=True)
    reference_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'rotation_reference'

    def __str__(self):
        return f"يوم الصفر: {self.reference_date}"


class Employee(models.Model):
    """
    بيانات الموظف الأساسية
    """
    employee_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    national_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'employees'

    def __str__(self):
        return self.full_name


class EmployeeAssignment(models.Model):
    """
    تعيين الموظف على وظيفة معينة - ده اللي بيربط الموظف بالمنصب وبالوردية
    shift_mode: rotating (بيتنقل مع مجموعة) أو fixed (وردية ثابتة)
    """
    SHIFT_MODE_CHOICES = [
        ('rotating', 'مدوّر مع مجموعة'),
        ('fixed', 'وردية ثابتة'),
    ]

    assignment_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='employee_id')
    # هنربط position بموديل OrgPosition لما نوصلها - دلوقتي هنسيبها ID عادي مؤقتًا
    position = models.ForeignKey(OrgPosition, on_delete=models.CASCADE, db_column='position_id')
    shift_mode = models.CharField(max_length=10, choices=SHIFT_MODE_CHOICES)
    group = models.ForeignKey(ShiftGroup, on_delete=models.SET_NULL, db_column='group_id', null=True, blank=True)
    fixed_shift_type = models.ForeignKey(ShiftType, on_delete=models.SET_NULL, db_column='fixed_shift_type_id', null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'employee_assignments'

    def __str__(self):
        return f"{self.employee.full_name} - {self.shift_mode}"