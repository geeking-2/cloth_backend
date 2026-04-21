from django.urls import path
from . import views

urlpatterns = [
    path('config/', views.StripeConfigView.as_view(), name='stripe-config'),
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    # Stripe Connect — venue payouts
    path('connect/status/', views.StripeConnectStatusView.as_view(), name='stripe-connect-status'),
    path('connect/onboard/', views.StripeConnectOnboardView.as_view(), name='stripe-connect-onboard'),
    path('connect/refresh/', views.StripeConnectRefreshView.as_view(), name='stripe-connect-refresh'),
    path('connect/dashboard/', views.StripeConnectDashboardView.as_view(), name='stripe-connect-dashboard'),
]
