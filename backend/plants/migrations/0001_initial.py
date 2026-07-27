from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('role_id', models.AutoField(db_column='role_id', primary_key=True, serialize=False)),
                ('role_name', models.CharField(db_column='role_name', max_length=50, unique=True)),
            ],
            options={
                'db_table': 'roles',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('department_id', models.AutoField(db_column='department_id', primary_key=True, serialize=False)),
                ('department_code', models.CharField(db_column='department_code', max_length=20, unique=True)),
                ('department_name', models.CharField(db_column='department_name', max_length=50, unique=True)),
            ],
            options={
                'db_table': 'departments',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Plant',
            fields=[
                ('plant_id', models.AutoField(db_column='plant_id', primary_key=True, serialize=False)),
                ('plant_code', models.CharField(db_column='plant_code', max_length=20, unique=True)),
                ('plant_name', models.CharField(db_column='plant_name', max_length=50, unique=True)),
                ('phase', models.SmallIntegerField(blank=True, db_column='phase', null=True)),
            ],
            options={
                'db_table': 'plants',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='OrgPosition',
            fields=[
                ('position_id', models.AutoField(db_column='position_id', primary_key=True, serialize=False)),
                ('entity_type', models.CharField(db_column='entity_type', max_length=10)),
                ('hierarchy_level', models.IntegerField(db_column='hierarchy_level')),
                ('plant', models.ForeignKey(blank=True, db_column='plant_id', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='positions', to='plants.plant')),
                ('department', models.ForeignKey(blank=True, db_column='department_id', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='positions', to='plants.department')),
                ('role', models.ForeignKey(db_column='role_id', on_delete=django.db.models.deletion.DO_NOTHING, related_name='positions', to='plants.role')),
            ],
            options={
                'db_table': 'org_positions',
                'managed': False,
            },
        ),
    ]