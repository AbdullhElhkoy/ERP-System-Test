from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("factory", "0012_outputreading_sampling_status_result_time"),
    ]

    operations = [
        migrations.AddField(
            model_name="outputreading",
            name="dynamic_data",
            field=models.JSONField(blank=True, default=dict, help_text="قيم الحقول الديناميكية المفعّلة لنوع التعبئة"),
        ),
    ]
