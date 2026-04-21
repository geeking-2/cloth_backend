from django.db import models


class PortfolioProject(models.Model):
    TECHNOLOGY_CHOICES = [
        ('vr', 'Virtual Reality'),
        ('ar', 'Augmented Reality'),
        ('mr', 'Mixed Reality'),
        ('immersive', 'Immersive Installation'),
        ('projection', 'Projection Mapping'),
        ('interactive', 'Interactive Art'),
        ('other', 'Other'),
    ]
    creator = models.ForeignKey(
        'accounts.CreatorProfile', on_delete=models.CASCADE, related_name='portfolio_projects'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    technology = models.CharField(max_length=20, choices=TECHNOLOGY_CHOICES, default='immersive')
    year = models.PositiveIntegerField()
    cover_image = models.TextField(blank=True, default='')  # URL or base64 data URL (legacy - first image)
    video_url = models.CharField(max_length=500, blank=True, default='')  # legacy single video
    external_url = models.URLField(blank=True, default='')  # legacy single link
    # New multi-media fields
    gallery_images = models.JSONField(default=list, blank=True)  # list of image URLs/data URLs
    videos = models.JSONField(default=list, blank=True)  # list of video URLs
    external_links = models.JSONField(default=list, blank=True)  # list of {url, label}
    tags = models.JSONField(default=list, blank=True)
    # ---- Case study fields (additive; all optional) ----
    client_name = models.CharField(max_length=200, blank=True, default='')
    role = models.CharField(max_length=200, blank=True, default='', help_text='e.g. "Lead artist & creative director"')
    brief = models.TextField(blank=True, default='', help_text='The problem / starting point')
    outcome = models.TextField(blank=True, default='', help_text='What happened. Numbers welcome.')
    metrics = models.JSONField(default=list, blank=True)  # list of {label, value}  e.g. [{"label":"Attendees","value":"12,400"}]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-created_at']

    def __str__(self):
        return self.title


class PortfolioImage(models.Model):
    project = models.ForeignKey(PortfolioProject, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


class Proposal(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    creator = models.ForeignKey(
        'accounts.CreatorProfile', on_delete=models.CASCADE, related_name='proposals'
    )
    space = models.ForeignKey(
        'spaces.Space', on_delete=models.CASCADE, related_name='proposals'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    project_type = models.CharField(max_length=20, choices=PortfolioProject.TECHNOLOGY_CHOICES, default='immersive')
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    technical_requirements = models.TextField(blank=True, default='')
    audience_description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    venue_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.status}"
