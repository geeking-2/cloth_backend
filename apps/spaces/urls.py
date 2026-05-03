from django.urls import path
from . import views
from .search_views import UnifiedSearchView

urlpatterns = [
    path('search/all/', UnifiedSearchView.as_view(), name='unified-search'),
    path('spaces/', views.SpaceListCreateView.as_view(), name='space-list-create'),
    path('spaces/featured/', views.FeaturedSpacesView.as_view(), name='space-featured'),
    path('spaces/sponsored/', views.SponsoredSpacesView.as_view(), name='space-sponsored'),
    path('spaces/my/', views.VenueSpacesView.as_view(), name='venue-spaces'),
    path('spaces/<slug:slug>/', views.SpaceDetailView.as_view(), name='space-detail'),
    path('spaces/<slug:slug>/images/', views.SpaceImageCreateView.as_view(), name='space-images'),
    path('spaces/<slug:slug>/availability/', views.AvailabilityListCreateView.as_view(), name='space-availability'),
    path('spaces/<slug:slug>/availability/bulk/', views.AvailabilityBulkView.as_view(), name='space-availability-bulk'),
    path('spaces/<slug:slug>/calendar/', views.SpaceCalendarView.as_view(), name='space-calendar'),
    path('spaces/<slug:slug>/similar/', views.SimilarSpacesView.as_view(), name='space-similar'),
    path('saved-spaces/', views.SavedSpaceListView.as_view(), name='saved-spaces'),
    path('landing/stats/', views.LandingStatsView.as_view(), name='landing-stats'),
]
