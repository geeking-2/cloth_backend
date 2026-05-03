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
from apps.feed.models import Post, Story


SEED_DIR = Path(r'C:\Users\User\Desktop\caftania\caftania_frontend\seed')
SEED_PASSWORD = 'caftania2026'  # Demo accounts only — never use in prod.


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
        posts = load('posts.json')
        stories = load('stories.json')

        counts = {
            'marketplace': 0, 'loueuses': 0, 'clientes': 0,
            'caftans': 0, 'reviews_skipped': 0, 'events': 0,
            'posts': 0, 'stories': 0,
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

            # Loueuses: user + VenueProfile (JSON uses `id` like "loueuse-001")
            loueuse_user_by_id = {}
            for row in loueuses:
                username = row.get('username') or row['id']
                user, _ = User.objects.update_or_create(
                    username=username,
                    defaults=dict(
                        email=row.get('email', ''),
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', ''),
                        role='venue',
                        bio=row.get('bio', ''),
                        marketplace=marketplace,
                        display_mode=row.get('display_mode', 'real'),
                        pseudonym=row.get('pseudonym', ''),
                        is_kyc_verified=row.get('is_kyc_verified', False),
                        care_score=row.get('care_score', 5.0),
                        is_pro=row.get('is_pro', False),
                        pro_tier=row.get('pro_tier', 'none'),
                        shop_name=row.get('shop_name', ''),
                        shop_city=row.get('venue_city', row.get('city', '')),
                        has_physical_shop=row.get('has_physical_shop', False),
                        pro_featured=row.get('pro_featured', False),
                    ),
                )
                VenueProfile.objects.update_or_create(
                    user=user,
                    defaults=dict(
                        organization_name=row.get('organization_name',
                                                  row.get('pseudonym') or username),
                        organization_type='other',
                        city=row.get('venue_city', row.get('city', '')),
                        country=row.get('venue_country', 'BE'),
                        description=row.get('bio', ''),
                    ),
                )
                if not user.has_usable_password():
                    user.set_password(SEED_PASSWORD)
                    user.save(update_fields=['password'])
                loueuse_user_by_id[row['id']] = user
                counts['loueuses'] += 1

            # Clientes: user + CreatorProfile
            for row in clientes:
                username = row.get('username') or row['id']
                user, _ = User.objects.update_or_create(
                    username=username,
                    defaults=dict(
                        email=row.get('email', ''),
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', ''),
                        role='creator',
                        bio=row.get('bio', ''),
                        marketplace=marketplace,
                        display_mode=row.get('display_mode', 'real'),
                        pseudonym=row.get('pseudonym', ''),
                        is_kyc_verified=row.get('is_kyc_verified', False),
                        care_score=row.get('care_score', 5.0),
                    ),
                )
                CreatorProfile.objects.update_or_create(
                    user=user,
                    defaults=dict(
                        display_name=row.get('display_name',
                                             row.get('pseudonym') or username),
                        specialty='other',
                        city=row.get('city', ''),
                        country=row.get('country', 'BE'),
                    ),
                )
                if not user.has_usable_password():
                    user.set_password(SEED_PASSWORD)
                    user.save(update_fields=['password'])
                counts['clientes'] += 1

            # Caftans (Space)
            for row in caftans:
                owner_ref = row.get('owner_username') or row.get('owner_id')
                owner_user = (loueuse_user_by_id.get(owner_ref)
                              or User.objects.filter(username=owner_ref).first())
                if not owner_user or not hasattr(owner_user, 'venue_profile'):
                    self.stdout.write(self.style.WARNING(
                        f"skip caftan {row['title']}: owner {owner_ref} has no VenueProfile"))
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
                        category=row.get('category', row.get('space_type', 'caftan')),
                        weekly_rate=row.get('weekly_rate'),
                        rental_count=row.get('rental_count', 0),
                        is_featured=row.get('is_featured', False),
                        tags=row.get('tags', []),
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
            from datetime import datetime
            for row in events:
                host_ref = row.get('host_username') or row.get('organizer_id')
                host = (loueuse_user_by_id.get(host_ref)
                        or User.objects.filter(username=host_ref).first())
                if not host:
                    continue
                start_str = row.get('start_datetime')
                try:
                    starts = datetime.fromisoformat(start_str.replace('Z', '+00:00')) if start_str else timezone.now() + timezone.timedelta(days=30)
                except Exception:
                    starts = timezone.now() + timezone.timedelta(days=30)
                Event.objects.update_or_create(
                    slug=row.get('slug') or slugify(row['title'])[:200],
                    defaults=dict(
                        host=host,
                        title=row['title'],
                        description=row.get('description', ''),
                        starts_at=starts,
                        location_text=f"{row.get('venue_name','')}, {row.get('venue_address','')}".strip(', '),
                        is_public=not row.get('is_private', False),
                    ),
                )
                counts['events'] += 1

            # Posts (feed)
            from datetime import datetime
            item_by_sid = {}  # seed id (e.g. "caftan-001") -> Space
            for row in caftans:
                sp = Space.objects.filter(qr_code=row['qr_code']).first()
                if sp:
                    item_by_sid[row['id']] = sp
            cliente_user_by_id = {c['id']: User.objects.filter(
                username=c.get('username') or c['id']).first() for c in clientes}
            user_by_sid = {**loueuse_user_by_id, **cliente_user_by_id}

            for row in posts:
                author = user_by_sid.get(row.get('author_id'))
                if not author:
                    continue
                item = item_by_sid.get(row.get('item_id')) if row.get('item_id') else None
                created_str = row.get('created_at')
                try:
                    created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00')) if created_str else None
                except Exception:
                    created_at = None
                post_obj, _ = Post.objects.update_or_create(
                    author=author,
                    caption=row.get('caption', ''),
                    defaults=dict(
                        item=item,
                        marketplace=marketplace,
                        post_type=row.get('post_type', 'community_review'),
                        location_tag=row.get('location_tag', ''),
                        event_type=row.get('event_type', ''),
                        media_urls=row.get('media_urls', []),
                        has_face_blur=row.get('has_face_blur', False),
                        has_background_blur=row.get('has_background_blur', False),
                        is_anonymous=row.get('is_anonymous', False),
                        likes_count=row.get('likes_count', 0),
                        comments_count=row.get('comments_count', 0),
                        item_clicks_count=row.get('item_clicks_count', 0),
                    ),
                )
                if created_at:
                    Post.objects.filter(pk=post_obj.pk).update(created_at=created_at)
                counts['posts'] += 1

            # Stories (24h expiry from now)
            for row in stories:
                author = user_by_sid.get(row.get('author_id'))
                if not author:
                    continue
                item = item_by_sid.get(row.get('item_id')) if row.get('item_id') else None
                Story.objects.update_or_create(
                    author=author,
                    media_url=row['media_url'],
                    defaults=dict(
                        item=item,
                        marketplace=marketplace,
                        media_type=row.get('media_type', 'image'),
                        caption=row.get('caption', ''),
                        has_face_blur=row.get('has_face_blur', False),
                        is_anonymous=row.get('is_anonymous', False),
                        views_count=row.get('views_count', 0),
                        expires_at=timezone.now() + timezone.timedelta(hours=24),
                    ),
                )
                counts['stories'] += 1

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
