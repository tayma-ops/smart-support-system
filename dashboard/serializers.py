from rest_framework import serializers


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class PriorityCountSerializer(serializers.Serializer):
    priority = serializers.CharField()
    count = serializers.IntegerField()


class CategoryCountSerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()


class DailyCountSerializer(serializers.Serializer):
    day = serializers.DateField()
    count = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    open = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    waiting = serializers.IntegerField()
    resolved = serializers.IntegerField()
    closed = serializers.IntegerField()
    urgent = serializers.IntegerField()
    unassigned = serializers.IntegerField()
    average_resolution_hours = serializers.FloatField(allow_null=True)
    by_status = StatusCountSerializer(many=True)
    by_priority = PriorityCountSerializer(many=True)
    by_category = CategoryCountSerializer(many=True)
    daily = DailyCountSerializer(many=True)
