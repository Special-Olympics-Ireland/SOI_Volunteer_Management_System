"""
API views for notification system
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
)
from drf_spectacular.types import OpenApiTypes

from .notification_models import (
    NotificationTemplate, Notification, NotificationPreference,
    NotificationChannel, NotificationLog
)
from .notification_serializers import (
    NotificationListSerializer, NotificationCreateSerializer,
    NotificationPreferenceSerializer, NotificationStatsSerializer,
    BulkNotificationSerializer
)
from .notification_service import notification_service, NotificationService

User = get_user_model()


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        description="""
        Retrieve a paginated list of notifications for the authenticated user.
        
        **Features:**
        - Automatic filtering to user's notifications only
        - Support for status, priority, and read status filtering
        - Search functionality across title and message
        - Ordering by creation date (newest first)
        - Pagination with 20 items per page
        """,
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by notification status',
                enum=['PENDING', 'SENT', 'DELIVERED', 'READ', 'FAILED', 'EXPIRED', 'CANCELLED']
            ),
            OpenApiParameter(
                name='priority',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by notification priority',
                enum=['LOW', 'MEDIUM', 'HIGH', 'URGENT', 'CRITICAL']
            ),
            OpenApiParameter(
                name='unread_only',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only unread notifications'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in notification title and message'
            ),
        ],
        examples=[
            OpenApiExample(
                'Unread notifications',
                summary='Get unread notifications',
                description='Retrieve only unread notifications for the user',
                value={'unread_only': True}
            ),
            OpenApiExample(
                'High priority notifications',
                summary='Get high priority notifications',
                description='Retrieve notifications with HIGH or URGENT priority',
                value={'priority': 'HIGH'}
            ),
        ],
        tags=['Notifications']
    ),
    create=extend_schema(
        summary="Create notification",
        description="""
        Create a new notification. This endpoint is typically used by system processes
        or administrators to send notifications to users.
        
        **Note:** Regular users can only create notifications for themselves.
        Staff users can create notifications for any user.
        """,
        examples=[
            OpenApiExample(
                'System alert',
                summary='Create a system alert notification',
                description='Example of creating a system-wide alert notification',
                value={
                    'notification_type': 'SYSTEM_ALERT',
                    'title': 'System Maintenance',
                    'message': 'The system will be under maintenance from 2 AM to 4 AM.',
                    'priority': 'HIGH',
                    'channels': ['IN_APP', 'EMAIL']
                }
            ),
            OpenApiExample(
                'Event reminder',
                summary='Create an event reminder',
                description='Example of creating an event reminder notification',
                value={
                    'notification_type': 'EVENT_REMINDER',
                    'title': 'Event Tomorrow',
                    'message': 'Don\'t forget about your volunteer assignment tomorrow at 9 AM.',
                    'priority': 'MEDIUM',
                    'channels': ['IN_APP', 'PUSH']
                }
            ),
        ],
        tags=['Notifications']
    ),
    retrieve=extend_schema(
        summary="Get notification details",
        description="Retrieve detailed information about a specific notification.",
        tags=['Notifications']
    ),
    update=extend_schema(
        summary="Update notification",
        description="Update notification details. Only the notification owner or staff can update.",
        tags=['Notifications']
    ),
    partial_update=extend_schema(
        summary="Partially update notification",
        description="Partially update notification details. Only the notification owner or staff can update.",
        tags=['Notifications']
    ),
    destroy=extend_schema(
        summary="Delete notification",
        description="Delete a notification. Only the notification owner or staff can delete.",
        tags=['Notifications']
    ),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications.
    
    Provides CRUD operations for notifications with user-specific filtering,
    custom actions for marking as read, and comprehensive statistics.
    """
    serializer_class = NotificationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter notifications to current user only"""
        return Notification.objects.filter(recipient=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return NotificationCreateSerializer
        elif self.action == 'statistics':
            return NotificationStatsSerializer
        elif self.action == 'bulk_notify':
            return BulkNotificationSerializer
        return NotificationListSerializer
    
    def perform_create(self, serializer):
        """Set recipient to current user if not specified"""
        if not serializer.validated_data.get('recipient'):
            serializer.save(recipient=self.request.user)
        else:
            serializer.save()
    
    @extend_schema(
        summary="Mark notification as read",
        description="""
        Mark a specific notification as read for the current user.
        
        **Effects:**
        - Updates notification status to 'READ'
        - Sets read_at timestamp
        - Updates user's unread count cache
        """,
        request=None,
        responses={
            200: OpenApiExample(
                'Success',
                value={'detail': 'Notification marked as read'}
            )
        },
        tags=['Notifications']
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'detail': 'Notification marked as read'})
    
    @extend_schema(
        summary="Mark all notifications as read",
        description="""
        Mark all notifications for the current user as read.
        
        **Effects:**
        - Updates all unread notifications to 'READ' status
        - Sets read_at timestamp for all notifications
        - Clears user's unread count cache
        """,
        request=None,
        responses={
            200: OpenApiExample(
                'Success',
                value={'detail': 'All notifications marked as read', 'count': 5}
            )
        },
        tags=['Notifications']
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for current user"""
        count = self.get_queryset().filter(
            status__in=['PENDING', 'SENT', 'DELIVERED']
        ).update(
            status='READ',
            read_at=timezone.now()
        )
        return Response({
            'detail': 'All notifications marked as read',
            'count': count
        })
    
    @extend_schema(
        summary="Get unread notification count",
        description="""
        Get the count of unread notifications for the current user.
        
        **Returns:**
        - Total count of unread notifications
        - Breakdown by priority level
        - Cached for performance
        """,
        request=None,
        responses={
            200: OpenApiExample(
                'Unread count',
                value={
                    'unread_count': 12,
                    'by_priority': {
                        'CRITICAL': 1,
                        'HIGH': 3,
                        'MEDIUM': 5,
                        'LOW': 3
                    }
                }
            )
        },
        tags=['Notifications']
    )
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        service = NotificationService()
        count = service.get_unread_count(request.user)
        
        # Get breakdown by priority
        priority_breakdown = self.get_queryset().filter(
            status__in=['PENDING', 'SENT', 'DELIVERED']
        ).values('priority').annotate(count=Count('id'))
        
        by_priority = {item['priority']: item['count'] for item in priority_breakdown}
        
        return Response({
            'unread_count': count,
            'by_priority': by_priority
        })
    
    @extend_schema(
        summary="Get recent notifications",
        description="""
        Get recent notifications for the current user with optional limit.
        
        **Features:**
        - Ordered by creation date (newest first)
        - Configurable limit (default: 10, max: 50)
        - Includes read status and priority information
        """,
        parameters=[
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of notifications to return (max: 50)',
                default=10
            ),
        ],
        responses={
            200: NotificationListSerializer(many=True)
        },
        tags=['Notifications']
    )
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications"""
        limit = min(int(request.query_params.get('limit', 10)), 50)
        service = NotificationService()
        notifications = service.get_recent_notifications(request.user, limit=limit)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get notification statistics",
        description="""
        Get comprehensive statistics about notifications for the current user.
        
        **Includes:**
        - Total notification counts by status
        - Breakdown by priority and type
        - Recent activity trends
        - Read/unread ratios
        """,
        request=None,
        responses={
            200: NotificationStatsSerializer()
        },
        tags=['Notifications']
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get notification statistics"""
        queryset = self.get_queryset()
        
        # Basic counts
        total_count = queryset.count()
        unread_count = queryset.filter(status__in=['PENDING', 'SENT', 'DELIVERED']).count()
        read_count = queryset.filter(status='READ').count()
        
        # Status breakdown
        status_breakdown = queryset.values('status').annotate(count=Count('id'))
        status_counts = {item['status']: item['count'] for item in status_breakdown}
        
        # Priority breakdown
        priority_breakdown = queryset.values('priority').annotate(count=Count('id'))
        priority_counts = {item['priority']: item['count'] for item in priority_breakdown}
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = queryset.filter(created_at__gte=week_ago).count()
        
        stats = {
            'total_count': total_count,
            'unread_count': unread_count,
            'read_count': read_count,
            'status_breakdown': status_counts,
            'priority_breakdown': priority_counts,
            'recent_activity': recent_count,
            'read_percentage': round((read_count / total_count * 100) if total_count > 0 else 0, 2)
        }
        
        serializer = NotificationStatsSerializer(data=stats)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Get notification preferences",
        description="""
        Retrieve notification preferences for the authenticated user.
        
        **Features:**
        - User-specific preference settings
        - Channel preferences (email, push, in-app, SMS)
        - Notification type preferences
        - Quiet hours and timezone settings
        - Digest frequency configuration
        """,
        tags=['Notifications']
    ),
    create=extend_schema(
        summary="Create notification preferences",
        description="""
        Create notification preferences for the authenticated user.
        
        **Note:** Each user can only have one set of preferences.
        Use PUT/PATCH to update existing preferences.
        """,
        examples=[
            OpenApiExample(
                'Default preferences',
                summary='Create default notification preferences',
                description='Example of creating notification preferences with default settings',
                value={
                    'is_enabled': True,
                    'email_enabled': True,
                    'push_enabled': True,
                    'in_app_enabled': True,
                    'sms_enabled': False,
                    'quiet_hours_start': '22:00',
                    'quiet_hours_end': '08:00',
                    'timezone': 'Europe/Dublin',
                    'digest_frequency': 'IMMEDIATE'
                }
            ),
        ],
        tags=['Notifications']
    ),
    retrieve=extend_schema(
        summary="Get specific notification preferences",
        description="Retrieve detailed notification preferences for a specific user.",
        tags=['Notifications']
    ),
    update=extend_schema(
        summary="Update notification preferences",
        description="Update all notification preference settings.",
        tags=['Notifications']
    ),
    partial_update=extend_schema(
        summary="Partially update notification preferences",
        description="Update specific notification preference settings.",
        tags=['Notifications']
    ),
)
class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification preferences.
    
    Allows users to configure their notification settings including
    channels, types, quiet hours, and delivery preferences.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter preferences to current user only"""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)


class SystemNotificationViewSet(viewsets.ViewSet):
    """ViewSet for system-wide notification management"""
    
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def broadcast(self, request):
        """Send notification to all users of a specific type"""
        try:
            user_type = request.data.get('user_type')
            title = request.data.get('title')
            message = request.data.get('message')
            priority = request.data.get('priority', 'MEDIUM')
            
            if not all([user_type, title, message]):
                return Response(
                    {'error': 'user_type, title, and message are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            notifications = notification_service.notify_user_type(
                user_type=user_type,
                title=title,
                message=message,
                priority=priority,
                sender=request.user
            )
            
            return Response({
                'status': 'broadcast_sent',
                'count': len(notifications),
                'user_type': user_type
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def system_stats(self, request):
        """Get system-wide notification statistics"""
        try:
            now = timezone.now()
            today = now.date()
            week_ago = now - timedelta(days=7)
            
            # System-wide counts
            total = Notification.objects.count()
            pending = Notification.objects.filter(status='PENDING').count()
            failed = Notification.objects.filter(status='FAILED').count()
            today_count = Notification.objects.filter(created_at__date=today).count()
            week_count = Notification.objects.filter(created_at__gte=week_ago).count()
            
            # User type breakdown
            user_type_stats = {}
            for user_type, display_name in User.USER_TYPE_CHOICES:
                count = Notification.objects.filter(recipient__user_type=user_type).count()
                user_type_stats[user_type] = {
                    'display_name': display_name,
                    'count': count
                }
            
            return Response({
                'total_notifications': total,
                'pending_notifications': pending,
                'failed_notifications': failed,
                'notifications_today': today_count,
                'notifications_this_week': week_count,
                'user_type_breakdown': user_type_stats
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 