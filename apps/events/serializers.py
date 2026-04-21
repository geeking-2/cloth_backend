from rest_framework import serializers
from django.utils import timezone
from .models import Event, Story, EventRSVP, EventInvite, EventBroadcast


def _profile_name(user):
    if not user:
        return ''
    if user.role == 'venue' and hasattr(user, 'venue_profile') and user.venue_profile:
        return user.venue_profile.organization_name or user.username
    if user.role == 'creator' and hasattr(user, 'creator_profile') and user.creator_profile:
        return user.creator_profile.display_name or user.username
    if user.role == 'audience' and hasattr(user, 'audience_profile') and user.audience_profile:
        return user.audience_profile.display_name or user.username
    return user.username


def _profile_avatar(user):
    if not user:
        return None
    # CreatorProfile has no image field — use User.avatar
    if user.role == 'venue' and hasattr(user, 'venue_profile') and user.venue_profile:
        return user.venue_profile.logo or getattr(user, 'avatar', None)
    return getattr(user, 'avatar', None)


class EventSerializer(serializers.ModelSerializer):
    host_name = serializers.SerializerMethodField()
    host_avatar = serializers.SerializerMethodField()
    host_role = serializers.CharField(source='host.role', read_only=True)
    host_username = serializers.CharField(source='host.username', read_only=True)
    space_title = serializers.CharField(source='space.title', read_only=True)
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'slug', 'host', 'host_name', 'host_avatar', 'host_role', 'host_username',
            'title', 'event_type', 'description', 'cover_image',
            'starts_at', 'ends_at', 'space', 'space_title', 'space_slug',
            'portfolio_project', 'location_text', 'external_url', 'is_public',
            'max_capacity', 'public_attendee_list', 'ticketing_enabled',
            'age_restriction', 'incognito_fee_cents',
            'is_live', 'is_upcoming', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'host', 'created_at', 'updated_at', 'is_live', 'is_upcoming']

    def get_host_name(self, obj):
        return _profile_name(obj.host)

    def get_host_avatar(self, obj):
        return _profile_avatar(obj.host)

    def create(self, validated_data):
        validated_data['host'] = self.context['request'].user
        return super().create(validated_data)


class StorySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    author_role = serializers.CharField(source='author.role', read_only=True)
    author_username = serializers.CharField(source='author.username', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    space_title = serializers.CharField(source='space.title', read_only=True)
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Story
        fields = [
            'id', 'author', 'author_name', 'author_avatar', 'author_role', 'author_username',
            'event', 'event_title', 'event_slug', 'space', 'space_title', 'space_slug',
            'image', 'caption', 'link_url', 'created_at', 'expires_at', 'is_active',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'expires_at', 'is_active']

    def get_author_name(self, obj):
        return _profile_name(obj.author)

    def get_author_avatar(self, obj):
        return _profile_avatar(obj.author)

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class EventRSVPSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    display_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = EventRSVP
        fields = [
            'id', 'event', 'user_id', 'username', 'user_role',
            'display_name', 'avatar',
            'status', 'incognito', 'created_at',
        ]
        read_only_fields = ['id', 'event', 'user_id', 'created_at']

    def get_display_name(self, obj):
        return _profile_name(obj.user)

    def get_avatar(self, obj):
        return _profile_avatar(obj.user)


class EventInviteSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    event_starts_at = serializers.DateTimeField(source='event.starts_at', read_only=True)
    event_cover_image = serializers.URLField(source='event.cover_image', read_only=True)
    inviter_name = serializers.SerializerMethodField()
    inviter_avatar = serializers.SerializerMethodField()
    inviter_username = serializers.CharField(source='inviter.username', read_only=True)
    invitee_name = serializers.SerializerMethodField()
    invitee_avatar = serializers.SerializerMethodField()
    invitee_username = serializers.CharField(source='invitee.username', read_only=True)

    class Meta:
        model = EventInvite
        fields = [
            'id', 'event', 'event_title', 'event_slug', 'event_starts_at', 'event_cover_image',
            'inviter', 'inviter_name', 'inviter_avatar', 'inviter_username',
            'invitee', 'invitee_name', 'invitee_avatar', 'invitee_username',
            'message', 'status', 'created_at', 'responded_at',
        ]
        read_only_fields = [
            'id', 'event', 'inviter', 'status', 'created_at', 'responded_at',
        ]

    def get_inviter_name(self, obj): return _profile_name(obj.inviter)
    def get_inviter_avatar(self, obj): return _profile_avatar(obj.inviter)
    def get_invitee_name(self, obj): return _profile_name(obj.invitee)
    def get_invitee_avatar(self, obj): return _profile_avatar(obj.invitee)


class EventBroadcastSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_avatar = serializers.SerializerMethodField()
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)

    class Meta:
        model = EventBroadcast
        fields = [
            'id', 'event', 'event_title', 'event_slug',
            'sender', 'sender_name', 'sender_avatar',
            'subject', 'body', 'audience', 'recipient_count', 'created_at',
        ]
        read_only_fields = ['id', 'event', 'sender', 'recipient_count', 'created_at']

    def get_sender_name(self, obj): return _profile_name(obj.sender)
    def get_sender_avatar(self, obj): return _profile_avatar(obj.sender)
