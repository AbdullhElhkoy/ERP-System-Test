from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("factory", "0013_outputreading_dynamic_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="processstage",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="مفعّلة"),
        ),
        migrations.AddField(
            model_name="processstage",
            name="order",
            field=models.PositiveIntegerField(default=0, verbose_name="الترتيب"),
        ),
        migrations.AlterField(
            model_name="processstage",
            name="code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="اختياري — يُفضل استخدامه ككود إضافي فقط",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="processstage",
            options={
                "ordering": ["plant", "order", "pk"],
                "verbose_name": "مرحلة تفاعل",
                "verbose_name_plural": "مراحل التفاعل",
            },
        ),
        migrations.AlterUniqueTogether(
            name="processstage",
            unique_together=set(),
        ),
    ]
