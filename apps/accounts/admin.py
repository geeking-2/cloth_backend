from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import User, VenueProfile, CreatorProfile, EmailVerificationToken, PasswordResetToken


class VenueProfileInline(admin.StackedInline):
    model = VenueProfile
    can_delete = False
    fk_name = 'user'


class CreatorProfileInline(admin.StackedInline):
    model = CreatorProfile
    can_delete = False
    fk_name = 'user'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'is_verified', 'is_staff', 'date_joined']
    list_filter = ['role', 'is_verified', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_per_page = 50
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('role', 'avatar', 'bio', 'phone', 'website', 'is_verified')}),
    )
    inlines = [VenueProfileInline, CreatorProfileInline]

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or '-'
    full_name.short_description = 'Name'


@admin.register(VenueProfile)
class VenueProfileAdmin(admin.ModelAdmin):
    list_display = ['organization_name', 'owner_username', 'owner_email', 'organization_type', 'city', 'country', 'is_featured']
    list_filter = ['organization_type', 'is_featured', 'country']
    search_fields = [
        'organization_name', 'city', 'country',
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
    ]
    list_per_page = 50
    list_select_related = ['user']

    def owner_username(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}"><code>{}</code></a>', url, obj.user.username)
    owner_username.short_description = 'Owner username'
    owner_username.admin_order_field = 'user__username'

    def owner_email(self, obj):
        return obj.user.email
    owner_email.short_description = 'Email'


@admin.register(CreatorProfile)
class CreatorProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'owner_username', 'owner_email', 'specialty', 'city', 'country', 'years_experience', 'is_featured']
    list_filter = ['specialty', 'is_featured', 'country']
    search_fields = [
        'display_name', 'city',
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
    ]
    list_per_page = 50
    list_select_related = ['user']

    def owner_username(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}"><code>{}</code></a>', url, obj.user.username)
    owner_username.short_description = 'Username'
    owner_username.admin_order_field = 'user__username'

    def owner_email(self, obj):
        return obj.user.email
    owner_email.short_description = 'Email'


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'used', 'created_at']
