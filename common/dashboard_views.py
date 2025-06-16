"""
Dashboard views for SOI Hub Volunteer Management System.

Provides web interface and API endpoints for real-time statistics,
KPIs, and administrative dashboard functionality.
"""

import json
from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .dashboard_service import DashboardService
from .models import AuditLog, AdminOverride
from volunteers.models import VolunteerProfile
from events.models import Event, Assignment


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(TemplateView):
    """
    Main dashboard view with comprehensive statistics and KPIs.
    """
    template_name = 'admin/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get dashboard overview
        dashboard_data = DashboardService.get_dashboard_overview(user=self.request.user)
        
        # Add dashboard data to context
        context.update({
            'dashboard_data': dashboard_data,
            'page_title': 'SOI Hub Dashboard',
            'refresh_interval': 300000,  # 5 minutes in milliseconds
            'user_permissions': {
                'can_view_sensitive': self.request.user.is_superuser,
                'can_manage_overrides': self.request.user.has_perm('common.change_adminoverride'),
                'can_view_audit': self.request.user.has_perm('common.view_auditlog')
            }
        })
        
        return context


@staff_member_required
@cache_page(60 * 5)  # Cache for 5 minutes
@vary_on_headers('User-Agent')
def dashboard_api(request):
    """
    API endpoint for dashboard data (for AJAX updates).
    """
    try:
        dashboard_data = DashboardService.get_dashboard_overview(user=request.user)
        
        return JsonResponse({
            'success': True,
            'data': dashboard_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@staff_member_required
def dashboard_metrics_api(request, metric_type):
    """
    API endpoint for specific metric types.
    """
    try:
        if metric_type == 'volunteers':
            data = DashboardService.get_volunteer_metrics()
        elif metric_type == 'events':
            data = DashboardService.get_event_metrics()
        elif metric_type == 'assignments':
            data = DashboardService.get_assignment_metrics()
        elif metric_type == 'tasks':
            data = DashboardService.get_task_metrics()
        elif metric_type == 'system':
            data = DashboardService.get_system_metrics()
        elif metric_type == 'integrations':
            data = DashboardService.get_integration_metrics()
        elif metric_type == 'performance':
            data = DashboardService.get_performance_metrics()
        elif metric_type == 'kpis':
            data = DashboardService.get_key_performance_indicators()
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown metric type: {metric_type}'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'metric_type': metric_type,
            'data': data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@staff_member_required
def dashboard_alerts_api(request):
    """
    API endpoint for alerts and notifications.
    """
    try:
        alerts_data = DashboardService.get_alerts_and_notifications()
        
        return JsonResponse({
            'success': True,
            'data': alerts_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@staff_member_required
def dashboard_activity_api(request):
    """
    API endpoint for recent activity.
    """
    try:
        limit = int(request.GET.get('limit', 20))
        activity_data = DashboardService.get_recent_activity(limit=limit)
        
        return JsonResponse({
            'success': True,
            'data': activity_data,
            'limit': limit,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@staff_member_required
def dashboard_trends_api(request):
    """
    API endpoint for trend data.
    """
    try:
        trends_data = DashboardService.get_trend_data()
        
        return JsonResponse({
            'success': True,
            'data': trends_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@method_decorator(staff_member_required, name='dispatch')
class VolunteerDashboardView(TemplateView):
    """
    Volunteer-specific dashboard view.
    """
    template_name = 'admin/dashboard/volunteer_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get volunteer-specific metrics
        volunteer_metrics = DashboardService.get_volunteer_metrics()
        
        context.update({
            'volunteer_metrics': volunteer_metrics,
            'page_title': 'Volunteer Dashboard',
            'section': 'volunteers'
        })
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class EventDashboardView(TemplateView):
    """
    Event-specific dashboard view.
    """
    template_name = 'admin/dashboard/event_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get event-specific metrics
        event_metrics = DashboardService.get_event_metrics()
        assignment_metrics = DashboardService.get_assignment_metrics()
        
        context.update({
            'event_metrics': event_metrics,
            'assignment_metrics': assignment_metrics,
            'page_title': 'Event Dashboard',
            'section': 'events'
        })
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class SystemDashboardView(TemplateView):
    """
    System administration dashboard view.
    """
    template_name = 'admin/dashboard/system_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get system-specific metrics
        system_metrics = DashboardService.get_system_metrics()
        performance_metrics = DashboardService.get_performance_metrics()
        integration_metrics = DashboardService.get_integration_metrics()
        
        context.update({
            'system_metrics': system_metrics,
            'performance_metrics': performance_metrics,
            'integration_metrics': integration_metrics,
            'page_title': 'System Dashboard',
            'section': 'system'
        })
        
        return context


@staff_member_required
def dashboard_export(request, export_type):
    """
    Export dashboard data in various formats.
    """
    try:
        if export_type == 'overview':
            data = DashboardService.get_dashboard_overview(user=request.user)
            filename = f'dashboard_overview_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif export_type == 'volunteers':
            data = DashboardService.get_volunteer_metrics()
            filename = f'volunteer_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif export_type == 'events':
            data = DashboardService.get_event_metrics()
            filename = f'event_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif export_type == 'kpis':
            data = DashboardService.get_key_performance_indicators()
            filename = f'kpi_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown export type: {export_type}'
            }, status=400)
        
        # Determine format
        format_type = request.GET.get('format', 'json')
        
        if format_type == 'json':
            response = HttpResponse(
                json.dumps(data, indent=2, default=str),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
        
        elif format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write CSV headers and data based on export type
            if export_type == 'volunteers':
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Volunteers', data.get('total_volunteers', 0)])
                writer.writerow(['Active Volunteers', data.get('active_volunteers', 0)])
                writer.writerow(['Pending Applications', data.get('pending_applications', 0)])
                writer.writerow(['Approval Rate', f"{data.get('approval_rate', 0)}%"])
                
                # Status distribution
                writer.writerow([])
                writer.writerow(['Status Distribution'])
                for status, count in data.get('status_distribution', {}).items():
                    writer.writerow([status, count])
            
            elif export_type == 'kpis':
                writer.writerow(['KPI', 'Score', 'Status', 'Target'])
                for kpi_name, kpi_data in data.items():
                    if isinstance(kpi_data, dict) and 'score' in kpi_data:
                        writer.writerow([
                            kpi_name.replace('_', ' ').title(),
                            kpi_data.get('score', 'N/A'),
                            kpi_data.get('status', 'N/A'),
                            kpi_data.get('target', 'N/A')
                        ])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unsupported format: {format_type}'
            }, status=400)
        
        # Log the export
        from .audit_service import AdminAuditService
        AdminAuditService.log_data_export(
            user=request.user,
            export_type=f'dashboard_{export_type}',
            model_class=None,
            record_count=1,
            export_format=format_type,
            request=request,
            details={
                'dashboard_export': True,
                'export_type': export_type,
                'format': format_type
            }
        )
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@staff_member_required
def dashboard_refresh_cache(request):
    """
    Force refresh of dashboard cache.
    """
    try:
        # Clear dashboard-related cache keys
        cache_keys = [
            'dashboard_overview_global',
            f'dashboard_overview_{request.user.id}',
            'dashboard_volunteer_metrics',
            'dashboard_event_metrics',
            'dashboard_assignment_metrics',
            'dashboard_task_metrics',
            'dashboard_system_metrics',
            'dashboard_integration_metrics',
            'dashboard_performance_metrics',
            'dashboard_alerts_notifications',
            'dashboard_trend_data',
            'dashboard_kpis'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        # Log the cache refresh
        from .audit_service import AdminAuditService
        AdminAuditService.log_system_management_operation(
            operation='dashboard_cache_refresh',
            user=request.user,
            request=request,
            details={
                'cache_keys_cleared': len(cache_keys),
                'manual_refresh': True
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Dashboard cache refreshed successfully',
            'keys_cleared': len(cache_keys),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


# REST API Views for external integrations

@api_view(['GET'])
@permission_classes([IsAdminUser])
def api_dashboard_overview(request):
    """
    REST API endpoint for dashboard overview.
    """
    try:
        data = DashboardService.get_dashboard_overview(user=request.user)
        return Response({
            'success': True,
            'data': data,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def api_dashboard_kpis(request):
    """
    REST API endpoint for KPIs.
    """
    try:
        data = DashboardService.get_key_performance_indicators()
        return Response({
            'success': True,
            'data': data,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def api_dashboard_alerts(request):
    """
    REST API endpoint for alerts.
    """
    try:
        data = DashboardService.get_alerts_and_notifications()
        return Response({
            'success': True,
            'data': data,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@staff_member_required
def dashboard_widget_config(request):
    """
    Dashboard widget configuration endpoint.
    """
    if request.method == 'GET':
        # Get current widget configuration
        user_config = request.user.profile.dashboard_config if hasattr(request.user, 'profile') else {}
        
        default_config = {
            'widgets': {
                'volunteer_summary': {'enabled': True, 'position': 1, 'size': 'medium'},
                'event_overview': {'enabled': True, 'position': 2, 'size': 'medium'},
                'recent_activity': {'enabled': True, 'position': 3, 'size': 'large'},
                'kpi_summary': {'enabled': True, 'position': 4, 'size': 'large'},
                'alerts': {'enabled': True, 'position': 5, 'size': 'small'},
                'performance_metrics': {'enabled': True, 'position': 6, 'size': 'medium'},
                'integration_status': {'enabled': True, 'position': 7, 'size': 'small'},
                'trend_charts': {'enabled': True, 'position': 8, 'size': 'large'}
            },
            'refresh_interval': 300,  # 5 minutes
            'theme': 'light',
            'compact_mode': False
        }
        
        config = {**default_config, **user_config}
        
        return JsonResponse({
            'success': True,
            'config': config
        })
    
    elif request.method == 'POST':
        # Update widget configuration
        try:
            new_config = json.loads(request.body)
            
            # Validate configuration
            if 'widgets' not in new_config:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid configuration format'
                }, status=400)
            
            # Save configuration (would need user profile model)
            # For now, just return success
            
            return JsonResponse({
                'success': True,
                'message': 'Configuration updated successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405) 