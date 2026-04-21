from django.contrib import admin
from .models import Ticket, TicketTier


@admin.register(TicketTier)
class TicketTierAdmin(admin.ModelAdmin):
    list_display = ['event', 'name', 'price_cents', 'currency', 'quantity', 'sold', 'is_active']
    list_filter = ['is_active', 'currency']
    search_fields = ['name', 'event__title']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'holder', 'tier', 'total_cents', 'payment_status', 'checked_in_at']
    list_filter = ['payment_status', 'is_incognito']
    search_fields = ['event__title', 'holder__username', 'stripe_payment_intent_id']
    readonly_fields = ['qr_token', 'qr_signature', 'stripe_payment_intent_id', 'stripe_client_secret']
