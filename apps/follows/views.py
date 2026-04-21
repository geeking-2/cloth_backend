from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Follow
from .serializers import FollowUserSerializer

User = get_user_model()


class FollowToggleView(APIView):
    """POST /api/follow/<user_id>/ — toggle follow. Returns {is_following, followers_count}."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        from apps.messaging.models import Block
        target = get_object_or_404(User, pk=user_id)
        if target == request.user:
            return Response({'detail': "You can't follow yourself."}, status=status.HTTP_400_BAD_REQUEST)
        # Block enforcement — can't follow someone who blocked you (or that you blocked)
        if Block.objects.filter(
            blocker__in=[request.user, target], blocked__in=[request.user, target]
        ).exclude(blocker=request.user, blocked=request.user).exclude(blocker=target, blocked=target).exists():
            return Response({'detail': 'Cannot follow — user is blocked.'}, status=403)
        existing = Follow.objects.filter(follower=request.user, following=target).first()
        if existing:
            existing.delete()
            is_following = False
        else:
            Follow.objects.create(follower=request.user, following=target)
            is_following = True
            try:
                from apps.accounts.notifications import notify
                actor_name = (request.user.first_name + ' ' + request.user.last_name).strip() or request.user.username
                notify(
                    user=target, kind='follow', actor=request.user,
                    title=f'{actor_name} started following you',
                    url=f'/{target.role}s/{target.id}' if target.role in ('creator', 'venue', 'audience') else '/',
                )
            except Exception:
                pass
        return Response({
            'is_following': is_following,
            'followers_count': target.followers.count(),
            'following_count': target.following.count(),
        })


class FollowStatusView(APIView):
    """GET /api/users/<user_id>/follow-status/ — am I following this user + counts."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        is_following = False
        if request.user.is_authenticated and request.user != target:
            is_following = Follow.objects.filter(follower=request.user, following=target).exists()
        return Response({
            'is_following': is_following,
            'followers_count': target.followers.count(),
            'following_count': target.following.count(),
            'is_self': request.user.is_authenticated and request.user == target,
        })


class FollowActivityView(APIView):
    """GET /api/follows/activity/ — recent activity for notifications:
    - new followers (people who followed me, latest 20)
    - new stories/events from users I follow (latest 20)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.events.models import Story, Event
        from django.utils import timezone

        new_followers = Follow.objects.filter(following=request.user).select_related(
            'follower__creator_profile', 'follower__venue_profile'
        ).order_by('-created_at')[:20]

        followed_ids = list(request.user.following.values_list('following_id', flat=True))
        now = timezone.now()

        recent_stories = Story.objects.filter(
            author_id__in=followed_ids, expires_at__gt=now
        ).select_related('author__creator_profile', 'author__venue_profile').order_by('-created_at')[:10]

        recent_events = Event.objects.filter(
            host_id__in=followed_ids, is_public=True, created_at__gte=now - timezone.timedelta(days=7)
        ).select_related('host__creator_profile', 'host__venue_profile').order_by('-created_at')[:10]

        def _actor(u):
            name = u.username
            avatar = getattr(u, 'avatar', None)
            if u.role == 'creator' and hasattr(u, 'creator_profile') and u.creator_profile:
                name = u.creator_profile.display_name or u.username
            elif u.role == 'venue' and hasattr(u, 'venue_profile') and u.venue_profile:
                name = u.venue_profile.organization_name or u.username
                avatar = u.venue_profile.logo or avatar
            return {'id': u.id, 'name': name, 'avatar': avatar, 'username': u.username, 'role': u.role}

        return Response({
            'new_followers': [
                {'id': f.id, 'actor': _actor(f.follower), 'created_at': f.created_at}
                for f in new_followers
            ],
            'new_stories': [
                {'id': s.id, 'actor': _actor(s.author), 'caption': s.caption,
                 'image': s.image, 'created_at': s.created_at}
                for s in recent_stories
            ],
            'new_events': [
                {'id': e.id, 'actor': _actor(e.host), 'title': e.title, 'slug': e.slug,
                 'event_type': e.event_type, 'starts_at': e.starts_at, 'created_at': e.created_at}
                for e in recent_events
            ],
        })


class MutualFollowersView(APIView):
    """GET /api/users/<user_id>/mutual-followers/ — social proof.
    Returns up to `limit` followers of <user_id> that the requester also follows,
    plus the total overlap count. Public users get an empty list."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        limit = int(request.query_params.get('limit', 3))
        if not request.user.is_authenticated or request.user == target:
            return Response({'mutuals': [], 'total': 0})
        my_following_ids = request.user.following.values_list('following_id', flat=True)
        overlap_qs = User.objects.filter(
            pk__in=my_following_ids, following__following=target
        ).select_related('creator_profile', 'venue_profile').distinct()
        total = overlap_qs.count()
        mutuals = []
        for u in overlap_qs[:limit]:
            name = u.username
            avatar = getattr(u, 'avatar', None)
            if u.role == 'creator' and hasattr(u, 'creator_profile') and u.creator_profile:
                name = u.creator_profile.display_name or u.username
            elif u.role == 'venue' and hasattr(u, 'venue_profile') and u.venue_profile:
                name = u.venue_profile.organization_name or u.username
                avatar = u.venue_profile.logo or avatar
            mutuals.append({'id': u.id, 'name': name, 'avatar': avatar, 'role': u.role})
        return Response({'mutuals': mutuals, 'total': total})


class FollowersListView(generics.ListAPIView):
    """GET /api/users/<user_id>/followers/ — list of users who follow this user."""
    serializer_class = FollowUserSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        target = get_object_or_404(User, pk=self.kwargs['user_id'])
        return User.objects.filter(following__following=target).select_related(
            'creator_profile', 'venue_profile'
        ).order_by('-following__created_at')


class FollowingListView(generics.ListAPIView):
    """GET /api/users/<user_id>/following/ — list of users this user follows."""
    serializer_class = FollowUserSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        target = get_object_or_404(User, pk=self.kwargs['user_id'])
        return User.objects.filter(followers__follower=target).select_related(
            'creator_profile', 'venue_profile'
        ).order_by('-followers__created_at')
