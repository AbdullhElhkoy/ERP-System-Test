from plants.models import Plant


class FactoryPlant(Plant):
    class Meta:
        proxy = True
        app_label = "factory"
        verbose_name = "Plant (مصنع)"
        verbose_name_plural = "Plants (مصانع)"
