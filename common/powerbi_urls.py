"""
URL Configuration for PowerBI Integration Endpoints.

This module defines all URL patterns for PowerBI integration APIs,
providing structured access to analytics data and real-time metrics.
"""

from django.urls import path, include
from . import powerbi_views

app_name = 'powerbi'

# Main PowerBI API endpoints
urlpatterns = [
    # Analytics Endpoints
    path('volunteer-analytics/', 
         powerbi_views.VolunteerAnalyticsView.as_view(), 
         name='volunteer_analytics'),
    
    path('event-analytics/', 
         powerbi_views.EventAnalyticsView.as_view(), 
         name='event_analytics'),
    
    path('operational-analytics/', 
         powerbi_views.OperationalAnalyticsView.as_view(), 
         name='operational_analytics'),
    
    path('financial-analytics/', 
         powerbi_views.FinancialAnalyticsView.as_view(), 
         name='financial_analytics'),
    
    path('predictive-analytics/', 
         powerbi_views.PredictiveAnalyticsView.as_view(), 
         name='predictive_analytics'),
    
    # Real-time Data Endpoints
    path('real-time-dashboard/', 
         powerbi_views.RealTimeDashboardView.as_view(), 
         name='real_time_dashboard'),
    
    # Custom Dataset Endpoints
    path('custom-dataset/', 
         powerbi_views.CustomDatasetView.as_view(), 
         name='custom_dataset'),
    
    # Metadata and Schema Endpoints
    path('metadata/', 
         powerbi_views.PowerBIMetadataView.as_view(), 
         name='metadata'),
    
    # Export Endpoints
    path('export/<str:dataset_type>/', 
         powerbi_views.PowerBIExportView.as_view(), 
         name='export_dataset'),
    
    # Health Check and Monitoring
    path('health/', 
         powerbi_views.PowerBIHealthCheckView.as_view(), 
         name='health_check'),
    
    # Summary and Overview
    path('summary/', 
         powerbi_views.powerbi_summary_view, 
         name='summary'),
    
    # Cache Management
    path('cache/refresh/', 
         powerbi_views.powerbi_cache_refresh_view, 
         name='cache_refresh'),
]

# Additional URL patterns for versioned APIs
v1_patterns = [
    path('v1/', include(urlpatterns)),
]

# Complete URL patterns including versioning
urlpatterns += v1_patterns 