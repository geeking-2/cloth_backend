from django.urls import path
from .views import (
    ConversationListCreateView,
    MessageListCreateView,
    ConversationReadView,
    UnreadCountView,
    BlockToggleView,
    BlockStatusView,
)

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/unread-count/', UnreadCountView.as_view(), name='conversation-unread-count'),
    path('conversations/<int:conv_id>/messages/', MessageListCreateView.as_view(), name='message-list'),
    path('conversations/<int:conv_id>/read/', ConversationReadView.as_view(), name='conversation-read'),
    path('blocks/<int:user_id>/', BlockToggleView.as_view(), name='block-toggle'),
    path('blocks/<int:user_id>/status/', BlockStatusView.as_view(), name='block-status'),
]
