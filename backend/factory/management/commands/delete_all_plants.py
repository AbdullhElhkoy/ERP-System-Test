"""
Delete all factories and all associated data, then create a new empty factory.

Usage:
    python manage.py delete_all_plants            # shows factories and asks for confirmation
    python manage.py delete_all_plants --yes      # no confirmation
    python manage.py delete_all_plants --yes --keep-positions  # deletes all factories but keeps positions

Methodology:
    - Collects all models that reference Plant (directly or via FK chains) from apps:
      factory, orders, raw_materials.
    - Deletes in rounds: each model is deleted first, and any model that raises
      ProtectedError is deferred to the next round (the referenced model is deleted first),
    """

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ForeignKey, OneToOneField
from django.apps import apps
from django.db.utils import ProgrammingError, OperationalError
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _

from plants.models import Plant, OrgPosition, DepartmentPlantScope

SHARED_LABELS = {"factory.FieldDefinition", "factory.FactoryPlant"}


class Command(BaseCommand):
    help = _("Delete all factories and all associated data, then create a new empty factory.")

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help=_("Confirm without asking"))
        parser.add_argument(
            "--keep-positions",
            action="store_true",
            help=_("Do not delete OrgPosition (left referencing deleted factory — not recommended)"),
        )

    def handle(self, *args, **options):
        plants = list(Plant.objects.all().order_by("plant_id"))
        if not plants:
            self.stdout.write(self.style.WARNING(_("No factories to delete.")))
            return

        self.stdout.write(_("Existing factories:"))
        for p in plants:
            self.stdout.write(f"  [{p.pk}] {p.plant_name}")

        if not options["yes"]:
            confirm = input(_("\nDelete %(count)d factory and all its data? (type yes): ") % {"count": len(plants)})
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING(_("Cancelled.")))
                return

        labels = self._collect_related_models()
        labels.append("plants.OrgPosition")
        labels.append("plants.DepartmentPlantScope")

        with transaction.atomic():
            remaining = set(labels)
            deleted = set()
            while remaining:
                progressed = False
                for label in list(remaining):
                    if label in deleted:
                        continue
                    try:
                        n = apps.get_model(label).objects.all().delete()[0]
                    except ProtectedError as e:
                        # أضف أي موديل يحمي من حذف — يُحذف قبل هذا
                        for obj in e.protected_objects:
                            remaining.add(obj._meta.label_lower)
                        continue
                    except (ProgrammingError, OperationalError) as e:
                        self.stdout.write(
                            self.style.WARNING(
                                _("Skipping %(label)s (table not found?): %(error)s") % {"label": label, "error": e}
                            )
                        )
                        n = 0
                    deleted.add(label)
                    remaining.discard(label)
                    progressed = True
                    if n:
                        self.stdout.write(_("Deleted %(label)s: %(count)s") % {"label": label, "count": n})
                if not progressed:
                    self.stdout.write(
                        self.style.ERROR(
                            _("Remaining protected records from old factories — check models: %(models)s") % {"models": ", ".join(sorted(remaining))}
                        )
                    )
                    break

            # حذف المناصب (لا تحذف تلقائياً لـ DO_NOTHING)
            if not options["keep_positions"]:
                n = OrgPosition.objects.all().delete()[0]
                if n:
                    self.stdout.write(_("Deleted OrgPosition: %(count)s") % {"count": n})

            # حذف المصانع نفسها
            n = Plant.objects.filter(pk__in=[p.pk for p in plants]).delete()[0]
            self.stdout.write(_("Deleted factories: %(count)s") % {"count": n})

            # إنشاء مصنع جديد فارغ
            new_plant = Plant.objects.create(plant_name=_("New Factory"))
            self.stdout.write(
                self.style.SUCCESS(
                    _("All factories deleted. New factory: [%(pk)s] %(name)s") % {"pk": new_plant.pk, "name": new_plant.plant_name}
                )
            )

    def _collect_related_models(self):
        """Collect all models (from factory/orders/raw_materials apps) that reference Plant
        via FK chains (direct or indirect), excluding shared company models."""
        plant_label = "plants.plant"
        related = set()
        frontier = {plant_label}
        seen = set()

        def fk_targets(label):
            out = set()
            try:
                model = apps.get_model(label)
            except LookupError:
                return out
            for f in model._meta.get_fields():
                if isinstance(f, (ForeignKey, OneToOneField)) and f.related_model is not None:
                    t = f.related_model
                    if not t._meta.proxy:
                        out.add(t._meta.label_lower)
            return out

        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            for app_label in ("factory", "orders", "raw_materials"):
                for model in apps.get_app_config(app_label).get_models():
                    label = model._meta.label_lower
                    if model._meta.proxy or label in SHARED_LABELS:
                        continue
                    if current in fk_targets(label):
                        related.add(label)
                        frontier.add(label)
        return sorted(related)
