from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    """
    A review left by one party about the other after a booking completes.
    Both sides (creator and venue) can review each other — so one booking
    can have up to two Reviews, one per reviewer.
    """
    DIRECTION_CREATOR_TO_VENUE = 'creator_to_venue'
    DIRECTION_VENUE_TO_CREATOR = 'venue_to_creator'
    DIRECTION_CHOICES = [
        (DIRECTION_CREATOR_TO_VENUE, 'Creator → Venue'),
        (DIRECTION_VENUE_TO_CREATOR, 'Venue → Creator'),
    ]

    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_received')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('booking', 'reviewer')]

    def __str__(self):
        return f"{self.reviewer.username} → {self.reviewee.username}: {self.rating}/5"
