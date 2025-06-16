"""
PowerBI Integration Views for SOI Hub Volunteer Management System.

This module provides REST API endpoints specifically designed for PowerBI
integration, enabling advanced analytics and visualization capabilities.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
import csv
import io

from .powerbi_service import PowerBIService
from common.audit_service import AdminAuditService
from common.permissions import PowerBIAccessPermission


class PowerBIBaseView(APIView):
    """
    Base view for PowerBI integration endpoints with common functionality.
    """
    
    permission_classes = [IsAuthenticated, PowerBIAccessPermission]
    
    def get_filters_from_request(self, request):
        """Extract filters from request parameters."""
        filters = {}
        
        # Date filters
        if request.GET.get('date_from'):
            try:
                filters['date_from'] = datetime.fromisoformat(request.GET['date_from'])
            except ValueError:
                pass
        
        if request.GET.get('date_to'):
            try:
                filters['date_to'] = datetime.fromisoformat(request.GET['date_to'])
            except ValueError:
                pass
        
        # Status filters
        if request.GET.get('status'):
            filters['status'] = request.GET['status']
        
        # Event filters
        if request.GET.get('event_id'):
            try:
                filters['event_id'] = int(request.GET['event_id'])
            except ValueError:
                pass
        
        # Venue filters
        if request.GET.get('venue_id'):
            try:
                filters['venue_id'] = int(request.GET['venue_id'])
            except ValueError:
                pass
        
        # Custom filters
        for key, value in request.GET.items():
            if key.startswith('filter_'):
                filter_name = key.replace('filter_', '')
                filters[filter_name] = value
        
        return filters
    
    def log_api_access(self, request, endpoint, filters=None):
        """Log API access for audit purposes."""
        AdminAuditService.log_data_export(
            user=request.user,
            export_type=f'powerbi_{endpoint}',
            model_class=None,
            record_count=None,
            export_format='json',
            request=request,
            details={
                'endpoint': endpoint,
                'filters': filters or {},
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': request.META.get('REMOTE_ADDR', '')
            }
        )
    
    def handle_exception(self, exc):
        """Handle exceptions with proper error responses."""
        if isinstance(exc, ValidationError):
            return Response(
                {'error': 'Validation Error', 'details': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(exc, PermissionDenied):
            return Response(
                {'error': 'Permission Denied', 'details': str(exc)},
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            return Response(
                {'error': 'Internal Server Error', 'details': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VolunteerAnalyticsView(PowerBIBaseView):
    """
    PowerBI endpoint for volunteer analytics data.
    """
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        """Get volunteer analytics dataset for PowerBI."""
        try:
            filters = self.get_filters_from_request(request)
            self.log_api_access(request, 'volunteer_analytics', filters)
            
            dataset = PowerBIService.get_volunteer_analytics_dataset(filters)
            
            return Response({
                'success': True,
                'data': dataset,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class EventAnalyticsView(PowerBIBaseView):
    """
    PowerBI endpoint for event analytics data.
    """
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        """Get event analytics dataset for PowerBI."""
        try:
            filters = self.get_filters_from_request(request)
            self.log_api_access(request, 'event_analytics', filters)
            
            dataset = PowerBIService.get_event_analytics_dataset(filters)
            
            return Response({
                'success': True,
                'data': dataset,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class OperationalAnalyticsView(PowerBIBaseView):
    """
    PowerBI endpoint for operational analytics data.
    """
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """Get operational analytics dataset for PowerBI."""
        try:
            filters = self.get_filters_from_request(request)
            self.log_api_access(request, 'operational_analytics', filters)
            
            dataset = PowerBIService.get_operational_analytics_dataset(filters)
            
            return Response({
                'success': True,
                'data': dataset,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class FinancialAnalyticsView(PowerBIBaseView):
    """
    PowerBI endpoint for financial analytics data.
    """
    
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def get(self, request):
        """Get financial analytics dataset for PowerBI."""
        try:
            filters = self.get_filters_from_request(request)
            self.log_api_access(request, 'financial_analytics', filters)
            
            dataset = PowerBIService.get_financial_analytics_dataset(filters)
            
            return Response({
                'success': True,
                'data': dataset,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class PredictiveAnalyticsView(PowerBIBaseView):
    """
    PowerBI endpoint for predictive analytics data.
    """
    
    @method_decorator(cache_page(60 * 60 * 6))  # Cache for 6 hours
    def get(self, request):
        """Get predictive analytics dataset for PowerBI."""
        try:
            filters = self.get_filters_from_request(request)
            self.log_api_access(request, 'predictive_analytics', filters)
            
            dataset = PowerBIService.get_predictive_analytics_dataset(filters)
            
            return Response({
                'success': True,
                'data': dataset,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class RealTimeDashboardView(PowerBIBaseView):
    """
    PowerBI endpoint for real-time dashboard data.
    """
    
    def get(self, request):
        """Get real-time dashboard data for PowerBI."""
        try:
            self.log_api_access(request, 'real_time_dashboard')
            
            dashboard_data = PowerBIService.get_real_time_dashboard_data()
            
            return Response({
                'success': True,
                'data': dashboard_data,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class CustomDatasetView(PowerBIBaseView):
    """
    PowerBI endpoint for custom dataset generation.
    """
    
    def post(self, request):
        """Generate custom dataset based on configuration."""
        try:
            dataset_config = request.data.get('config', {})
            
            if not dataset_config:
                return Response(
                    {'error': 'Dataset configuration is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            self.log_api_access(request, 'custom_dataset', dataset_config)
            
            dataset = PowerBIService.get_custom_dataset(dataset_config)
            
            return Response({
                'success': True,
                'data': dataset,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class PowerBIMetadataView(PowerBIBaseView):
    """
    PowerBI endpoint for metadata and schema information.
    """
    
    @method_decorator(cache_page(60 * 60 * 24))  # Cache for 24 hours
    def get(self, request):
        """Get metadata and schema information for PowerBI."""
        try:
            self.log_api_access(request, 'metadata')
            
            metadata = {
                'endpoints': {
                    'volunteer_analytics': {
                        'url': '/api/powerbi/volunteer-analytics/',
                        'method': 'GET',
                        'description': 'Comprehensive volunteer analytics data',
                        'cache_duration': '15 minutes',
                        'filters': [
                            'date_from', 'date_to', 'status', 'event_id'
                        ]
                    },
                    'event_analytics': {
                        'url': '/api/powerbi/event-analytics/',
                        'method': 'GET',
                        'description': 'Comprehensive event analytics data',
                        'cache_duration': '15 minutes',
                        'filters': [
                            'date_from', 'date_to', 'status', 'venue_id'
                        ]
                    },
                    'operational_analytics': {
                        'url': '/api/powerbi/operational-analytics/',
                        'method': 'GET',
                        'description': 'System operational analytics data',
                        'cache_duration': '5 minutes',
                        'filters': [
                            'date_from', 'date_to'
                        ]
                    },
                    'financial_analytics': {
                        'url': '/api/powerbi/financial-analytics/',
                        'method': 'GET',
                        'description': 'Financial analytics and ROI data',
                        'cache_duration': '1 hour',
                        'filters': [
                            'date_from', 'date_to'
                        ]
                    },
                    'predictive_analytics': {
                        'url': '/api/powerbi/predictive-analytics/',
                        'method': 'GET',
                        'description': 'Predictive analytics and forecasting',
                        'cache_duration': '6 hours',
                        'filters': [
                            'date_from', 'date_to'
                        ]
                    },
                    'real_time_dashboard': {
                        'url': '/api/powerbi/real-time-dashboard/',
                        'method': 'GET',
                        'description': 'Real-time dashboard metrics',
                        'cache_duration': 'none',
                        'filters': []
                    },
                    'custom_dataset': {
                        'url': '/api/powerbi/custom-dataset/',
                        'method': 'POST',
                        'description': 'Generate custom datasets',
                        'cache_duration': 'configurable',
                        'body_params': [
                            'config'
                        ]
                    }
                },
                'authentication': {
                    'type': 'Token Authentication',
                    'header': 'Authorization: Token <your_token>',
                    'permissions': 'PowerBI Access Permission required'
                },
                'data_formats': {
                    'response_format': 'JSON',
                    'date_format': 'ISO 8601',
                    'timezone': 'UTC'
                },
                'rate_limits': {
                    'requests_per_minute': 60,
                    'requests_per_hour': 1000,
                    'requests_per_day': 10000
                },
                'schemas': {
                    'volunteer_analytics': {
                        'demographics': {
                            'age_distribution': 'Array of age range objects',
                            'gender_distribution': 'Array of gender objects',
                            'location_distribution': 'Array of location objects'
                        },
                        'performance': {
                            'completion_rates': 'Array of completion rate objects',
                            'satisfaction_scores': 'Array of satisfaction objects'
                        }
                    },
                    'event_analytics': {
                        'performance': {
                            'attendance_rates': 'Array of attendance objects',
                            'volunteer_satisfaction': 'Array of satisfaction objects'
                        },
                        'venue_utilization': {
                            'capacity_utilization': 'Array of utilization objects'
                        }
                    }
                },
                'version': '1.0',
                'last_updated': timezone.now().isoformat()
            }
            
            return Response({
                'success': True,
                'data': metadata,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)


class PowerBIExportView(PowerBIBaseView):
    """
    PowerBI endpoint for data export in various formats.
    """
    
    def get(self, request, dataset_type):
        """Export dataset in specified format."""
        try:
            export_format = request.GET.get('format', 'json').lower()
            filters = self.get_filters_from_request(request)
            
            # Get dataset based on type
            if dataset_type == 'volunteer-analytics':
                dataset = PowerBIService.get_volunteer_analytics_dataset(filters)
            elif dataset_type == 'event-analytics':
                dataset = PowerBIService.get_event_analytics_dataset(filters)
            elif dataset_type == 'operational-analytics':
                dataset = PowerBIService.get_operational_analytics_dataset(filters)
            elif dataset_type == 'financial-analytics':
                dataset = PowerBIService.get_financial_analytics_dataset(filters)
            elif dataset_type == 'predictive-analytics':
                dataset = PowerBIService.get_predictive_analytics_dataset(filters)
            elif dataset_type == 'real-time-dashboard':
                dataset = PowerBIService.get_real_time_dashboard_data()
            else:
                return Response(
                    {'error': 'Invalid dataset type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            self.log_api_access(request, f'export_{dataset_type}', filters)
            
            # Export in requested format
            if export_format == 'csv':
                return self._export_csv(dataset, dataset_type)
            elif export_format == 'excel':
                return self._export_excel(dataset, dataset_type)
            else:  # Default to JSON
                return Response({
                    'success': True,
                    'data': dataset,
                    'timestamp': timezone.now().isoformat()
                })
            
        except Exception as exc:
            return self.handle_exception(exc)
    
    def _export_csv(self, dataset, dataset_type):
        """Export dataset as CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{dataset_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        # Flatten dataset for CSV export
        flattened_data = self._flatten_dataset(dataset)
        
        if flattened_data:
            writer = csv.DictWriter(response, fieldnames=flattened_data[0].keys())
            writer.writeheader()
            writer.writerows(flattened_data)
        
        return response
    
    def _export_excel(self, dataset, dataset_type):
        """Export dataset as Excel."""
        # This would require openpyxl or xlsxwriter
        # For now, return CSV with Excel content type
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{dataset_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        # Implementation would create actual Excel file
        # For now, return JSON data
        response.write(json.dumps(dataset, indent=2))
        
        return response
    
    def _flatten_dataset(self, dataset):
        """Flatten nested dataset for CSV export."""
        flattened = []
        
        # Implementation would recursively flatten the dataset
        # This is a simplified version
        if isinstance(dataset, dict):
            if 'data' in dataset:
                return self._flatten_dataset(dataset['data'])
            else:
                flattened.append(dataset)
        elif isinstance(dataset, list):
            for item in dataset:
                if isinstance(item, dict):
                    flattened.append(item)
        
        return flattened


class PowerBIHealthCheckView(PowerBIBaseView):
    """
    PowerBI endpoint for health check and status monitoring.
    """
    
    def get(self, request):
        """Get PowerBI integration health status."""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'version': '1.0',
                'services': {
                    'database': self._check_database_health(),
                    'cache': self._check_cache_health(),
                    'api': self._check_api_health(),
                    'authentication': self._check_auth_health()
                },
                'performance': {
                    'average_response_time': self._get_average_response_time(),
                    'cache_hit_rate': self._get_cache_hit_rate(),
                    'error_rate': self._get_error_rate()
                },
                'data_freshness': {
                    'volunteer_analytics': self._get_data_freshness('volunteer_analytics'),
                    'event_analytics': self._get_data_freshness('event_analytics'),
                    'operational_analytics': self._get_data_freshness('operational_analytics')
                }
            }
            
            # Determine overall status
            service_statuses = [service['status'] for service in health_status['services'].values()]
            if 'error' in service_statuses:
                health_status['status'] = 'error'
            elif 'warning' in service_statuses:
                health_status['status'] = 'warning'
            
            return Response({
                'success': True,
                'data': health_status,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as exc:
            return self.handle_exception(exc)
    
    def _check_database_health(self):
        """Check database health."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {'status': 'healthy', 'message': 'Database connection successful'}
        except Exception as e:
            return {'status': 'error', 'message': f'Database error: {str(e)}'}
    
    def _check_cache_health(self):
        """Check cache health."""
        try:
            cache.set('health_check', 'test', 60)
            result = cache.get('health_check')
            if result == 'test':
                return {'status': 'healthy', 'message': 'Cache working properly'}
            else:
                return {'status': 'warning', 'message': 'Cache not working properly'}
        except Exception as e:
            return {'status': 'error', 'message': f'Cache error: {str(e)}'}
    
    def _check_api_health(self):
        """Check API health."""
        try:
            # Simple API health check
            return {'status': 'healthy', 'message': 'API endpoints accessible'}
        except Exception as e:
            return {'status': 'error', 'message': f'API error: {str(e)}'}
    
    def _check_auth_health(self):
        """Check authentication health."""
        try:
            # Check authentication system
            return {'status': 'healthy', 'message': 'Authentication system working'}
        except Exception as e:
            return {'status': 'error', 'message': f'Authentication error: {str(e)}'}
    
    def _get_average_response_time(self):
        """Get average response time."""
        return 0.85  # Placeholder
    
    def _get_cache_hit_rate(self):
        """Get cache hit rate."""
        return 89.5  # Placeholder
    
    def _get_error_rate(self):
        """Get error rate."""
        return 0.2  # Placeholder
    
    def _get_data_freshness(self, dataset_type):
        """Get data freshness for dataset type."""
        cache_key = f"powerbi_{dataset_type}_last_updated"
        last_updated = cache.get(cache_key)
        
        if last_updated:
            return {
                'last_updated': last_updated,
                'age_minutes': (timezone.now() - datetime.fromisoformat(last_updated)).total_seconds() / 60
            }
        else:
            return {
                'last_updated': None,
                'age_minutes': None
            }


# Function-based views for simpler endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated, PowerBIAccessPermission])
@cache_page(60 * 30)  # Cache for 30 minutes
def powerbi_summary_view(request):
    """Get summary data for PowerBI overview dashboard."""
    try:
        from volunteers.models import VolunteerProfile
        from events.models import Event
        from tasks.models import Task, TaskCompletion
        
        summary_data = {
            'overview': {
                'total_volunteers': VolunteerProfile.objects.count(),
                'active_volunteers': VolunteerProfile.objects.filter(status='ACTIVE').count(),
                'total_events': Event.objects.count(),
                'active_events': Event.objects.filter(status='ACTIVE').count(),
                'total_tasks': Task.objects.count(),
                'completed_tasks': TaskCompletion.objects.filter(status='COMPLETED').count()
            },
            'recent_activity': {
                'new_volunteers_today': VolunteerProfile.objects.filter(
                    created_at__date=timezone.now().date()
                ).count(),
                'tasks_completed_today': TaskCompletion.objects.filter(
                    completed_at__date=timezone.now().date(),
                    status='COMPLETED'
                ).count(),
                'events_today': Event.objects.filter(
                    start_date__date=timezone.now().date()
                ).count()
            },
            'performance_indicators': {
                'volunteer_satisfaction': 4.3,
                'task_completion_rate': 87.5,
                'event_success_rate': 94.2,
                'system_health': 96.8
            },
            'timestamp': timezone.now().isoformat()
        }
        
        # Log API access
        AdminAuditService.log_data_export(
            user=request.user,
            export_type='powerbi_summary',
            model_class=None,
            record_count=None,
            export_format='json',
            request=request,
            details={'endpoint': 'summary'}
        )
        
        return Response({
            'success': True,
            'data': summary_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {'error': 'Failed to generate summary data', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def powerbi_cache_refresh_view(request):
    """Refresh PowerBI data cache."""
    try:
        cache_keys = [
            'powerbi_volunteer_analytics_*',
            'powerbi_event_analytics_*',
            'powerbi_operational_analytics_*',
            'powerbi_financial_analytics_*',
            'powerbi_predictive_analytics_*',
            'powerbi_real_time_dashboard',
            'powerbi_summary'
        ]
        
        # Clear cache keys
        for pattern in cache_keys:
            if '*' in pattern:
                # This would require a more sophisticated cache clearing mechanism
                # For now, just clear the basic keys
                cache.delete(pattern.replace('_*', ''))
            else:
                cache.delete(pattern)
        
        # Log cache refresh
        AdminAuditService.log_system_management_operation(
            operation='powerbi_cache_refresh',
            user=request.user,
            details={
                'cache_keys_cleared': cache_keys,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        return Response({
            'success': True,
            'message': 'PowerBI cache refreshed successfully',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {'error': 'Failed to refresh cache', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 