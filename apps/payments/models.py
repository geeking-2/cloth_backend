from django.db import models


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('booking_payment', 'Booking Payment'),
        ('platform_fee', 'Platform Fee'),
        ('featured_listing', 'Featured Listing'),
        ('refund', 'Refund'),
    ]
    booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions'
    )
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ProcessedStripeEvent(models.Model):
    """Idempotency guard for Stripe webhook events — prevents double-processing."""
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class FeaturedListing(models.Model):
    space = models.ForeignKey('spaces.Space', on_delete=models.CASCADE, null=True, blank=True)
    creator = models.ForeignKey('accounts.CreatorProfile', on_delete=models.CASCADE, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
