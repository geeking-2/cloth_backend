from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Event, Story, EventRSVP, EventInvite, EventBroadcast
from .serializers import (
    EventSerializer, StorySerializer, EventRSVPSerializer,
    EventInviteSerializer, EventBroadcastSerializer,
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, 'host', None) or getattr(obj, 'author', None)
        return owner == request.user


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Event.objects.select_related('host', 'space', 'host__creator_profile', 'host__venue_profile').all()
        params = self.request.query_params

        scope = params.get('scope')
        now = timezone.now()
        if scope == 'upcoming':
            qs = qs.filter(Q(ends_at__gte=now) | Q(ends_at__isnull=True, starts_at__gte=now))
        elif scope == 'past':
            qs = qs.filter(Q(ends_at__lt=now) | Q(ends_at__isnull=True, starts_at__lt=now))
        elif scope == 'live':
            qs = qs.filter(starts_at__lte=now).filter(Q(ends_at__gte=now) | Q(ends_at__isnull=True))
        elif scope == 'week':
            qs = qs.filter(starts_at__gte=now, starts_at__lte=now + timezone.timedelta(days=7))

        if params.get('host'):
            qs = qs.filter(host_id=params['host'])
        if params.get('space'):
            qs = qs.filter(space__slug=params['space'])
        if params.get('event_type'):
            qs = qs.filter(event_type=params['event_type'])
        if params.get('mine') and self.request.user.is_authenticated:
            qs = qs.filter(host=self.request.user)
        else:
            qs = qs.filter(is_public=True)
        return qs


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.select_related('host', 'space').all()
    serializer_class = EventSerializer
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = 'slug'


class StoryListCreateView(generics.ListCreateAPIView):
    serializer_class = StorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        # Active only by default (not expired)
        now = timezone.now()
        qs = Story.objects.select_related('author', 'event', 'space', 'author__creator_profile', 'author__venue_profile').filter(expires_at__gt=now)
        params = self.request.query_params
        if params.get('author'):
            qs = qs.filter(author_id=params['author'])
        if params.get('event'):
            qs = qs.filter(event__slug=params['event'])
        if params.get('space'):
            qs = qs.filter(space__slug=params['space'])
        if params.get('mine') and self.request.user.is_authenticated:
            qs = qs.filter(author=self.request.user)
        return qs


class StoryDetailView(generics.RetrieveDestroyAPIView):
    queryset = Story.objects.all()
    serializer_class = StorySerializer
    permission_classes = [IsOwnerOrReadOnly]


class EventRSVPView(APIView):
    """
    GET  /events/<slug>/rsvp/           → my current RSVP + counts
    POST /events/<slug>/rsvp/ {status}  → set/toggle my RSVP (going/maybe/interested/not_going)
    DELETE /events/<slug>/rsvp/         → remove my RSVP
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def _event(self, slug):
        return get_object_or_404(Event, slug=slug)

    def _counts(self, event):
        counts = {s: 0 for s, _ in EventRSVP.STATUS_CHOICES}
        for row in event.rsvps.values('status').annotate(n=Count('id')):
            counts[row['status']] = row['n']
        counts['total_going'] = counts[EventRSVP.STATUS_GOING]
        return counts

    def get(self, request, slug):
        event = self._event(slug)
        my = None
        if request.user.is_authenticated:
            rsvp = event.rsvps.filter(user=request.user).first()
            if rsvp:
                my = EventRSVPSerializer(rsvp).data
        return Response({'my_rsvp': my, 'counts': self._counts(event)})

    def post(self, request, slug):
        event = self._event(slug)
        new_status = request.data.get('status', EventRSVP.STATUS_GOING)
        if new_status not in dict(EventRSVP.STATUS_CHOICES):
            return Response({'detail': 'Invalid status.'}, status=400)

        # Host can't RSVP to their own event
        if event.host_id == request.user.id:
            return Response({'detail': "You're the host — you're automatically going."}, status=400)

        # Block enforcement
        from apps.messaging.models import Block
        if Block.objects.filter(
            blocker__in=[request.user, event.host], blocked__in=[request.user, event.host]
        ).exclude(blocker=request.user, blocked=request.user).exclude(blocker=event.host, blocked=event.host).exists():
            return Response({'detail': 'Cannot RSVP — host has blocked you.'}, status=403)

        # Capacity check (only when marking as going/maybe)
        if new_status in (EventRSVP.STATUS_GOING, EventRSVP.STATUS_MAYBE) and event.max_capacity:
            current_going = event.rsvps.filter(status=EventRSVP.STATUS_GOING).exclude(user=request.user).count()
            if current_going >= event.max_capacity:
                return Response({'detail': 'This event is at full capacity.'}, status=409)

        # Age restriction
        if event.age_restriction and hasattr(request.user, 'audience_profile'):
            age = request.user.audience_profile.age
            if event.age_restriction == '18+' and (age is None or age < 18):
                return Response({'detail': 'This event requires 18+.'}, status=403)
            if event.age_restriction == '21+' and (age is None or age < 21):
                return Response({'detail': 'This event requires 21+.'}, status=403)

        # Default incognito = user's profile privacy preference (audience only)
        default_incognito = False
        if hasattr(request.user, 'audience_profile'):
            default_incognito = not request.user.audience_profile.is_public

        rsvp, _created = EventRSVP.objects.update_or_create(
            event=event, user=request.user,
            defaults={'status': new_status, 'incognito': default_incognito},
        )
        return Response(EventRSVPSerializer(rsvp).data, status=200)

    def delete(self, request, slug):
        event = self._event(slug)
        EventRSVP.objects.filter(event=event, user=request.user).delete()
        return Response(status=204)


class EventAttendeesView(generics.ListAPIView):
    """GET /events/<slug>/attendees/ — paginated list of going-attendees.
    Host sees everyone (incl. incognito).
    Non-hosts see only if event.public_attendee_list = True, and only non-incognito rows."""
    serializer_class = EventRSVPSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        qs = event.rsvps.select_related(
            'user__audience_profile', 'user__creator_profile', 'user__venue_profile'
        ).filter(status=EventRSVP.STATUS_GOING).order_by('-created_at')

        user = self.request.user
        is_host = user.is_authenticated and event.host_id == user.id

        if is_host:
            return qs
        if not event.public_attendee_list:
            return qs.none()
        return qs.exclude(incognito=True)


class FeedView(generics.GenericAPIView):
    """Aggregate feed: stories strip + upcoming events.
    ?following=1 filters everything to users the authenticated user follows."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()
        following_only = request.query_params.get('following') in ('1', 'true', 'yes')

        stories_qs = Story.objects.select_related(
            'author', 'event', 'space', 'author__creator_profile', 'author__venue_profile'
        ).filter(expires_at__gt=now)

        upcoming_qs = Event.objects.select_related(
            'host', 'space', 'host__creator_profile', 'host__venue_profile'
        ).filter(is_public=True, starts_at__gte=now, starts_at__lte=now + timezone.timedelta(days=14))

        live_qs = Event.objects.select_related(
            'host', 'space', 'host__creator_profile', 'host__venue_profile'
        ).filter(is_public=True, starts_at__lte=now).filter(
            Q(ends_at__gte=now) | Q(ends_at__isnull=True, starts_at__gte=now - timezone.timedelta(hours=6))
        )

        if following_only and request.user.is_authenticated:
            followed_ids = list(request.user.following.values_list('following_id', flat=True))
            stories_qs = stories_qs.filter(author_id__in=followed_ids)
            upcoming_qs = upcoming_qs.filter(host_id__in=followed_ids)
            live_qs = live_qs.filter(host_id__in=followed_ids)

        return Response({
            'stories': StorySerializer(stories_qs[:100], many=True, context={'request': request}).data,
            'live': EventSerializer(live_qs[:10], many=True, context={'request': request}).data,
            'upcoming': EventSerializer(upcoming_qs[:30], many=True, context={'request': request}).data,
        })


# ----- Invites -----

class EventInviteListCreateView(APIView):
    """
    GET  /events/<slug>/invites/  - host sees all invites
    POST /events/<slug>/invites/  - body {user_ids, message}
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_event(self, slug):
        return get_object_or_404(Event, slug=slug)

    def _can_invite(self, user, event):
        if user == event.host:
            return True
        return EventRSVP.objects.filter(
            event=event, user=user,
            status__in=[EventRSVP.STATUS_GOING, EventRSVP.STATUS_MAYBE, EventRSVP.STATUS_INTERESTED],
        ).exists()

    def get(self, request, slug):
        event = self._get_event(slug)
        if request.user != event.host:
            qs = EventInvite.objects.filter(event=event, inviter=request.user)
        else:
            qs = EventInvite.objects.filter(event=event)
        qs = qs.select_related('inviter', 'invitee', 'event')
        return Response(EventInviteSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request, slug):
        from apps.messaging.models import Block
        event = self._get_event(slug)
        if not self._can_invite(request.user, event):
            return Response(
                {'detail': 'Only the host or a confirmed attendee can invite.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_ids = request.data.get('user_ids') or []
        emails = request.data.get('emails') or []
        if not isinstance(user_ids, list):
            user_ids = []
        if not isinstance(emails, list):
            emails = []
        if not user_ids and not emails:
            return Response(
                {'detail': 'Provide user_ids and/or emails (non-empty).'}, status=400
            )
        message = (request.data.get('message') or '')[:500]
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Resolve emails → users (case-insensitive)
        unmatched_emails = []
        email_ids = []
        if emails:
            from django.db.models.functions import Lower
            cleaned = list({e.strip().lower() for e in emails if isinstance(e, str) and e.strip()})
            if cleaned:
                email_map = {
                    row['e_lower']: row['id']
                    for row in User.objects.annotate(e_lower=Lower('email'))
                    .filter(e_lower__in=cleaned).values('id', 'e_lower')
                }
                for e in cleaned:
                    if e in email_map:
                        email_ids.append(email_map[e])
                    else:
                        unmatched_emails.append(e)

        all_ids = set(user_ids) | set(email_ids)
        targets = User.objects.filter(id__in=all_ids).exclude(id=request.user.id)
        created, skipped = [], []
        for t in targets:
            if Block.objects.filter(
                Q(blocker=request.user, blocked=t) | Q(blocker=t, blocked=request.user)
            ).exists():
                skipped.append({'id': t.id, 'reason': 'blocked'})
                continue
            obj, was_created = EventInvite.objects.get_or_create(
                event=event, invitee=t,
                defaults={'inviter': request.user, 'message': message},
            )
            if was_created:
                created.append(obj.id)
            else:
                skipped.append({'id': t.id, 'reason': 'already_invited'})
        qs = EventInvite.objects.filter(id__in=created).select_related('inviter', 'invitee', 'event')
        # Fire notifications to each freshly-invited user
        try:
            from apps.accounts.notifications import notify
            inviter_name = (request.user.first_name + ' ' + request.user.last_name).strip() or request.user.username
            for inv in qs:
                notify(
                    user=inv.invitee, kind='invite', actor=request.user,
                    title=f'{inviter_name} invited you to {event.title}',
                    body=message or '',
                    url='/invites',
                )
        except Exception:
            pass
        return Response({
            'created': EventInviteSerializer(qs, many=True, context={'request': request}).data,
            'skipped': skipped,
            'unmatched_emails': unmatched_emails,
        }, status=status.HTTP_201_CREATED)


class MyInvitesView(generics.ListAPIView):
    """GET /invites/  - current user's received invites"""
    serializer_class = EventInviteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = EventInvite.objects.filter(invitee=self.request.user).select_related('inviter', 'event')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class InviteRespondView(APIView):
    """POST /invites/<id>/respond/  body {action: accept|decline}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        invite = get_object_or_404(EventInvite, pk=pk)
        if invite.invitee != request.user:
            return Response({'detail': 'Not your invite.'}, status=403)
        if invite.status != EventInvite.STATUS_PENDING:
            return Response({'detail': f'Already {invite.status}.'}, status=400)
        action = request.data.get('action')
        if action == 'accept':
            invite.status = EventInvite.STATUS_ACCEPTED
            EventRSVP.objects.update_or_create(
                event=invite.event, user=request.user,
                defaults={'status': EventRSVP.STATUS_GOING},
            )
        elif action == 'decline':
            invite.status = EventInvite.STATUS_DECLINED
        else:
            return Response({'detail': "action must be 'accept' or 'decline'."}, status=400)
        invite.responded_at = timezone.now()
        invite.save(update_fields=['status', 'responded_at'])
        # Notify the inviter about the response
        try:
            from apps.accounts.notifications import notify
            invitee_name = (request.user.first_name + ' ' + request.user.last_name).strip() or request.user.username
            verb = 'accepted' if action == 'accept' else 'declined'
            notify(
                user=invite.inviter, kind='invite_response', actor=request.user,
                title=f'{invitee_name} {verb} your invite to {invite.event.title}',
                url=f'/events/{invite.event.slug}',
            )
        except Exception:
            pass
        return Response(EventInviteSerializer(invite, context={'request': request}).data)


# ----- Broadcasts -----

class EventBroadcastListCreateView(APIView):
    """
    GET  /events/<slug>/broadcasts/  - RSVP'd users + host
    POST /events/<slug>/broadcasts/  - host only
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_event(self, slug):
        return get_object_or_404(Event, slug=slug)

    def _recipients_queryset(self, event, audience):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if audience == EventBroadcast.AUDIENCE_TICKET_HOLDERS:
            from apps.tickets.models import Ticket
            uids = Ticket.objects.filter(event=event, payment_status='paid').values_list('holder_id', flat=True)
            return User.objects.filter(id__in=uids)
        elif audience == EventBroadcast.AUDIENCE_GOING:
            uids = EventRSVP.objects.filter(event=event, status=EventRSVP.STATUS_GOING).values_list('user_id', flat=True)
            return User.objects.filter(id__in=uids)
        else:
            uids = EventRSVP.objects.filter(event=event).exclude(
                status=EventRSVP.STATUS_NOT_GOING
            ).values_list('user_id', flat=True)
            return User.objects.filter(id__in=uids)

    def get(self, request, slug):
        event = self._get_event(slug)
        is_attendee = (
            request.user == event.host
            or EventRSVP.objects.filter(event=event, user=request.user).exists()
        )
        if not is_attendee:
            from apps.tickets.models import Ticket
            is_attendee = Ticket.objects.filter(
                event=event, holder=request.user, payment_status='paid'
            ).exists()
        if not is_attendee:
            return Response({'detail': 'RSVP to see updates from the host.'}, status=403)
        qs = EventBroadcast.objects.filter(event=event).select_related('sender')
        return Response(EventBroadcastSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request, slug):
        event = self._get_event(slug)
        if request.user != event.host:
            return Response({'detail': 'Only the host can broadcast.'}, status=403)
        subject = (request.data.get('subject') or '').strip()
        body = (request.data.get('body') or '').strip()
        audience = request.data.get('audience') or EventBroadcast.AUDIENCE_ALL
        if not subject or not body:
            return Response({'detail': 'subject and body are required.'}, status=400)
        if audience not in dict(EventBroadcast.AUDIENCE_CHOICES):
            return Response({'detail': 'Invalid audience.'}, status=400)
        recipients = self._recipients_queryset(event, audience)
        count = recipients.count()
        broadcast = EventBroadcast.objects.create(
            event=event, sender=request.user,
            subject=subject[:200], body=body[:4000],
            audience=audience, recipient_count=count,
        )
        try:
            from django.core.mail import send_mail
            from django.conf import settings as dj_settings
            emails = list(recipients.exclude(id=request.user.id).values_list('email', flat=True))
            emails = [e for e in emails if e]
            if emails:
                send_mail(
                    subject=f'[{event.title}] {subject[:150]}',
                    message=f'Update from the host:\n\n{body}\n\n-- Event page: /events/{event.slug}',
                    from_email=getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None),
                    recipient_list=[],
                    bcc=emails,
                    fail_silently=True,
                )
        except Exception:
            pass
        # In-app notifications for each recipient (except the sender)
        try:
            from apps.accounts.notifications import notify_many
            notify_many(
                users=list(recipients.exclude(id=request.user.id)),
                kind='broadcast', actor=request.user,
                title=f'{event.title}: {subject[:150]}',
                body=body[:400],
                url=f'/events/{event.slug}',
            )
        except Exception:
            pass
        return Response(
            EventBroadcastSerializer(broadcast, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
