from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, FileResponse
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F
from django.core.cache import cache
from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from datetime import datetime, timedelta
import os
import json
import logging

from .models import Report, ReportTemplate, ReportSchedule, ReportMetrics, ReportShare
from .serializers import (
    ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer,
    ReportTemplateSerializer, ReportScheduleSerializer, ReportShareSerializer,
    AnalyticsSerializer, DashboardStatsSerializer, ReportTypeInfoSerializer,
    BulkReportOperationSerializer, ReportGenerationRequestSerializer,
    ReportProgressSerializer, ReportExportSerializer
)
from .permissions import (
    ReportPermission, ReportTemplatePermission, ReportSchedulePermission,
    ReportSharePermission, AnalyticsPermission, BulkOperationPermission,
    ReportDownloadPermission, SystemStatsPermission, ReportMetricsPermission,
    CustomReportPermission, ReportExportPermission, DashboardPermission
)
from .services import generate_report, ReportGenerationError
from common.audit_service import AdminAuditService
from volunteers.models import VolunteerProfile
from events.models import Event, Assignment
from tasks.models import TaskCompletion
from accounts.models import User

logger = logging.getLogger(__name__)


class ReportPagination(PageNumberPagination):
    """Custom pagination for reports"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class ReportFilter(filters.FilterSet):
    """Filter class for reports"""
    
    report_type = filters.ChoiceFilter(choices=Report.ReportType.choices)
    status = filters.ChoiceFilter(choices=Report.Status.choices)
    export_format = filters.ChoiceFilter(choices=Report.ExportFormat.choices)
    created_by = filters.ModelChoiceFilter(queryset=User.objects.all())
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    completed_after = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    is_expired = filters.BooleanFilter(method='filter_expired')
    
    class Meta:
        model = Report
        fields = [
            'report_type', 'status', 'export_format', 'created_by',
            'created_after', 'created_before', 'completed_after',
            'completed_before', 'is_expired'
        ]
    
    def filter_expired(self, queryset, name, value):
        """Filter by expiration status"""
        now = timezone.now()
        if value:
            return queryset.filter(expires_at__lt=now)
        else:
            return queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports with comprehensive functionality.
    
    Provides CRUD operations, filtering, search, and custom actions for:
    - Report generation and management
    - Progress tracking
    - Download functionality
    - Sharing capabilities
    - Bulk operations
    """
    
    queryset = Report.objects.all()
    permission_classes = [ReportPermission]
    pagination_class = ReportPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ReportFilter
    search_fields = ['name', 'description', 'created_by__first_name', 'created_by__last_name']
    ordering_fields = ['created_at', 'completed_at', 'name', 'status', 'report_type']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ReportListSerializer
        elif self.action == 'create':
            return ReportCreateSerializer
        else:
            return ReportDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        # Staff and management can see all reports
        if (self.request.user.is_staff or 
            self.request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return queryset.select_related('created_by').prefetch_related('shares')
        
        # Regular users can only see their own reports
        return queryset.filter(created_by=self.request.user).select_related('created_by')
    
    def perform_create(self, serializer):
        """Create report and start generation"""
        report = serializer.save(created_by=self.request.user)
        
        # Log report creation
        AdminAuditService.log_report_generation(
            user=self.request.user,
            report_type=report.report_type,
            report_name=report.name,
            parameters=report.parameters
        )
        
        # Start report generation asynchronously
        try:
            generate_report(str(report.id))
        except Exception as e:
            logger.error(f"Failed to start report generation for {report.id}: {str(e)}")
            report.status = Report.Status.FAILED
            report.error_message = f"Failed to start generation: {str(e)}"
            report.save()
    
    @action(detail=True, methods=['get'], permission_classes=[ReportDownloadPermission])
    def download(self, request, pk=None):
        """Download report file"""
        report = self.get_object()
        
        if report.status != Report.Status.COMPLETED:
            return Response(
                {'error': 'Report is not ready for download'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not report.file_path or not os.path.exists(report.file_path):
            return Response(
                {'error': 'Report file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update metrics
        try:
            metrics = report.metrics
            metrics.increment_download_count()
        except ReportMetrics.DoesNotExist:
            pass
        
        # Log download
        AdminAuditService.log_data_export(
            user=request.user,
            export_type='report_download',
            data_type=report.report_type,
            record_count=report.total_records,
            file_format=report.export_format
        )
        
        # Return file response
        response = FileResponse(
            open(report.file_path, 'rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(report.file_path)}"'
        return response
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get report generation progress"""
        report = self.get_object()
        
        # Estimate completion time if in progress
        estimated_completion = None
        if report.status == Report.Status.GENERATING and report.started_at:
            # Simple estimation based on progress
            if report.progress_percentage > 0:
                elapsed = timezone.now() - report.started_at
                total_estimated = elapsed * (100 / report.progress_percentage)
                estimated_completion = report.started_at + total_estimated
        
        serializer = ReportProgressSerializer({
            'report_id': report.id,
            'status': report.status,
            'progress_percentage': report.progress_percentage,
            'current_step': report.error_message if report.status == Report.Status.FAILED else 'Processing...',
            'estimated_completion': estimated_completion,
            'error_message': report.error_message if report.status == Report.Status.FAILED else ''
        })
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate report"""
        report = self.get_object()
        
        # Reset report status
        report.status = Report.Status.PENDING
        report.progress_percentage = 0
        report.error_message = ''
        report.file_path = ''
        report.file_size = 0
        report.started_at = None
        report.completed_at = None
        report.save()
        
        # Log regeneration
        AdminAuditService.log_report_generation(
            user=request.user,
            report_type=report.report_type,
            report_name=f"{report.name} (Regenerated)",
            parameters=report.parameters
        )
        
        # Start generation
        try:
            generate_report(str(report.id))
            return Response({'message': 'Report regeneration started'})
        except Exception as e:
            report.status = Report.Status.FAILED
            report.error_message = f"Failed to start regeneration: {str(e)}"
            report.save()
            return Response(
                {'error': f'Failed to start regeneration: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Create report share"""
        report = self.get_object()
        
        serializer = ReportShareSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            share = serializer.save(report=report)
            return Response(ReportShareSerializer(share).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get report metrics"""
        report = self.get_object()
        
        try:
            metrics = report.metrics
            return Response({
                'query_time': metrics.query_time.total_seconds() if metrics.query_time else None,
                'processing_time': metrics.processing_time.total_seconds() if metrics.processing_time else None,
                'export_time': metrics.export_time.total_seconds() if metrics.export_time else None,
                'memory_usage_mb': metrics.memory_usage_mb,
                'cpu_usage_percent': metrics.cpu_usage_percent,
                'rows_processed': metrics.rows_processed,
                'columns_included': metrics.columns_included,
                'data_completeness_percent': metrics.data_completeness_percent,
                'error_count': metrics.error_count,
                'warning_count': metrics.warning_count,
                'download_count': metrics.download_count,
                'last_downloaded': metrics.last_downloaded
            })
        except ReportMetrics.DoesNotExist:
            return Response({'error': 'Metrics not available'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[BulkOperationPermission])
    def bulk_operations(self, request):
        """Perform bulk operations on reports"""
        serializer = BulkReportOperationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        report_ids = data['report_ids']
        action = data['action']
        parameters = data.get('parameters', {})
        
        # Get reports
        reports = Report.objects.filter(id__in=report_ids)
        if not reports.exists():
            return Response({'error': 'No reports found'}, status=status.HTTP_404_NOT_FOUND)
        
        results = []
        
        if action == 'delete':
            count = reports.count()
            reports.delete()
            results.append(f"Deleted {count} reports")
            
        elif action == 'regenerate':
            for report in reports:
                try:
                    report.status = Report.Status.PENDING
                    report.progress_percentage = 0
                    report.error_message = ''
                    report.save()
                    generate_report(str(report.id))
                    results.append(f"Started regeneration for {report.name}")
                except Exception as e:
                    results.append(f"Failed to regenerate {report.name}: {str(e)}")
        
        elif action == 'share':
            share_type = parameters.get('share_type', 'LINK')
            for report in reports:
                share = ReportShare.objects.create(
                    report=report,
                    share_type=share_type,
                    created_by=request.user
                )
                results.append(f"Created share for {report.name}: {share.get_share_url()}")
        
        # Log bulk operation
        AdminAuditService.log_bulk_operation(
            user=request.user,
            operation_type='report_bulk_operation',
            affected_count=len(report_ids),
            operation_details={'action': action, 'parameters': parameters}
        )
        
        return Response({'results': results})
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available report types with information"""
        report_types = []
        
        for choice in Report.ReportType.choices:
            report_type = choice[0]
            display_name = choice[1]
            
            # Define report type information
            type_info = {
                'report_type': report_type,
                'display_name': display_name,
                'description': self._get_report_description(report_type),
                'required_parameters': self._get_required_parameters(report_type),
                'optional_parameters': self._get_optional_parameters(report_type),
                'supported_formats': ['CSV', 'EXCEL', 'PDF', 'JSON'],
                'estimated_generation_time': self._get_estimated_time(report_type)
            }
            
            report_types.append(type_info)
        
        return Response(report_types)
    
    def _get_report_description(self, report_type):
        """Get description for report type"""
        descriptions = {
            'VOLUNTEER_SUMMARY': 'Summary report of volunteer statistics and status',
            'VOLUNTEER_DETAILED': 'Detailed report with comprehensive volunteer information',
            'EVENT_SUMMARY': 'Summary of events and their key metrics',
            'EVENT_DETAILED': 'Detailed event report with assignments and attendance',
            'VENUE_UTILIZATION': 'Analysis of venue usage and capacity utilization',
            'ROLE_ASSIGNMENT': 'Report on role assignments and fulfillment',
            'TRAINING_STATUS': 'Training completion status across volunteers',
            'BACKGROUND_CHECK': 'Background check status and compliance report',
            'JUSTGO_SYNC': 'JustGo integration synchronization report',
            'EOI_ANALYTICS': 'Expression of Interest analytics and trends',
            'PERFORMANCE_METRICS': 'System performance and usage metrics',
            'ATTENDANCE_TRACKING': 'Volunteer attendance tracking and analysis',
            'CUSTOM': 'Custom report with user-defined parameters'
        }
        return descriptions.get(report_type, 'Custom report type')
    
    def _get_required_parameters(self, report_type):
        """Get required parameters for report type"""
        required_params = {
            'EVENT_DETAILED': ['event_id'],
            'ATTENDANCE_TRACKING': ['event_id'],
            'CUSTOM': ['query', 'columns']
        }
        return required_params.get(report_type, [])
    
    def _get_optional_parameters(self, report_type):
        """Get optional parameters for report type"""
        return ['date_from', 'date_to', 'status_filter', 'venue_filter', 'role_filter']
    
    def _get_estimated_time(self, report_type):
        """Get estimated generation time for report type"""
        times = {
            'VOLUNTEER_SUMMARY': '1-2 minutes',
            'VOLUNTEER_DETAILED': '3-5 minutes',
            'EVENT_SUMMARY': '1-2 minutes',
            'EVENT_DETAILED': '2-4 minutes',
            'VENUE_UTILIZATION': '1-3 minutes',
            'ROLE_ASSIGNMENT': '2-4 minutes',
            'TRAINING_STATUS': '2-3 minutes',
            'BACKGROUND_CHECK': '1-2 minutes',
            'JUSTGO_SYNC': '3-5 minutes',
            'EOI_ANALYTICS': '2-4 minutes',
            'PERFORMANCE_METRICS': '1-2 minutes',
            'ATTENDANCE_TRACKING': '2-3 minutes',
            'CUSTOM': 'Varies'
        }
        return times.get(report_type, '2-5 minutes')


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report templates"""
    
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [ReportTemplatePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['report_type', 'is_active', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'usage_count']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter templates based on user permissions"""
        queryset = super().get_queryset()
        
        # Staff and management can see all templates
        if (self.request.user.is_staff or 
            self.request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return queryset.select_related('created_by')
        
        # Regular users can see public templates and their own
        return queryset.filter(
            Q(is_public=True) | Q(created_by=self.request.user)
        ).select_related('created_by')
    
    @action(detail=True, methods=['post'])
    def use_template(self, request, pk=None):
        """Use template to create a new report"""
        template = self.get_object()
        
        # Increment usage count
        template.increment_usage()
        
        # Create report from template
        serializer = ReportGenerationRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            report = Report.objects.create(
                name=data.get('name', f"Report from {template.name}"),
                description=data.get('description', template.description),
                report_type=template.report_type,
                parameters={**template.default_parameters, **data.get('parameters', {})},
                export_format=data.get('export_format', template.default_export_format),
                created_by=request.user
            )
            
            # Start generation
            try:
                generate_report(str(report.id))
                return Response(ReportDetailSerializer(report).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                report.delete()
                return Response(
                    {'error': f'Failed to generate report: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report schedules"""
    
    queryset = ReportSchedule.objects.all()
    serializer_class = ReportScheduleSerializer
    permission_classes = [ReportSchedulePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['frequency', 'status', 'report_template__report_type']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'next_run']
    ordering = ['next_run']
    
    def get_queryset(self):
        """Filter schedules based on user permissions"""
        return super().get_queryset().select_related('report_template', 'created_by')
    
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Run scheduled report immediately"""
        schedule = self.get_object()
        
        # Create report from schedule
        report = Report.objects.create(
            name=f"{schedule.name} - Manual Run",
            description=f"Manual execution of scheduled report: {schedule.description}",
            report_type=schedule.report_template.report_type,
            parameters=schedule.report_template.default_parameters,
            export_format=schedule.report_template.default_export_format,
            created_by=request.user
        )
        
        # Start generation
        try:
            generate_report(str(report.id))
            return Response(ReportDetailSerializer(report).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            report.delete()
            return Response(
                {'error': f'Failed to run scheduled report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics and dashboard data.
    Provides various analytics endpoints for system insights.
    """
    
    permission_classes = [AnalyticsPermission]
    
    def list(self, request):
        """List available analytics endpoints"""
        endpoints = {
            'dashboard': '/api/reporting/analytics/dashboard/',
            'trends': '/api/reporting/analytics/trends/',
        }
        return Response({
            'message': 'Analytics API endpoints',
            'endpoints': endpoints
        })
    
    @action(detail=False, methods=['get'], permission_classes=[DashboardPermission])
    def dashboard(self, request):
        """Get dashboard statistics"""
        # Cache key for dashboard stats
        cache_key = f"dashboard_stats_{request.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        # Get allowed sections for user
        permission = DashboardPermission()
        allowed_sections = permission.get_allowed_sections(request.user)
        
        stats = {}
        
        if 'volunteers' in allowed_sections:
            stats['volunteers'] = self._get_volunteer_stats()
        
        if 'events' in allowed_sections:
            stats['events'] = self._get_event_stats()
        
        if 'assignments' in allowed_sections:
            stats['assignments'] = self._get_assignment_stats()
        
        if 'tasks' in allowed_sections:
            stats['tasks'] = self._get_task_stats()
        
        if 'reports' in allowed_sections:
            stats['reports'] = self._get_report_stats()
        
        if 'system' in allowed_sections:
            stats['system'] = self._get_system_stats()
        
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)
        
        return Response(stats)
    
    def _get_volunteer_stats(self):
        """Get volunteer statistics"""
        total = VolunteerProfile.objects.count()
        active = VolunteerProfile.objects.filter(status='ACTIVE').count()
        pending = VolunteerProfile.objects.filter(status='PENDING').count()
        
        return {
            'total': total,
            'active': active,
            'pending': pending,
            'approval_rate': round((active / total * 100) if total > 0 else 0, 1)
        }
    
    def _get_event_stats(self):
        """Get event statistics"""
        total = Event.objects.count()
        active = Event.objects.filter(status='ACTIVE').count()
        upcoming = Event.objects.filter(
            status='ACTIVE',
            start_date__gt=timezone.now()
        ).count()
        
        return {
            'total': total,
            'active': active,
            'upcoming': upcoming
        }
    
    def _get_assignment_stats(self):
        """Get assignment statistics"""
        total = Assignment.objects.count()
        confirmed = Assignment.objects.filter(status='CONFIRMED').count()
        pending = Assignment.objects.filter(status='PENDING').count()
        
        return {
            'total': total,
            'confirmed': confirmed,
            'pending': pending,
            'confirmation_rate': round((confirmed / total * 100) if total > 0 else 0, 1)
        }
    
    def _get_task_stats(self):
        """Get task statistics"""
        total = TaskCompletion.objects.count()
        completed = TaskCompletion.objects.filter(status='COMPLETED').count()
        in_progress = TaskCompletion.objects.filter(status='IN_PROGRESS').count()
        
        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1)
        }
    
    def _get_report_stats(self):
        """Get report statistics"""
        total = Report.objects.count()
        completed = Report.objects.filter(status='COMPLETED').count()
        generating = Report.objects.filter(status='GENERATING').count()
        
        return {
            'total': total,
            'completed': completed,
            'generating': generating,
            'success_rate': round((completed / total * 100) if total > 0 else 0, 1)
        }
    
    def _get_system_stats(self):
        """Get system statistics"""
        return {
            'uptime': '99.9%',  # This would come from monitoring system
            'active_users': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=30)).count(),
            'storage_used': '45%',  # This would come from system monitoring
            'api_calls_today': 1250  # This would come from API monitoring
        }
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get trend data for analytics"""
        period = request.query_params.get('period', '30')  # days
        
        try:
            days = int(period)
        except ValueError:
            days = 30
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get daily trends
        trends = {
            'volunteer_registrations': self._get_daily_trend(
                VolunteerProfile.objects.filter(created_at__gte=start_date),
                'created_at',
                days
            ),
            'report_generations': self._get_daily_trend(
                Report.objects.filter(created_at__gte=start_date),
                'created_at',
                days
            ),
            'task_completions': self._get_daily_trend(
                TaskCompletion.objects.filter(completed_at__gte=start_date),
                'completed_at',
                days
            )
        }
        
        return Response(trends)
    
    def _get_daily_trend(self, queryset, date_field, days):
        """Get daily trend data for a queryset"""
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        
        # Get daily counts
        daily_data = queryset.extra(
            select={'day': f'DATE({date_field})'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        # Create complete date range
        result = []
        for i in range(days):
            date = (timezone.now() - timedelta(days=days-i-1)).date()
            count = 0
            
            # Find count for this date
            for item in daily_data:
                if item['day'] == date:
                    count = item['count']
                    break
            
            result.append({
                'date': date.isoformat(),
                'count': count
            })
        
        return result
