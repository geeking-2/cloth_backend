from django.db import models
from django.db.models import Q


class Conversation(models.Model):
    """1-to-1 thread between exactly two users."""
    participants = models.ManyToManyField('accounts.User', related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-last_message_at']

    def other_participant(self, user):
        return self.participants.exclude(pk=user.pk).first()

    @classmethod
    def between(cls, user_a, user_b):
        """Return the existing 1-to-1 conversation between these two users, or None."""
        return (
            cls.objects
            .filter(participants=user_a)
            .filter(participants=user_b)
            .annotate(num=models.Count('participants'))
            .filter(num=2)
            .first()
        )


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField(blank=True, default='')
    image = models.TextField(blank=True, default='')  # URL or base64 data URL
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f'{self.sender_id}: {self.body[:40]}'


class Block(models.Model):
    """One-directional block: blocker prevents blocked from messaging."""
    blocker = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='blocks_made')
    blocked = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='blocks_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('blocker', 'blocked')]
        indexes = [
            models.Index(fields=['blocker']),
            models.Index(fields=['blocked']),
        ]

    def __str__(self):
        return f'{self.blocker_id} blocked {self.blocked_id}'
