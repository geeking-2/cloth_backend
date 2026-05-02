from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ConditionReport
from .serializers import ConditionReportSerializer
from .services import analyze_with_claude


class ConditionReportViewSet(viewsets.ModelViewSet):
    """List + create condition reports.

    POST /api/condition-reports/      create a new report (photos + moment)
    POST /api/condition-reports/{id}/analyze/  run Claude Vision against the latest baseline
    """
    serializer_class = ConditionReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ConditionReport.objects.select_related('item', 'rental', 'handover', 'submitted_by')

    def get_queryset(self):
        qs = super().get_queryset()
        item_id = self.request.query_params.get('item')
        if item_id:
            qs = qs.filter(item_id=item_id)
        rental_id = self.request.query_params.get('rental')
        if rental_id:
            qs = qs.filter(rental_id=rental_id)
        return qs

    def perform_create(self, serializer):
        report = serializer.save(submitted_by=self.request.user)
        # Auto-analyze on creation if it's a comparison moment.
        if report.moment in ('reception', 'post_return', 'manual'):
            self._run_analysis(report)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        report = self.get_object()
        result = self._run_analysis(report)
        return Response(self.get_serializer(report).data | {'_meta': {'source': result.get('_source')}})

    def _run_analysis(self, report):
        baseline = (
            ConditionReport.objects
            .filter(item=report.item, moment='baseline')
            .order_by('-created_at')
            .first()
        )
        baseline_urls = baseline.photo_urls if baseline else []
        result = analyze_with_claude(baseline_urls, report.photo_urls)
        report.ai_score = result['overall_score']
        report.ai_is_acceptable = result['is_acceptable']
        report.ai_detected_issues = result['detected_issues']
        report.ai_estimated_repair_cost = result['estimated_repair_cost_eur']
        report.ai_recommendation = result['recommendation']
        report.ai_raw = {'source': result['_source'], 'raw': str(result.get('_raw', ''))[:5000]}
        report.save(update_fields=[
            'ai_score', 'ai_is_acceptable', 'ai_detected_issues',
            'ai_estimated_repair_cost', 'ai_recommendation', 'ai_raw',
        ])
        return result
