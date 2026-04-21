from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event
from apps.tickets.models import TicketTier


class Command(BaseCommand):
    help = 'Create a demo event with paid ticket tiers for live-site testing.'

    def handle(self, *args, **options):
        User = get_user_model()

        # Prefer a venue host, fall back to creator, then any staff/user.
        host = (
            User.objects.filter(role='venue').order_by('id').first()
            or User.objects.filter(role='creator').order_by('id').first()
            or User.objects.exclude(username='audience_demo').order_by('id').first()
        )
        if not host:
            self.stdout.write(self.style.ERROR('No host user found — seed users first.'))
            return

        title = 'Neon Garden — Opening Night'
        slug = 'neon-garden-opening-night'
        starts_at = timezone.now() + timedelta(days=14)
        ends_at = starts_at + timedelta(hours=4)

        event, created = Event.objects.get_or_create(
            slug=slug,
            defaults={
                'host': host,
                'title': title,
                'event_type': Event.TYPE_OPENING,
                'description': (
                    'A one-night immersive exhibition featuring 12 emerging artists, '
                    'live electronic sets, and an interactive light installation. '
                    'Drinks and small bites included with every ticket.'
                ),
                'cover_image': 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=1600',
                'starts_at': starts_at,
                'ends_at': ends_at,
                'location_text': '88 Wythe Ave, Brooklyn, NY',
                'is_public': True,
                'max_capacity': 200,
                'public_attendee_list': True,
                'ticketing_enabled': True,
                'age_restriction': '21+',
                'incognito_fee_cents': 200,  # $2 to attend incognito
            },
        )
        # Ensure ticketing stays on if the event already existed
        event.ticketing_enabled = True
        event.save()

        tiers = [
            {'name': 'General Admission', 'price_cents': 2500, 'quantity': 150, 'sort_order': 1,
             'description': 'Entry + welcome drink.'},
            {'name': 'VIP', 'price_cents': 7500, 'quantity': 40, 'sort_order': 2,
             'description': 'Priority entry, open bar, exclusive lounge.'},
            {'name': 'Artist Circle', 'price_cents': 15000, 'quantity': 10, 'sort_order': 3,
             'description': 'All VIP perks + pre-show artist meet & greet and signed print.'},
        ]
        created_tiers = []
        for t in tiers:
            tier, made = TicketTier.objects.get_or_create(
                event=event, name=t['name'],
                defaults={
                    'price_cents': t['price_cents'],
                    'currency': 'USD',
                    'quantity': t['quantity'],
                    'sort_order': t['sort_order'],
                    'description': t['description'],
                    'is_active': True,
                },
            )
            created_tiers.append((tier.name, made))

        self.stdout.write(self.style.SUCCESS(
            f'OK  event_slug={event.slug}  host={host.username}  created={created}'
        ))
        for name, made in created_tiers:
            self.stdout.write(f'  tier: {name}  (created={made})')
        self.stdout.write(self.style.SUCCESS(
            f'URL: /events/{event.slug}'
        ))
