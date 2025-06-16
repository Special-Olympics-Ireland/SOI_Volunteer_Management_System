"""
EOI API Views for ISG 2026 Volunteer Management System

This module provides REST API endpoints for the Expression of Interest (EOI) system,
enabling external integrations and programmatic access to volunteer registration data.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
import logging

from .eoi_models import (
    EOISubmission,
    EOIProfileInformation,
    EOIRecruitmentPreferences,
    EOIGamesInformation,
    CorporateVolunteerGroup
)
from .eoi_serializers import (
    EOISubmissionSerializer,
    EOISubmissionCreateSerializer,
    EOISubmissionUpdateSerializer,
    EOISubmissionListSerializer,
    EOIProfileInformationSerializer,
    EOIRecruitmentPreferencesSerializer,
    EOIGamesInformationSerializer,
    CorporateVolunteerGroupSerializer,
    EOIStatsSerializer
)
from .permissions import IsStaffOrVMTOrCVT
from common.audit import log_audit_event

logger = logging.getLogger(__name__)


class EOISubmissionPagination(PageNumberPagination):
    """Custom pagination for EOI submissions"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class EOISubmissionListCreateAPIView(generics.ListCreateAPIView):
    """
    List all EOI submissions or create a new one
    
    GET: List submissions (staff only)
    POST: Create new submission (public)
    """
    queryset = EOISubmission.objects.select_related(
        'user', 'profile_information', 'recruitment_preferences', 'games_information'
    ).order_by('-created_at')
    pagination_class = EOISubmissionPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'volunteer_type', 'confirmation_email_sent']
    search_fields = ['profile_information__first_name', 'profile_information__last_name', 'profile_information__email']
    ordering_fields = ['created_at', 'submitted_at', 'completion_percentage']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EOISubmissionCreateSerializer
        return EOISubmissionListSerializer
    
    def get_permissions(self):
        """
        GET requires staff permissions, POST is public
        """
        if self.request.method == 'GET':
            permission_classes = [IsStaffOrVMTOrCVT]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Create EOI submission with audit logging"""
        # Set user if authenticated
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            # For anonymous users, set session key
            if not self.request.session.session_key:
                self.request.session.create()
            serializer.save(session_key=self.request.session.session_key)
        
        # Log audit event
        log_audit_event(
            user=self.request.user if self.request.user.is_authenticated else None,
            action='EOI_SUBMITTED_API',
            resource_type='EOISubmission',
            resource_id=str(serializer.instance.id),
            details={
                'volunteer_type': serializer.instance.volunteer_type,
                'via_api': True,
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self.request.META.get('REMOTE_ADDR', '')
            }
        )


class EOISubmissionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an EOI submission
    
    GET: Retrieve submission details
    PUT/PATCH: Update submission (staff only)
    DELETE: Delete submission (staff only)
    """
    queryset = EOISubmission.objects.select_related(
        'user', 'profile_information', 'recruitment_preferences', 'games_information'
    )
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return EOISubmissionUpdateSerializer
        return EOISubmissionSerializer
    
    def get_permissions(self):
        """
        GET: Owner or staff can view
        PUT/PATCH/DELETE: Staff only
        """
        if self.request.method == 'GET':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsStaffOrVMTOrCVT]
        return [permission() for permission in permission_classes]
    
    def get_object(self):
        """Get object with access control"""
        obj = super().get_object()
        
        # For GET requests, check if user has access
        if self.request.method == 'GET':
            if not self.request.user.is_staff:
                # Non-staff users can only access their own submissions
                if obj.user != self.request.user:
                    # Also check session key for anonymous submissions
                    if not (obj.session_key and obj.session_key == self.request.session.session_key):
                        raise permissions.PermissionDenied("You don't have permission to access this submission.")
        
        return obj
    
    def perform_update(self, serializer):
        """Update with audit logging"""
        old_status = self.get_object().status
        serializer.save(reviewed_at=timezone.now())
        
        # Log status change if applicable
        if 'status' in serializer.validated_data:
            new_status = serializer.validated_data['status']
            if old_status != new_status:
                log_audit_event(
                    user=self.request.user,
                    action='EOI_STATUS_CHANGED',
                    resource_type='EOISubmission',
                    resource_id=str(serializer.instance.id),
                    details={
                        'old_status': old_status,
                        'new_status': new_status,
                        'reviewer_notes': serializer.validated_data.get('reviewer_notes', ''),
                        'via_api': True
                    }
                )
    
    def perform_destroy(self, instance):
        """Delete with audit logging"""
        log_audit_event(
            user=self.request.user,
            action='EOI_DELETED',
            resource_type='EOISubmission',
            resource_id=str(instance.id),
            details={
                'volunteer_type': instance.volunteer_type,
                'status': instance.status,
                'via_api': True
            }
        )
        instance.delete()


class CorporateVolunteerGroupListCreateAPIView(generics.ListCreateAPIView):
    """
    List all corporate groups or create a new one
    
    GET: List active groups (public)
    POST: Create new group (public)
    """
    serializer_class = CorporateVolunteerGroupSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'industry_sector']
    search_fields = ['name', 'description', 'primary_contact_name']
    ordering_fields = ['name', 'created_at', 'expected_volunteer_count']
    ordering = ['name']
    
    def get_queryset(self):
        """Return active groups for GET, all for staff"""
        if self.request.method == 'GET':
            return CorporateVolunteerGroup.objects.filter(status='ACTIVE')
        return CorporateVolunteerGroup.objects.all()
    
    def get_permissions(self):
        """
        GET: Public access to active groups
        POST: Public registration
        """
        return [permissions.AllowAny()]
    
    def perform_create(self, serializer):
        """Create corporate group with audit logging"""
        serializer.save()
        
        log_audit_event(
            user=self.request.user if self.request.user.is_authenticated else None,
            action='CORPORATE_GROUP_REGISTERED',
            resource_type='CorporateVolunteerGroup',
            resource_id=str(serializer.instance.id),
            details={
                'group_name': serializer.instance.name,
                'expected_volunteers': serializer.instance.expected_volunteer_count,
                'via_api': True,
                'contact_email': serializer.instance.primary_contact_email
            }
        )


class CorporateVolunteerGroupDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a corporate group
    
    GET: Retrieve group details (public for active groups)
    PUT/PATCH: Update group (staff only)
    DELETE: Delete group (staff only)
    """
    queryset = CorporateVolunteerGroup.objects.all()
    serializer_class = CorporateVolunteerGroupSerializer
    
    def get_permissions(self):
        """
        GET: Public for active groups, staff for all
        PUT/PATCH/DELETE: Staff only
        """
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsStaffOrVMTOrCVT()]
    
    def get_object(self):
        """Get object with access control for non-staff users"""
        obj = super().get_object()
        
        if self.request.method == 'GET' and not self.request.user.is_staff:
            # Non-staff users can only view active groups
            if obj.status != 'ACTIVE':
                raise permissions.PermissionDenied("This group is not publicly accessible.")
        
        return obj


@api_view(['GET'])
@permission_classes([IsStaffOrVMTOrCVT])
def eoi_stats_api_view(request):
    """
    Get EOI statistics
    
    Returns comprehensive statistics about EOI submissions
    """
    try:
        # Get basic counts
        total_submissions = EOISubmission.objects.count()
        
        # Count by status
        status_counts = EOISubmission.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        by_status = {item['status']: item['count'] for item in status_counts}
        
        # Count by volunteer type
        type_counts = EOISubmission.objects.values('volunteer_type').annotate(
            count=Count('id')
        ).order_by('volunteer_type')
        by_volunteer_type = {item['volunteer_type']: item['count'] for item in type_counts}
        
        # Calculate completion rate
        completed_submissions = EOISubmission.objects.filter(
            profile_completed=True,
            recruitment_completed=True,
            games_completed=True
        ).count()
        completion_rate = (completed_submissions / total_submissions * 100) if total_submissions > 0 else 0
        
        # Recent submissions (last 7 days)
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        recent_submissions = EOISubmission.objects.filter(created_at__gte=recent_date).count()
        
        # Pending review count
        pending_review = EOISubmission.objects.filter(status='UNDER_REVIEW').count()
        
        # Approved count
        approved_count = EOISubmission.objects.filter(status='APPROVED').count()
        
        stats_data = {
            'total_submissions': total_submissions,
            'by_status': by_status,
            'by_volunteer_type': by_volunteer_type,
            'completion_rate': round(completion_rate, 2),
            'recent_submissions': recent_submissions,
            'pending_review': pending_review,
            'approved_count': approved_count
        }
        
        serializer = EOIStatsSerializer(stats_data)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error generating EOI stats: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsStaffOrVMTOrCVT])
def bulk_update_eoi_status(request):
    """
    Bulk update EOI submission statuses
    
    Expected payload:
    {
        "submission_ids": [uuid1, uuid2, ...],
        "status": "APPROVED",
        "reviewer_notes": "Bulk approval"
    }
    """
    try:
        submission_ids = request.data.get('submission_ids', [])
        new_status = request.data.get('status')
        reviewer_notes = request.data.get('reviewer_notes', '')
        
        if not submission_ids or not new_status:
            return Response(
                {'error': 'submission_ids and status are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status
        valid_statuses = [choice[0] for choice in EOISubmission.EOIStatus.choices]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update submissions
        submissions = EOISubmission.objects.filter(id__in=submission_ids)
        updated_count = 0
        
        for submission in submissions:
            old_status = submission.status
            submission.status = new_status
            submission.reviewer_notes = reviewer_notes
            submission.reviewed_at = timezone.now()
            submission.save()
            
            # Log audit event
            log_audit_event(
                user=request.user,
                action='EOI_BULK_STATUS_UPDATE',
                resource_type='EOISubmission',
                resource_id=str(submission.id),
                details={
                    'old_status': old_status,
                    'new_status': new_status,
                    'reviewer_notes': reviewer_notes,
                    'bulk_operation': True,
                    'via_api': True
                }
            )
            updated_count += 1
        
        return Response({
            'message': f'Successfully updated {updated_count} submissions',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def eoi_submission_status_check(request, submission_id):
    """
    Check the status of an EOI submission (public endpoint)
    
    Returns basic status information without sensitive data
    """
    try:
        submission = get_object_or_404(EOISubmission, id=submission_id)
        
        # Basic status information
        data = {
            'id': str(submission.id),
            'status': submission.status,
            'status_display': submission.get_status_display(),
            'completion_percentage': submission.completion_percentage,
            'submitted_at': submission.submitted_at,
            'confirmation_email_sent': submission.confirmation_email_sent
        }
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error checking submission status: {str(e)}")
        return Response(
            {'error': 'Submission not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_confirmation_email(request, submission_id):
    """
    Resend confirmation email for an EOI submission
    """
    try:
        submission = get_object_or_404(EOISubmission, id=submission_id)
        
        # Verify access (user owns submission or has session key)
        if request.user.is_authenticated:
            if submission.user != request.user and not request.user.is_staff:
                raise permissions.PermissionDenied("You don't have permission to access this submission.")
        else:
            if not (submission.session_key and submission.session_key == request.session.session_key):
                raise permissions.PermissionDenied("You don't have permission to access this submission.")
        
        # Check if submission has profile information with email
        if not submission.profile_information or not submission.profile_information.email:
            return Response(
                {'error': 'No email address found for this submission'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import and call the email function
        from .eoi_views import _send_confirmation_email
        _send_confirmation_email(submission)
        
        # Log audit event
        log_audit_event(
            user=request.user if request.user.is_authenticated else None,
            action='EOI_CONFIRMATION_EMAIL_RESENT',
            resource_type='EOISubmission',
            resource_id=str(submission.id),
            details={
                'email': submission.profile_information.email,
                'via_api': True
            }
        )
        
        return Response({
            'message': 'Confirmation email sent successfully',
            'email': submission.profile_information.email
        })
        
    except permissions.PermissionDenied as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error resending confirmation email: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 