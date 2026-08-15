# Generated manually to make legacy shift tables usable by Django ORM.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE shift_rotation_pattern ADD COLUMN IF NOT EXISTS id bigserial",
            reverse_sql="ALTER TABLE shift_rotation_pattern DROP COLUMN IF EXISTS id",
        ),
        migrations.RunSQL(
            "ALTER TABLE rotation_reference ADD COLUMN IF NOT EXISTS id bigserial",
            reverse_sql="ALTER TABLE rotation_reference DROP COLUMN IF EXISTS id",
        ),
    ]
