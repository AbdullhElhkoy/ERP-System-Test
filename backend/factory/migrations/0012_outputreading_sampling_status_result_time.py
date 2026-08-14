from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("factory", "0011_fielddefinition_packingtypefield"),
    ]

    operations = [
        migrations.AddField(
            model_name="outputreading",
            name="sampling_status",
            field=models.CharField(
                blank=True,
                choices=[("تم", "تم"), ("لم يتم", "لم يتم")],
                default="",
                help_text="حالة سحب العينة من شاشة الإدخال",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="outputreading",
            name="result_time",
            field=models.TimeField(
                blank=True, help_text="وقت ظهور النتيجة", null=True
            ),
        ),
    ]
