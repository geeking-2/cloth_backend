from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class Event(models.Model):
    TYPE_OPENING = 'opening'
    TYPE_PERFORMANCE = 'performance'
    TYPE_WORKSHOP = 'workshop'
    TYPE_INSTALLATION = 'installation'
    TYPE_RESIDENCY = 'residency'
    TYPE_EXHIBITION = 'exhibition'
    TYPE_SCREENING = 'screening'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_OPENING, 'Opening'),
        (TYPE_PERFORMANCE, 'Performance'),
        (TYPE_WORKSHOP, 'Workshop'),
        (TYPE_INSTALLATION, 'Installation'),
        (TYPE_RESIDENCY, 'Residency'),
        (TYPE_EXHIBITION, 'Exhibition'),
        (TYPE_SCREENING, 'Screening'),
        (TYPE_OTHER, 'Other'),
    ]

    host = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='events_hosted')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OPENING)
    description = models.TextField(blank=True)
    cover_image = models.URLField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, null=True)
    space = models.ForeignKey('spaces.Space', on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    portfolio_project = models.ForeignKey(
        'proposals.PortfolioProject', on_delete=models.SET_NULL, null=True, blank=True, related_name='events'
    )
    location_text = models.CharField(max_length=255, blank=True, help_text='Free-form location if no linked space')
    external_url = models.URLField(blank=True)
    is_public = models.BooleanField(default=True)
    # Ticketing + RSVP
    max_capacity = models.PositiveIntegerField(null=True, blank=True, help_text='Total attendees allowed')
    public_attendee_list = models.BooleanField(default=True, help_text='Non-hosts can see the attendee directory')
    ticketing_enabled = models.BooleanField(default=False, help_text='Paid tickets required (vs free RSVP)')
    age_restriction = models.CharField(
        max_length=10, blank=True, default='',
        choices=[('', 'No restriction'), ('18+', '18+'), ('21+', '21+')],
    )
    incognito_fee_cents = models.PositiveIntegerField(
        default=0, help_text='Extra fee in cents for hiding attendee name from public grid'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_at']
        indexes = [
            models.Index(fields=['starts_at']),
            models.Index(fields=['host', '-starts_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or 'event'
            candidate = base
            i = 2
            while Event.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f'{base}-{i}'
                i += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.starts_at > timezone.now()

    @property
    def is_live(self):
        now = timezone.now()
        end = self.ends_at or self.starts_at
        return self.starts_at <= now <= end

    def __str__(self):
        return f'{self.title} ({self.starts_at:%Y-%m-%d})'


class EventRSVP(models.Model):
    """Free RSVP to an event (separate from paid tickets).
    For ticketed events, a Ticket row automatically implies RSVP=going."""
    STATUS_GOING = 'going'
    STATUS_MAYBE = 'maybe'
    STATUS_INTERESTED = 'interested'
    STATUS_NOT_GOING = 'not_going'
    STATUS_CHOICES = [
        (STATUS_GOING, 'Going'),
        (STATUS_MAYBE, 'Maybe'),
        (STATUS_INTERESTED, 'Interested'),
        (STATUS_NOT_GOING, 'Not going'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='rsvps')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_GOING)
    # If True, hide user from the public attendee grid. Set to True either via paid
    # "incognito" ticket fee OR any user with is_public=False on their audience profile.
    incognito = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('event', 'user')]
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} {self.status} → {self.event.title}'


class EventInvite(models.Model):
    """Host (or any RSVP'd attendee) invites another user to an event."""
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DECLINED, 'Declined'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invites')
    inviter = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='invites_sent'
    )
    invitee = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='invites_received'
    )
    message = models.TextField(blank=True, default='', max_length=500)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('event', 'invitee')]
        indexes = [
            models.Index(fields=['invitee', 'status', '-created_at']),
            models.Index(fields=['event', 'status']),
        ]

    def __str__(self):
        return f'{self.inviter.username} → {self.invitee.username} for {self.event.title}'


class EventBroadcast(models.Model):
    """A host-sent update to attendees (going/maybe/interested/ticket holders)."""
    AUDIENCE_ALL = 'all'
    AUDIENCE_GOING = 'going'
    AUDIENCE_TICKET_HOLDERS = 'ticket_holders'
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, 'Everyone RSVP\'d'),
        (AUDIENCE_GOING, 'Only "Going"'),
        (AUDIENCE_TICKET_HOLDERS, 'Ticket holders'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='broadcasts')
    sender = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='broadcasts_sent'
    )
    subject = models.CharField(max_length=200)
    body = models.TextField(max_length=4000)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    recipient_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['event', '-created_at'])]

    def __str__(self):
        return f'Broadcast "{self.subject}" on {self.event.title}'


class Story(models.Model):
    """Short-lived visual updates (24h). Can optionally be attached to an event."""
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='stories')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='stories')
    space = models.ForeignKey('spaces.Space', on_delete=models.SET_NULL, null=True, blank=True, related_name='stories')
    image = models.URLField()
    caption = models.CharField(max_length=280, blank=True)
    link_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['author', '-created_at']), models.Index(fields=['expires_at'])]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f'Story by {self.author.username} at {self.created_at:%Y-%m-%d %H:%M}'
