from rest_framework import serializers
from .models import Ticket, TicketTier
from .qr import encode_qr_payload


class TicketTierSerializer(serializers.ModelSerializer):
    remaining = serializers.IntegerField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)

    class Meta:
        model = TicketTier
        fields = [
            'id', 'event', 'name', 'description', 'price_cents', 'currency',
            'quantity', 'sold', 'remaining', 'is_sold_out', 'is_active', 'sort_order',
            'created_at',
        ]
        read_only_fields = ['id', 'sold', 'created_at']


class TicketSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    event_starts_at = serializers.DateTimeField(source='event.starts_at', read_only=True)
    event_cover_image = serializers.URLField(source='event.cover_image', read_only=True)
    tier_name = serializers.CharField(source='tier.name', read_only=True)
    holder_name = serializers.SerializerMethodField()
    qr_payload = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'event', 'event_title', 'event_slug', 'event_starts_at', 'event_cover_image',
            'tier', 'tier_name', 'holder', 'holder_name',
            'price_cents', 'platform_fee_cents', 'incognito_fee_cents', 'total_cents', 'currency',
            'payment_status', 'stripe_client_secret',
            'qr_token', 'qr_payload', 'is_incognito',
            'checked_in_at', 'refunded_at',
            'created_at',
        ]
        read_only_fields = [
            'id', 'price_cents', 'platform_fee_cents', 'incognito_fee_cents',
            'total_cents', 'currency', 'payment_status',
            'stripe_client_secret', 'qr_token', 'checked_in_at', 'refunded_at',
            'created_at',
        ]
        extra_kwargs = {
            'holder': {'read_only': True},
            'event': {'read_only': True},
        }

    def get_holder_name(self, obj):
        u = obj.holder
        ap = getattr(u, 'audience_profile', None)
        if ap and ap.display_name:
            return ap.display_name
        return u.get_full_name() or u.username

    def get_qr_payload(self, obj):
        # Only expose QR payload to the ticket holder
        request = self.context.get('request')
        if request and request.user == obj.holder and obj.payment_status == 'paid':
            return encode_qr_payload(str(obj.qr_token), obj.qr_signature)
        return None
