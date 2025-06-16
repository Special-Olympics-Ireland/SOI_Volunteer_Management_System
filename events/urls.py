"""
URL configuration for events app.
Handles events, venues, roles, and assignments management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'events'

# Create router for API endpoints
router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'venues', views.VenueViewSet, basename='venue')
router.register(r'roles', views.RoleViewSet, basename='role')
router.register(r'assignments', views.AssignmentViewSet, basename='assignment')

urlpatterns = [
    # API endpoints - Direct router URLs
    path('', include(router.urls)),
    
    # Event management
    path('api/events/<uuid:event_id>/venues/', views.EventVenuesView.as_view(), name='event-venues'),
    path('api/events/<uuid:event_id>/roles/', views.EventRolesView.as_view(), name='event-roles'),
    path('api/events/<uuid:event_id>/assignments/', views.EventAssignmentsView.as_view(), name='event-assignments'),
    
    # Venue management
    path('api/venues/<uuid:venue_id>/roles/', views.VenueRolesView.as_view(), name='venue-roles'),
    path('api/venues/<uuid:venue_id>/capacity/', views.VenueCapacityView.as_view(), name='venue-capacity'),
    
    # Role management
    path('api/roles/<uuid:role_id>/requirements/', views.RoleRequirementsView.as_view(), name='role-requirements'),
    path('api/roles/<uuid:role_id>/volunteers/', views.RoleVolunteersView.as_view(), name='role-volunteers'),
    
    # Assignment management
    path('api/assignments/bulk/', views.BulkAssignmentView.as_view(), name='bulk-assignment'),
    path('api/assignments/<uuid:assignment_id>/override/', views.AssignmentOverrideView.as_view(), name='assignment-override'),
    path('api/assignments/stats/', views.AssignmentStatsView.as_view(), name='assignment-stats'),
    
    # Bulk operations
    path('api/events/bulk/', views.BulkEventOperationsView.as_view(), name='bulk-event-operations'),
] 