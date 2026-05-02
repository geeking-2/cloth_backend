from rest_framework import serializers
from .models import ConditionReport


class ConditionReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionReport
        fields = [
            'id', 'item', 'rental', 'handover', 'submitted_by',
            'moment', 'photo_urls', 'video_url', 'notes',
            'ai_score', 'ai_is_acceptable', 'ai_detected_issues',
            'ai_estimated_repair_cost', 'ai_recommendation',
            'created_at',
        ]
        read_only_fields = [
            'submitted_by', 'ai_score', 'ai_is_acceptable',
            'ai_detected_issues', 'ai_estimated_repair_cost',
            'ai_recommendation', 'created_at',
        ]
