from rest_framework import serializers
from .models import HandoverReceipt


class HandoverReceiptSerializer(serializers.ModelSerializer):
    both_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = HandoverReceipt
        fields = [
            'id', 'rental', 'moment', 'photo_urls', 'gps_lat', 'gps_lng',
            'owner_confirmed_at', 'renter_confirmed_at',
            'owner_sms_verified', 'renter_sms_verified',
            'both_verified', 'created_at', 'updated_at',
        ]
        read_only_fields = (
            'owner_confirmed_at', 'renter_confirmed_at',
            'owner_sms_verified', 'renter_sms_verified',
            'created_at', 'updated_at',
        )
