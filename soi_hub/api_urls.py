"""
API URL configuration for SOI Hub.
Centralizes all API v1 endpoints with proper routing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import ViewSets from each app
from accounts.views import UserViewSet
from volunteers.views import VolunteerProfileViewSet
from events.views import EventViewSet, VenueViewSet, RoleViewSet, AssignmentViewSet
from tasks.views import TaskViewSet, TaskCompletionViewSet
from reporting.views import ReportViewSet, ReportTemplateViewSet, AnalyticsViewSet
from common.views import AdminOverrideViewSet

# Create main API router
router = DefaultRouter()

# Register all ViewSets
router.register(r'accounts/users', UserViewSet, basename='user')
router.register(r'volunteers/profiles', VolunteerProfileViewSet, basename='volunteerprofile')
router.register(r'events/events', EventViewSet, basename='event')
router.register(r'events/venues', VenueViewSet, basename='venue')
router.register(r'events/roles', RoleViewSet, basename='role')
router.register(r'events/assignments', AssignmentViewSet, basename='assignment')
router.register(r'tasks/tasks', TaskViewSet, basename='task')
router.register(r'tasks/completions', TaskCompletionViewSet, basename='taskcompletion')
router.register(r'reporting/reports', ReportViewSet, basename='report')
router.register(r'reporting/templates', ReportTemplateViewSet, basename='reporttemplate')
router.register(r'reporting/analytics', AnalyticsViewSet, basename='analytics')
router.register(r'common/admin-overrides', AdminOverrideViewSet, basename='adminoverride')

urlpatterns = [
    # Main API router
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('accounts/auth/', include([
        path('login/', include('accounts.urls')),
        path('logout/', include('accounts.urls')),
        path('register/', include('accounts.urls')),
    ])),
    
    # Volunteer EOI endpoints
    path('volunteers/eoi/', include('volunteers.eoi_api_urls')),
    
    # Notification endpoints
    path('notifications/', include('common.notification_urls')),
] 