from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    """Bilateral review left after a Caftania rental.

    `direction` keeps two stable strings even when callers think in
    "cliente"/"loueuse" terms — the labels in the choices map to those words
    on the UI side. Each booking can have one review per reviewer (unique).
    Caftania-specific criteria (état, conformité aux photos, communication,
    ponctualité, soin) are stored as a JSON dict so the schema stays stable
    if we tune the rubric.
    """
    DIRECTION_CREATOR_TO_VENUE = 'creator_to_venue'    # cliente → loueuse
    DIRECTION_VENUE_TO_CREATOR = 'venue_to_creator'    # loueuse → cliente
    DIRECTION_CHOICES = [
        (DIRECTION_CREATOR_TO_VENUE, 'Cliente → Loueuse'),
        (DIRECTION_VENUE_TO_CREATOR, 'Loueuse → Cliente'),
    ]

    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_received')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    # Caftania-specific bilateral rubric.
    # cliente → loueuse:
    #   etat, conformite_photos, communication, ponctualite, accueil
    # loueuse → cliente:
    #   soin, ponctualite, communication, retour_etat, recommanderait
    # Each: int 1..5
    criteria = models.JSONField(default=dict, blank=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('booking', 'reviewer')]

    def __str__(self):
        return f"{self.reviewer.username} → {self.reviewee.username}: {self.rating}/5"
