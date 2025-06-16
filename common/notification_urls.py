"""
URL routing for notification API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .notification_views import (
    NotificationViewSet, NotificationPreferenceViewSet
)

# Create router for notification API
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='notification-preference')

urlpatterns = [
    path('api/notifications/', include(router.urls)),
] 