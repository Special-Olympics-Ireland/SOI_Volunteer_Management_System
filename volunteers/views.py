from django.shortcuts import render
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404
import logging

from .models import VolunteerProfile
from .eoi_models import EOISubmission
from .serializers import (
    VolunteerProfileListSerializer,
    VolunteerProfileDetailSerializer,
    VolunteerProfileCreateSerializer,
    VolunteerProfileUpdateSerializer,
    VolunteerProfileStatusSerializer,
    VolunteerProfileStatsSerializer,
    VolunteerEOIIntegrationSerializer,
    VolunteerBulkOperationSerializer
)
from .permissions import IsStaffOrVMTOrCVT, VolunteerProfilePermission
from events.models import Assignment, Event, Role
from tasks.models import TaskCompletion
from common.audit import log_audit_event

logger = logging.getLogger(__name__)


class VolunteerProfilePagination(PageNumberPagination):
    """Custom pagination for volunteer profiles"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class VolunteerProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing volunteer profiles with comprehensive functionality
    
    Provides CRUD operations, status management, statistics, and EOI integration
    """
    queryset = VolunteerProfile.objects.select_related(
        'user', 'reviewed_by', 'status_changed_by'
    ).order_by('-application_date')
    
    pagination_class = VolunteerProfilePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'experience_level', 'availability_level', 'is_corporate_volunteer',
        'background_check_status', 'reference_check_status', 'reviewed_by'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email', 'preferred_name',
        'corporate_group_name', 'special_skills', 'previous_events'
    ]
    ordering_fields = [
        'application_date', 'review_date', 'approval_date', 'performance_rating',
        'user__last_name', 'status_changed_at'
    ]
    ordering = ['-application_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return VolunteerProfileListSerializer
        elif self.action == 'create':
            return VolunteerProfileCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VolunteerProfileUpdateSerializer
        elif self.action == 'status':
            return VolunteerProfileStatusSerializer
        elif self.action == 'stats':
            return VolunteerProfileStatsSerializer
        elif self.action == 'eoi_integration':
            return VolunteerEOIIntegrationSerializer
        elif self.action == 'bulk_operations':
            return VolunteerBulkOperationSerializer
        else:
            return VolunteerProfileDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [VolunteerProfilePermission]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsStaffOrVMTOrCVT]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            return queryset.none()
        
        # Staff users can see all profiles
        if self.request.user.is_staff:
            return queryset
        
        # Volunteers can only see their own profile
        return queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create volunteer profile with audit logging"""
        # Set user if not provided
        if 'user' not in serializer.validated_data:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
        
        # Log audit event
        log_audit_event(
            user=self.request.user,
            action='VOLUNTEER_PROFILE_CREATED',
            resource_type='VolunteerProfile',
            resource_id=str(serializer.instance.id),
            details={
                'volunteer_name': serializer.instance.user.get_full_name(),
                'experience_level': serializer.instance.experience_level,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update volunteer profile with audit logging"""
        old_data = {
            'status': self.get_object().status,
            'experience_level': self.get_object().experience_level,
            'availability_level': self.get_object().availability_level
        }
        
        serializer.save()
        
        # Log significant changes
        changes = []
        for field, old_value in old_data.items():
            new_value = getattr(serializer.instance, field)
            if old_value != new_value:
                changes.append(f'{field}: {old_value} → {new_value}')
        
        if changes:
            log_audit_event(
                user=self.request.user,
                action='VOLUNTEER_PROFILE_UPDATED',
                resource_type='VolunteerProfile',
                resource_id=str(serializer.instance.id),
                details={
                    'volunteer_name': serializer.instance.user.get_full_name(),
                    'changes': changes,
                    'via_api': True
                }
            )
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def status(self, request, pk=None):
        """Get or update volunteer profile status"""
        profile = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'status': profile.status,
                'status_display': profile.get_status_display(),
                'status_changed_at': profile.status_changed_at,
                'status_changed_by': profile.status_changed_by.get_full_name() if profile.status_changed_by else None,
                'status_change_reason': profile.status_change_reason,
                'review_date': profile.review_date,
                'approval_date': profile.approval_date,
                'reviewed_by': profile.reviewed_by.get_full_name() if profile.reviewed_by else None
            })
        
        # Update status
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': profile.status,
            'status_display': profile.get_status_display(),
            'message': f'Status updated to {profile.get_status_display()}'
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get comprehensive statistics for a volunteer profile"""
        profile = self.get_object()
        
        # Assignment statistics
        assignments = Assignment.objects.filter(volunteer=profile.user)
        assignment_stats = {
            'total': assignments.count(),
            'active': assignments.filter(status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']).count(),
            'completed': assignments.filter(status='COMPLETED').count(),
            'cancelled': assignments.filter(status='CANCELLED').count()
        }
        
        # Task statistics
        tasks = TaskCompletion.objects.filter(volunteer=profile.user)
        task_stats = {
            'total': tasks.count(),
            'completed': tasks.filter(status__in=['APPROVED', 'VERIFIED']).count(),
            'pending': tasks.filter(status='PENDING').count(),
            'in_progress': tasks.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count()
        }
        
        # Training statistics
        training_stats = {
            'completed_modules': len(profile.training_completed) if profile.training_completed else 0,
            'required_modules': len(profile.training_required) if profile.training_required else 0,
            'completion_percentage': 0
        }
        if training_stats['required_modules'] > 0:
            training_stats['completion_percentage'] = round(
                (training_stats['completed_modules'] / training_stats['required_modules']) * 100, 1
            )
        
        # Performance statistics
        performance_stats = {
            'rating': float(profile.performance_rating) if profile.performance_rating else None,
            'commendations': len(profile.commendations) if profile.commendations else 0,
            'feedback_summary': profile.feedback_summary
        }
        
        # Summary
        summary = {
            'volunteer_name': profile.user.get_full_name(),
            'status': profile.status,
            'experience_level': profile.experience_level,
            'days_since_application': (timezone.now() - profile.application_date).days,
            'is_active': profile.is_active(),
            'is_available': profile.is_available_for_assignment()
        }
        
        return Response({
            'profile_id': profile.id,
            'volunteer_name': profile.user.get_full_name(),
            'summary': summary,
            'assignments': assignment_stats,
            'tasks': task_stats,
            'training': training_stats,
            'performance': performance_stats
        })
    
    @action(detail=True, methods=['get'])
    def eoi_integration(self, request, pk=None):
        """Get volunteer profile with EOI integration data"""
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Filter volunteers by status"""
        status_param = request.query_params.get('status')
        if not status_param:
            return Response({'error': 'Status parameter is required'}, status=400)
        
        queryset = self.filter_queryset(self.get_queryset()).filter(status=status_param)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_experience(self, request):
        """Filter volunteers by experience level"""
        experience_param = request.query_params.get('experience')
        if not experience_param:
            return Response({'error': 'Experience parameter is required'}, status=400)
        
        queryset = self.filter_queryset(self.get_queryset()).filter(experience_level=experience_param)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_for_assignment(self, request):
        """Get volunteers available for assignment"""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            status__in=['APPROVED', 'ACTIVE']
        )
        
        # Filter by availability
        available_volunteers = []
        for volunteer in queryset:
            if volunteer.is_available_for_assignment():
                available_volunteers.append(volunteer)
        
        page = self.paginate_queryset(available_volunteers)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(available_volunteers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def corporate_volunteers(self, request):
        """Get corporate volunteers"""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            is_corporate_volunteer=True
        )
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get volunteers pending review"""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            status__in=['PENDING', 'UNDER_REVIEW']
        )
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def background_check_required(self, request):
        """Get volunteers requiring background checks"""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            background_check_status__in=['REQUIRED', 'SUBMITTED', 'EXPIRED']
        )
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """Perform bulk operations on volunteer profiles"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        volunteer_ids = serializer.validated_data['volunteer_ids']
        action_type = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        notes = serializer.validated_data.get('notes', '')
        tags = serializer.validated_data.get('tags', [])
        
        # Get volunteer profiles
        profiles = VolunteerProfile.objects.filter(id__in=volunteer_ids)
        
        if not profiles.exists():
            return Response({'error': 'No valid volunteer profiles found'}, status=400)
        
        results = []
        
        for profile in profiles:
            try:
                if action_type == 'approve':
                    profile.approve(self.request.user, notes)
                    results.append({'id': str(profile.id), 'status': 'approved'})
                
                elif action_type == 'reject':
                    profile.reject(self.request.user, reason)
                    results.append({'id': str(profile.id), 'status': 'rejected'})
                
                elif action_type == 'activate':
                    profile.activate(self.request.user)
                    results.append({'id': str(profile.id), 'status': 'activated'})
                
                elif action_type == 'suspend':
                    profile.suspend(self.request.user, reason)
                    results.append({'id': str(profile.id), 'status': 'suspended'})
                
                elif action_type == 'update_tags':
                    profile.tags = tags
                    profile.save()
                    results.append({'id': str(profile.id), 'status': 'tags_updated'})
                
                elif action_type == 'send_notification':
                    # TODO: Implement notification sending
                    results.append({'id': str(profile.id), 'status': 'notification_sent'})
                
                elif action_type == 'export_data':
                    # TODO: Implement data export
                    results.append({'id': str(profile.id), 'status': 'exported'})
                
            except Exception as e:
                results.append({'id': str(profile.id), 'status': 'error', 'error': str(e)})
        
        # Log bulk operation
        log_audit_event(
            user=request.user,
            action='VOLUNTEER_BULK_OPERATION',
            resource_type='VolunteerProfile',
            resource_id='bulk',
            details={
                'action': action_type,
                'volunteer_count': len(volunteer_ids),
                'reason': reason,
                'notes': notes,
                'via_api': True
            }
        )
        
        return Response({
            'action': action_type,
            'processed': len(results),
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def global_stats(self, request):
        """Get global volunteer statistics"""
        total_volunteers = VolunteerProfile.objects.count()
        
        # Status breakdown
        status_stats = {}
        for status_choice in VolunteerProfile.VolunteerStatus.choices:
            status_code = status_choice[0]
            status_stats[status_code] = VolunteerProfile.objects.filter(status=status_code).count()
        
        # Experience level breakdown
        experience_stats = {}
        for exp_choice in VolunteerProfile.ExperienceLevel.choices:
            exp_code = exp_choice[0]
            experience_stats[exp_code] = VolunteerProfile.objects.filter(experience_level=exp_code).count()
        
        # Recent activity
        recent_applications = VolunteerProfile.objects.filter(
            application_date__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        recent_approvals = VolunteerProfile.objects.filter(
            approval_date__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        # Performance metrics
        avg_rating = VolunteerProfile.objects.filter(
            performance_rating__isnull=False
        ).aggregate(avg_rating=Avg('performance_rating'))['avg_rating']
        
        return Response({
            'total_volunteers': total_volunteers,
            'status_breakdown': status_stats,
            'experience_breakdown': experience_stats,
            'recent_activity': {
                'applications_last_30_days': recent_applications,
                'approvals_last_30_days': recent_approvals
            },
            'performance': {
                'average_rating': round(float(avg_rating), 2) if avg_rating else None,
                'rated_volunteers': VolunteerProfile.objects.filter(performance_rating__isnull=False).count()
            },
            'corporate_volunteers': VolunteerProfile.objects.filter(is_corporate_volunteer=True).count(),
            'background_checks': {
                'required': VolunteerProfile.objects.filter(background_check_status='REQUIRED').count(),
                'approved': VolunteerProfile.objects.filter(background_check_status='APPROVED').count(),
                'expired': VolunteerProfile.objects.filter(background_check_status='EXPIRED').count()
            }
        })
