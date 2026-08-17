from django.db import models
from plants.models import Plant, OrgPosition, DepartmentPlantScope


# ---------------------------------------------------------------------------
# Plant-scope permission helpers (existing)
# ---------------------------------------------------------------------------

def get_user_position(user):
    profile = getattr(user, "profile", None)
    if not profile or not profile.org_position:
        return None
    return profile.org_position


def get_editable_plant_ids(user):
    position = get_user_position(user)
    if not position:
        return Plant.objects.none()
    if position.entity_type == "plant" and position.plant:
        return Plant.objects.filter(plant_id=position.plant_id)
    if position.entity_type == "department" and position.department:
        scoped = DepartmentPlantScope.objects.filter(
            department=position.department
        ).values_list("plant_id", flat=True)
        return Plant.objects.filter(plant_id__in=scoped)
    return Plant.objects.none()


def get_viewable_plant_ids(user):
    position = get_user_position(user)
    if not position:
        return Plant.objects.none()
    if position.entity_type == "plant" and position.plant:
        plant_phase = getattr(position.plant, "phase", None)
        if plant_phase is None:
            return Plant.objects.filter(plant_id=position.plant_id)
        return Plant.objects.filter(phase=plant_phase)
    if position.entity_type == "department" and position.department:
        scoped = DepartmentPlantScope.objects.filter(
            department=position.department
        ).values_list("plant_id", flat=True)
        return Plant.objects.filter(plant_id__in=scoped)
    return Plant.objects.none()


def can_view_plant(user, plant_id):
    return get_viewable_plant_ids(user).filter(plant_id=plant_id).exists()


def can_edit_plant(user, plant_id):
    return get_editable_plant_ids(user).filter(plant_id=plant_id).exists()


# ---------------------------------------------------------------------------
# Screen / Column Permission models
# ---------------------------------------------------------------------------

class Screen(models.Model):
    """A registered screen/sheet in the system."""
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "custom_permissions_screens"
        ordering = ["code"]

    def __str__(self):
        return self.name or self.code


class ScreenColumn(models.Model):
    """A column or action within a screen."""
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name="columns")
    code = models.SlugField(max_length=50)
    label = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "custom_permissions_screen_columns"
        unique_together = (("screen", "code"),)
        ordering = ["screen", "order"]

    def __str__(self):
        return f"{self.screen.code}.{self.code}"


class ColumnPermission(models.Model):
    """Permission level for a role on a specific column."""
    LEVEL_HIDDEN = "hidden"
    LEVEL_VIEW = "view"
    LEVEL_EDIT = "edit"
    LEVEL_CHOICES = [
        (LEVEL_HIDDEN, "Hidden"),
        (LEVEL_VIEW, "View Only"),
        (LEVEL_EDIT, "View & Edit"),
    ]

    column = models.ForeignKey(ScreenColumn, on_delete=models.CASCADE, related_name="permissions")
    role = models.ForeignKey("plants.Role", on_delete=models.CASCADE, related_name="column_permissions")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_HIDDEN)

    class Meta:
        db_table = "custom_permissions_column_permissions"
        unique_together = (("column", "role"),)

    def __str__(self):
        return f"{self.column} / {self.role} = {self.level}"
