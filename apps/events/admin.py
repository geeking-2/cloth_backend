from django.contrib import admin
from .models import Event, Story


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'host', 'event_type', 'starts_at', 'space', 'is_public']
    list_filter = ['event_type', 'is_public', 'starts_at']
    search_fields = ['title', 'host__username', 'space__title']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['host', 'space', 'portfolio_project']


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ['author', 'event', 'created_at', 'expires_at']
    search_fields = ['author__username', 'caption']
    raw_id_fields = ['author', 'event', 'space']
