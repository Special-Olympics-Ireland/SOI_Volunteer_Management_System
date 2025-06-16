"""
URL configuration for common app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, dashboard_views, mobile_admin_views

app_name = 'common'

router = DefaultRouter()
# Admin Override API
router.register(r'admin-overrides', views.AdminOverrideViewSet, basename='adminoverride')
# Audit Log API
router.register(r'audit-logs', views.AuditLogViewSet, basename='auditlog')
# System Config API
router.register(r'system-config', views.SystemConfigViewSet, basename='systemconfig')

urlpatterns = [
    # Dashboard URLs
    path('dashboard/', dashboard_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/volunteers/', dashboard_views.VolunteerDashboardView.as_view(), name='volunteer_dashboard'),
    path('dashboard/events/', dashboard_views.EventDashboardView.as_view(), name='event_dashboard'),
    path('dashboard/system/', dashboard_views.SystemDashboardView.as_view(), name='system_dashboard'),
    
    # Dashboard API endpoints
    path('api/dashboard/', dashboard_views.dashboard_api, name='dashboard_api'),
    path('api/dashboard/metrics/<str:metric_type>/', dashboard_views.dashboard_metrics_api, name='dashboard_metrics_api'),
    path('api/dashboard/alerts/', dashboard_views.dashboard_alerts_api, name='dashboard_alerts_api'),
    path('api/dashboard/activity/', dashboard_views.dashboard_activity_api, name='dashboard_activity_api'),
    path('api/dashboard/trends/', dashboard_views.dashboard_trends_api, name='dashboard_trends_api'),
    path('api/dashboard/export/<str:export_type>/', dashboard_views.dashboard_export, name='dashboard_export'),
    path('api/dashboard/cache/refresh/', dashboard_views.dashboard_refresh_cache, name='dashboard_refresh_cache'),
    
    # REST API endpoints
    path('api/v1/dashboard/overview/', dashboard_views.api_dashboard_overview, name='api_dashboard_overview'),
    path('api/v1/dashboard/kpis/', dashboard_views.api_dashboard_kpis, name='api_dashboard_kpis'),
    path('api/v1/dashboard/alerts/', dashboard_views.api_dashboard_alerts, name='api_dashboard_alerts'),
    
    # Widget configuration
    path('dashboard/widgets/config/', dashboard_views.dashboard_widget_config, name='dashboard_widget_config'),
    
    # Mobile admin URLs
    path('mobile-admin/', mobile_admin_views.mobile_admin_dashboard, name='mobile_dashboard'),
    path('mobile-admin/volunteers/', mobile_admin_views.mobile_volunteer_list, name='mobile_volunteers'),
    path('mobile-admin/events/', mobile_admin_views.mobile_event_list, name='mobile_events'),
    path('mobile-admin/assignments/', mobile_admin_views.mobile_assignment_management, name='mobile_assignments'),
    path('mobile-admin/quick-action/', mobile_admin_views.mobile_quick_action, name='mobile_quick_action'),
    
    # Mobile admin API endpoints
    path('api/mobile/stats/', mobile_admin_views.mobile_stats_api, name='mobile_stats_api'),
    path('api/mobile/search/', mobile_admin_views.mobile_search_api, name='mobile_search_api'),
    path('api/mobile/notifications/', mobile_admin_views.mobile_notifications_api, name='mobile_notifications_api'),
    path('api/mobile/bulk-actions/', mobile_admin_views.mobile_bulk_actions, name='mobile_bulk_actions'),
    
    # Admin Override API endpoints (custom actions)
    path('api/admin-overrides/<uuid:pk>/approve/', views.AdminOverrideViewSet.as_view({'post': 'approve'}), name='adminoverride-approve'),
    path('api/admin-overrides/<uuid:pk>/reject/', views.AdminOverrideViewSet.as_view({'post': 'reject'}), name='adminoverride-reject'),
    path('api/admin-overrides/<uuid:pk>/activate/', views.AdminOverrideViewSet.as_view({'post': 'activate'}), name='adminoverride-activate'),
    path('api/admin-overrides/<uuid:pk>/revoke/', views.AdminOverrideViewSet.as_view({'post': 'revoke'}), name='adminoverride-revoke'),
    path('api/admin-overrides/<uuid:pk>/complete/', views.AdminOverrideViewSet.as_view({'post': 'complete'}), name='adminoverride-complete'),
    path('api/admin-overrides/<uuid:pk>/monitoring/', views.AdminOverrideViewSet.as_view({'post': 'monitoring'}), name='adminoverride-monitoring'),
    path('api/admin-overrides/bulk-operations/', views.AdminOverrideViewSet.as_view({'post': 'bulk_operations'}), name='adminoverride-bulk-operations'),
    path('api/admin-overrides/statistics/', views.AdminOverrideViewSet.as_view({'get': 'statistics'}), name='adminoverride-statistics'),
    path('api/admin-overrides/pending/', views.AdminOverrideViewSet.as_view({'get': 'pending'}), name='adminoverride-pending'),
    path('api/admin-overrides/active/', views.AdminOverrideViewSet.as_view({'get': 'active'}), name='adminoverride-active'),
    path('api/admin-overrides/expiring/', views.AdminOverrideViewSet.as_view({'get': 'expiring'}), name='adminoverride-expiring'),
    path('api/admin-overrides/types/', views.AdminOverrideViewSet.as_view({'get': 'types'}), name='adminoverride-types'),
    
    # Theme management URLs
    path('themes/', include('common.theme_urls')),
    
    # API URLs
    path('api/', include(router.urls)),
] 