from django.db import models


class HandoverReceipt(models.Model):
    """A double-signed receipt captured at delivery or return of a rental.

    Each rental produces up to 2 HandoverReceipt rows (delivery + return).
    Both parties confirm via SMS code; the timestamps + GPS + photos form
    the evidence bundle used by the condition-analysis pipeline and, if
    needed, dispute resolution.
    """
    MOMENT_CHOICES = [
        ('delivery', 'Delivery'),
        ('return', 'Return'),
    ]
    rental = models.ForeignKey(
        'bookings.Booking', on_delete=models.CASCADE, related_name='handover_receipts'
    )
    moment = models.CharField(max_length=20, choices=MOMENT_CHOICES)
    photo_urls = models.JSONField(default=list, blank=True)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    owner_confirmed_at = models.DateTimeField(null=True, blank=True)
    renter_confirmed_at = models.DateTimeField(null=True, blank=True)
    owner_sms_code = models.CharField(max_length=10, blank=True, default='')
    renter_sms_code = models.CharField(max_length=10, blank=True, default='')
    owner_sms_verified = models.BooleanField(default=False)
    renter_sms_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Handover {self.moment} for booking #{self.rental_id}'

    @property
    def both_verified(self):
        return self.owner_sms_verified and self.renter_sms_verified
