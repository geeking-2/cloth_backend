from rest_framework.routers import DefaultRouter
from .views import PostViewSet, StoryViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'stories', StoryViewSet, basename='story')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = router.urls
