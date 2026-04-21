import uuid
from django.db import models


class TicketTier(models.Model):
    """A purchasable ticket tier on an event (e.g. "General $20", "VIP $50")."""
    event = models.ForeignKey(
        'events.Event', on_delete=models.CASCADE, related_name='ticket_tiers'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    price_cents = models.PositiveIntegerField(help_text='Price in smallest currency unit (cents)')
    currency = models.CharField(max_length=3, default='USD')
    quantity = models.PositiveIntegerField(help_text='Total tickets available at this tier')
    sold = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price_cents']
        indexes = [models.Index(fields=['event', 'is_active'])]

    @property
    def remaining(self):
        return max(0, self.quantity - self.sold)

    @property
    def is_sold_out(self):
        return self.sold >= self.quantity

    def __str__(self):
        return f'{self.event.title} — {self.name} ({self.price_cents}¢)'


class Ticket(models.Model):
    """A single purchased ticket. One row per seat."""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]

    event = models.ForeignKey(
        'events.Event', on_delete=models.CASCADE, related_name='tickets'
    )
    tier = models.ForeignKey(
        TicketTier, on_delete=models.PROTECT, related_name='tickets'
    )
    holder = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='tickets'
    )
    # Money snapshot at purchase time
    price_cents = models.PositiveIntegerField()
    platform_fee_cents = models.PositiveIntegerField(default=0)
    incognito_fee_cents = models.PositiveIntegerField(default=0)
    total_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='USD')
    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    stripe_client_secret = models.CharField(max_length=255, blank=True, default='')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    # QR / check-in
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_signature = models.CharField(max_length=128, blank=True, default='')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_scanned'
    )
    # Privacy
    is_incognito = models.BooleanField(default=False)
    # Refund
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', 'payment_status']),
            models.Index(fields=['holder', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.qr_signature and self.qr_token:
            from .qr import sign
            self.qr_signature = sign(str(self.qr_token))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Ticket #{self.pk} — {self.event.title} — {self.holder.username}'


class TicketWaitlist(models.Model):
    """A user signed up to be notified when a sold-out tier has inventory again."""
    tier = models.ForeignKey(TicketTier, on_delete=models.CASCADE, related_name='waitlist_entries')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='waitlists')
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('tier', 'user')]
        ordering = ['created_at']
        indexes = [models.Index(fields=['tier', 'created_at'])]

    def __str__(self):
        return f'Waitlist: {self.user.username} → {self.tier}'
