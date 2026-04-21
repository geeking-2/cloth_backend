from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event, EventInvite
from apps.spaces.models import Space


class Command(BaseCommand):
    help = 'Send demo event invitations to the audience_demo user from creator_1 and space #15 owner.'

    def handle(self, *args, **options):
        User = get_user_model()

        invitee = User.objects.filter(username='audience_demo').first()
        if not invitee:
            self.stdout.write(self.style.ERROR('audience_demo user not found. Run create_demo_audience first.'))
            return

        # --- Inviter 1: creator_1 (fallback: first creator) ---
        creator = (
            User.objects.filter(username='creator_1').first()
            or User.objects.filter(role='creator').order_by('id').first()
        )
        # --- Inviter 2: owner of space #15 (fallback: first space's owner) ---
        space = Space.objects.filter(id=15).first() or Space.objects.order_by('id').first()
        venue_user = space.venue.user if space else None

        now = timezone.now()
        created_count = 0

        def ensure_event(host, title, slug, days_ahead, description, location, space_ref=None):
            starts = now + timedelta(days=days_ahead)
            event, _ = Event.objects.get_or_create(
                slug=slug,
                defaults={
                    'host': host,
                    'title': title,
                    'event_type': Event.TYPE_OPENING,
                    'description': description,
                    'cover_image': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1600',
                    'starts_at': starts,
                    'ends_at': starts + timedelta(hours=3),
                    'location_text': location,
                    'space': space_ref,
                    'is_public': True,
                    'max_capacity': 80,
                    'public_attendee_list': True,
                    'ticketing_enabled': False,
                },
            )
            return event

        def send_invite(event, inviter, message):
            nonlocal created_count
            inv, made = EventInvite.objects.get_or_create(
                event=event, invitee=invitee,
                defaults={'inviter': inviter, 'message': message, 'status': EventInvite.STATUS_PENDING},
            )
            if made:
                created_count += 1
            return inv, made

        results = []

        if creator:
            ev1 = ensure_event(
                host=creator,
                title=f'Studio Visit with {creator.first_name or creator.username}',
                slug=f'studio-visit-{creator.username}',
                days_ahead=7,
                description='An intimate studio visit — see new work in progress, share a drink, talk process.',
                location='Bushwick Studios, Brooklyn, NY',
            )
            send_invite(ev1, creator, f'Hey Alex — would love to have you come by the studio!')
            results.append(('creator invite', creator.username, ev1.slug))
        else:
            results.append(('creator invite', 'SKIPPED — no creator user', None))

        if venue_user and space:
            ev2 = ensure_event(
                host=venue_user,
                title=f'Late Night at {space.title}',
                slug=f'late-night-{space.slug}',
                days_ahead=10,
                description=f'A curated late-night program at {space.title}. DJ set, limited entry, come through.',
                location=space.title,
                space_ref=space,
            )
            send_invite(ev2, venue_user, f'Alex — saving a spot for you at {space.title}. Come through!')
            results.append(('venue invite', venue_user.username, ev2.slug))
        else:
            results.append(('venue invite', 'SKIPPED — no space/venue user', None))

        self.stdout.write(self.style.SUCCESS(
            f'OK  invitee=audience_demo  new_invites_created={created_count}'
        ))
        for label, who, slug in results:
            self.stdout.write(f'  {label}: inviter={who}  event_slug={slug}')
