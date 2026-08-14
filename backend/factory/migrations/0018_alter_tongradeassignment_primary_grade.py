from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("factory", "0017_final_product_grade_hierarchy_ton_status_floor_stock_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tongradeassignment",
            name="primary_grade",
            field=models.ForeignKey(
                help_text="الجريد الأساسي (تصدير / محلي / غير مطابق)",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ton_primary_assignments",
                to="factory.grade",
            ),
        ),
    ]
