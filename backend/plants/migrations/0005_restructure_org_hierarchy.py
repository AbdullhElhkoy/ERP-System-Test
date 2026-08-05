from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('plants', '0004_add_department_category'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='plant', name='phase'),
                migrations.AddField(
                    model_name='department', name='parent_department',
                    field=models.ForeignKey(
                        null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name='sub_departments', to='plants.department',
                        db_column='parent_department_id',
                    ),
                ),
                migrations.AlterField(
                    model_name='orgposition', name='hierarchy_level',
                    field=models.IntegerField(
                        db_column='hierarchy_level',
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(10),
                        ],
                    ),
                ),
                migrations.AddField(
                    model_name='departmentplantscope', name='id',
                    field=models.AutoField(primary_key=True, db_column='id', serialize=False),
                ),
                migrations.CreateModel(
                    name='OrgPositionDepartmentScope',
                    fields=[
                        ('id', models.AutoField(primary_key=True, db_column='id', serialize=False)),
                        ('position', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_scopes', to='plants.orgposition', db_column='position_id')),
                        ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='position_scopes', to='plants.department', db_column='department_id')),
                    ],
                    options={'db_table': 'org_position_department_scope'},
                ),
                migrations.AlterUniqueTogether(
                    name='orgpositiondepartmentscope',
                    unique_together={('position', 'department')},
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE plants DROP COLUMN IF EXISTS phase;

                        ALTER TABLE departments ADD COLUMN parent_department_id INTEGER
                            REFERENCES departments(department_id) ON DELETE SET NULL;

                        ALTER TABLE org_positions
                            ADD CONSTRAINT chk_hierarchy_level CHECK (hierarchy_level BETWEEN 1 AND 10);

                        ALTER TABLE department_plant_scope DROP CONSTRAINT department_plant_scope_pkey;
                        ALTER TABLE department_plant_scope ADD COLUMN id SERIAL PRIMARY KEY;
                        ALTER TABLE department_plant_scope ADD CONSTRAINT uq_dept_plant UNIQUE (department_id, plant_id);

                        CREATE TABLE org_position_department_scope (
                            id SERIAL PRIMARY KEY,
                            position_id INTEGER NOT NULL REFERENCES org_positions(position_id) ON DELETE CASCADE,
                            department_id INTEGER NOT NULL REFERENCES departments(department_id) ON DELETE CASCADE,
                            UNIQUE (position_id, department_id)
                        );
                    """,
                    reverse_sql="""
                        DROP TABLE IF EXISTS org_position_department_scope;
                        ALTER TABLE department_plant_scope DROP CONSTRAINT IF EXISTS uq_dept_plant;
                        ALTER TABLE department_plant_scope DROP COLUMN IF EXISTS id;
                        ALTER TABLE org_positions DROP CONSTRAINT IF EXISTS chk_hierarchy_level;
                        ALTER TABLE departments DROP COLUMN IF EXISTS parent_department_id;
                        ALTER TABLE plants ADD COLUMN phase SMALLINT;
                    """,
                ),
            ],
        ),
    ]