from django.db import models


class Follow(models.Model):
    follower = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('follower', 'following')]
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.follower} → {self.following}'
