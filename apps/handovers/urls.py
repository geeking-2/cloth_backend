from django.urls import path
from . import views

urlpatterns = [
    path('handovers/open/', views.open_handover, name='handover-open'),
    path('handovers/<int:pk>/request-sms/', views.request_sms, name='handover-request-sms'),
    path('handovers/<int:pk>/verify-sms/', views.verify_sms, name='handover-verify-sms'),
    path('handovers/<int:pk>/', views.get_handover, name='handover-detail'),
]
