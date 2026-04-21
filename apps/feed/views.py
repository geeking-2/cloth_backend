from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Post, Story, Like, Comment
from .serializers import PostSerializer, StorySerializer, CommentSerializer


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Post.objects.select_related('author', 'item').all()
        mp = getattr(self.request, 'marketplace', None)
        if mp:
            qs = qs.filter(marketplace=mp)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            marketplace=getattr(self.request, 'marketplace', None),
        )

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
            post.likes_count = max(0, post.likes_count - 1)
            post.save(update_fields=['likes_count'])
            return Response({'liked': False, 'likes_count': post.likes_count})
        post.likes_count += 1
        post.save(update_fields=['likes_count'])
        return Response({'liked': True, 'likes_count': post.likes_count})

    @action(detail=True, methods=['post'])
    def track_item_click(self, request, pk=None):
        post = self.get_object()
        post.item_clicks_count += 1
        post.save(update_fields=['item_clicks_count'])
        return Response({'item_clicks_count': post.item_clicks_count})


class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Story.objects.filter(expires_at__gt=timezone.now())
        mp = getattr(self.request, 'marketplace', None)
        if mp:
            qs = qs.filter(marketplace=mp)
        return qs.select_related('author', 'item').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            marketplace=getattr(self.request, 'marketplace', None),
        )


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Comment.objects.all()

    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        comment.post.comments_count += 1
        comment.post.save(update_fields=['comments_count'])
