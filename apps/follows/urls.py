from django.urls import path
from . import views

urlpatterns = [
    path('follow/<int:user_id>/', views.FollowToggleView.as_view(), name='follow-toggle'),
    path('users/<int:user_id>/follow-status/', views.FollowStatusView.as_view(), name='follow-status'),
    path('follows/activity/', views.FollowActivityView.as_view(), name='follows-activity'),
    path('users/<int:user_id>/mutual-followers/', views.MutualFollowersView.as_view(), name='mutual-followers'),
    path('users/<int:user_id>/followers/', views.FollowersListView.as_view(), name='follow-followers'),
    path('users/<int:user_id>/following/', views.FollowingListView.as_view(), name='follow-following'),
]
