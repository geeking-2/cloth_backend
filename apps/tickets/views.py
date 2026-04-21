import uuid
import stripe
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import Event
from apps.payments.stripe_client import (
    create_instant_payment_intent,
    retrieve_payment_intent,
    refund_payment_intent,
)
from .models import Ticket, TicketTier
from .qr import decode_qr_payload, verify
from .serializers import TicketSerializer, TicketTierSerializer


PLATFORM_FEE_PERCENT = 6  # 6% marketplace fee on ticket price
REFUND_CUTOFF_HOURS = 24  # users can self-refund up to 24h before event


# ----- Ticket tier management (host only) -----

class TicketTierListCreateView(generics.ListCreateAPIView):
    """GET /events/<slug>/tiers/  — public list of active tiers for an event
       POST — host creates a new tier"""
    serializer_class = TicketTierSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def _get_event(self):
        return get_object_or_404(Event, slug=self.kwargs['slug'])

    def get_queryset(self):
        event = self._get_event()
        qs = TicketTier.objects.filter(event=event)
        if not (self.request.user.is_authenticated and self.request.user == event.host):
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        event = self._get_event()
        if self.request.user != event.host:
            raise PermissionDenied('Only the event host can create ticket tiers.')
        serializer.save(event=event)


class TicketTierDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TicketTierSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = TicketTier.objects.all()

    def get_object(self):
        obj = super().get_object()
        if self.request.method in ('PATCH', 'PUT', 'DELETE') and self.request.user != obj.event.host:
            raise PermissionDenied('Only the event host can modify ticket tiers.')
        return obj

    def perform_destroy(self, instance):
        if instance.sold > 0:
            # Don't hard-delete tiers that already have tickets sold — just deactivate
            instance.is_active = False
            instance.save(update_fields=['is_active'])
        else:
            instance.delete()


# ----- Ticket purchase -----

class TicketPurchaseView(APIView):
    """POST /events/<slug>/purchase/
       Body: {tier_id, incognito: bool}
       Creates a pending Ticket + Stripe PaymentIntent. Returns client_secret."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        tier_id = request.data.get('tier_id')
        want_incognito = bool(request.data.get('incognito'))

        if not tier_id:
            raise ValidationError({'tier_id': 'Required.'})

        # Age check via audience profile DOB
        if event.age_restriction:
            ap = getattr(request.user, 'audience_profile', None)
            if not ap or not ap.date_of_birth or (ap.age or 0) < int(event.age_restriction.rstrip('+')):
                raise ValidationError({'detail': f'This event requires age {event.age_restriction}.'})

        with transaction.atomic():
            tier = TicketTier.objects.select_for_update().filter(
                id=tier_id, event=event, is_active=True
            ).first()
            if not tier:
                raise ValidationError({'detail': 'Tier not found or inactive.'})
            if tier.is_sold_out:
                return Response({'detail': 'Sold out.'}, status=status.HTTP_409_CONFLICT)

            # Capacity check across all tiers
            if event.max_capacity:
                paid_count = Ticket.objects.filter(
                    event=event, payment_status__in=['paid', 'pending']
                ).count()
                if paid_count >= event.max_capacity:
                    return Response({'detail': 'Event at capacity.'}, status=status.HTTP_409_CONFLICT)

            # Money
            base = tier.price_cents
            incog_fee = event.incognito_fee_cents if want_incognito else 0
            platform_fee = int(round((base + incog_fee) * PLATFORM_FEE_PERCENT / 100))
            total = base + incog_fee + platform_fee
            currency = (tier.currency or 'USD').lower()

            ticket = Ticket.objects.create(
                event=event,
                tier=tier,
                holder=request.user,
                price_cents=base,
                platform_fee_cents=platform_fee,
                incognito_fee_cents=incog_fee,
                total_cents=total,
                currency=tier.currency or 'USD',
                is_incognito=want_incognito,
                payment_status='pending',
            )
            # Reserve the seat
            tier.sold = tier.sold + 1
            tier.save(update_fields=['sold'])

        # Stripe PI (outside the tx — idempotency key on ticket id)
        if settings.STRIPE_SECRET_KEY:
            try:
                intent = create_instant_payment_intent(
                    amount_cents=total,
                    currency=currency,
                    metadata={
                        'ticket_id': str(ticket.id),
                        'event_id': str(event.id),
                        'event_slug': event.slug,
                        'holder_id': str(request.user.id),
                        'kind': 'ticket',
                    },
                    idempotency_key=f'ticket-{ticket.id}',
                )
                ticket.stripe_payment_intent_id = intent.id
                ticket.stripe_client_secret = intent.client_secret
                ticket.save(update_fields=['stripe_payment_intent_id', 'stripe_client_secret'])
            except stripe.error.StripeError as e:
                # Roll back the hold
                with transaction.atomic():
                    tier.refresh_from_db()
                    tier.sold = max(0, tier.sold - 1)
                    tier.save(update_fields=['sold'])
                    ticket.payment_status = 'failed'
                    ticket.save(update_fields=['payment_status'])
                return Response({'detail': str(e)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        return Response(
            TicketSerializer(ticket, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class TicketConfirmView(APIView):
    """POST /tickets/<id>/confirm/  — called by frontend after Stripe client confirm.
       Verifies PI.status == 'succeeded' and promotes ticket to 'paid'."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, holder=request.user)
        if ticket.payment_status == 'paid':
            return Response(TicketSerializer(ticket, context={'request': request}).data)

        if not ticket.stripe_payment_intent_id or not settings.STRIPE_SECRET_KEY:
            return Response({'detail': 'No payment intent.'}, status=400)

        try:
            intent = retrieve_payment_intent(ticket.stripe_payment_intent_id)
        except stripe.error.StripeError as e:
            return Response({'detail': str(e)}, status=400)

        if intent.status == 'succeeded':
            ticket.payment_status = 'paid'
            ticket.save(update_fields=['payment_status'])
            try:
                from apps.accounts.notifications import notify
                buyer_name = (request.user.first_name + ' ' + request.user.last_name).strip() or request.user.username
                notify(
                    user=ticket.event.host, kind='ticket_sold', actor=request.user,
                    title=f'{buyer_name} bought a {ticket.tier.name} ticket to {ticket.event.title}',
                    url=f'/events/{ticket.event.slug}',
                )
            except Exception:
                pass
        elif intent.status in ('requires_payment_method', 'canceled'):
            ticket.payment_status = 'failed'
            ticket.save(update_fields=['payment_status'])
        return Response(TicketSerializer(ticket, context={'request': request}).data)


# ----- Ticket read / list -----

class MyTicketsView(generics.ListAPIView):
    """GET /tickets/  — current user's tickets"""
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.filter(holder=self.request.user).select_related('event', 'tier')


class TicketDetailView(generics.RetrieveAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.select_related('event', 'tier')

    def get_object(self):
        obj = super().get_object()
        # Only the holder or the event host can see a ticket
        if self.request.user != obj.holder and self.request.user != obj.event.host:
            raise PermissionDenied()
        return obj


# ----- Refunds -----

class TicketRefundView(APIView):
    """POST /tickets/<id>/refund/  — holder requests refund, allowed until 24h before event."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if request.user != ticket.holder:
            raise PermissionDenied()
        if ticket.payment_status != 'paid':
            return Response({'detail': 'Ticket is not paid.'}, status=400)
        if ticket.refunded_at:
            return Response({'detail': 'Already refunded.'}, status=400)

        hours_to_event = (ticket.event.starts_at - timezone.now()).total_seconds() / 3600
        if hours_to_event < REFUND_CUTOFF_HOURS:
            return Response(
                {'detail': f'Refunds only allowed up to {REFUND_CUTOFF_HOURS}h before the event.'},
                status=400,
            )

        if settings.STRIPE_SECRET_KEY and ticket.stripe_payment_intent_id:
            try:
                refund_payment_intent(ticket.stripe_payment_intent_id)
            except stripe.error.StripeError as e:
                return Response({'detail': str(e)}, status=400)

        with transaction.atomic():
            ticket.payment_status = 'refunded'
            ticket.refunded_at = timezone.now()
            ticket.refund_reason = request.data.get('reason', '')[:500]
            ticket.save(update_fields=['payment_status', 'refunded_at', 'refund_reason'])
            # Release the seat
            tier = TicketTier.objects.select_for_update().get(pk=ticket.tier_id)
            tier.sold = max(0, tier.sold - 1)
            tier.save(update_fields=['sold'])

        # Notify the first person on waitlist that a seat freed up
        try:
            from .models import TicketWaitlist
            from apps.accounts.notifications import notify
            next_entry = TicketWaitlist.objects.filter(
                tier=tier, notified_at__isnull=True
            ).order_by('created_at').first()
            if next_entry:
                notify(
                    user=next_entry.user, kind='waitlist', actor=None,
                    title=f'A {tier.name} ticket opened up for {tier.event.title}',
                    body='Grab it before someone else does.',
                    url=f'/events/{tier.event.slug}',
                )
                next_entry.notified_at = timezone.now()
                next_entry.save(update_fields=['notified_at'])
        except Exception:
            pass
        return Response(TicketSerializer(ticket, context={'request': request}).data)


# ----- Check-in (scanner) -----

class TicketCheckInView(APIView):
    """POST /events/<slug>/check-in/   Body: {payload}  (scanner app posts QR payload)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        if request.user != event.host:
            raise PermissionDenied('Only the event host can check people in.')

        payload = request.data.get('payload', '')
        try:
            token, sig = decode_qr_payload(payload)
        except ValueError:
            return Response({'detail': 'Malformed QR.', 'ok': False}, status=400)

        if not verify(token, sig):
            return Response({'detail': 'Invalid signature.', 'ok': False}, status=400)

        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return Response({'detail': 'Malformed token.', 'ok': False}, status=400)

        ticket = Ticket.objects.filter(qr_token=token_uuid, event=event).first()
        if not ticket:
            return Response({'detail': 'Ticket not found for this event.', 'ok': False}, status=404)
        if ticket.payment_status != 'paid':
            return Response({'detail': 'Ticket not paid.', 'ok': False, 'status': ticket.payment_status}, status=400)

        already = ticket.checked_in_at is not None
        if not already:
            ticket.checked_in_at = timezone.now()
            ticket.checked_in_by = request.user
            ticket.save(update_fields=['checked_in_at', 'checked_in_by'])

        return Response({
            'ok': True,
            'already_checked_in': already,
            'holder_name': ticket.holder.get_full_name() or ticket.holder.username,
            'tier_name': ticket.tier.name,
            'checked_in_at': ticket.checked_in_at,
        })


# ----- Waitlist -----

class TierWaitlistView(APIView):
    """POST /ticket-tiers/<pk>/waitlist/  — join waitlist
       DELETE /ticket-tiers/<pk>/waitlist/  — leave
       GET   /ticket-tiers/<pk>/waitlist/  — my position + total size
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_tier(self, pk):
        return get_object_or_404(TicketTier.objects.select_related('event'), pk=pk)

    def get(self, request, pk):
        from .models import TicketWaitlist
        tier = self._get_tier(pk)
        total = TicketWaitlist.objects.filter(tier=tier).count()
        entry = TicketWaitlist.objects.filter(tier=tier, user=request.user).first()
        position = None
        if entry:
            position = TicketWaitlist.objects.filter(
                tier=tier, created_at__lte=entry.created_at
            ).count()
        return Response({
            'on_waitlist': entry is not None,
            'position': position,
            'total': total,
        })

    def post(self, request, pk):
        from .models import TicketWaitlist
        tier = self._get_tier(pk)
        if not tier.is_sold_out:
            return Response({'detail': 'Tier still has inventory.'}, status=400)
        entry, created = TicketWaitlist.objects.get_or_create(tier=tier, user=request.user)
        total = TicketWaitlist.objects.filter(tier=tier).count()
        position = TicketWaitlist.objects.filter(tier=tier, created_at__lte=entry.created_at).count()
        if created:
            try:
                from apps.accounts.notifications import notify
                notify(
                    user=request.user, kind='waitlist', actor=None,
                    title=f"You're on the waitlist for {tier.event.title}",
                    body=f'Tier: {tier.name} · position {position}',
                    url=f'/events/{tier.event.slug}',
                )
            except Exception:
                pass
        return Response({'on_waitlist': True, 'position': position, 'total': total, 'created': created})

    def delete(self, request, pk):
        from .models import TicketWaitlist
        tier = self._get_tier(pk)
        TicketWaitlist.objects.filter(tier=tier, user=request.user).delete()
        return Response({'on_waitlist': False})
