import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("factory", "0023_packingtype_ordering"),
        ("employees", "0002_shift_tables_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="processreading",
            name="shift",
            field=models.ForeignKey(
                blank=True,
                db_column="shift_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="factory_process_readings",
                to="employees.shifttype",
            ),
        ),
    ]
