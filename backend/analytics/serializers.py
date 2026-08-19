from rest_framework import serializers


class AggregateRequestSerializer(serializers.Serializer):
    model_key = serializers.ChoiceField(
        choices=[],  # populated dynamically from REPORTABLE_MODELS
        help_text="Key identifying the model to aggregate.",
    )
    metric_field = serializers.CharField(required=False, allow_blank=True, default=None)
    agg_func = serializers.ChoiceField(choices=["sum", "avg", "count", "min", "max"])
    group_by = serializers.ListField(child=serializers.CharField(), min_length=1, max_length=5)
    filters = serializers.DictField(required=False, default=dict)
    date_from = serializers.DateField(required=False, allow_null=True, default=None)
    date_to = serializers.DateField(required=False, allow_null=True, default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from analytics.aggregation import REPORTABLE_MODELS
        self.fields["model_key"].choices = list(REPORTABLE_MODELS.keys())


class AggregateResponseSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    series = serializers.ListField(child=serializers.DictField())
    meta = serializers.DictField()


class StockSnapshotResponseSerializer(serializers.Serializer):
    plants = serializers.DictField()
    summary = serializers.DictField()


class StockTrendResponseSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    series = serializers.ListField(child=serializers.DictField())
    meta = serializers.DictField()


class SPCTestSerializer(serializers.Serializer):
    plant_id = serializers.IntegerField()
    plant_name = serializers.CharField()
    test_id = serializers.IntegerField()
    test_name = serializers.CharField()
    test_category = serializers.CharField()
    unit = serializers.CharField()
    rule_id = serializers.IntegerField()
    rule_name = serializers.CharField()
    min_value = serializers.FloatField(allow_null=True)
    max_value = serializers.FloatField(allow_null=True)
    quality_grade = serializers.CharField()


class NelsonViolationSerializer(serializers.Serializer):
    rule = serializers.IntegerField()
    point_indices = serializers.ListField(child=serializers.IntegerField())
    description = serializers.CharField()


class SPCReportSerializer(serializers.Serializer):
    plant_id = serializers.IntegerField()
    test_name = serializers.CharField()
    n = serializers.IntegerField()
    provisional = serializers.BooleanField()
    mu = serializers.FloatField()
    sigma_within = serializers.FloatField()
    sigma_overall = serializers.FloatField()
    spec = serializers.DictField()
    cp = serializers.FloatField(allow_null=True)
    cpu = serializers.FloatField(allow_null=True)
    cpl = serializers.FloatField(allow_null=True)
    cpk = serializers.FloatField(allow_null=True)
    pp = serializers.FloatField(allow_null=True)
    ppu = serializers.FloatField(allow_null=True)
    ppl = serializers.FloatField(allow_null=True)
    ppk = serializers.FloatField(allow_null=True)
    cpm = serializers.FloatField(allow_null=True)
    sigma_level = serializers.FloatField(allow_null=True)
    dpmo = serializers.FloatField()
    nelson_violations = NelsonViolationSerializer(many=True)
    measurements = serializers.ListField(child=serializers.DictField())
