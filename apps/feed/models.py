from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Post(models.Model):
    POST_TYPE_CHOICES = [
        ('community_review', 'Avis communauté'),
        ('p2p_listing',      'Mise en ligne particulière'),
        ('p2p_offer',        'Annonce — louer ma pièce'),
        ('pro_drop',         'Drop boutique pro'),
        ('pro_event',        'Évènement pro (vide-dressing, ouverture…)'),
        ('pro_styling',      'Conseil styling pro'),
        ('other',            'Autre'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    item = models.ForeignKey('spaces.Space', on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    marketplace = models.ForeignKey('core.Marketplace', on_delete=models.SET_NULL, null=True, blank=True)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='community_review')
    caption = models.TextField(blank=True, default='')
    location_tag = models.CharField(max_length=120, blank=True, default='')
    event_type = models.CharField(max_length=40, blank=True, default='')
    media_urls = models.JSONField(default=list)  # list of {url, type}
    has_face_blur = models.BooleanField(default=False)
    has_background_blur = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    item_clicks_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.author_id} — {self.caption[:40]}"


class Story(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feed_stories')
    item = models.ForeignKey('spaces.Space', on_delete=models.SET_NULL, null=True, blank=True, related_name='feed_stories')
    marketplace = models.ForeignKey('core.Marketplace', on_delete=models.SET_NULL, null=True, blank=True)
    media_url = models.URLField()
    media_type = models.CharField(max_length=10, default='image')
    caption = models.CharField(max_length=200, blank=True, default='')
    has_face_blur = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
