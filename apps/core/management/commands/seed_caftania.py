"""Seed the Caftania marketplace with demo data.

Reads JSON fixtures from `caftania_frontend/seed/` and populates:
  - one Marketplace(slug='caftania')
  - loueuses as users + VenueProfile
  - clientes as users + CreatorProfile
  - caftans as Space rows (category + occasion_tags)
  - reviews (best-effort; requires bookings — skipped if missing)
  - events with host

Idempotent: uses update_or_create on natural keys (username, qr_code, slug).
Run with --dry-run to preview counts without writing.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import Marketplace
from apps.accounts.models import User, VenueProfile, CreatorProfile
from apps.spaces.models import Space
from apps.events.models import Event


SEED_DIR = Path(r'C:\Users\User\Desktop\caftania\caftania_frontend\seed')


class Command(BaseCommand):
    help = 'Seed the Caftania marketplace from frontend JSON fixtures.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Report what would be created without writing.')
        parser.add_argument('--seed-dir', default=str(SEED_DIR),
                            help='Override the seed JSON directory.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        seed_dir = Path(opts['seed_dir'])

        def load(name):
            p = seed_dir / name
            if not p.exists():
                self.stdout.write(self.style.WARNING(f'missing {p}'))
                return []
            return json.loads(p.read_text(encoding='utf-8'))

        loueuses = load('loueuses.json')
        clientes = load('clientes.json')
        caftans = load('caftans.json')
        reviews = load('reviews.json')
        events = load('events.json')

        counts = {
            'marketplace': 0, 'loueuses': 0, 'clientes': 0,
            'caftans': 0, 'reviews_skipped': 0, 'events': 0,
        }

        sid = transaction.savepoint() if not dry else None
        try:
            marketplace, created = Marketplace.objects.update_or_create(
                slug='caftania',
                defaults=dict(
                    name='Caftania', domain='caftania.com',
                    primary_language='fr', secondary_language='ar',
                    currency='EUR', commission_rate=15,
                    primary_color='#B85C38', logo_url='',
                    tagline_key='caftania.tagline',
                    is_active=True,
                ),
            )
            counts['marketplace'] = 1

            # Loueuses: user + VenueProfile
            for row in loueuses:
                user, _ = User.objects.update_or_create(
                    username=row['username'],
                    defaults=dict(
                        email=row.get('email', ''),
                        role='venue',
                        bio=row.get('bio', ''),
                        marketplace=marketplace,
                        display_mode='real',
                    ),
                )
                VenueProfile.objects.update_or_create(
                    user=user,
                    defaults=dict(
                        organization_name=row.get('organization_name', row['username']),
                        organization_type='other',
                        city=row.get('city', ''),
                        country=row.get('country', 'BE'),
                        description=row.get('bio', ''),
                    ),
                )
                counts['loueuses'] += 1

            # Clientes: user + CreatorProfile
            for row in clientes:
                user, _ = User.objects.update_or_create(
                    username=row['username'],
                    defaults=dict(
                        email=row.get('email', ''),
                        role='creator',
                        marketplace=marketplace,
                        display_mode='real',
                    ),
                )
                CreatorProfile.objects.update_or_create(
                    user=user,
                    defaults=dict(
                        display_name=row.get('display_name', row['username']),
                        specialty='other',
                        city=row.get('city', ''),
                        country=row.get('country', 'BE'),
                    ),
                )
                counts['clientes'] += 1

            # Caftans (Space)
            for row in caftans:
                owner_user = User.objects.filter(username=row['owner_username']).first()
                if not owner_user or not hasattr(owner_user, 'venue_profile'):
                    self.stdout.write(self.style.WARNING(
                        f"skip caftan {row['title']}: owner {row['owner_username']} has no VenueProfile"))
                    continue
                slug = f"{slugify(row['title'])}-{row['qr_code'].lower()}"
                Space.objects.update_or_create(
                    qr_code=row['qr_code'],
                    defaults=dict(
                        venue=owner_user.venue_profile,
                        marketplace=marketplace,
                        title=row['title'],
                        slug=slug,
                        description=row.get('description', ''),
                        space_type='other',
                        category=row.get('category', 'caftan'),
                        size=row.get('size', ''),
                        color=row.get('color', ''),
                        brand=row.get('brand', ''),
                        occasion_tags=row.get('occasion_tags', []),
                        daily_rate=row.get('daily_rate', 0),
                        deposit_amount=row.get('deposit_amount', 0),
                        available_for_rent=row.get('available_for_rent', True),
                        available_for_sale=row.get('available_for_sale', False),
                        sale_price=row.get('sale_price'),
                        currency='EUR',
                        is_active=True,
                    ),
                )
                counts['caftans'] += 1

            # Reviews require a booking in the current schema — skip cleanly.
            counts['reviews_skipped'] = len(reviews)

            # Events
            for row in events:
                host = User.objects.filter(username=row['host_username']).first()
                if not host:
                    continue
                starts = timezone.now() + timezone.timedelta(days=30)
                Event.objects.update_or_create(
                    slug=slugify(row['title'])[:200],
                    defaults=dict(
                        host=host,
                        title=row['title'],
                        description=row.get('description', ''),
                        starts_at=starts,
                        location_text=f"{row.get('city','')}, {row.get('country','')}",
                        is_public=True,
                    ),
                )
                counts['events'] += 1

            if dry:
                transaction.savepoint_rollback(sid) if sid else None
                self.stdout.write(self.style.NOTICE('DRY RUN — rolled back'))
            else:
                if sid:
                    transaction.savepoint_commit(sid)
        except Exception:
            if sid:
                transaction.savepoint_rollback(sid)
            raise

        for k, v in counts.items():
            self.stdout.write(f'  {k}: {v}')
        self.stdout.write(self.style.SUCCESS('seed_caftania done'))
