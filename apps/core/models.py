from django.db import models


class Marketplace(models.Model):
    """A tenant for the mutualised multi-marketplace backend.

    Each Marketplace row = one public-facing brand (Caftania, Blazer, etc.).
    Data is scoped via `marketplace` FK on the main business models and
    resolved at request time by `MarketplaceMiddleware`.
    """
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=255, blank=True, default='')
    primary_language = models.CharField(max_length=10, default='fr')
    secondary_language = models.CharField(max_length=10, blank=True, default='')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    currency = models.CharField(max_length=3, default='EUR')
    primary_color = models.CharField(max_length=20, blank=True, default='')
    secondary_color = models.CharField(max_length=20, blank=True, default='')
    logo_url = models.URLField(blank=True, default='')
    tagline_key = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({self.slug})'
