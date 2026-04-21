from rest_framework import generics, permissions
from django.db.models import Q
from .models import Review
from .serializers import ReviewSerializer


class ReviewListCreateView(generics.ListCreateAPIView):
    """
    GET filters:
      ?space=<slug>            — reviews about that space (creator→venue)
      ?venue=<user_id>         — reviews about that venue user
      ?creator=<user_id>       — reviews about that creator
      ?reviewee=<user_id>      — reviews received by any user
      ?mine=given|received     — reviews given/received by current user
    """
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Review.objects.all().select_related(
            'reviewer', 'reviewee', 'booking__space',
            'reviewer__creator_profile', 'reviewer__venue_profile',
        )
        params = self.request.query_params
        if params.get('space'):
            qs = qs.filter(booking__space__slug=params['space'], direction=Review.DIRECTION_CREATOR_TO_VENUE)
        if params.get('venue'):
            qs = qs.filter(reviewee_id=params['venue'], direction=Review.DIRECTION_CREATOR_TO_VENUE)
        if params.get('creator'):
            qs = qs.filter(reviewee_id=params['creator'], direction=Review.DIRECTION_VENUE_TO_CREATOR)
        if params.get('reviewee'):
            qs = qs.filter(reviewee_id=params['reviewee'])
        mine = params.get('mine')
        if mine and self.request.user.is_authenticated:
            if mine == 'given':
                qs = qs.filter(reviewer=self.request.user)
            elif mine == 'received':
                qs = qs.filter(reviewee=self.request.user)
        return qs
