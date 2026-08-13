from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Plant(models.Model):
    plant_id = models.AutoField(primary_key=True, db_column="plant_id")
    plant_name = models.CharField(
        max_length=50, unique=True, db_column="plant_name"
    )
    product_type = models.CharField(
        max_length=50, blank=True, db_column="product_type"
    )

    class Meta:
        db_table = "plants"
        managed = False

    def __str__(self):
        return self.plant_name

class Department(models.Model):
    department_id = models.AutoField(primary_key=True, db_column="department_id")
    department_code = models.CharField(max_length=20, unique=True, db_column="department_code")
    department_name = models.CharField(max_length=50, unique=True, db_column="department_name")
    category = models.CharField(max_length=20, null=True, blank=True, db_column="category")
    parent_department = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sub_departments",
        db_column="parent_department_id",
    )

    class Meta:
        db_table = "departments"
        managed = False

    def __str__(self):
        return self.department_name


class Role(models.Model):
    role_id = models.AutoField(primary_key=True, db_column="role_id")
    role_name = models.CharField(max_length=50, unique=True, db_column="role_name")

    class Meta:
        db_table = "roles"
        managed = False

    def __str__(self):
        return self.role_name


class OrgPosition(models.Model):
    position_id = models.AutoField(primary_key=True, db_column="position_id")
    entity_type = models.CharField(max_length=10, db_column="entity_type")
    plant = models.ForeignKey(
        Plant, on_delete=models.DO_NOTHING, db_column="plant_id",
        null=True, blank=True, related_name="positions"
    )
    department = models.ForeignKey(
        Department, on_delete=models.DO_NOTHING, db_column="department_id",
        null=True, blank=True, related_name="positions"
    )
    role = models.ForeignKey(
        Role, on_delete=models.DO_NOTHING, db_column="role_id",
        related_name="positions"
    )
    hierarchy_level = models.IntegerField(
        db_column="hierarchy_level",
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )

    class Meta:
        db_table = "org_positions"
        managed = False

    def __str__(self):
        target = self.plant.plant_name if self.plant else (
            self.department.department_name if self.department else "—"
        )
        return f"{target} - {self.role.role_name}"


class DepartmentPlantScope(models.Model):
    """
    ربط الإدارات المركزية بالمصانع اللي بتخدمها (إدارة واحدة ممكن تخدم أكتر من مصنع)
    """
    id = models.AutoField(primary_key=True, db_column="id")
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, db_column="department_id",
        related_name="plant_scopes"
    )
    plant = models.ForeignKey(
        Plant, on_delete=models.CASCADE, db_column="plant_id",
        related_name="department_scopes"
    )

    class Meta:
        db_table = "department_plant_scope"
        managed = False
        unique_together = (("department", "plant"),)

    def __str__(self):
        return f"{self.department.department_name} → {self.plant.plant_code}"


class OrgPositionDepartmentScope(models.Model):
    """
    ربط منصب واحد (زي Deputy CEO) بأكتر من إدارة/قطاع في نفس الوقت
    """
    id = models.AutoField(primary_key=True, db_column="id")
    position = models.ForeignKey(
        OrgPosition, on_delete=models.CASCADE, db_column="position_id",
        related_name="department_scopes"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, db_column="department_id",
        related_name="position_scopes"
    )

    class Meta:
        db_table = "org_position_department_scope"
        managed = False
        unique_together = (("position", "department"),)

    def __str__(self):
        return f"{self.position} → {self.department.department_name}"