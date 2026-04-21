from django.contrib import admin
from .models import Marketplace


@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'domain', 'currency', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('slug', 'name', 'domain')
