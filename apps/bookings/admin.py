from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Booking, BookingEvent


class BookingEventInline(admin.TabularInline):
    model = BookingEvent
    extra = 0
    readonly_fields = ['event_type', 'actor', 'note', 'created_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'space_title', 'space_venue', 'creator_name', 'creator_username',
        'start_date', 'end_date', 'total_amount', 'status', 'payment_status',
    ]
    list_filter = ['status', 'payment_status', 'booking_type']
    search_fields = [
        'space__title',
        'space__venue__organization_name', 'space__venue__user__username', 'space__venue__user__email',
        'creator__display_name', 'creator__user__username', 'creator__user__email',
        'stripe_payment_intent_id',
    ]
    list_per_page = 50
    list_select_related = ['space', 'space__venue', 'space__venue__user', 'creator', 'creator__user']
    inlines = [BookingEventInline]
    readonly_fields = ['stripe_payment_intent_id', 'stripe_client_secret', 'created_at', 'updated_at', 'responded_at']

    def space_title(self, obj):
        url = reverse('admin:spaces_space_change', args=[obj.space.id])
        return format_html('<a href="{}">{}</a>', url, obj.space.title)
    space_title.short_description = 'Space'
    space_title.admin_order_field = 'space__title'

    def space_venue(self, obj):
        return obj.space.venue.organization_name
    space_venue.short_description = 'Venue'

    def creator_name(self, obj):
        return obj.creator.display_name
    creator_name.short_description = 'Creator'

    def creator_username(self, obj):
        user = obj.creator.user
        url = reverse('admin:accounts_user_change', args=[user.id])
        return format_html('<a href="{}"><code>{}</code></a>', url, user.username)
    creator_username.short_description = 'Creator username'
    creator_username.admin_order_field = 'creator__user__username'


@admin.register(BookingEvent)
class BookingEventAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'event_type', 'actor', 'created_at']
    list_filter = ['event_type']
