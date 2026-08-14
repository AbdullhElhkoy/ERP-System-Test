"""
حذف كل المصانع وجميع البيانات المرتبطة بها، ثم إنشاء مصنع جديد فارغ.

الاستخدام:
    python manage.py delete_all_plants            # يعرض المصانع ويطلب التأكيد
    python manage.py delete_all_plants --yes      # بدون تأكيد
    python manage.py delete_all_plants --yes --keep-positions  # يحذف كل المصانع لكن يحفظ المناصب

المنهجية:
    - يُجمع كل الموديلات التي تشير (مباشرة أو عبر سلسلة FKs) إلى Plant من التطبيقات:
      factory, orders, raw_materials.
    - تُحذف في جولات: كل نموذج يُحذف أولاً، وأي نموذج يُرجع ProtectedError
      يُؤجَّل إلى الجولة التالية (يُحذف النموذج المرجع إليه أولاً)، حتى لا يعتمد
      الأمر على قائمة يدوية قد تنسى بعض الموديلات.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ForeignKey, OneToOneField
from django.apps import apps
from django.db.utils import ProgrammingError, OperationalError
from django.db.models.deletion import ProtectedError

from plants.models import Plant, OrgPosition, DepartmentPlantScope

SHARED_LABELS = {"factory.FieldDefinition", "factory.FactoryPlant"}


class Command(BaseCommand):
    help = "حذف كل المصانع وجميع البيانات المرتبطة بها وإنشاء مصنع جديد فارغ."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="تأكيد بدون سؤال")
        parser.add_argument(
            "--keep-positions",
            action="store_true",
            help="لا تحذف OrgPosition (تُترك بإشارتها للمصنع المحذوف - غير مستحسن)",
        )

    def handle(self, *args, **options):
        plants = list(Plant.objects.all().order_by("plant_id"))
        if not plants:
            self.stdout.write(self.style.WARNING("لا توجد مصانع لحذفها."))
            return

        self.stdout.write("المصانع الموجودة:")
        for p in plants:
            self.stdout.write(f"  [{p.pk}] {p.plant_name}")

        if not options["yes"]:
            confirm = input(f"\nحذف {len(plants)} مصنع وكل بياناتها؟ (اكتب yes): ")
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("تم الإلغاء."))
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
                                f"تخطي {label} (الجدول غير موجود؟): {e}"
                            )
                        )
                        n = 0
                    deleted.add(label)
                    remaining.discard(label)
                    progressed = True
                    if n:
                        self.stdout.write(f"حذف {label}: {n}")
                if not progressed:
                    self.stdout.write(
                        self.style.ERROR(
                            "لم يتبقَّ سجلات محمية من المصانع القديمة — تحقق من "
                            "الموديلات: " + ", ".join(sorted(remaining))
                        )
                    )
                    break

            # حذف المناصب (لا تحذف تلقائياً لـ DO_NOTHING)
            if not options["keep_positions"]:
                n = OrgPosition.objects.all().delete()[0]
                if n:
                    self.stdout.write(f"حذف OrgPosition: {n}")

            # حذف المصانع نفسها
            n = Plant.objects.filter(pk__in=[p.pk for p in plants]).delete()[0]
            self.stdout.write(f"حذف المصانع: {n}")

            # إنشاء مصنع جديد فارغ
            new_plant = Plant.objects.create(plant_name="مصنع جديد")
            self.stdout.write(
                self.style.SUCCESS(
                    f"تم حذف كل المصانع. المصنع الجديد: [{new_plant.pk}] {new_plant.plant_name}"
                )
            )

    def _collect_related_models(self):
        """كل الموديلات (من التطبيقات factory/orders/raw_materials) التي تشير إلى Plant
        عبر سلسلة FKs (مباشرة أو غير مباشرة)، عدا المشتركة للشركة."""
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
