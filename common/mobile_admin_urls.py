"""
URL Configuration for Mobile Admin Views

This module defines URL patterns for mobile-optimized admin interfaces.
"""

from django.urls import path
from . import mobile_admin_views

app_name = 'mobile_admin'

urlpatterns = [
    # Mobile admin dashboard
    path('', mobile_admin_views.mobile_admin_dashboard, name='dashboard'),
    
    # Mobile volunteer management
    path('volunteers/', mobile_admin_views.mobile_volunteer_list, name='volunteer_list'),
    
    # Mobile quick actions
    path('quick-action/', mobile_admin_views.mobile_quick_action, name='quick_action'),
    
    # Mobile API endpoints
    path('api/stats/', mobile_admin_views.mobile_stats_api, name='stats_api'),
    path('api/search/', mobile_admin_views.mobile_search_api, name='search_api'),
    path('api/notifications/', mobile_admin_views.mobile_notifications_api, name='notifications_api'),
    
    # Mobile bulk actions
    path('bulk-actions/', mobile_admin_views.mobile_bulk_actions, name='bulk_actions'),
] 