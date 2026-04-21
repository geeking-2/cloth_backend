from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q
from .models import Space, SpaceImage, Availability, SavedSpace
from .serializers import (
    SpaceListSerializer, SpaceDetailSerializer, SpaceCreateUpdateSerializer,
    SpaceImageSerializer, AvailabilitySerializer,
)


class IsVenueOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'venue'

    def has_object_permission(self, request, view, obj):
        return obj.venue.user == request.user


class SpaceListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'venue__organization_name', 'venue__city']
    ordering_fields = ['daily_rate', 'area_sqft', 'created_at']
    filterset_fields = {
        'space_type': ['exact'],
        'daily_rate': ['gte', 'lte'],
        'area_sqft': ['gte', 'lte'],
        'has_projection_surfaces': ['exact'],
        'has_blackout_capability': ['exact'],
        'has_sound_system': ['exact'],
        'is_featured': ['exact'],
        'venue': ['exact'],
        'venue__user': ['exact'],
        'venue__city': ['exact', 'icontains'],
        'venue__country': ['exact'],
    }

    def get_queryset(self):
        qs = Space.objects.filter(is_active=True).select_related('venue').prefetch_related('images')
        qs = qs.annotate(
            rating=Avg('bookings__reviews__rating', filter=Q(bookings__reviews__direction='creator_to_venue')),
            review_count=Count('bookings__reviews', filter=Q(bookings__reviews__direction='creator_to_venue')),
        )
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SpaceCreateUpdateSerializer
        return SpaceListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsVenueOwner()]
        return [permissions.AllowAny()]


class SpaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'slug'

    def get_queryset(self):
        return Space.objects.select_related('venue', 'venue__user').prefetch_related(
            'images', 'availabilities'
        ).annotate(
            rating=Avg('bookings__reviews__rating', filter=Q(bookings__reviews__direction='creator_to_venue')),
            review_count=Count('bookings__reviews', filter=Q(bookings__reviews__direction='creator_to_venue')),
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SpaceCreateUpdateSerializer
        return SpaceDetailSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsVenueOwner()]
        return [permissions.AllowAny()]


class FeaturedSpacesView(generics.ListAPIView):
    serializer_class = SpaceListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Space.objects.filter(
            is_active=True, is_featured=True
        ).select_related('venue').prefetch_related('images').annotate(
            rating=Avg('bookings__reviews__rating', filter=Q(bookings__reviews__direction='creator_to_venue')),
            review_count=Count('bookings__reviews', filter=Q(bookings__reviews__direction='creator_to_venue')),
        )[:8]


class VenueSpacesView(generics.ListAPIView):
    serializer_class = SpaceListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Space.objects.filter(
            venue=self.request.user.venue_profile
        ).select_related('venue').prefetch_related('images').annotate(
            rating=Avg('bookings__reviews__rating', filter=Q(bookings__reviews__direction='creator_to_venue')),
            review_count=Count('bookings__reviews', filter=Q(bookings__reviews__direction='creator_to_venue')),
        )


class SpaceImageCreateView(generics.CreateAPIView):
    serializer_class = SpaceImageSerializer
    permission_classes = [IsVenueOwner]

    def perform_create(self, serializer):
        space = Space.objects.get(slug=self.kwargs['slug'])
        serializer.save(space=space)


class AvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer

    def get_queryset(self):
        return Availability.objects.filter(space__slug=self.kwargs['slug'])

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsVenueOwner()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        space = Space.objects.get(slug=self.kwargs['slug'])
        serializer.save(space=space)


class AvailabilityBulkView(APIView):
    """Bulk add/remove availability for multiple dates.
    Handles single-day replacements AND splits overlapping multi-day ranges.
    """
    permission_classes = [IsVenueOwner]

    def post(self, request, slug):
        from datetime import datetime, timedelta
        from django.db import transaction
        space = Space.objects.get(slug=slug)
        if space.venue.user_id != request.user.id:
            return Response({'error': 'Not authorized'}, status=403)

        dates = request.data.get('dates', [])
        is_available = request.data.get('is_available', False)

        if not dates:
            return Response({'error': 'dates is required'}, status=400)

        parsed = []
        for d in dates:
            try:
                parsed.append(datetime.strptime(d, '%Y-%m-%d').date())
            except (ValueError, TypeError):
                return Response({'error': f'Invalid date: {d}'}, status=400)

        parsed_set = set(parsed)
        date_min, date_max = min(parsed), max(parsed)

        with transaction.atomic():
            # Find all availability entries that overlap with any of the dates being toggled
            overlapping = list(Availability.objects.select_for_update().filter(
                space=space,
                start_date__lte=date_max,
                end_date__gte=date_min,
            ))

            for avail in overlapping:
                # Check if any of our target dates falls within this availability
                covered_days = set()
                d = avail.start_date
                while d <= avail.end_date:
                    if d in parsed_set:
                        covered_days.add(d)
                    d += timedelta(days=1)

                if not covered_days:
                    continue

                # Delete the original and create split ranges for uncovered parts
                orig_start = avail.start_date
                orig_end = avail.end_date
                orig_status = avail.is_available
                avail.delete()

                # Compute remaining ranges (segments not in parsed_set)
                d = orig_start
                seg_start = None
                while d <= orig_end:
                    if d in parsed_set:
                        # Close any open segment
                        if seg_start is not None:
                            Availability.objects.create(
                                space=space,
                                start_date=seg_start,
                                end_date=d - timedelta(days=1),
                                is_available=orig_status,
                            )
                            seg_start = None
                    else:
                        if seg_start is None:
                            seg_start = d
                    d += timedelta(days=1)
                # Close trailing segment
                if seg_start is not None:
                    Availability.objects.create(
                        space=space,
                        start_date=seg_start,
                        end_date=orig_end,
                        is_available=orig_status,
                    )

            # Now create fresh single-day entries for the toggled dates
            Availability.objects.bulk_create([
                Availability(space=space, start_date=d, end_date=d, is_available=is_available)
                for d in parsed
            ])

        return Response({'updated': len(parsed)})


class SpaceCalendarView(APIView):
    """Returns day->status map for a given month (available/blocked/booked/pending)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        from datetime import datetime, timedelta
        from apps.bookings.models import Booking
        try:
            space = Space.objects.get(slug=slug)
        except Space.DoesNotExist:
            return Response({}, status=404)

        month_str = request.query_params.get('month')
        if month_str:
            try:
                month_start = datetime.strptime(month_str + '-01', '%Y-%m-%d').date()
            except ValueError:
                month_start = datetime.now().date().replace(day=1)
        else:
            month_start = datetime.now().date().replace(day=1)

        # End of month
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)

        day_map = {}

        # Availability entries - order by id so newer entries override older ones
        for avail in Availability.objects.filter(
            space=space, start_date__lte=month_end, end_date__gte=month_start
        ).order_by('id'):
            d = max(avail.start_date, month_start)
            while d <= min(avail.end_date, month_end):
                day_map[d.isoformat()] = 'available' if avail.is_available else 'blocked'
                d += timedelta(days=1)

        # Bookings override availability
        for booking in Booking.objects.filter(
            space=space,
            status__in=['pending', 'accepted', 'confirmed', 'in_progress'],
            start_date__lte=month_end,
            end_date__gte=month_start,
        ):
            d = max(booking.start_date, month_start)
            while d <= min(booking.end_date, month_end):
                day_map[d.isoformat()] = 'pending' if booking.status == 'pending' else 'booked'
                d += timedelta(days=1)

        return Response(day_map)


class SavedSpaceListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        saved = SavedSpace.objects.filter(user=request.user).select_related('space', 'space__venue')
        spaces = [s.space for s in saved]
        serializer = SpaceListSerializer(spaces, many=True)
        return Response(serializer.data)

    def post(self, request):
        space_id = request.data.get('space_id')
        SavedSpace.objects.get_or_create(user=request.user, space_id=space_id)
        return Response({'status': 'saved'}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        space_id = request.data.get('space_id')
        SavedSpace.objects.filter(user=request.user, space_id=space_id).delete()
        return Response({'status': 'removed'}, status=status.HTTP_204_NO_CONTENT)


class SimilarSpacesView(generics.ListAPIView):
    serializer_class = SpaceListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        from django.db.models import Q
        try:
            space = Space.objects.select_related('venue').get(slug=self.kwargs['slug'])
        except Space.DoesNotExist:
            return Space.objects.none()
        return Space.objects.filter(
            is_active=True
        ).filter(
            Q(venue__city=space.venue.city) | Q(space_type=space.space_type)
        ).exclude(id=space.id).select_related('venue').prefetch_related('images').annotate(
            rating=Avg('bookings__reviews__rating', filter=Q(bookings__reviews__direction='creator_to_venue')),
            review_count=Count('bookings__reviews', filter=Q(bookings__reviews__direction='creator_to_venue')),
        )[:6]


class LandingStatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from apps.accounts.models import VenueProfile, CreatorProfile
        from apps.bookings.models import Booking
        return Response({
            'total_venues': VenueProfile.objects.count(),
            'total_creators': CreatorProfile.objects.count(),
            'total_spaces': Space.objects.filter(is_active=True).count(),
            'total_bookings': Booking.objects.filter(status='completed').count(),
        })
