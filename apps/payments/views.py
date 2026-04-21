import stripe
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class StripeConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
            'currency': settings.STRIPE_CURRENCY,
            'platform_fee_venue_percent': getattr(settings, 'PLATFORM_FEE_VENUE_PERCENT', 8),
            'platform_fee_creator_percent': getattr(settings, 'PLATFORM_FEE_CREATOR_PERCENT', 12),
        })


# -----------------------------------------------------------------------------
# Stripe Connect — venue payouts
# -----------------------------------------------------------------------------

class StripeConnectStatusView(APIView):
    """GET /api/payments/connect/status/ — Venue's payout readiness snapshot."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, 'venue_profile', None)
        if profile is None:
            return Response({'detail': 'Not a venue account.'}, status=400)
        return Response({
            'has_account': bool(profile.stripe_account_id),
            'charges_enabled': profile.stripe_charges_enabled,
            'payouts_enabled': profile.stripe_payouts_enabled,
            'details_submitted': profile.stripe_details_submitted,
            'payouts_ready': profile.payouts_ready,
        })


class StripeConnectOnboardView(APIView):
    """POST /api/payments/connect/onboard/ — returns a hosted onboarding URL.

    Creates the connected account on first call, then always returns a fresh
    AccountLink (they expire after use, so we mint on demand)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .stripe_client import create_express_account, create_account_link

        profile = getattr(request.user, 'venue_profile', None)
        if profile is None:
            return Response({'detail': 'Not a venue account.'}, status=400)
        if not settings.STRIPE_SECRET_KEY:
            return Response({'detail': 'Stripe is not configured on the server.'}, status=503)

        if not profile.stripe_account_id:
            try:
                acct = create_express_account(
                    email=request.user.email,
                    country=(profile.country or 'US'),
                )
            except stripe.error.StripeError as e:
                return Response({'detail': str(e.user_message or e)}, status=400)
            profile.stripe_account_id = acct.id
            profile.save(update_fields=['stripe_account_id'])

        site = getattr(settings, 'FRONTEND_URL', '').rstrip('/') or 'https://cultureconnect-e4d4e201dfdb.herokuapp.com'
        try:
            link = create_account_link(
                account_id=profile.stripe_account_id,
                return_url=f'{site}/venue/settings/payouts?onboarded=1',
                refresh_url=f'{site}/venue/settings/payouts?refresh=1',
            )
        except stripe.error.StripeError as e:
            return Response({'detail': str(e.user_message or e)}, status=400)

        return Response({'url': link.url, 'expires_at': link.expires_at})


class StripeConnectRefreshView(APIView):
    """POST /api/payments/connect/refresh/ — re-pull latest account status from Stripe."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .stripe_client import retrieve_account

        profile = getattr(request.user, 'venue_profile', None)
        if profile is None or not profile.stripe_account_id:
            return Response({'detail': 'No connected account.'}, status=400)

        try:
            acct = retrieve_account(profile.stripe_account_id)
        except stripe.error.StripeError as e:
            return Response({'detail': str(e.user_message or e)}, status=400)

        profile.stripe_charges_enabled = bool(acct.charges_enabled)
        profile.stripe_payouts_enabled = bool(acct.payouts_enabled)
        profile.stripe_details_submitted = bool(acct.details_submitted)
        profile.save(update_fields=[
            'stripe_charges_enabled', 'stripe_payouts_enabled', 'stripe_details_submitted',
        ])
        return Response({
            'charges_enabled': profile.stripe_charges_enabled,
            'payouts_enabled': profile.stripe_payouts_enabled,
            'details_submitted': profile.stripe_details_submitted,
            'payouts_ready': profile.payouts_ready,
        })


class StripeConnectDashboardView(APIView):
    """POST /api/payments/connect/dashboard/ — one-off Express dashboard link."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .stripe_client import create_login_link
        profile = getattr(request.user, 'venue_profile', None)
        if profile is None or not profile.stripe_account_id:
            return Response({'detail': 'No connected account.'}, status=400)
        try:
            link = create_login_link(profile.stripe_account_id)
        except stripe.error.StripeError as e:
            return Response({'detail': str(e.user_message or e)}, status=400)
        return Response({'url': link.url})


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from apps.bookings.models import Booking, BookingEvent
        from apps.tickets.models import Ticket, TicketTier
        from .models import ProcessedStripeEvent
        from django.db import transaction

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                # Dev fallback: parse without signature verification
                import json
                event = json.loads(payload.decode('utf-8'))
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response({'error': 'Invalid signature'}, status=400)

        event_type = event.get('type') if isinstance(event, dict) else event['type']
        event_id = event.get('id') if isinstance(event, dict) else event['id']
        data_object = event['data']['object'] if isinstance(event, dict) else event['data']['object']
        pi_id = data_object.get('id')

        # Idempotency — skip if we've already processed this event
        if event_id:
            _, created = ProcessedStripeEvent.objects.get_or_create(
                event_id=event_id, defaults={'event_type': event_type or ''}
            )
            if not created:
                return Response({'received': True, 'duplicate': True})

        # Stripe Connect — sync account status when Stripe tells us it changed.
        if event_type == 'account.updated':
            from apps.accounts.models import VenueProfile
            acct_id = data_object.get('id')
            profile = VenueProfile.objects.filter(stripe_account_id=acct_id).first()
            if profile:
                profile.stripe_charges_enabled = bool(data_object.get('charges_enabled'))
                profile.stripe_payouts_enabled = bool(data_object.get('payouts_enabled'))
                profile.stripe_details_submitted = bool(data_object.get('details_submitted'))
                profile.save(update_fields=[
                    'stripe_charges_enabled', 'stripe_payouts_enabled', 'stripe_details_submitted',
                ])
            return Response({'received': True})

        # Route by metadata.kind — tickets use instant capture; bookings use manual capture
        metadata = data_object.get('metadata') or {}
        kind = metadata.get('kind')

        if kind == 'ticket':
            ticket = Ticket.objects.filter(stripe_payment_intent_id=pi_id).first()
            if not ticket:
                return Response({'received': True})
            if event_type == 'payment_intent.succeeded':
                if ticket.payment_status != 'paid':
                    ticket.payment_status = 'paid'
                    ticket.save(update_fields=['payment_status'])
            elif event_type in ('payment_intent.payment_failed', 'payment_intent.canceled'):
                if ticket.payment_status == 'pending':
                    ticket.payment_status = 'failed'
                    ticket.save(update_fields=['payment_status'])
                    # Release the seat
                    with transaction.atomic():
                        tier = TicketTier.objects.select_for_update().filter(pk=ticket.tier_id).first()
                        if tier:
                            tier.sold = max(0, tier.sold - 1)
                            tier.save(update_fields=['sold'])
            return Response({'received': True})

        try:
            booking = Booking.objects.get(stripe_payment_intent_id=pi_id)
        except Booking.DoesNotExist:
            return Response({'received': True})

        if event_type == 'payment_intent.amount_capturable_updated':
            if booking.payment_status != 'captured':
                booking.payment_status = 'authorized'
                booking.save(update_fields=['payment_status'])
                BookingEvent.objects.create(booking=booking, event_type='payment_authorized')
        elif event_type == 'payment_intent.succeeded':
            if booking.payment_status != 'captured':
                booking.payment_status = 'captured'
                booking.save(update_fields=['payment_status'])
                BookingEvent.objects.create(booking=booking, event_type='payment_captured')
        elif event_type == 'payment_intent.canceled':
            if booking.payment_status != 'voided':
                booking.payment_status = 'voided'
                booking.save(update_fields=['payment_status'])
                BookingEvent.objects.create(booking=booking, event_type='payment_voided')
        elif event_type == 'payment_intent.payment_failed':
            booking.payment_status = 'failed'
            booking.save(update_fields=['payment_status'])
            BookingEvent.objects.create(booking=booking, event_type='payment_failed')

        return Response({'received': True})
