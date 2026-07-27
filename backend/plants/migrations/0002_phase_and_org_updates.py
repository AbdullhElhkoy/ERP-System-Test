from django.db import migrations, models


PHASE_MAP = {
    "DCP": 1,
    "GCC1": 1,
    "GCC2": 1,
    "PA": 1,
    "SOP A": 2,
    "SOP B": 2,
    "SOP C": 2,
    "SOP D": 2,
    "SOP H": 2,
    "G SOP": 2,
    "SA 200": 3,
    "SA 600": 3,
}

NEW_ROLES = [
    "CEO",
    "Deputy CEO",
    "Head of Quality Sector",
    "Head of ECOPHOS Production Sector",
    "Head of SOP Production Sector",
    "Head of SA Production Sector",
]

EXEC_POSITIONS = [
    ("CEO", 0),
    ("Deputy CEO", 0),
    ("Head of Quality Sector", 1),
    ("Head of ECOPHOS Production Sector", 1),
    ("Head of SOP Production Sector", 1),
    ("Head of SA Production Sector", 1),
]


def populate_data(apps, schema_editor):
    Plant = apps.get_model("plants", "Plant")
    Department = apps.get_model("plants", "Department")
    Role = apps.get_model("plants", "Role")
    OrgPosition = apps.get_model("plants", "OrgPosition")

    Department.objects.filter(department_code="LAB_ECHPS").update(
        department_code="LAB_ECOPHOS", department_name="ECOPHOS LAB"
    )

    for plant in Plant.objects.all():
        phase = PHASE_MAP.get(plant.plant_name)
        if phase:
            plant.phase = phase
            plant.save(update_fields=["phase"])

    Department.objects.get_or_create(
        department_code="QC_ECOPHOS", defaults={"department_name": "QC ECOPHOS"}
    )
    Department.objects.get_or_create(
        department_code="QC_SOP", defaults={"department_name": "QC SOP"}
    )

    exec_office, _ = Department.objects.get_or_create(
        department_code="EXEC", defaults={"department_name": "Executive Office"}
    )

    roles = {}
    for name in NEW_ROLES:
        role, _ = Role.objects.get_or_create(role_name=name)
        roles[name] = role

    for role_name, level in EXEC_POSITIONS:
        OrgPosition.objects.get_or_create(
            entity_type="department",
            department=exec_office,
            plant=None,
            role=roles[role_name],
            defaults={"hierarchy_level": level},
        )


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE plants ADD COLUMN IF NOT EXISTS phase SMALLINT NULL;",
                    reverse_sql="ALTER TABLE plants DROP COLUMN IF EXISTS phase;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="plant",
                    name="phase",
                    field=models.SmallIntegerField(
                        null=True, blank=True, db_column="phase"
                    ),
                ),
            ],
        ),
        migrations.RunPython(populate_data, reverse_populate),
    ]