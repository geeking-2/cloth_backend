from django.db import models


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('refunded', 'Refunded'),
        ('voided', 'Voided'),
        ('failed', 'Failed'),
    ]
    BOOKING_TYPE_CHOICES = [
        ('proposal', 'From Proposal'),
        ('direct', 'Direct Booking'),
    ]

    proposal = models.OneToOneField(
        'proposals.Proposal', on_delete=models.SET_NULL, null=True, blank=True, related_name='booking'
    )
    space = models.ForeignKey('spaces.Space', on_delete=models.CASCADE, related_name='bookings')
    creator = models.ForeignKey(
        'accounts.CreatorProfile', on_delete=models.CASCADE, related_name='bookings'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee_venue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee_creator = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Direct booking + Stripe fields
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='proposal')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default='')
    stripe_client_secret = models.CharField(max_length=255, blank=True, default='')
    rejection_reason = models.TextField(blank=True, default='')
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking: {self.space.title} by {self.creator.display_name}"


class BookingEvent(models.Model):
    EVENT_TYPES = [
        ('created', 'Created'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('payment_authorized', 'Payment Authorized'),
        ('payment_captured', 'Payment Captured'),
        ('payment_voided', 'Payment Voided'),
        ('payment_failed', 'Payment Failed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    actor = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.booking_id}: {self.event_type}"
