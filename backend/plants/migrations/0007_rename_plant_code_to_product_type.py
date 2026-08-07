from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plants', '0006_alter_orgpositiondepartmentscope_options'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='plant', name='plant_code'),
                migrations.AddField(
                    model_name='plant', name='product_type',
                    field=models.CharField(max_length=50, blank=True, db_column='product_type'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE plants DROP CONSTRAINT IF EXISTS plants_plant_code_key;
                        ALTER TABLE plants RENAME COLUMN plant_code TO product_type;
                    """,
                    reverse_sql="""
                        ALTER TABLE plants RENAME COLUMN product_type TO plant_code;
                        ALTER TABLE plants ADD CONSTRAINT plants_plant_code_key UNIQUE (plant_code);
                    """,
                ),
            ],
        ),
    ]