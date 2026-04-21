from django.urls import path
from . import views

urlpatterns = [
    path('proposals/', views.ProposalListCreateView.as_view(), name='proposal-list-create'),
    path('proposals/<int:pk>/', views.ProposalDetailView.as_view(), name='proposal-detail'),
    path('portfolio/', views.PortfolioListCreateView.as_view(), name='portfolio-list-create'),
    path('portfolio/<int:pk>/', views.PortfolioDetailView.as_view(), name='portfolio-detail'),
    path('portfolio-public/<int:pk>/', views.PortfolioProjectPublicView.as_view(), name='portfolio-public'),
    path('creators/<int:creator_id>/portfolio/', views.PortfolioListCreateView.as_view(), name='creator-portfolio'),
]
