"""Public download endpoints for .ics calendar files."""
import hashlib
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import permissions
from django.conf import settings

from .models import Event
from .ical import build_ical, event_vevent, ticket_vevent, booking_vevent


def _ical_response(text, filename):
    resp = HttpResponse(text, content_type='text/calendar; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


def _user_token(user):
    """Stable per-user token for subscribable feeds. Not strong auth — obscurity
    only. Good enough for a calendar URL people paste into Google/Apple."""
    secret = getattr(settings, 'SECRET_KEY', 'dev')
    return hashlib.sha256(f'{user.pk}:{user.date_joined}:{secret}'.encode()).hexdigest()[:32]


class EventIcalView(APIView):
    """GET /api/events/<slug>/ical/ — public single-event download."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        text = build_ical([event_vevent(event)], cal_name=event.title)
        return _ical_response(text, f'{event.slug}.ics')


class TicketIcalView(APIView):
    """GET /api/tickets/<id>/ical/ — ticket holder's event download."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from apps.tickets.models import Ticket
        ticket = get_object_or_404(Ticket, pk=pk, holder=request.user)
        text = build_ical([ticket_vevent(ticket)], cal_name=ticket.event.title)
        return _ical_response(text, f'ticket-{ticket.pk}.ics')


class BookingIcalView(APIView):
    """GET /api/bookings/<id>/ical/ — booking as all-day event(s)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from apps.bookings.models import Booking
        booking = get_object_or_404(Booking, pk=pk)
        # Permission: creator on this booking, or space owner
        is_creator = booking.creator.user_id == request.user.id
        is_venue = booking.space.venue.user_id == request.user.id
        if not (is_creator or is_venue):
            raise Http404
        text = build_ical([booking_vevent(booking)], cal_name=f'Booking — {booking.space.title}')
        return _ical_response(text, f'booking-{booking.pk}.ics')


class MyCalendarTokenView(APIView):
    """GET /api/me/calendar-token/ — returns the subscribable feed URL."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tok = _user_token(request.user)
        site = getattr(settings, 'SITE_URL', 'https://cultureconnect-e4d4e201dfdb.herokuapp.com').rstrip('/')
        from rest_framework.response import Response
        return Response({
            'url': f'{site}/api/my-calendar/{request.user.id}-{tok}.ics',
            'webcal_url': f'webcal://{site.replace("https://", "").replace("http://", "")}'
                          f'/api/my-calendar/{request.user.id}-{tok}.ics',
        })


class MyCalendarFeedView(APIView):
    """GET /api/my-calendar/<uid>-<token>.ics — aggregated feed of every upcoming
    event the user has RSVP'd to, every ticket they hold, and every booking
    they're party to. Subscribable by Google/Apple Calendar."""
    permission_classes = [permissions.AllowAny]  # token-in-URL is the auth

    def get(self, request, uid, token):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, pk=uid)
        if token != _user_token(user):
            raise Http404
        vevents = []

        # RSVP'd events (incl. going/maybe/interested)
        from .models import EventRSVP
        rsvp_events = Event.objects.filter(
            rsvps__user=user
        ).exclude(rsvps__status=EventRSVP.STATUS_NOT_GOING).distinct()
        for ev in rsvp_events:
            vevents.append(event_vevent(ev))

        # Paid tickets
        try:
            from apps.tickets.models import Ticket
            tickets = Ticket.objects.filter(holder=user, payment_status='paid').select_related('event', 'tier')
            for t in tickets:
                vevents.append(ticket_vevent(t))
        except Exception:
            pass

        # Confirmed bookings (both sides)
        try:
            from apps.bookings.models import Booking
            bookings = Booking.objects.filter(
                status__in=['confirmed', 'accepted', 'in_progress', 'completed']
            ).filter(
                creator__user=user
            ) | Booking.objects.filter(
                status__in=['confirmed', 'accepted', 'in_progress', 'completed'],
                space__venue__user=user,
            )
            for b in bookings.distinct():
                vevents.append(booking_vevent(b))
        except Exception:
            pass

        text = build_ical(vevents, cal_name=f'CultureConnect — {user.username}')
        return _ical_response(text, f'my-calendar.ics')
