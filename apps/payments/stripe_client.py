import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(amount_cents, currency='usd', metadata=None, idempotency_key=None):
    """Create a PaymentIntent with manual capture (authorize on book, capture on accept)."""
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        capture_method='manual',
        automatic_payment_methods={'enabled': True},
        metadata=metadata or {},
        idempotency_key=idempotency_key,
    )


def create_instant_payment_intent(amount_cents, currency='usd', metadata=None, idempotency_key=None):
    """Create a PaymentIntent that auto-captures on confirm (used for tickets)."""
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        automatic_payment_methods={'enabled': True},
        metadata=metadata or {},
        idempotency_key=idempotency_key,
    )


def refund_payment_intent(pi_id, amount_cents=None, reason='requested_by_customer'):
    """Create a refund for a captured payment intent."""
    kwargs = {'payment_intent': pi_id, 'reason': reason}
    if amount_cents is not None:
        kwargs['amount'] = amount_cents
    return stripe.Refund.create(**kwargs)


def capture_payment_intent(pi_id, idempotency_key=None):
    """Capture an authorized payment intent."""
    return stripe.PaymentIntent.capture(pi_id, idempotency_key=idempotency_key)


def cancel_payment_intent(pi_id, reason='requested_by_customer'):
    """Cancel (void) a payment intent."""
    return stripe.PaymentIntent.cancel(pi_id, cancellation_reason=reason)


def retrieve_payment_intent(pi_id):
    return stripe.PaymentIntent.retrieve(pi_id)


# -----------------------------------------------------------------------------
# Stripe Connect (Express) — venues receive payouts; platform takes a fee.
# -----------------------------------------------------------------------------

def create_express_account(email, country='US'):
    """Create an Express connected account for a venue."""
    return stripe.Account.create(
        type='express',
        email=email,
        country=country,
        capabilities={
            'card_payments': {'requested': True},
            'transfers': {'requested': True},
        },
    )


def create_account_link(account_id, return_url, refresh_url):
    """Onboarding/refresh link the venue clicks through to complete KYC."""
    return stripe.AccountLink.create(
        account=account_id,
        return_url=return_url,
        refresh_url=refresh_url,
        type='account_onboarding',
    )


def create_login_link(account_id):
    """Dashboard link (post-onboarding) so the venue can see payouts."""
    return stripe.Account.create_login_link(account_id)


def retrieve_account(account_id):
    return stripe.Account.retrieve(account_id)


def create_destination_payment_intent(
    amount_cents, destination_account_id, application_fee_cents,
    currency='usd', metadata=None, idempotency_key=None, capture_method='manual',
):
    """Create a PaymentIntent that settles to the venue's Stripe account.

    Uses destination charges: funds hit the platform briefly, then Stripe
    transfers (amount - application_fee) to the connected account.
    """
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        capture_method=capture_method,
        automatic_payment_methods={'enabled': True},
        application_fee_amount=application_fee_cents,
        transfer_data={'destination': destination_account_id},
        metadata=metadata or {},
        idempotency_key=idempotency_key,
    )
