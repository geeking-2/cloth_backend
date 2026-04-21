from django.urls import path, re_path
from . import views
from .ical_views import (
    EventIcalView, TicketIcalView, BookingIcalView,
    MyCalendarTokenView, MyCalendarFeedView,
)

urlpatterns = [
    path('events/', views.EventListCreateView.as_view(), name='event-list-create'),
    path('events/<slug:slug>/', views.EventDetailView.as_view(), name='event-detail'),
    path('events/<slug:slug>/rsvp/', views.EventRSVPView.as_view(), name='event-rsvp'),
    path('events/<slug:slug>/attendees/', views.EventAttendeesView.as_view(), name='event-attendees'),
    path('events/<slug:slug>/invites/', views.EventInviteListCreateView.as_view(), name='event-invites'),
    path('events/<slug:slug>/broadcasts/', views.EventBroadcastListCreateView.as_view(), name='event-broadcasts'),
    path('events/<slug:slug>/ical/', EventIcalView.as_view(), name='event-ical'),
    path('tickets/<int:pk>/ical/', TicketIcalView.as_view(), name='ticket-ical'),
    path('bookings/<int:pk>/ical/', BookingIcalView.as_view(), name='booking-ical'),
    path('me/calendar-token/', MyCalendarTokenView.as_view(), name='calendar-token'),
    re_path(r'^my-calendar/(?P<uid>\d+)-(?P<token>[a-f0-9]+)\.ics$', MyCalendarFeedView.as_view(), name='calendar-feed'),
    path('invites/', views.MyInvitesView.as_view(), name='my-invites'),
    path('invites/<int:pk>/respond/', views.InviteRespondView.as_view(), name='invite-respond'),
    path('stories/', views.StoryListCreateView.as_view(), name='story-list-create'),
    path('stories/<int:pk>/', views.StoryDetailView.as_view(), name='story-detail'),
    path('feed/', views.FeedView.as_view(), name='feed'),
]
