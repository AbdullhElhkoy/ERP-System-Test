from django.utils.translation import gettext_lazy as _
from plants.models import Plant


class FactoryPlant(Plant):
    class Meta:
        proxy = True
        app_label = "factory"
        verbose_name = _("Plant")
        verbose_name_plural = _("Plants")
