"""Notification helpers + API views.

Exposed at /api/auth/notifications/ (same app mount).
"""
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, User


def notify(user, kind, title, body='', url='', actor=None):
    """Create a notification; swallow errors so callers never break.

    Also fires a Web Push to all of the user's subscribed devices.
    """
    if not user or user == actor:
        return None
    try:
        n = Notification.objects.create(
            user=user, kind=kind, actor=actor,
            title=title[:200], body=body[:500], url=url[:300],
        )
    except Exception:
        return None
    # Best-effort web push — never break the caller.
    try:
        from .push import send_push
        send_push(user, title=n.title, body=n.body, url=n.url or '/', tag=kind)
    except Exception:
        pass
    return n


def notify_many(users, kind, title, body='', url='', actor=None):
    rows = []
    for u in users:
        if u and u != actor:
            rows.append(Notification(
                user=u, kind=kind, actor=actor,
                title=title[:200], body=body[:500], url=url[:300],
            ))
    if rows:
        Notification.objects.bulk_create(rows, ignore_conflicts=True)
        # Best-effort web push to every recipient — never break the caller.
        try:
            from .push import send_push
            for n in rows:
                try:
                    send_push(n.user, title=n.title, body=n.body, url=n.url or '/', tag=kind)
                except Exception:
                    pass
        except Exception:
            pass
    return len(rows)


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_avatar = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'kind', 'title', 'body', 'url',
            'actor', 'actor_name', 'actor_avatar',
            'read_at', 'is_read', 'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor:
            return ''
        return (obj.actor.first_name + ' ' + obj.actor.last_name).strip() or obj.actor.username

    def get_actor_avatar(self, obj):
        return (obj.actor.avatar if obj.actor else '') or ''

    def get_is_read(self, obj):
        return obj.read_at is not None


class NotificationListView(generics.ListAPIView):
    """GET /notifications/?unread=1  — current user's notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).select_related('actor')
        if self.request.query_params.get('unread') in ('1', 'true', 'True'):
            qs = qs.filter(read_at__isnull=True)
        return qs[:100]


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
        return Response({'unread': count})


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            user=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({'ok': True})


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        if n.read_at is None:
            n.read_at = timezone.now()
            n.save(update_fields=['read_at'])
        return Response(NotificationSerializer(n).data)
