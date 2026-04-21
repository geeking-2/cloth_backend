from django.db import models
from django.utils.text import slugify
import uuid


class Space(models.Model):
    SPACE_TYPES = [
        ('gallery_room', 'Gallery Room'),
        ('main_hall', 'Main Hall'),
        ('outdoor', 'Outdoor Space'),
        ('theater', 'Theater/Auditorium'),
        ('lobby', 'Lobby/Foyer'),
        ('studio', 'Studio Space'),
        ('entire_venue', 'Entire Venue'),
        ('other', 'Other'),
    ]
    # Caftania taxonomy — a `Space` now represents a garment (caftan, takchita, …)
    CATEGORY_CHOICES = [
        ('caftan', 'Caftan'),
        ('takchita', 'Takchita'),
        ('jabador', 'Jabador'),
        ('jellaba', 'Jellaba'),
        ('gandoura', 'Gandoura'),
        ('accessoire', 'Accessoire'),
    ]
    marketplace = models.ForeignKey(
        'core.Marketplace', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='spaces',
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True, default='')
    size = models.CharField(max_length=20, blank=True, default='')
    color = models.CharField(max_length=40, blank=True, default='')
    brand = models.CharField(max_length=120, blank=True, default='')
    occasion_tags = models.JSONField(default=list, blank=True)
    available_for_rent = models.BooleanField(default=True)
    available_for_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rental_count = models.PositiveIntegerField(default=0)
    qr_code = models.CharField(max_length=64, unique=True, null=True, blank=True)
    venue = models.ForeignKey(
        'accounts.VenueProfile', on_delete=models.CASCADE, related_name='spaces'
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    space_type = models.CharField(max_length=20, choices=SPACE_TYPES, default='gallery_room')
    # Physical specs
    area_sqft = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    ceiling_height_ft = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    max_capacity = models.PositiveIntegerField(null=True, blank=True)
    # Technical specs
    has_wifi = models.BooleanField(default=True)
    has_power_outlets = models.BooleanField(default=True)
    has_projection_surfaces = models.BooleanField(default=False)
    has_sound_system = models.BooleanField(default=False)
    has_blackout_capability = models.BooleanField(default=False)
    has_climate_control = models.BooleanField(default=True)
    technical_notes = models.TextField(blank=True, default='')
    # Pricing
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weekly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True)
    # Extended features (LoopNet-style)
    features = models.JSONField(default=dict, blank=True)  # {"Access": ["24hr Access", ...], "Technical": [...]}
    floor_plan_url = models.URLField(blank=True, default='')
    video_url = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            self.slug = f"{base}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img.image_url if img else ''

    def get_rating(self):
        from apps.reviews.models import Review
        reviews = Review.objects.filter(booking__space=self)
        if not reviews.exists():
            return 0
        return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)

    def get_review_count(self):
        from apps.reviews.models import Review
        return Review.objects.filter(booking__space=self).count()


class SpaceImage(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='images')
    image_url = models.TextField()  # Supports both URLs and base64 data URLs
    caption = models.CharField(max_length=255, blank=True, default='')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.space.title}"


class Availability(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='availabilities')
    start_date = models.DateField()
    end_date = models.DateField()
    is_available = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['start_date']
        verbose_name_plural = 'Availabilities'

    def __str__(self):
        status = "Available" if self.is_available else "Blocked"
        return f"{self.space.title}: {status} {self.start_date} - {self.end_date}"


class SpaceAttachment(models.Model):
    ATTACHMENT_TYPES = [
        ('floor_plan', 'Floor Plan'),
        ('spec_sheet', 'Spec Sheet'),
        ('brochure', 'Brochure'),
        ('contract', 'Contract Template'),
        ('other', 'Other'),
    ]
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='attachments')
    title = models.CharField(max_length=255)
    file_url = models.URLField()
    file_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"


class SavedSpace(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='saved_spaces')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'space']
