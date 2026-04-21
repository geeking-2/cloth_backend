from rest_framework import serializers
from django.db import IntegrityError
from .models import Review
from apps.bookings.models import Booking


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    reviewer_avatar = serializers.SerializerMethodField()
    reviewer_role = serializers.CharField(source='reviewer.role', read_only=True)
    reviewee_name = serializers.SerializerMethodField()
    space_title = serializers.CharField(source='booking.space.title', read_only=True)
    space_slug = serializers.CharField(source='booking.space.slug', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'booking', 'reviewer', 'reviewee', 'direction', 'rating', 'comment',
            'reviewer_name', 'reviewer_avatar', 'reviewer_role', 'reviewee_name',
            'space_title', 'space_slug', 'created_at',
        ]
        read_only_fields = ['id', 'reviewer', 'reviewee', 'direction', 'created_at']

    def _profile_name(self, user):
        if not user:
            return ''
        if user.role == 'venue' and hasattr(user, 'venue_profile'):
            return user.venue_profile.organization_name or user.username
        if user.role == 'creator' and hasattr(user, 'creator_profile'):
            return user.creator_profile.display_name or user.username
        return user.username

    def _profile_avatar(self, user):
        if not user:
            return None
        if user.role == 'venue' and hasattr(user, 'venue_profile') and user.venue_profile:
            return user.venue_profile.logo or getattr(user, 'avatar', None)
        return getattr(user, 'avatar', None)

    def get_reviewer_name(self, obj):
        return self._profile_name(obj.reviewer)

    def get_reviewer_avatar(self, obj):
        return self._profile_avatar(obj.reviewer)

    def get_reviewee_name(self, obj):
        return self._profile_name(obj.reviewee)

    def _parties(self, booking):
        """Both Booking.creator (CreatorProfile) and Space.venue (VenueProfile)
        are profile FKs — resolve them to their User ids."""
        creator_user_id = booking.creator.user_id
        venue_user_id = booking.space.venue.user_id
        return creator_user_id, venue_user_id

    def validate(self, attrs):
        booking = attrs.get('booking')
        user = self.context['request'].user
        if not booking:
            raise serializers.ValidationError({'booking': 'Booking is required.'})
        creator_user_id, venue_user_id = self._parties(booking)
        if user.id not in (creator_user_id, venue_user_id):
            raise serializers.ValidationError('You can only review bookings you were part of.')
        if booking.status not in ('confirmed', 'completed', 'in_progress'):
            raise serializers.ValidationError('You can only review confirmed, in-progress or completed bookings.')
        if Review.objects.filter(booking=booking, reviewer=user).exists():
            raise serializers.ValidationError('You have already reviewed this booking.')
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        booking = validated_data['booking']
        creator_user_id, venue_user_id = self._parties(booking)
        if user.id == creator_user_id:
            reviewee = booking.space.venue.user
            direction = Review.DIRECTION_CREATOR_TO_VENUE
        else:
            reviewee = booking.creator.user
            direction = Review.DIRECTION_VENUE_TO_CREATOR
        validated_data['reviewer'] = user
        validated_data['reviewee'] = reviewee
        validated_data['direction'] = direction
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError('You have already reviewed this booking.')
