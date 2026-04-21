from django.urls import path
from . import views

urlpatterns = [
    # Tier management (per-event)
    path('events/<slug:slug>/tiers/', views.TicketTierListCreateView.as_view(), name='ticket-tier-list'),
    path('ticket-tiers/<int:pk>/', views.TicketTierDetailView.as_view(), name='ticket-tier-detail'),
    # Purchase
    path('events/<slug:slug>/purchase/', views.TicketPurchaseView.as_view(), name='ticket-purchase'),
    # Door scanner
    path('events/<slug:slug>/check-in/', views.TicketCheckInView.as_view(), name='ticket-check-in'),
    # User-owned tickets
    path('tickets/', views.MyTicketsView.as_view(), name='my-tickets'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<int:pk>/confirm/', views.TicketConfirmView.as_view(), name='ticket-confirm'),
    path('tickets/<int:pk>/refund/', views.TicketRefundView.as_view(), name='ticket-refund'),
    # Waitlist
    path('ticket-tiers/<int:pk>/waitlist/', views.TierWaitlistView.as_view(), name='tier-waitlist'),
]
