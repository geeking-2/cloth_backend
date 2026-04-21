import uuid
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [('venue', 'Venue'), ('creator', 'Creator'), ('audience', 'Audience')]
    DISPLAY_MODE_CHOICES = [
        ('real', 'Real name'),
        ('pseudo', 'Pseudonym'),
        ('anonymous', 'Anonymous'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    avatar = models.URLField(blank=True, default='')
    bio = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    website = models.URLField(blank=True, default='')
    is_verified = models.BooleanField(default=False)
    # Caftania multi-tenant + privacy extensions
    marketplace = models.ForeignKey(
        'core.Marketplace', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users',
    )
    display_mode = models.CharField(max_length=10, choices=DISPLAY_MODE_CHOICES, default='real')
    pseudonym = models.CharField(max_length=80, blank=True, default='')
    care_score = models.FloatField(default=5.0)
    is_kyc_verified = models.BooleanField(default=False)
    is_private_circle = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=80, blank=True, default='')
    stripe_account_id = models.CharField(max_length=80, blank=True, default='')
    # Pro tier — negafat & physical rental shops
    PRO_TIER_CHOICES = [
        ('none', 'Particulier'),
        ('negafa', 'Négafa indépendante'),
        ('atelier', 'Atelier / Créatrice pro'),
        ('boutique', 'Boutique physique'),
        ('partner', 'Partenaire officiel'),
    ]
    is_pro = models.BooleanField(default=False)
    pro_tier = models.CharField(max_length=20, choices=PRO_TIER_CHOICES, default='none')
    shop_name = models.CharField(max_length=200, blank=True, default='')
    shop_address = models.CharField(max_length=500, blank=True, default='')
    shop_city = models.CharField(max_length=100, blank=True, default='')
    has_physical_shop = models.BooleanField(default=False)
    pro_featured = models.BooleanField(default=False)  # paid spotlight
    vat_number = models.CharField(max_length=40, blank=True, default='')

    def __str__(self):
        return f"{self.username} ({self.role})"


class VenueProfile(models.Model):
    ORGANIZATION_TYPES = [
        ('museum', 'Museum'),
        ('gallery', 'Gallery'),
        ('cultural_house', 'Cultural House'),
        ('theater', 'Theater'),
        ('studio', 'Studio'),
        ('other', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='venue_profile')
    organization_name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=20, choices=ORGANIZATION_TYPES, default='gallery')
    address = models.CharField(max_length=500, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, default='US')
    zip_code = models.CharField(max_length=20, blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    description = models.TextField(blank=True, default='')
    logo = models.URLField(blank=True, default='')
    cover_image = models.URLField(blank=True, default='')
    is_featured = models.BooleanField(default=False)
    # Transportation & accessibility (LoopNet-style)
    walkability_score = models.PositiveIntegerField(default=0)  # 0-100
    transit_score = models.PositiveIntegerField(default=0)  # 0-100
    bike_score = models.PositiveIntegerField(default=0)  # 0-100
    parking_info = models.CharField(max_length=255, blank=True, default='')
    nearby_transit = models.JSONField(default=list, blank=True)  # [{"name": "16th-Stout", "lines": ["E","W"], "walk_min": 4}, ...]
    # Stripe Connect — venues receive payouts directly from bookings, platform
    # takes an application fee. Empty until the venue onboards via Express.
    stripe_account_id = models.CharField(max_length=80, blank=True, default='')
    stripe_charges_enabled = models.BooleanField(default=False)
    stripe_payouts_enabled = models.BooleanField(default=False)
    stripe_details_submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.organization_name

    @property
    def payouts_ready(self):
        """True if this venue can receive transfers from Stripe."""
        return bool(self.stripe_account_id) and self.stripe_charges_enabled and self.stripe_payouts_enabled


class CreatorProfile(models.Model):
    SPECIALTY_CHOICES = [
        ('vr', 'Virtual Reality'),
        ('ar', 'Augmented Reality'),
        ('mr', 'Mixed Reality'),
        ('immersive', 'Immersive Installation'),
        ('projection', 'Projection Mapping'),
        ('interactive', 'Interactive Art'),
        ('other', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='creator_profile')
    display_name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=20, choices=SPECIALTY_CHOICES, default='immersive')
    skills = models.JSONField(default=list, blank=True)
    portfolio_url = models.URLField(blank=True, default='')
    showreel_url = models.URLField(blank=True, default='')
    years_experience = models.PositiveIntegerField(default=0)
    city = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, default='US')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name


class AudienceProfile(models.Model):
    """
    Audience = regular users who attend events, follow venues/creators, buy tickets.
    Third role alongside Creator and Venue. Public-profile by default (Partiful-style)
    but with is_public toggle for privacy.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='audience_profile')
    display_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, default='US')
    cover_image = models.URLField(blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    # Interests = list of free-form tags or specialty-like enums, drives event recommendations
    interests = models.JSONField(default=list, blank=True)
    # Socials: {"instagram": "...", "tiktok": "...", "website": "..."}
    socials = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=24)

    def __str__(self):
        return f"Verify {self.user.email}"


class Notification(models.Model):
    """In-app notification delivered to a user."""
    KIND_CHOICES = [
        ('invite', 'Invite'),
        ('invite_response', 'Invite response'),
        ('broadcast', 'Broadcast'),
        ('rsvp', 'RSVP'),
        ('follow', 'Follow'),
        ('ticket_sold', 'Ticket sold'),
        ('booking', 'Booking'),
        ('waitlist', 'Waitlist'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications_sent',
    )
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True, default='')
    url = models.CharField(max_length=300, blank=True, default='')
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read_at', '-created_at']),
        ]

    def __str__(self):
        return f'{self.kind} → {self.user.username}: {self.title}'


class PushSubscription(models.Model):
    """Web Push endpoint registered by an installed PWA client."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user'])]

    def __str__(self):
        return f'Push→{self.user.username}'


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=1)

    def __str__(self):
        return f"Reset {self.user.email}"
