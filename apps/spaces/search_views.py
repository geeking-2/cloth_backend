"""Unified cross-resource search.

Uses Postgres full-text when available (via `SearchQuery`/`SearchRank`), falls
back to case-insensitive LIKE on non-Postgres. Postgres is our production DB,
so FTS is the hot path.
"""
from django.db.models import Q
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


def _postgres():
    return connection.vendor == 'postgresql'


def _spaces_qs(q):
    from apps.spaces.models import Space
    qs = Space.objects.filter(is_active=True).select_related('venue__user')
    if not q:
        return qs[:10]
    if _postgres():
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
        vector = (
            SearchVector('title', weight='A') +
            SearchVector('description', weight='B') +
            SearchVector('technical_notes', weight='C')
        )
        query = SearchQuery(q)
        qs = qs.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0).order_by('-rank')
        # Fallback: if FTS returned nothing, try icontains (helps short queries).
        if not qs.exists():
            qs = Space.objects.filter(is_active=True).filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(tags__icontains=q)
            ).select_related('venue__user')
    else:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(tags__icontains=q)
        )
    return qs[:10]


def _creators_qs(q):
    from apps.accounts.models import CreatorProfile
    qs = CreatorProfile.objects.select_related('user')
    if not q:
        return qs[:10]
    qs = qs.filter(
        Q(display_name__icontains=q)
        | Q(bio__icontains=q)
        | Q(specialty__icontains=q)
        | Q(skills__icontains=q)
        | Q(user__username__icontains=q)
        | Q(user__first_name__icontains=q)
        | Q(user__last_name__icontains=q)
    )
    return qs[:10]


def _events_qs(q):
    from apps.events.models import Event
    from django.utils import timezone
    qs = Event.objects.filter(is_public=True, starts_at__gte=timezone.now()).select_related('host', 'space')
    if not q:
        return qs[:10]
    if _postgres():
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
        vector = SearchVector('title', weight='A') + SearchVector('description', weight='B') + SearchVector('location_text', weight='C')
        query = SearchQuery(q)
        qs = qs.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0).order_by('-rank')
        if not qs.exists():
            qs = Event.objects.filter(is_public=True).filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(location_text__icontains=q)
            ).select_related('host', 'space')
    else:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(location_text__icontains=q)
        )
    return qs[:10]


def _serialize_space(s):
    return {
        'kind': 'space',
        'id': s.id,
        'slug': s.slug,
        'title': s.title,
        'description': (s.description or '')[:200],
        'city': getattr(s.venue, 'city', ''),
        'cover_image': s.images.first().image_url if s.images.exists() else '',
        'daily_rate': str(s.daily_rate or ''),
        'currency': s.currency,
    }


def _serialize_creator(c):
    return {
        'kind': 'creator',
        'id': c.user_id,
        'display_name': c.display_name or c.user.username,
        'specialty': c.specialty or '',
        'bio': (c.bio or '')[:200],
        'avatar': getattr(c.user, 'avatar', None) or '',
        'city': c.city or '',
    }


def _serialize_event(e):
    return {
        'kind': 'event',
        'id': e.id,
        'slug': e.slug,
        'title': e.title,
        'description': (e.description or '')[:200],
        'starts_at': e.starts_at,
        'event_type': e.event_type,
        'cover_image': e.cover_image or '',
        'location': e.location_text or (e.space.title if e.space else ''),
    }


class UnifiedSearchView(APIView):
    """GET /api/search/all/?q=foo[&kind=spaces|creators|events]"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        kind = request.query_params.get('kind')

        result = {}
        if not kind or kind == 'spaces':
            result['spaces'] = [_serialize_space(s) for s in _spaces_qs(q)]
        if not kind or kind == 'creators':
            result['creators'] = [_serialize_creator(c) for c in _creators_qs(q)]
        if not kind or kind == 'events':
            result['events'] = [_serialize_event(e) for e in _events_qs(q)]
        result['query'] = q
        result['total'] = sum(len(v) for k, v in result.items() if isinstance(v, list))
        return Response(result)
