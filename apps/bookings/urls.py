from django.urls import path
from . import views

urlpatterns = [
    path('bookings/', views.BookingListCreateView.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/<int:pk>/accept/', views.BookingAcceptView.as_view(), name='booking-accept'),
    path('bookings/<int:pk>/reject/', views.BookingRejectView.as_view(), name='booking-reject'),
    path('bookings/<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking-cancel'),
    path('bookings/<int:pk>/confirm-payment/', views.PaymentConfirmView.as_view(), name='booking-confirm-payment'),
    path('bookings/<int:pk>/events/', views.BookingEventListView.as_view(), name='booking-events'),
]
