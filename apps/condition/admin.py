from django.contrib import admin
from .models import ConditionReport


@admin.register(ConditionReport)
class ConditionReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'moment', 'ai_score', 'ai_recommendation', 'created_at')
    list_filter = ('moment', 'ai_recommendation', 'ai_is_acceptable')
    search_fields = ('item__title',)
