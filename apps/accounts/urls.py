from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from . import notifications as notif_views
from . import push as push_views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('google/', views.GoogleAuthView.as_view(), name='google-auth'),
    path('me/', views.MeView.as_view(), name='me'),
    path('venue/profile/', views.VenueProfileUpdateView.as_view(), name='venue-profile-update'),
    path('creator/profile/', views.CreatorProfileUpdateView.as_view(), name='creator-profile-update'),
    path('audience/profile/', views.AudienceProfileUpdateView.as_view(), name='audience-profile-update'),
    path('venues/', views.VenueListView.as_view(), name='venue-list'),
    path('venues/<int:user_id>/', views.VenueDetailView.as_view(), name='venue-detail'),
    path('creators/', views.CreatorListView.as_view(), name='creator-list'),
    path('creators/<int:user_id>/', views.CreatorDetailView.as_view(), name='creator-detail'),
    path('audiences/', views.AudienceListView.as_view(), name='audience-list'),
    path('audiences/<int:user_id>/', views.AudienceDetailView.as_view(), name='audience-detail'),
    # Notifications
    path('notifications/', notif_views.NotificationListView.as_view(), name='notifications-list'),
    path('notifications/unread-count/', notif_views.NotificationUnreadCountView.as_view(), name='notifications-unread'),
    path('notifications/mark-all-read/', notif_views.NotificationMarkAllReadView.as_view(), name='notifications-mark-all'),
    path('notifications/<int:pk>/read/', notif_views.NotificationMarkReadView.as_view(), name='notifications-mark-one'),
    # Push notifications
    path('push/public-key/', push_views.PushPublicKeyView.as_view(), name='push-public-key'),
    path('push/subscribe/', push_views.PushSubscribeView.as_view(), name='push-subscribe'),
    path('push/unsubscribe/', push_views.PushUnsubscribeView.as_view(), name='push-unsubscribe'),
]
