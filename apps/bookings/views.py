from decimal import Decimal
from datetime import date
import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, BookingEvent
from .serializers import BookingSerializer, BookingCreateSerializer, BookingEventSerializer
from .emails import (
    send_booking_request_email, send_booking_accepted_email,
    send_booking_rejected_email, send_booking_cancelled_email,
)
from apps.payments.stripe_client import (
    create_payment_intent, capture_payment_intent,
    cancel_payment_intent, retrieve_payment_intent,
    create_destination_payment_intent,
)


class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.select_related(
            'space', 'space__venue', 'space__venue__user', 'creator', 'creator__user'
        ).prefetch_related('space__images', 'events')
        if user.role == 'creator':
            return qs.filter(creator=user.creator_profile)
        elif user.role == 'venue':
            return qs.filter(space__venue=user.venue_profile)
        return qs.none()

    def get_serializer_class(self):
        return BookingCreateSerializer if self.request.method == 'POST' else BookingSerializer

    def create(self, request, *args, **kwargs):
        from apps.spaces.models import Space
        user = request.user

        if user.role != 'creator':
            return Response({'error': 'Only creators can book spaces.'}, status=403)

        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        space_id = serializer.validated_data['space'].id
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']

        if start_date >= end_date:
            return Response({'error': 'End date must be after start date.'}, status=400)
        if start_date < date.today():
            return Response({'error': 'Start date cannot be in the past.'}, status=400)

        with transaction.atomic():
            space = Space.objects.select_for_update().get(id=space_id)

            overlap = Booking.objects.filter(
                space=space,
                status__in=['pending', 'accepted', 'confirmed', 'in_progress'],
            ).filter(
                Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
            ).exists()
            if overlap:
                return Response({'error': 'These dates overlap with an existing booking.'}, status=409)

            nights = (end_date - start_date).days
            if nights <= 0:
                nights = 1

            daily = Decimal(str(space.daily_rate or 0))
            weekly = Decimal(str(space.weekly_rate or 0))
            monthly = Decimal(str(space.monthly_rate or 0))

            if nights >= 28 and monthly > 0:
                total = monthly * Decimal(nights) / Decimal(30)
            elif nights >= 7 and weekly > 0:
                total = weekly * Decimal(nights) / Decimal(7)
            else:
                total = daily * Decimal(nights)

            total = total.quantize(Decimal('0.01'))
            fee_venue = (total * Decimal(settings.PLATFORM_FEE_VENUE_PERCENT) / Decimal(100)).quantize(Decimal('0.01'))
            fee_creator = (total * Decimal(settings.PLATFORM_FEE_CREATOR_PERCENT) / Decimal(100)).quantize(Decimal('0.01'))

            booking = Booking.objects.create(
                space=space,
                creator=user.creator_profile,
                start_date=start_date,
                end_date=end_date,
                total_amount=total,
                platform_fee_venue=fee_venue,
                platform_fee_creator=fee_creator,
                booking_type='direct',
                status='pending',
                payment_status='unpaid',
            )

            if settings.STRIPE_SECRET_KEY:
                try:
                    amount_cents = int(total * 100)
                    pi_metadata = {
                        'booking_id': str(booking.id),
                        'space_id': str(space.id),
                        'creator_id': str(user.creator_profile.id),
                    }
                    pi_currency = (space.currency or settings.STRIPE_CURRENCY).lower()

                    # If the venue has completed Stripe Connect onboarding,
                    # route the payment as a destination charge so payouts
                    # land in their account minus the platform fee.
                    venue_profile = space.venue  # VenueProfile FK
                    if getattr(venue_profile, 'payouts_ready', False):
                        platform_fee_cents = int((fee_venue + fee_creator) * 100)
                        intent = create_destination_payment_intent(
                            amount_cents=amount_cents,
                            destination_account_id=venue_profile.stripe_account_id,
                            application_fee_cents=platform_fee_cents,
                            currency=pi_currency,
                            metadata={**pi_metadata, 'venue_connect': venue_profile.stripe_account_id},
                            idempotency_key=f'booking-{booking.id}-create-pi',
                        )
                    else:
                        intent = create_payment_intent(
                            amount_cents=amount_cents,
                            currency=pi_currency,
                            metadata=pi_metadata,
                            idempotency_key=f'booking-{booking.id}-create-pi',
                        )
                    booking.stripe_payment_intent_id = intent.id
                    booking.stripe_client_secret = intent.client_secret
                    booking.save(update_fields=['stripe_payment_intent_id', 'stripe_client_secret'])
                except stripe.error.StripeError as e:
                    booking.delete()
                    return Response({'error': f'Payment setup failed: {str(e)}'}, status=402)

            BookingEvent.objects.create(
                booking=booking, event_type='created', actor=user,
                note=f'Direct booking created for {space.title}',
            )

            try:
                send_booking_request_email(booking)
            except Exception:
                pass

        data = BookingSerializer(booking, context={'request': request}).data
        return Response(data, status=201)


class BookingDetailView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.select_related(
            'space', 'space__venue', 'creator', 'creator__user'
        ).prefetch_related('events')
        if user.role == 'creator':
            return qs.filter(creator=user.creator_profile)
        return qs.filter(space__venue=user.venue_profile)


class BookingAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.select_related('space__venue').get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        if request.user.role != 'venue' or booking.space.venue.user_id != request.user.id:
            return Response({'error': 'Not authorized'}, status=403)
        if booking.status != 'pending':
            return Response({'error': f'Cannot accept a {booking.status} booking'}, status=400)

        if booking.stripe_payment_intent_id and settings.STRIPE_SECRET_KEY:
            try:
                capture_payment_intent(
                    booking.stripe_payment_intent_id,
                    idempotency_key=f'booking-{booking.id}-capture',
                )
                booking.payment_status = 'captured'
            except stripe.error.StripeError as e:
                return Response({'error': f'Payment capture failed: {str(e)}'}, status=402)

        booking.status = 'confirmed'
        booking.responded_at = timezone.now()
        booking.save()

        BookingEvent.objects.create(booking=booking, event_type='accepted', actor=request.user)
        if booking.payment_status == 'captured':
            BookingEvent.objects.create(booking=booking, event_type='payment_captured')

        try:
            send_booking_accepted_email(booking)
        except Exception:
            pass

        return Response(BookingSerializer(booking, context={'request': request}).data)


class BookingRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.select_related('space__venue').get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        if request.user.role != 'venue' or booking.space.venue.user_id != request.user.id:
            return Response({'error': 'Not authorized'}, status=403)
        if booking.status != 'pending':
            return Response({'error': f'Cannot reject a {booking.status} booking'}, status=400)

        reason = request.data.get('reason', '')

        if booking.stripe_payment_intent_id and settings.STRIPE_SECRET_KEY:
            try:
                cancel_payment_intent(booking.stripe_payment_intent_id)
                booking.payment_status = 'voided'
            except stripe.error.StripeError:
                pass

        booking.status = 'rejected'
        booking.rejection_reason = reason
        booking.responded_at = timezone.now()
        booking.save()

        BookingEvent.objects.create(
            booking=booking, event_type='rejected', actor=request.user, note=reason,
        )
        if booking.payment_status == 'voided':
            BookingEvent.objects.create(booking=booking, event_type='payment_voided')

        try:
            send_booking_rejected_email(booking)
        except Exception:
            pass

        return Response(BookingSerializer(booking, context={'request': request}).data)


class BookingCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        if request.user.role != 'creator' or booking.creator.user_id != request.user.id:
            return Response({'error': 'Not authorized'}, status=403)
        if booking.status != 'pending':
            return Response({'error': 'Can only cancel pending bookings'}, status=400)

        if booking.stripe_payment_intent_id and settings.STRIPE_SECRET_KEY:
            try:
                cancel_payment_intent(booking.stripe_payment_intent_id)
                booking.payment_status = 'voided'
            except stripe.error.StripeError:
                pass

        booking.status = 'cancelled'
        booking.save()
        BookingEvent.objects.create(booking=booking, event_type='cancelled', actor=request.user)

        try:
            send_booking_cancelled_email(booking)
        except Exception:
            pass

        return Response(BookingSerializer(booking, context={'request': request}).data)


class PaymentConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        if booking.creator.user_id != request.user.id:
            return Response({'error': 'Not authorized'}, status=403)

        if booking.stripe_payment_intent_id and settings.STRIPE_SECRET_KEY:
            try:
                intent = retrieve_payment_intent(booking.stripe_payment_intent_id)
                if intent.status == 'requires_capture':
                    booking.payment_status = 'authorized'
                    booking.save(update_fields=['payment_status'])
                    BookingEvent.objects.create(booking=booking, event_type='payment_authorized')
            except stripe.error.StripeError:
                pass

        return Response(BookingSerializer(booking, context={'request': request}).data)


class BookingEventListView(generics.ListAPIView):
    serializer_class = BookingEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BookingEvent.objects.filter(booking_id=self.kwargs['pk']).order_by('created_at')
