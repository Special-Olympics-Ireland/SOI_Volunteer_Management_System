"""
URL routing for SOI Hub Dashboard views and API endpoints.
"""

from django.urls import path
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard views
    path('', dashboard_views.DashboardView.as_view(), name='overview'),
    path('volunteers/', dashboard_views.VolunteerDashboardView.as_view(), name='volunteers'),
    path('events/', dashboard_views.EventDashboardView.as_view(), name='events'),
    path('system/', dashboard_views.SystemDashboardView.as_view(), name='system'),
    
    # Dashboard API endpoints
    path('api/', dashboard_views.dashboard_api, name='api'),
    path('api/metrics/<str:metric_type>/', dashboard_views.dashboard_metrics_api, name='metrics_api'),
    path('api/alerts/', dashboard_views.dashboard_alerts_api, name='alerts_api'),
    path('api/activity/', dashboard_views.dashboard_activity_api, name='activity_api'),
    path('api/trends/', dashboard_views.dashboard_trends_api, name='trends_api'),
    
    # Dashboard utilities
    path('export/<str:export_type>/', dashboard_views.dashboard_export, name='export'),
    path('refresh-cache/', dashboard_views.dashboard_refresh_cache, name='refresh_cache'),
    path('widget-config/', dashboard_views.dashboard_widget_config, name='widget_config'),
    
    # REST API endpoints
    path('rest/overview/', dashboard_views.api_dashboard_overview, name='rest_overview'),
    path('rest/kpis/', dashboard_views.api_dashboard_kpis, name='rest_kpis'),
    path('rest/alerts/', dashboard_views.api_dashboard_alerts, name='rest_alerts'),
] 