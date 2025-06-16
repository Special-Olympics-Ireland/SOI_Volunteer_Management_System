"""
URL configuration for volunteers app.
Handles volunteer profiles, EOI submissions, and volunteer management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import eoi_views
from . import eoi_api_views

# Create router for API endpoints
router = DefaultRouter()
router.register(r'profiles', views.VolunteerProfileViewSet, basename='volunteerprofile')

app_name = 'volunteers'

urlpatterns = [
    # EOI System URLs (existing web interface)
    path('eoi/', include('volunteers.eoi_urls')),
    
    # Volunteer Profile API URLs - Direct router
    path('', include(router.urls)),
    
    # EOI API URLs
    path('eoi/', include('volunteers.eoi_api_urls')),
    
    # Additional volunteer profile API endpoints
    path('profiles/stats/global/', views.VolunteerProfileViewSet.as_view({'get': 'global_stats'}), name='volunteer-global-stats'),
    path('profiles/filter/by-status/', views.VolunteerProfileViewSet.as_view({'get': 'by_status'}), name='volunteer-by-status'),
    path('profiles/filter/by-experience/', views.VolunteerProfileViewSet.as_view({'get': 'by_experience'}), name='volunteer-by-experience'),
    path('profiles/filter/available/', views.VolunteerProfileViewSet.as_view({'get': 'available_for_assignment'}), name='volunteer-available'),
    path('profiles/filter/corporate/', views.VolunteerProfileViewSet.as_view({'get': 'corporate_volunteers'}), name='volunteer-corporate'),
    path('profiles/filter/pending-review/', views.VolunteerProfileViewSet.as_view({'get': 'pending_review'}), name='volunteer-pending-review'),
    path('profiles/filter/background-check/', views.VolunteerProfileViewSet.as_view({'get': 'background_check_required'}), name='volunteer-background-check'),
    path('profiles/bulk-operations/', views.VolunteerProfileViewSet.as_view({'post': 'bulk_operations'}), name='volunteer-bulk-operations'),
] 