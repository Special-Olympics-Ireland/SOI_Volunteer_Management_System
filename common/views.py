"""
Views for common app including admin override API
"""

from django.shortcuts import render
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from rest_framework.pagination import PageNumberPagination
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .models import AdminOverride, AuditLog, SystemConfig
from .serializers import (
    AdminOverrideListSerializer, AdminOverrideDetailSerializer,
    AdminOverrideCreateSerializer, AdminOverrideUpdateSerializer,
    AdminOverrideStatusSerializer, AdminOverrideMonitoringSerializer,
    AdminOverrideBulkOperationSerializer, AdminOverrideStatsSerializer,
    AuditLogSerializer, SystemConfigSerializer
)
from .permissions import (
    AdminOverridePermission, AdminOverrideApprovalPermission,
    AdminOverrideBulkOperationPermission, AdminOverrideMonitoringPermission,
    AdminOverrideStatsPermission, AuditLogPermission, SystemConfigPermission
)
from .override_service import AdminOverrideService
from .audit_service import AdminAuditService

logger = logging.getLogger(__name__)


class AdminOverrideFilter(django_filters.FilterSet):
    """Filter class for admin overrides"""
    
    override_type = django_filters.ChoiceFilter(choices=AdminOverride.OverrideType.choices)
    status = django_filters.ChoiceFilter(choices=AdminOverride.OverrideStatus.choices)
    risk_level = django_filters.ChoiceFilter(choices=AdminOverride.RiskLevel.choices)
    impact_level = django_filters.ChoiceFilter(choices=AdminOverride.ImpactLevel.choices)
    is_emergency = django_filters.BooleanFilter()
    is_effective = django_filters.BooleanFilter(method='filter_is_effective')
    is_expired = django_filters.BooleanFilter(method='filter_is_expired')
    requires_monitoring = django_filters.BooleanFilter()
    
    # Date filters
    requested_after = django_filters.DateTimeFilter(field_name='requested_at', lookup_expr='gte')
    requested_before = django_filters.DateTimeFilter(field_name='requested_at', lookup_expr='lte')
    approved_after = django_filters.DateTimeFilter(field_name='approved_at', lookup_expr='gte')
    approved_before = django_filters.DateTimeFilter(field_name='approved_at', lookup_expr='lte')
    effective_from_after = django_filters.DateTimeFilter(field_name='effective_from', lookup_expr='gte')
    effective_from_before = django_filters.DateTimeFilter(field_name='effective_from', lookup_expr='lte')
    effective_until_after = django_filters.DateTimeFilter(field_name='effective_until', lookup_expr='gte')
    effective_until_before = django_filters.DateTimeFilter(field_name='effective_until', lookup_expr='lte')
    
    # User filters
    requested_by = django_filters.CharFilter(field_name='requested_by__username')
    approved_by = django_filters.CharFilter(field_name='approved_by__username')
    
    # Priority filters
    priority_min = django_filters.NumberFilter(field_name='priority_level', lookup_expr='gte')
    priority_max = django_filters.NumberFilter(field_name='priority_level', lookup_expr='lte')
    
    # Content type filters
    content_type = django_filters.CharFilter(method='filter_content_type')
    
    # Tag filters
    tags = django_filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = AdminOverride
        fields = [
            'override_type', 'status', 'risk_level', 'impact_level',
            'is_emergency', 'requires_monitoring'
        ]
    
    def filter_is_effective(self, queryset, name, value):
        now = timezone.now()
        if value:
            return queryset.filter(
                Q(status='ACTIVE') &
                Q(effective_from__lte=now) &
                (Q(effective_until__isnull=True) | Q(effective_until__gte=now))
            )
        else:
            return queryset.exclude(
                Q(status='ACTIVE') &
                Q(effective_from__lte=now) &
                (Q(effective_until__isnull=True) | Q(effective_until__gte=now))
            )
    
    def filter_is_expired(self, queryset, name, value):
        now = timezone.now()
        if value:
            return queryset.filter(
                effective_until__lt=now
            ).exclude(status__in=['EXPIRED', 'REVOKED', 'COMPLETED'])
        else:
            return queryset.exclude(
                effective_until__lt=now
            )
    
    def filter_content_type(self, queryset, name, value):
        try:
            app_label, model = value.split('.')
            content_type = ContentType.objects.get(app_label=app_label, model=model)
            return queryset.filter(content_type=content_type)
        except (ValueError, ContentType.DoesNotExist):
            return queryset.none()
    
    def filter_tags(self, queryset, name, value):
        return queryset.filter(tags__contains=[value])


class AdminOverridePagination(PageNumberPagination):
    """Custom pagination for admin overrides"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminOverrideViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing admin overrides with comprehensive functionality
    """
    
    queryset = AdminOverride.objects.all().select_related(
        'requested_by', 'approved_by', 'reviewed_by', 'status_changed_by', 'content_type'
    ).order_by('-created_at', '-priority_level')
    
    permission_classes = [IsAuthenticated, AdminOverridePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AdminOverrideFilter
    search_fields = ['title', 'description', 'justification', 'business_case']
    ordering_fields = [
        'created_at', 'requested_at', 'approved_at', 'priority_level',
        'risk_level', 'impact_level', 'status', 'override_type'
    ]
    ordering = ['-created_at', '-priority_level']
    pagination_class = AdminOverridePagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AdminOverrideListSerializer
        elif self.action == 'create':
            return AdminOverrideCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AdminOverrideUpdateSerializer
        elif self.action in ['approve', 'reject', 'activate', 'revoke', 'complete']:
            return AdminOverrideStatusSerializer
        elif self.action == 'monitoring':
            return AdminOverrideMonitoringSerializer
        elif self.action == 'bulk_operations':
            return AdminOverrideBulkOperationSerializer
        elif self.action == 'statistics':
            return AdminOverrideStatsSerializer
        else:
            return AdminOverrideDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        
        # Admin and VMT can see all overrides
        if user_type in ['ADMIN', 'VMT']:
            return queryset
        
        # Others can only see overrides they're involved with
        return queryset.filter(
            Q(requested_by=user) |
            Q(approved_by=user) |
            Q(reviewed_by=user) |
            Q(status_changed_by=user)
        )
    
    def perform_create(self, serializer):
        """Create override with audit logging"""
        try:
            with transaction.atomic():
                override = serializer.save()
                
                # Log the creation
                AdminAuditService.log_admin_override(
                    user=self.request.user,
                    override_type=override.override_type,
                    target_object=override.target_object or override,
                    justification=override.justification,
                    request=self.request,
                    details={'action': 'CREATE', 'title': override.title}
                )
                
                logger.info(f"Admin override created: {override.id} by {self.request.user.username}")
                
        except Exception as e:
            logger.error(f"Failed to create admin override: {str(e)}")
            raise
    
    def perform_update(self, serializer):
        """Update override with audit logging"""
        try:
            with transaction.atomic():
                old_instance = self.get_object()
                override = serializer.save()
                
                # Log the update
                AdminAuditService.log_admin_override(
                    user=self.request.user,
                    override_type=override.override_type,
                    target_object=override.target_object or override,
                    justification=override.justification,
                    request=self.request,
                    details={'action': 'UPDATE', 'title': override.title}
                )
                
                logger.info(f"Admin override updated: {override.id} by {self.request.user.username}")
                
        except Exception as e:
            logger.error(f"Failed to update admin override: {str(e)}")
            raise
    
    def perform_destroy(self, instance):
        """Delete override with audit logging"""
        try:
            with transaction.atomic():
                # Log the deletion
                AdminAuditService.log_admin_override(
                    user=self.request.user,
                    override_type=instance.override_type,
                    target_object=instance.target_object or instance,
                    justification=f"Override deletion: {instance.title}",
                    request=self.request,
                    details={'action': 'DELETE', 'title': instance.title}
                )
                
                logger.info(f"Admin override deleted: {instance.id} by {self.request.user.username}")
                
                super().perform_destroy(instance)
                
        except Exception as e:
            logger.error(f"Failed to delete admin override: {str(e)}")
            raise
    
    @action(detail=True, methods=['post'], permission_classes=[AdminOverrideApprovalPermission])
    def approve(self, request, pk=None):
        """Approve an admin override"""
        override = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                notes = serializer.validated_data.get('notes', '')
                auto_activate = request.data.get('auto_activate', False)
                
                updated_override = AdminOverrideService.approve_override(
                    override=override,
                    approved_by=request.user,
                    approval_notes=notes,
                    auto_activate=auto_activate
                )
                
                return Response({
                    'message': 'Override approved successfully',
                    'override': AdminOverrideDetailSerializer(updated_override).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[AdminOverrideApprovalPermission])
    def reject(self, request, pk=None):
        """Reject an admin override"""
        override = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                reason = serializer.validated_data.get('reason', '')
                
                updated_override = AdminOverrideService.reject_override(
                    override=override,
                    rejected_by=request.user,
                    rejection_reason=reason
                )
                
                return Response({
                    'message': 'Override rejected successfully',
                    'override': AdminOverrideDetailSerializer(updated_override).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[AdminOverrideApprovalPermission])
    def activate(self, request, pk=None):
        """Activate an approved override"""
        override = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                notes = serializer.validated_data.get('notes', '')
                
                updated_override = AdminOverrideService.activate_override(
                    override=override,
                    activated_by=request.user,
                    activation_notes=notes
                )
                
                return Response({
                    'message': 'Override activated successfully',
                    'override': AdminOverrideDetailSerializer(updated_override).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[AdminOverrideApprovalPermission])
    def revoke(self, request, pk=None):
        """Revoke an active override"""
        override = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                reason = serializer.validated_data.get('reason', '')
                
                updated_override = AdminOverrideService.revoke_override(
                    override=override,
                    revoked_by=request.user,
                    revocation_reason=reason
                )
                
                return Response({
                    'message': 'Override revoked successfully',
                    'override': AdminOverrideDetailSerializer(updated_override).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark an override as completed"""
        override = self.get_object()
        
        try:
            updated_override = override.complete(completed_by=request.user)
            
            # Log the completion
            AdminAuditService.log_admin_override(
                user=request.user,
                override_type=updated_override.override_type,
                target_object=updated_override.target_object or updated_override,
                justification=f"Override completion: {updated_override.title}",
                request=request,
                details={'action': 'COMPLETE', 'title': updated_override.title}
            )
            
            return Response({
                'message': 'Override completed successfully',
                'override': AdminOverrideDetailSerializer(updated_override).data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[AdminOverrideMonitoringPermission])
    def monitoring(self, request, pk=None):
        """Update monitoring information for an override"""
        override = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                notes = serializer.validated_data.get('monitoring_notes', '')
                
                updated_override = AdminOverrideService.update_monitoring(
                    override=override,
                    monitored_by=request.user,
                    monitoring_notes=notes
                )
                
                return Response({
                    'message': 'Monitoring updated successfully',
                    'override': AdminOverrideDetailSerializer(updated_override).data
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AdminOverrideBulkOperationPermission])
    def bulk_operations(self, request):
        """Perform bulk operations on multiple overrides"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                override_ids = serializer.validated_data['override_ids']
                action_type = serializer.validated_data['action']
                notes = serializer.validated_data.get('notes', '')
                reason = serializer.validated_data.get('reason', '')
                tags = serializer.validated_data.get('tags', [])
                priority_level = serializer.validated_data.get('priority_level')
                
                # Get overrides
                overrides = AdminOverride.objects.filter(id__in=override_ids)
                
                if not overrides.exists():
                    return Response(
                        {'error': 'No valid overrides found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                results = []
                errors = []
                
                with transaction.atomic():
                    for override in overrides:
                        try:
                            if action_type == 'approve':
                                updated_override = AdminOverrideService.approve_override(
                                    override=override,
                                    approved_by=request.user,
                                    approval_notes=notes
                                )
                            elif action_type == 'reject':
                                updated_override = AdminOverrideService.reject_override(
                                    override=override,
                                    rejected_by=request.user,
                                    rejection_reason=reason
                                )
                            elif action_type == 'activate':
                                updated_override = AdminOverrideService.activate_override(
                                    override=override,
                                    activated_by=request.user,
                                    activation_notes=notes
                                )
                            elif action_type == 'revoke':
                                updated_override = AdminOverrideService.revoke_override(
                                    override=override,
                                    revoked_by=request.user,
                                    revocation_reason=reason
                                )
                            elif action_type == 'update_tags':
                                override.tags = tags
                                override.save()
                                updated_override = override
                            elif action_type == 'update_priority':
                                override.priority_level = priority_level
                                override.save()
                                updated_override = override
                            
                            results.append({
                                'id': str(updated_override.id),
                                'title': updated_override.title,
                                'status': 'success'
                            })
                            
                        except Exception as e:
                            errors.append({
                                'id': str(override.id),
                                'title': override.title,
                                'error': str(e)
                            })
                
                # Log bulk operation
                AdminAuditService.log_bulk_operation(
                    user=request.user,
                    operation_type=f'bulk_{action_type}_overrides',
                    affected_count=len(results),
                    request=request,
                    details={'action': action_type, 'successful': len(results), 'failed': len(errors)}
                )
                
                return Response({
                    'message': f'Bulk {action_type} completed',
                    'successful': len(results),
                    'failed': len(errors),
                    'results': results,
                    'errors': errors
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[AdminOverrideStatsPermission])
    def statistics(self, request):
        """Get comprehensive statistics about admin overrides"""
        try:
            # Basic counts
            total_overrides = AdminOverride.objects.count()
            pending_overrides = AdminOverride.objects.filter(status='PENDING').count()
            approved_overrides = AdminOverride.objects.filter(status='APPROVED').count()
            active_overrides = AdminOverride.objects.filter(status='ACTIVE').count()
            expired_overrides = AdminOverride.objects.filter(status='EXPIRED').count()
            revoked_overrides = AdminOverride.objects.filter(status='REVOKED').count()
            emergency_overrides = AdminOverride.objects.filter(is_emergency=True).count()
            high_risk_overrides = AdminOverride.objects.filter(risk_level__in=['HIGH', 'CRITICAL']).count()
            
            # Overrides by type
            overrides_by_type = dict(
                AdminOverride.objects.values('override_type').annotate(
                    count=Count('id')
                ).values_list('override_type', 'count')
            )
            
            # Overrides by status
            overrides_by_status = dict(
                AdminOverride.objects.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')
            )
            
            # Overrides by risk level
            overrides_by_risk_level = dict(
                AdminOverride.objects.values('risk_level').annotate(
                    count=Count('id')
                ).values_list('risk_level', 'count')
            )
            
            # Recent activity (last 10 overrides)
            recent_overrides = AdminOverride.objects.select_related(
                'requested_by'
            ).order_by('-created_at')[:10]
            
            recent_activity = []
            for override in recent_overrides:
                recent_activity.append({
                    'id': str(override.id),
                    'title': override.title,
                    'override_type': override.override_type,
                    'status': override.status,
                    'requested_by': override.requested_by.username if override.requested_by else 'Unknown',
                    'created_at': override.created_at.isoformat()
                })
            
            # Expiring soon (next 7 days)
            expiring_soon = AdminOverrideService.get_expiring_overrides(days_ahead=7).count()
            
            # Requires monitoring
            requires_monitoring = AdminOverride.objects.filter(
                requires_monitoring=True,
                status='ACTIVE'
            ).count()
            
            stats_data = {
                'total_overrides': total_overrides,
                'pending_overrides': pending_overrides,
                'approved_overrides': approved_overrides,
                'active_overrides': active_overrides,
                'expired_overrides': expired_overrides,
                'revoked_overrides': revoked_overrides,
                'emergency_overrides': emergency_overrides,
                'high_risk_overrides': high_risk_overrides,
                'overrides_by_type': overrides_by_type,
                'overrides_by_status': overrides_by_status,
                'overrides_by_risk_level': overrides_by_risk_level,
                'recent_activity': recent_activity,
                'expiring_soon': expiring_soon,
                'requires_monitoring': requires_monitoring
            }
            
            serializer = self.get_serializer(stats_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to get override statistics: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending overrides for current user or all (if admin)"""
        user_type = getattr(request.user, 'user_type', None)
        
        if user_type in ['ADMIN', 'VMT']:
            # Admin and VMT can see all pending overrides
            pending_overrides = AdminOverrideService.get_pending_overrides()
        else:
            # Others can only see their own pending overrides
            pending_overrides = AdminOverrideService.get_pending_overrides(user=request.user)
        
        serializer = AdminOverrideListSerializer(pending_overrides, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active overrides"""
        active_overrides = AdminOverrideService.get_active_overrides()
        serializer = AdminOverrideListSerializer(active_overrides, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get overrides expiring soon"""
        days_ahead = int(request.query_params.get('days', 7))
        expiring_overrides = AdminOverrideService.get_expiring_overrides(days_ahead=days_ahead)
        serializer = AdminOverrideListSerializer(expiring_overrides, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available override types"""
        types = [
            {'value': choice[0], 'label': choice[1]}
            for choice in AdminOverride.OverrideType.choices
        ]
        return Response({'override_types': types})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs (read-only)
    """
    
    queryset = AuditLog.objects.all().select_related('user', 'content_type').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, AuditLogPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['action_description', 'user__username', 'object_representation']
    ordering_fields = ['timestamp', 'action_type', 'user__username']
    ordering = ['-timestamp']
    pagination_class = AdminOverridePagination


class SystemConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for system configuration management
    """
    
    queryset = SystemConfig.objects.all().order_by('config_type', 'key')
    serializer_class = SystemConfigSerializer
    permission_classes = [IsAuthenticated, SystemConfigPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['key', 'name', 'description']
    ordering_fields = ['key', 'name', 'config_type', 'created_at', 'updated_at']
    ordering = ['config_type', 'key']


@method_decorator([login_required, staff_member_required], name='dispatch')
class ComprehensiveAPIDocsView(TemplateView):
    """
    Comprehensive API Documentation View - Admin Only
    
    Provides a one-stop site for all API endpoints with:
    - Clear labeling and sequential organization
    - Real-world use cases with code examples
    - Interactive features and professional design
    - Restricted to admin/staff users only
    """
    template_name = 'api_comprehensive_docs.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'SOI Volunteer Management System - API Documentation',
            'user': self.request.user,
            'is_admin': self.request.user.is_staff,
            'system_status': 'operational',
            'total_endpoints': '100+',
            'api_version': 'v1',
        })
        return context 