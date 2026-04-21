from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Space, SpaceImage, Availability, SavedSpace, SpaceAttachment


class SpaceImageInline(admin.TabularInline):
    model = SpaceImage
    extra = 1
    readonly_fields = ['thumbnail']

    def thumbnail(self, obj):
        if obj.image_url:
            url = obj.image_url[:120] if len(obj.image_url) > 120 else obj.image_url
            return format_html('<img src="{}" style="max-height: 60px; max-width: 100px;" />', obj.image_url)
        return '-'


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 1


class SpaceAttachmentInline(admin.TabularInline):
    model = SpaceAttachment
    extra = 0


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'venue_organization', 'venue_owner_username', 'venue_owner_email',
        'space_type', 'daily_rate', 'is_active', 'is_featured',
    ]
    list_filter = ['space_type', 'is_active', 'is_featured', 'venue__city', 'venue__country']
    search_fields = [
        'title', 'slug', 'description',
        'venue__organization_name', 'venue__city', 'venue__country',
        'venue__user__username', 'venue__user__email', 'venue__user__first_name', 'venue__user__last_name',
    ]
    prepopulated_fields = {'slug': ('title',)}
    inlines = [SpaceImageInline, AvailabilityInline, SpaceAttachmentInline]
    list_per_page = 50
    list_select_related = ['venue', 'venue__user']

    def venue_organization(self, obj):
        url = reverse('admin:accounts_venueprofile_change', args=[obj.venue.id])
        return format_html('<a href="{}">{}</a>', url, obj.venue.organization_name)
    venue_organization.short_description = 'Venue'
    venue_organization.admin_order_field = 'venue__organization_name'

    def venue_owner_username(self, obj):
        user = obj.venue.user
        url = reverse('admin:accounts_user_change', args=[user.id])
        return format_html('<a href="{}"><code>{}</code></a>', url, user.username)
    venue_owner_username.short_description = 'Owner (username)'
    venue_owner_username.admin_order_field = 'venue__user__username'

    def venue_owner_email(self, obj):
        return obj.venue.user.email
    venue_owner_email.short_description = 'Owner email'


@admin.register(SavedSpace)
class SavedSpaceAdmin(admin.ModelAdmin):
    list_display = ['user', 'space', 'created_at']
    search_fields = ['user__username', 'space__title']


@admin.register(SpaceAttachment)
class SpaceAttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'space', 'file_type']
    list_filter = ['file_type']
