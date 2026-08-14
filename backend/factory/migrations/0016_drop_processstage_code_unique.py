from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("factory", "0015_alter_processstage_name"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE factory_process_stages "
                "DROP CONSTRAINT IF EXISTS factory_process_stages_plant_id_code_80d5c899_uniq;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
