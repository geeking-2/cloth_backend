import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import HandoverReceipt
from .serializers import HandoverReceiptSerializer


def _gen_sms_code():
    return f'{random.randint(0, 999999):06d}'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def open_handover(request):
    """Open a new handover receipt for a booking.

    Body: { rental: <booking_id>, moment: delivery|return,
            photo_urls: [...], gps_lat: ..., gps_lng: ... }
    """
    serializer = HandoverReceiptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    receipt = serializer.save()
    return Response(HandoverReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_sms(request, pk):
    """Issue SMS codes for both owner and renter.

    In production this would trigger Twilio / a provider. Here we just
    generate and persist the codes so the UI can render a verify flow.
    """
    receipt = get_object_or_404(HandoverReceipt, pk=pk)
    receipt.owner_sms_code = _gen_sms_code()
    receipt.renter_sms_code = _gen_sms_code()
    receipt.save(update_fields=['owner_sms_code', 'renter_sms_code', 'updated_at'])
    return Response({'detail': 'sms codes generated', 'sent': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_sms(request, pk):
    """Verify a party's SMS code.

    Body: { party: owner|renter, code: <6 digits> }
    """
    receipt = get_object_or_404(HandoverReceipt, pk=pk)
    party = request.data.get('party')
    code = str(request.data.get('code', '')).strip()

    if party == 'owner':
        if code and code == receipt.owner_sms_code:
            receipt.owner_sms_verified = True
            receipt.owner_confirmed_at = timezone.now()
            receipt.save()
            return Response(HandoverReceiptSerializer(receipt).data)
        return Response({'detail': 'invalid code'}, status=status.HTTP_400_BAD_REQUEST)
    if party == 'renter':
        if code and code == receipt.renter_sms_code:
            receipt.renter_sms_verified = True
            receipt.renter_confirmed_at = timezone.now()
            receipt.save()
            return Response(HandoverReceiptSerializer(receipt).data)
        return Response({'detail': 'invalid code'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': 'party must be owner|renter'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_handover(request, pk):
    receipt = get_object_or_404(HandoverReceipt, pk=pk)
    return Response(HandoverReceiptSerializer(receipt).data)
