from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Proposal, PortfolioProject
from .serializers import ProposalSerializer, PortfolioProjectSerializer


class ProposalListCreateView(generics.ListCreateAPIView):
    serializer_class = ProposalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'creator':
            return Proposal.objects.filter(creator=user.creator_profile).select_related(
                'space', 'space__venue', 'creator', 'creator__user'
            )
        elif user.role == 'venue':
            return Proposal.objects.filter(
                space__venue=user.venue_profile
            ).select_related('space', 'space__venue', 'creator', 'creator__user')
        return Proposal.objects.none()

    def create(self, request, *args, **kwargs):
        from apps.messaging.models import Block
        from apps.spaces.models import Space
        space_id = request.data.get('space')
        if space_id:
            try:
                space = Space.objects.select_related('venue__user').get(pk=space_id)
                venue_user = space.venue.user
                if Block.objects.filter(
                    blocker__in=[request.user, venue_user], blocked__in=[request.user, venue_user]
                ).exclude(blocker=request.user, blocked=request.user).exclude(blocker=venue_user, blocked=venue_user).exists():
                    return Response({'detail': 'Cannot submit proposal — user is blocked.'}, status=403)
            except Space.DoesNotExist:
                pass
        return super().create(request, *args, **kwargs)


class ProposalDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProposalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'creator':
            return Proposal.objects.filter(creator=user.creator_profile)
        elif user.role == 'venue':
            return Proposal.objects.filter(space__venue=user.venue_profile)
        return Proposal.objects.none()

    def update(self, request, *args, **kwargs):
        proposal = self.get_object()
        # Venue can update status and venue_notes - bypass serializer's read_only_fields
        if request.user.role == 'venue':
            # Verify venue owns the space
            if proposal.space.venue.user_id != request.user.id:
                return Response({'error': 'Not authorized'}, status=403)
            valid_statuses = [c[0] for c in Proposal.STATUS_CHOICES]
            updated = False
            if 'status' in request.data:
                new_status = request.data.get('status')
                if new_status not in valid_statuses:
                    return Response({'error': f'Invalid status: {new_status}. Must be one of {valid_statuses}'}, status=400)
                proposal.status = new_status
                updated = True
            if 'venue_notes' in request.data:
                proposal.venue_notes = request.data.get('venue_notes', '') or ''
                updated = True
            if updated:
                proposal.save()
                # Auto-block dates when proposal is accepted
                if proposal.status == 'accepted' and proposal.proposed_start_date and proposal.proposed_end_date:
                    from apps.spaces.models import Availability
                    # Create blocked availability for the proposed dates
                    Availability.objects.update_or_create(
                        space=proposal.space,
                        start_date=proposal.proposed_start_date,
                        end_date=proposal.proposed_end_date,
                        defaults={
                            'is_available': False,
                            'notes': f'Blocked by accepted proposal: {proposal.title}',
                        },
                    )
            return Response(ProposalSerializer(proposal, context={'request': request}).data)
        # Creator can update if draft
        if proposal.status != 'draft' and proposal.creator.user_id == request.user.id:
            # Allow creator to withdraw
            if request.data.get('status') == 'withdrawn':
                proposal.status = 'withdrawn'
                proposal.save()
                return Response(ProposalSerializer(proposal, context={'request': request}).data)
            return Response({'error': 'Cannot edit non-draft proposal (only withdraw allowed)'}, status=400)
        return super().update(request, *args, **kwargs)


class PortfolioListCreateView(generics.ListCreateAPIView):
    serializer_class = PortfolioProjectSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        creator_id = self.kwargs.get('creator_id')
        if creator_id:
            return PortfolioProject.objects.filter(creator_id=creator_id).prefetch_related('images')
        if self.request.user.is_authenticated and self.request.user.role == 'creator':
            return PortfolioProject.objects.filter(
                creator=self.request.user.creator_profile
            ).prefetch_related('images')
        return PortfolioProject.objects.none()


class PortfolioProjectPublicView(generics.RetrieveAPIView):
    """Public retrieve of a single portfolio project by id."""
    serializer_class = PortfolioProjectSerializer
    permission_classes = [permissions.AllowAny]
    queryset = PortfolioProject.objects.prefetch_related('images').select_related('creator', 'creator__user')


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PortfolioProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PortfolioProject.objects.filter(
            creator=self.request.user.creator_profile
        ).prefetch_related('images')
