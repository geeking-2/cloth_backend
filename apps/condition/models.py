from django.db import models
from django.conf import settings


class ConditionReport(models.Model):
    """A single visual analysis of a caftan's state at a given moment.

    Created either:
      - automatically by the loueuse when she lists the caftan (baseline)
      - automatically when a handover opens (delivery / return)
      - manually triggered by a dispute

    The IA fields are filled by `apps.condition.services.analyze_with_claude`
    when ANTHROPIC_API_KEY is configured; otherwise they stay null and the
    object becomes a simple photo log.
    """
    MOMENT_CHOICES = [
        ('baseline',     'Baseline (mise en ligne)'),
        ('pre_shipment', 'Avant envoi'),
        ('reception',    'Réception cliente'),
        ('pre_return',   'Avant retour'),
        ('post_return',  'Réception loueuse'),
        ('manual',       'Contrôle manuel'),
    ]
    RECOMMENDATION_CHOICES = [
        ('accept',         'Accepter'),
        ('minor_dispute',  'Litige mineur'),
        ('major_dispute',  'Litige majeur'),
        ('inconclusive',   'Inconcluant'),
    ]

    item = models.ForeignKey(
        'spaces.Space', on_delete=models.CASCADE, related_name='condition_reports')
    rental = models.ForeignKey(
        'bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='condition_reports')
    handover = models.ForeignKey(
        'handovers.HandoverReceipt', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='condition_reports')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='condition_reports')
    moment = models.CharField(max_length=20, choices=MOMENT_CHOICES)
    photo_urls = models.JSONField(default=list)
    video_url = models.URLField(blank=True, default='')
    notes = models.TextField(blank=True, default='')

    # AI output
    ai_score = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5
    ai_is_acceptable = models.BooleanField(null=True, blank=True)
    ai_detected_issues = models.JSONField(default=list, blank=True)
    ai_estimated_repair_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    ai_recommendation = models.CharField(
        max_length=20, choices=RECOMMENDATION_CHOICES, blank=True, default='')
    ai_raw = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_id}@{self.moment} score={self.ai_score or '-'}"
