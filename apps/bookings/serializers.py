from rest_framework import serializers
from .models import Booking, BookingEvent


class BookingEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingEvent
        fields = ['id', 'event_type', 'actor_name', 'note', 'created_at']

    def get_actor_name(self, obj):
        if not obj.actor:
            return 'System'
        return f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.username


class BookingSerializer(serializers.ModelSerializer):
    space_title = serializers.CharField(source='space.title', read_only=True)
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    space_image = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='creator.display_name', read_only=True)
    creator_avatar = serializers.URLField(source='creator.user.avatar', read_only=True)
    venue_name = serializers.CharField(source='space.venue.organization_name', read_only=True)
    venue_id = serializers.IntegerField(source='space.venue.id', read_only=True)
    events = BookingEventSerializer(many=True, read_only=True)
    stripe_client_secret = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'proposal', 'space', 'space_slug', 'creator', 'venue_id',
            'start_date', 'end_date', 'total_amount', 'platform_fee_venue',
            'platform_fee_creator', 'status', 'booking_type', 'payment_status',
            'rejection_reason', 'responded_at', 'space_title', 'space_image',
            'creator_name', 'creator_avatar', 'venue_name', 'events',
            'stripe_client_secret', 'stripe_payment_intent_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'platform_fee_venue', 'platform_fee_creator', 'created_at', 'updated_at',
            'stripe_payment_intent_id', 'payment_status', 'status', 'responded_at',
        ]

    def get_space_image(self, obj):
        img = obj.space.images.filter(is_primary=True).first() or obj.space.images.first()
        return img.image_url if img else ''

    def get_stripe_client_secret(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        if obj.creator.user_id == request.user.id and obj.status == 'pending':
            return obj.stripe_client_secret
        return ''


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['space', 'start_date', 'end_date']
