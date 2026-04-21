from rest_framework import serializers
from .models import Post, Story, Comment


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    item_title = serializers.CharField(source='item.title', read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'author', 'author_name', 'author_avatar', 'item', 'item_title',
                  'caption', 'location_tag', 'event_type', 'media_urls',
                  'has_face_blur', 'has_background_blur', 'is_anonymous',
                  'likes_count', 'comments_count', 'item_clicks_count', 'created_at']
        read_only_fields = ['author', 'likes_count', 'comments_count',
                            'item_clicks_count', 'created_at']

    def get_author_name(self, obj):
        if obj.is_anonymous:
            return 'Anonyme'
        u = obj.author
        if u.display_mode == 'pseudo' and u.pseudonym:
            return u.pseudonym
        if u.display_mode == 'anonymous':
            return 'Anonyme'
        return f"{u.first_name} {u.last_name}".strip() or u.username

    def get_author_avatar(self, obj):
        return obj.author.avatar


class StorySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    item_title = serializers.CharField(source='item.title', read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'author', 'author_name', 'item', 'item_title',
                  'media_url', 'media_type', 'caption',
                  'has_face_blur', 'is_anonymous',
                  'views_count', 'expires_at', 'created_at']
        read_only_fields = ['author', 'views_count', 'created_at']

    def get_author_name(self, obj):
        if obj.is_anonymous:
            return 'Anonyme'
        u = obj.author
        return u.pseudonym or u.username


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'user_name', 'post', 'text', 'created_at']
        read_only_fields = ['user', 'created_at']
