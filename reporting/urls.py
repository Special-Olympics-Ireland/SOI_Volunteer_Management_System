from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'templates', views.ReportTemplateViewSet, basename='reporttemplate')
router.register(r'schedules', views.ReportScheduleViewSet, basename='reportschedule')
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')

app_name = 'reporting'

urlpatterns = [
    # ViewSet URLs - Direct router
    path('', include(router.urls)),
    
    # Additional API endpoints
    path('reports/<uuid:pk>/download/', views.ReportViewSet.as_view({'get': 'download'}), name='report-download'),
    path('reports/<uuid:pk>/progress/', views.ReportViewSet.as_view({'get': 'progress'}), name='report-progress'),
    path('reports/<uuid:pk>/regenerate/', views.ReportViewSet.as_view({'post': 'regenerate'}), name='report-regenerate'),
    path('reports/<uuid:pk>/share/', views.ReportViewSet.as_view({'post': 'share'}), name='report-share'),
    path('reports/<uuid:pk>/metrics/', views.ReportViewSet.as_view({'get': 'metrics'}), name='report-metrics'),
    path('reports/bulk-operations/', views.ReportViewSet.as_view({'post': 'bulk_operations'}), name='report-bulk-operations'),
    path('reports/types/', views.ReportViewSet.as_view({'get': 'types'}), name='report-types'),
    
    # Template endpoints
    path('templates/<int:pk>/use/', views.ReportTemplateViewSet.as_view({'post': 'use_template'}), name='template-use'),
    
    # Schedule endpoints
    path('schedules/<int:pk>/run-now/', views.ReportScheduleViewSet.as_view({'post': 'run_now'}), name='schedule-run-now'),
    
    # Analytics endpoints
    path('analytics/dashboard/', views.AnalyticsViewSet.as_view({'get': 'dashboard'}), name='analytics-dashboard'),
    path('analytics/trends/', views.AnalyticsViewSet.as_view({'get': 'trends'}), name='analytics-trends'),
] 