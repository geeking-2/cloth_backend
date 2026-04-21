from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'reviewer', 'reviewee', 'direction', 'rating', 'booking', 'created_at']
    list_filter = ['rating', 'direction', 'created_at']
    search_fields = ['reviewer__username', 'reviewee__username', 'comment']
    raw_id_fields = ['booking', 'reviewer', 'reviewee']
