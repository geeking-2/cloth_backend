from rest_framework import serializers
from .models import Conversation, Message


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


class UserMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_name(self, obj):
        return _profile_name(obj)

    def get_avatar(self, obj):
        return _profile_avatar(obj)


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'body', 'image', 'created_at', 'read_at']
        read_only_fields = ['id', 'conversation', 'sender', 'created_at', 'read_at']


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'other_user', 'last_message', 'unread_count', 'last_message_at', 'created_at']

    def _me(self):
        request = self.context.get('request')
        return request.user if request else None

    def get_other_user(self, obj):
        me = self._me()
        other = obj.other_participant(me) if me else None
        return UserMiniSerializer(other).data if other else None

    def get_last_message(self, obj):
        m = obj.messages.order_by('-created_at').first()
        if not m:
            return None
        return {
            'id': m.id,
            'body': m.body,
            'has_image': bool(m.image),
            'sender_id': m.sender_id,
            'created_at': m.created_at,
            'read_at': m.read_at,
        }

    def get_unread_count(self, obj):
        me = self._me()
        if not me:
            return 0
        return obj.messages.filter(read_at__isnull=True).exclude(sender=me).count()
