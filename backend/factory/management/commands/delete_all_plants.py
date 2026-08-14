"""
حذف كل المصانع وجميع البيانات المرتبطة بها، ثم إنشاء مصنع جديد فارغ.

الاستخدام:
    python manage.py delete_all_plants            # يعرض المصانع ويطلب التأكيد
    python manage.py delete_all_plants --yes      # بدون تأكيد
    python manage.py delete_all_plants --yes --keep-positions  # يحذف كل المصانع لكن يحفظ المناصب التي لا تخص مصنعاً
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ForeignKey
from django.apps import apps

from plants.models import Plant, OrgPosition, DepartmentPlantScope


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

        with transaction.atomic():
            plant_ids = [p.pk for p in plants]

            # 1) حذف السجلات المحمية بـ PROTECT في orders
            self._delete_for_plant("orders.OrderPlantAllocation", "plant", plant_ids)
            self._delete_for_plant("orders.OrderPlantAllocationChangeLog", "from_plant", plant_ids)
            self._delete_for_plant("orders.OrderPlantAllocationChangeLog", "to_plant", plant_ids)
            self._delete_for_plant("orders.OrderMovement", "source_plant", plant_ids)

            # 2) حذف السجلات المحمية بـ PROTECT في raw_materials
            self._delete_for_plant("raw_materials.MaterialStorage", "plant", plant_ids)
            self._delete_for_plant("raw_materials.RawMaterialDelivery", "plant", plant_ids)
            self._delete_for_plant("raw_materials.InventoryTransaction", "plant", plant_ids)
            self._delete_for_plant("raw_materials.RawMaterialSample", "plant", plant_ids)

            # 3) حذف بيانات factory يدوياً بترتيب التبعية (بعض FKs محمية PROTECT)
            #    وتمنع الحذف التلقائي CASCADE بين قراءات السحب ونقاط السحب.
            factory_models = [
                "factory.FloorStockMovement",
                "factory.PackingConversion",
                "factory.PackingEvent",
                "factory.QualityConformityResult",
                "factory.TonGradeAssignment",
                "factory.SampleChemicalResult",
                "factory.RepresentativeSample",
                "factory.Ton",
                "factory.OutputReading",
                "factory.OutputPoint",
                "factory.Grade",
                "factory.GradeReason",
                "factory.ConformityRule",
                "factory.TestDefinition",
                "factory.RepresentativeGroupSize",
                "factory.PackingTypeField",
                "factory.PackingLocation",
                "factory.PackingType",
                "factory.PlantLotSetting",
                "factory.ProcessReading",
                "factory.ProcessStage",
            ]
            for label in factory_models:
                self._delete_all(label)

            # 4) حذف مناصب المصنع (لا تحذف تلقائياً لـ DO_NOTHING)
            #    يُحذف الكل وليس المرتبط بالمصانع فقط، لأن المناصب قد تُترك أيتاماً
            #    بعد حذف المصانع في جولة سابقة.
            if not options["keep_positions"]:
                n = OrgPosition.objects.all().delete()[0]
                self.stdout.write(f"حذف OrgPosition: {n}")
            n = DepartmentPlantScope.objects.filter(plant_id__in=plant_ids).delete()[0]
            self.stdout.write(f"حذف DepartmentPlantScope: {n}")

            # 5) حذف المصانع نفسها
            n = Plant.objects.filter(pk__in=plant_ids).delete()[0]
            self.stdout.write(f"حذف المصانع والبيانات المرتبطة: {n}")

            # 5) إنشاء مصنع جديد فارغ
            new_plant = Plant.objects.create(plant_name="مصنع جديد")
            self.stdout.write(
                self.style.SUCCESS(
                    f"تم حذف كل المصانع. المصنع الجديد: [{new_plant.pk}] {new_plant.plant_name}"
                )
            )

    def _delete_all(self, model_label):
        Model = apps.get_model(model_label)
        n = Model.objects.all().delete()[0]
        if n:
            self.stdout.write(f"حذف {model_label}: {n}")

    def _delete_for_plant(self, model_label, fk_field, plant_ids):
        Model = apps.get_model(model_label)
        filter_kwargs = {f"{fk_field}_id__in": plant_ids}
        n = Model.objects.filter(**filter_kwargs).delete()[0]
        if n:
            self.stdout.write(f"حذف {model_label}: {n}")
