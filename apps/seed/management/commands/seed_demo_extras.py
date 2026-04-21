"""
Fills out the demo with realistic RSVPs, paid tickets, reviews, and follows
so the UI doesn't feel empty.

Runs safely on production — all operations are idempotent (bulk_create with
ignore_conflicts, get_or_create, unique-constraint-aware writes). Pick which
parts to run with flags, or pass --all.

Usage:
  python manage.py seed_demo_extras --all
  python manage.py seed_demo_extras --rsvps --tickets
  python manage.py seed_demo_extras --follows --reviews
"""
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


REVIEW_COMMENTS_VENUE_POSITIVE = [
    "The space was exactly what we needed — beautifully lit, well ventilated, and the staff couldn't have been more helpful. Would book again in a heartbeat.",
    "Lovely venue. Flexible, professional, and the acoustics were much better than expected. Guests kept asking where we'd found it.",
    "Worked with us on load-in times and helped rig the last-minute lighting change. Real partners, not just landlords.",
    "Everything worked. Wifi was solid, the HVAC didn't rattle, and the bar staff were brilliant. 5 stars.",
    "Genuinely great experience. They opened early so we could do our tech run and stuck around past midnight. Above and beyond.",
]

REVIEW_COMMENTS_CREATOR_POSITIVE = [
    "A pleasure to host. Arrived on time, left the space cleaner than they found it, and the work itself was stunning.",
    "Easy to work with and clearly know what they're doing. We'd love to have them back for another residency.",
    "Audience loved it. Our ticket sales almost doubled the week of the event. Thoughtful, professional, talented.",
    "Communication was clear from day one. They flagged every requirement up front and there were zero surprises on show day.",
    "Pretty much the dream artist to work with. Kind to the front-of-house team, too — small thing, means a lot.",
]

STORY_CAPTIONS = [
    "Doors in 2 hours — last pieces going up now",
    "Sound check complete. The room sounds incredible tonight.",
    "Full house. Thank you for showing up.",
    "Behind the scenes of the installation going up this week",
    "New work in progress — opening Friday",
]


class Command(BaseCommand):
    help = 'Seed RSVPs, paid tickets, reviews, follows to flesh out the demo.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Run every seeder.')
        parser.add_argument('--rsvps', action='store_true')
        parser.add_argument('--tickets', action='store_true')
        parser.add_argument('--reviews', action='store_true')
        parser.add_argument('--follows', action='store_true')
        parser.add_argument('--stories', action='store_true')
        parser.add_argument('--min-rsvps', type=int, default=6)
        parser.add_argument('--max-rsvps', type=int, default=14)

    def handle(self, *args, **opts):
        run_all = opts['all'] or not any(
            opts.get(k) for k in ('rsvps', 'tickets', 'reviews', 'follows', 'stories')
        )
        random.seed(42)  # reproducible-ish

        if run_all or opts['rsvps']:
            self._seed_rsvps(opts['min_rsvps'], opts['max_rsvps'])
        if run_all or opts['tickets']:
            self._seed_tickets()
        if run_all or opts['reviews']:
            self._seed_reviews()
        if run_all or opts['follows']:
            self._seed_follows()
        if run_all or opts['stories']:
            self._seed_stories()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('All done.'))

    # ------------------------------------------------------------------ #
    # RSVPs                                                              #
    # ------------------------------------------------------------------ #
    def _seed_rsvps(self, min_n, max_n):
        from apps.events.models import Event, EventRSVP
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING('\n→ RSVPs'))
        upcoming = list(Event.objects.filter(starts_at__gte=timezone.now()).order_by('starts_at')[:20])
        if not upcoming:
            self.stdout.write('  (no upcoming events — skip)')
            return

        candidate_pool = list(User.objects.exclude(role='venue').values_list('id', flat=True))
        if len(candidate_pool) < 3:
            self.stdout.write('  (fewer than 3 non-venue users — skip)')
            return

        created = 0
        for event in upcoming:
            target = random.randint(min_n, max_n)
            existing_user_ids = set(
                EventRSVP.objects.filter(event=event).values_list('user_id', flat=True)
            )
            pool = [uid for uid in candidate_pool if uid not in existing_user_ids and uid != event.host_id]
            if not pool:
                continue
            pick = random.sample(pool, min(target, len(pool)))
            # 70% going, 20% maybe, 10% interested
            rows = []
            for uid in pick:
                r = random.random()
                status = (
                    EventRSVP.STATUS_GOING if r < 0.7
                    else EventRSVP.STATUS_MAYBE if r < 0.9
                    else EventRSVP.STATUS_INTERESTED
                )
                rows.append(EventRSVP(event=event, user_id=uid, status=status))
            EventRSVP.objects.bulk_create(rows, ignore_conflicts=True)
            created += len(rows)
            self.stdout.write(f'  · "{event.title[:50]}" → +{len(rows)} RSVPs')
        self.stdout.write(self.style.SUCCESS(f'  RSVPs attempted: {created}'))

    # ------------------------------------------------------------------ #
    # Tickets                                                            #
    # ------------------------------------------------------------------ #
    def _seed_tickets(self):
        from apps.tickets.models import TicketTier, Ticket
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING('\n→ Paid tickets'))
        tiers = TicketTier.objects.filter(is_active=True).select_related('event')
        if not tiers.exists():
            self.stdout.write('  (no ticket tiers — skip)')
            return

        # Non-host, non-venue users are plausible ticket buyers.
        buyer_pool = list(User.objects.exclude(role='venue').values_list('id', flat=True))
        created = 0
        for tier in tiers:
            remaining = tier.remaining
            if remaining <= 0:
                continue
            # Buy between 1 and min(5, remaining) tickets for this tier
            n_to_buy = random.randint(1, min(5, remaining))
            existing_holder_ids = set(
                Ticket.objects.filter(tier=tier, payment_status='paid').values_list('holder_id', flat=True)
            )
            pool = [uid for uid in buyer_pool if uid not in existing_holder_ids and uid != tier.event.host_id]
            if not pool:
                continue
            buyers = random.sample(pool, min(n_to_buy, len(pool)))
            platform_fee = int(round(tier.price_cents * 0.06))
            for uid in buyers:
                Ticket.objects.create(
                    event=tier.event, tier=tier, holder_id=uid,
                    price_cents=tier.price_cents,
                    platform_fee_cents=platform_fee,
                    incognito_fee_cents=0,
                    total_cents=tier.price_cents + platform_fee,
                    currency=tier.currency,
                    payment_status='paid',
                    stripe_payment_intent_id=f'pi_seed_{uuid.uuid4().hex[:16]}',
                    is_incognito=random.random() < 0.1,  # 10% incognito
                )
                created += 1
            tier.sold = Ticket.objects.filter(tier=tier, payment_status='paid').count()
            tier.save(update_fields=['sold'])
            self.stdout.write(f'  · "{tier.event.title[:40]}" / {tier.name} → +{len(buyers)} tickets (sold now: {tier.sold}/{tier.quantity})')
        self.stdout.write(self.style.SUCCESS(f'  Tickets created: {created}'))

    # ------------------------------------------------------------------ #
    # Reviews                                                            #
    # ------------------------------------------------------------------ #
    def _seed_reviews(self):
        from apps.bookings.models import Booking
        from apps.reviews.models import Review

        self.stdout.write(self.style.MIGRATE_HEADING('\n→ Reviews'))
        # Reviews require a booking. Prefer confirmed/completed/in_progress.
        reviewable = Booking.objects.filter(
            status__in=['confirmed', 'completed', 'in_progress']
        ).select_related('space__venue__user', 'creator__user')

        if not reviewable.exists():
            # Mark a few pending bookings as completed so we have something to review.
            stale = Booking.objects.filter(status__in=['pending', 'accepted'])[:5]
            if not stale.exists():
                self.stdout.write('  (no bookings to review — skip)')
                return
            for b in stale:
                b.status = 'completed'
                b.save(update_fields=['status'])
            reviewable = Booking.objects.filter(id__in=[b.id for b in stale])
            self.stdout.write(f'  · flipped {stale.count()} booking(s) → completed for reviewability')

        created = 0
        for booking in reviewable:
            venue_user = booking.space.venue.user
            creator_user = booking.creator.user
            # Creator → Venue
            cv, made1 = Review.objects.get_or_create(
                booking=booking, reviewer=creator_user,
                defaults={
                    'reviewee': venue_user,
                    'direction': Review.DIRECTION_CREATOR_TO_VENUE,
                    'rating': random.choice([4, 5, 5, 5]),
                    'comment': random.choice(REVIEW_COMMENTS_VENUE_POSITIVE),
                },
            )
            # Venue → Creator
            vc, made2 = Review.objects.get_or_create(
                booking=booking, reviewer=venue_user,
                defaults={
                    'reviewee': creator_user,
                    'direction': Review.DIRECTION_VENUE_TO_CREATOR,
                    'rating': random.choice([4, 5, 5, 5]),
                    'comment': random.choice(REVIEW_COMMENTS_CREATOR_POSITIVE),
                },
            )
            if made1: created += 1
            if made2: created += 1
        self.stdout.write(self.style.SUCCESS(f'  Reviews created: {created}'))

    # ------------------------------------------------------------------ #
    # Follows                                                            #
    # ------------------------------------------------------------------ #
    def _seed_follows(self):
        from apps.follows.models import Follow
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING('\n→ Follows'))
        user_ids = list(User.objects.values_list('id', flat=True))
        if len(user_ids) < 4:
            self.stdout.write('  (fewer than 4 users — skip)')
            return

        # Each user follows 3-8 random others.
        rows = []
        for uid in user_ids:
            targets = random.sample([x for x in user_ids if x != uid], min(random.randint(3, 8), len(user_ids) - 1))
            for tid in targets:
                rows.append(Follow(follower_id=uid, following_id=tid))
        n = Follow.objects.bulk_create(rows, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  Follow rows attempted: {len(rows)} (dupes ignored)'))

    # ------------------------------------------------------------------ #
    # Stories                                                            #
    # ------------------------------------------------------------------ #
    def _seed_stories(self):
        from apps.events.models import Story
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING('\n→ Stories'))
        # Pick a handful of creator/venue users; give each 1-2 active stories.
        authors = list(
            User.objects.filter(role__in=['creator', 'venue']).order_by('?')[:10]
        )
        if not authors:
            self.stdout.write('  (no creator/venue users — skip)')
            return

        created = 0
        now = timezone.now()
        sample_images = [
            'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800',
            'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=800',
            'https://images.unsplash.com/photo-1524368535928-5b5e00ddc76b?w=800',
            'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=800',
            'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800',
            'https://images.unsplash.com/photo-1551818255-e6e10975bc17?w=800',
        ]
        for author in authors:
            active = Story.objects.filter(author=author, expires_at__gt=now).count()
            if active >= 1:
                continue
            n = random.randint(1, 2)
            for _ in range(n):
                Story.objects.create(
                    author=author,
                    image=random.choice(sample_images),
                    caption=random.choice(STORY_CAPTIONS),
                    expires_at=now + timedelta(hours=random.randint(6, 23)),
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f'  Stories created: {created}'))
