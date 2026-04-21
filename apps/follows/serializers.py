from rest_framework import serializers
from .models import Follow


def _profile_name(user):
    if not user:
        return ''
    if user.role == 'venue' and hasattr(user, 'venue_profile') and user.venue_profile:
        return user.venue_profile.organization_name or user.username
    if user.role == 'creator' and hasattr(user, 'creator_profile') and user.creator_profile:
        return user.creator_profile.display_name or user.username
    return user.username


def _profile_avatar(user):
    if not user:
        return None
    if user.role == 'venue' and hasattr(user, 'venue_profile') and user.venue_profile:
        return user.venue_profile.logo or getattr(user, 'avatar', None)
    return getattr(user, 'avatar', None)


class FollowUserSerializer(serializers.Serializer):
    """Lightweight user shape for follower/following lists."""
    id = serializers.IntegerField(source='user.id' if False else 'id', read_only=True)
    username = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_name(self, obj):
        return _profile_name(obj)

    def get_avatar(self, obj):
        return _profile_avatar(obj)


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['id', 'created_at']
