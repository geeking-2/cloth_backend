"""
Seed realistic EventBroadcast rows so the host→attendee updates feature has
data to show in the UI + sends in-app notifications to recipients.

Strategy:
  1. Find events that already have at least one RSVP'd attendee (or a paid
     ticket holder). If none exist, auto-RSVP `audience_demo` to the most
     recent upcoming event so we always have a recipient.
  2. For each chosen event, post 2-3 broadcasts from the host spanning the
     three audience types (all / going / ticket_holders), bumping
     created_at backwards so the timeline looks lived-in.
  3. Each broadcast calls notify_many() so the bell badge lights up for
     recipients immediately.

Idempotent: subjects are prefixed with `[SEED]` and re-running skips any
broadcast whose (event, subject) already exists.
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event, EventBroadcast, EventRSVP


SCRIPTS = [
    {
        'audience': EventBroadcast.AUDIENCE_ALL,
        'subject': 'Schedule locked in — doors open 7pm sharp',
        'body': (
            "Hi everyone — quick heads up: we've finalized the run-of-show.\n\n"
            "• 7:00 pm — Doors\n"
            "• 7:30 pm — Opening remarks\n"
            "• 8:00 pm — Main programme\n"
            "• 10:00 pm — Close\n\n"
            "Bring ID. Can't wait to see you."
        ),
        'offset_hours': 48,
    },
    {
        'audience': EventBroadcast.AUDIENCE_GOING,
        'subject': 'A few practical things for tomorrow',
        'body': (
            "For everyone marked Going — the venue is fully accessible, coat "
            "check is free, and the nearest parking is across the street at the "
            "Market garage. If you need to bring a +1, reply to this message and "
            "we'll sort it out. See you soon."
        ),
        'offset_hours': 18,
    },
    {
        'audience': EventBroadcast.AUDIENCE_TICKET_HOLDERS,
        'subject': 'Your QR code + perks for ticket holders',
        'body': (
            "Ticket holders — your QR code is already live under My Tickets. "
            "Show it at the door for a faster check-in. Early arrivers (before "
            "7:15) get first pick of the welcome drinks at the bar. Thanks for "
            "backing this one."
        ),
        'offset_hours': 4,
    },
]


class Command(BaseCommand):
    help = 'Seed EventBroadcast rows on existing events with RSVPs for demo/testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-events', type=int, default=3,
            help='Maximum number of events to seed broadcasts for (default 3).'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        max_events = options['max_events']
        now = timezone.now()

        # Make sure audience_demo has something to hear about — auto-RSVP
        # to the newest upcoming event if they aren't already attending one.
        audience = User.objects.filter(username='audience_demo').first()
        if audience:
            has_any_rsvp = EventRSVP.objects.filter(
                user=audience, status=EventRSVP.STATUS_GOING
            ).exists()
            if not has_any_rsvp:
                upcoming = Event.objects.filter(starts_at__gte=now).order_by('starts_at').first()
                if upcoming and upcoming.host_id != audience.id:
                    EventRSVP.objects.get_or_create(
                        event=upcoming, user=audience,
                        defaults={'status': EventRSVP.STATUS_GOING},
                    )
                    self.stdout.write(self.style.NOTICE(
                        f'Auto-RSVP\'d audience_demo as GOING to "{upcoming.title}"'
                    ))

        # Pick events with an audience: events that have any RSVP (not "not going").
        candidate_events = (
            Event.objects.filter(
                rsvps__status__in=[EventRSVP.STATUS_GOING, EventRSVP.STATUS_MAYBE, EventRSVP.STATUS_INTERESTED],
            )
            .select_related('host')
            .distinct()
            .order_by('-starts_at')[:max_events]
        )

        if not candidate_events:
            # Nothing to broadcast to yet — fall back to the most recent event
            # regardless of RSVPs so we at least create the rows.
            candidate_events = list(Event.objects.select_related('host').order_by('-created_at')[:max_events])
            if not candidate_events:
                self.stdout.write(self.style.ERROR('No events exist. Seed events first.'))
                return

        created = 0
        skipped = 0
        for event in candidate_events:
            self.stdout.write(f'\nEvent: "{event.title}" (host: {event.host.username})')
            for script in SCRIPTS:
                subject = f"[SEED] {script['subject']}"
                if EventBroadcast.objects.filter(event=event, subject=subject).exists():
                    skipped += 1
                    self.stdout.write(f'  · skip (exists): {script["subject"]}')
                    continue

                recipients = self._recipients_for(event, script['audience'])
                count = recipients.count()

                bc = EventBroadcast.objects.create(
                    event=event,
                    sender=event.host,
                    subject=subject,
                    body=script['body'],
                    audience=script['audience'],
                    recipient_count=count,
                )
                # Backdate so the timeline shows history.
                bc.created_at = now - timedelta(hours=script['offset_hours'])
                bc.save(update_fields=['created_at'])

                # Fire in-app notifications, except to the sender.
                try:
                    from apps.accounts.notifications import notify_many
                    notify_many(
                        users=list(recipients.exclude(id=event.host_id)),
                        kind='broadcast',
                        actor=event.host,
                        title=f'Update: {event.title}',
                        body=script['subject'],
                        url=f'/events/{event.slug}',
                    )
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'  ! notify_many failed: {exc}'))

                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {script["audience"]:>16} → {count:>3} recipients · {script["subject"]}'
                ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {created} broadcast(s), skipped {skipped}.'
        ))

    def _recipients_for(self, event, audience):
        User = get_user_model()
        if audience == EventBroadcast.AUDIENCE_TICKET_HOLDERS:
            from apps.tickets.models import Ticket
            uids = Ticket.objects.filter(event=event, payment_status='paid').values_list('holder_id', flat=True)
            return User.objects.filter(id__in=uids)
        if audience == EventBroadcast.AUDIENCE_GOING:
            uids = EventRSVP.objects.filter(event=event, status=EventRSVP.STATUS_GOING).values_list('user_id', flat=True)
            return User.objects.filter(id__in=uids)
        uids = EventRSVP.objects.filter(event=event).exclude(
            status=EventRSVP.STATUS_NOT_GOING
        ).values_list('user_id', flat=True)
        return User.objects.filter(id__in=uids)
