from rest_framework.routers import DefaultRouter
from .views import ConditionReportViewSet

router = DefaultRouter()
router.register(r'condition-reports', ConditionReportViewSet, basename='condition-report')

urlpatterns = router.urls
