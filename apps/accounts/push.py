"""Web Push helper + subscribe/unsubscribe endpoints.

Requires VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT (a mailto: URL) in settings.
"""
import json
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover
    webpush = None
    WebPushException = Exception

from .models import PushSubscription

logger = logging.getLogger(__name__)


def send_push(user, *, title, body='', url='/', tag=None, **extra):
    """Fire a Web Push to every subscription the user has registered.

    Drops expired endpoints silently. Non-blocking — never raises to the caller.
    """
    if not webpush:
        return 0
    pub = getattr(settings, 'VAPID_PUBLIC_KEY', '')
    priv = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    subj = getattr(settings, 'VAPID_SUBJECT', 'mailto:noreply@cultureconnect.app')
    if not pub or not priv:
        return 0

    payload = json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag, **extra})
    sent = 0
    stale = []
    for sub in user.push_subscriptions.all():
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=priv,
                vapid_claims={'sub': subj},
            )
            sent += 1
            sub.last_used_at = timezone.now()
            sub.save(update_fields=['last_used_at'])
        except WebPushException as e:
            # 404/410 → subscription is dead; prune.
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            if status_code in (404, 410):
                stale.append(sub.pk)
            else:
                logger.warning('Web push failed for %s: %s', user.username, e)
        except Exception as e:  # noqa: BLE001
            logger.warning('Web push error for %s: %s', user.username, e)
    if stale:
        PushSubscription.objects.filter(pk__in=stale).delete()
    return sent


# --- API endpoints -------------------------------------------------------

class PushSubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, v):
        if 'p256dh' not in v or 'auth' not in v:
            raise serializers.ValidationError('keys must include p256dh and auth')
        return v


class PushPublicKeyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'publicKey': getattr(settings, 'VAPID_PUBLIC_KEY', '')})


class PushSubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        s = PushSubscribeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        endpoint = s.validated_data['endpoint']
        keys = s.validated_data['keys']
        ua = request.META.get('HTTP_USER_AGENT', '')[:300]
        sub, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': keys['p256dh'],
                'auth': keys['auth'],
                'user_agent': ua,
            },
        )
        return Response({'ok': True, 'id': sub.id}, status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint', '')
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({'ok': True})
