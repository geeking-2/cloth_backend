from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Proposal, PortfolioProject, PortfolioImage


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'creator_name', 'creator_username',
        'space_title', 'space_venue', 'status', 'created_at',
    ]
    list_filter = ['status', 'project_type']
    search_fields = [
        'title', 'description',
        'creator__display_name', 'creator__user__username', 'creator__user__email',
        'space__title', 'space__venue__organization_name',
    ]
    list_per_page = 50
    list_select_related = ['creator', 'creator__user', 'space', 'space__venue']

    def creator_name(self, obj):
        return obj.creator.display_name
    creator_name.short_description = 'Creator'

    def creator_username(self, obj):
        user = obj.creator.user
        url = reverse('admin:accounts_user_change', args=[user.id])
        return format_html('<a href="{}"><code>{}</code></a>', url, user.username)
    creator_username.short_description = 'Username'

    def space_title(self, obj):
        url = reverse('admin:spaces_space_change', args=[obj.space.id])
        return format_html('<a href="{}">{}</a>', url, obj.space.title)
    space_title.short_description = 'Space'

    def space_venue(self, obj):
        return obj.space.venue.organization_name
    space_venue.short_description = 'Venue'


@admin.register(PortfolioProject)
class PortfolioProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'creator_username', 'technology', 'year']
    list_filter = ['technology']
    search_fields = ['title', 'creator__display_name', 'creator__user__username']

    def creator_username(self, obj):
        return obj.creator.user.username
    creator_username.short_description = 'Username'
