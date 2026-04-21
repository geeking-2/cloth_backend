from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message, Block
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()

# Arbitrary safety cap on base64 image size (~5 MB encoded)
MAX_IMAGE_LEN = 7_500_000

# Allowed data-URL MIME prefixes for inline images. Anything else (SVG, HTML,
# arbitrary binary) is rejected to prevent XSS / script injection via data: URIs.
ALLOWED_IMAGE_PREFIXES = (
    'data:image/png;base64,',
    'data:image/jpeg;base64,',
    'data:image/jpg;base64,',
    'data:image/gif;base64,',
    'data:image/webp;base64,',
)


def _is_valid_image_data_url(value: str) -> bool:
    if not value:
        return False
    return value.startswith(ALLOWED_IMAGE_PREFIXES)


def _is_blocked_either_way(user_a, user_b):
    """True if either user has blocked the other."""
    return Block.objects.filter(
        blocker__in=[user_a, user_b], blocked__in=[user_a, user_b]
    ).exclude(blocker=user_b, blocked=user_b).exclude(blocker=user_a, blocked=user_a).exists()


class ConversationListCreateView(APIView):
    """
    GET  /api/conversations/         → list my threads
    POST /api/conversations/ {user_id} → open (or fetch) a thread with user_id
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            Conversation.objects
            .filter(participants=request.user)
            .prefetch_related('participants__creator_profile', 'participants__venue_profile', 'messages')
            .order_by('-last_message_at')
        )
        data = ConversationSerializer(qs, many=True, context={'request': request}).data
        return Response(data)

    def post(self, request):
        other_id = request.data.get('user_id')
        if not other_id:
            return Response({'detail': 'user_id required'}, status=400)
        other = get_object_or_404(User, pk=other_id)
        if other == request.user:
            return Response({'detail': "Can't message yourself."}, status=400)

        # Can't start a conversation with someone who has blocked you (or you've blocked)
        if _is_blocked_either_way(request.user, other):
            return Response({'detail': 'Cannot start conversation — user is blocked.'}, status=403)

        conv = Conversation.between(request.user, other)
        if not conv:
            conv = Conversation.objects.create()
            conv.participants.add(request.user, other)
        data = ConversationSerializer(conv, context={'request': request}).data
        return Response(data, status=status.HTTP_200_OK)


class MessageListCreateView(APIView):
    """
    GET  /api/conversations/<id>/messages/         → list messages (oldest first)
    POST /api/conversations/<id>/messages/ {body, image} → send new message
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_conv(self, request, conv_id):
        conv = get_object_or_404(Conversation, pk=conv_id)
        if not conv.participants.filter(pk=request.user.pk).exists():
            return None
        return conv

    def get(self, request, conv_id):
        conv = self._get_conv(request, conv_id)
        if not conv:
            return Response({'detail': 'Not found'}, status=404)
        msgs = conv.messages.select_related(
            'sender__creator_profile', 'sender__venue_profile'
        ).order_by('created_at')
        data = MessageSerializer(msgs, many=True).data
        return Response(data)

    def post(self, request, conv_id):
        conv = self._get_conv(request, conv_id)
        if not conv:
            return Response({'detail': 'Not found'}, status=404)

        other = conv.other_participant(request.user)
        if other and _is_blocked_either_way(request.user, other):
            return Response({'detail': 'Cannot send — user is blocked.'}, status=403)

        body = (request.data.get('body') or '').strip()
        image = (request.data.get('image') or '').strip()

        if not body and not image:
            return Response({'detail': 'Message must have text or image.'}, status=400)
        if len(body) > 4000:
            return Response({'detail': 'Message too long (max 4000 chars)'}, status=400)
        if image and len(image) > MAX_IMAGE_LEN:
            return Response({'detail': 'Image too large (max ~5 MB).'}, status=400)
        if image and not _is_valid_image_data_url(image):
            return Response(
                {'detail': 'Image must be a PNG, JPEG, GIF or WebP data URL.'},
                status=400,
            )

        msg = Message.objects.create(
            conversation=conv, sender=request.user, body=body, image=image,
        )
        conv.last_message_at = msg.created_at
        conv.save(update_fields=['last_message_at'])
        return Response(MessageSerializer(msg).data, status=201)


class ConversationReadView(APIView):
    """POST /api/conversations/<id>/read/ → mark all incoming messages as read."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        conv = get_object_or_404(Conversation, pk=conv_id)
        if not conv.participants.filter(pk=request.user.pk).exists():
            return Response({'detail': 'Not found'}, status=404)
        now = timezone.now()
        updated = conv.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=now)
        return Response({'marked_read': updated})


class UnreadCountView(APIView):
    """GET /api/conversations/unread-count/ → total unread messages across my threads."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(
            conversation__participants=request.user,
            read_at__isnull=True,
        ).exclude(sender=request.user).count()
        return Response({'unread_count': count})


class BlockToggleView(APIView):
    """
    POST /api/blocks/<user_id>/ → toggle block on that user.
    Returns {is_blocked: bool}.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        if target == request.user:
            return Response({'detail': "Can't block yourself."}, status=400)
        existing = Block.objects.filter(blocker=request.user, blocked=target).first()
        if existing:
            existing.delete()
            return Response({'is_blocked': False})
        Block.objects.create(blocker=request.user, blocked=target)
        return Response({'is_blocked': True})


class BlockStatusView(APIView):
    """GET /api/blocks/<user_id>/status/ → {is_blocked, blocked_me}."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        is_blocked = Block.objects.filter(blocker=request.user, blocked=target).exists()
        blocked_me = Block.objects.filter(blocker=target, blocked=request.user).exists()
        return Response({'is_blocked': is_blocked, 'blocked_me': blocked_me})
