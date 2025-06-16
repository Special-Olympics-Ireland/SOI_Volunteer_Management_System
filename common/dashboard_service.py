"""
Comprehensive dashboard service for SOI Hub Volunteer Management System.

This service provides real-time statistics, KPIs, and analytics for the admin dashboard
including volunteer metrics, event statistics, system performance, and operational insights.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from django.db.models import Count, Q, Avg, Sum, Max, Min, F, Case, When, IntegerField
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models.functions import TruncDate, TruncHour, Extract

from volunteers.models import VolunteerProfile
from events.models import Event, Role, Assignment
from tasks.models import Task, TaskCompletion
from .models import AuditLog, AdminOverride
from integrations.models import JustGoSync, IntegrationLog

User = get_user_model()


class DashboardService:
    """
    Comprehensive dashboard service providing real-time statistics and KPIs.
    """
    
    # Cache timeouts (in seconds)
    CACHE_TIMEOUT_SHORT = 300  # 5 minutes
    CACHE_TIMEOUT_MEDIUM = 900  # 15 minutes
    CACHE_TIMEOUT_LONG = 3600  # 1 hour
    
    @classmethod
    def get_dashboard_overview(cls, user=None) -> Dict[str, Any]:
        """
        Get comprehensive dashboard overview with all key metrics.
        
        Args:
            user: Optional user for personalized metrics
            
        Returns:
            Dictionary containing all dashboard metrics
        """
        cache_key = f"dashboard_overview_{user.id if user else 'global'}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        overview = {
            'timestamp': timezone.now().isoformat(),
            'volunteer_metrics': cls.get_volunteer_metrics(),
            'event_metrics': cls.get_event_metrics(),
            'assignment_metrics': cls.get_assignment_metrics(),
            'task_metrics': cls.get_task_metrics(),
            'system_metrics': cls.get_system_metrics(),
            'integration_metrics': cls.get_integration_metrics(),
            'performance_metrics': cls.get_performance_metrics(),
            'recent_activity': cls.get_recent_activity(),
            'alerts_and_notifications': cls.get_alerts_and_notifications(),
            'trends': cls.get_trend_data(),
            'kpis': cls.get_key_performance_indicators()
        }
        
        # Cache for medium duration
        cache.set(cache_key, overview, cls.CACHE_TIMEOUT_MEDIUM)
        
        return overview
    
    @classmethod
    def get_volunteer_metrics(cls) -> Dict[str, Any]:
        """Get comprehensive volunteer statistics."""
        cache_key = "dashboard_volunteer_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Basic counts
        total_volunteers = VolunteerProfile.objects.count()
        active_volunteers = VolunteerProfile.objects.filter(status='ACTIVE').count()
        pending_applications = VolunteerProfile.objects.filter(status='PENDING').count()
        under_review = VolunteerProfile.objects.filter(status='UNDER_REVIEW').count()
        
        # Status distribution
        status_distribution = dict(
            VolunteerProfile.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
        
        # Experience level distribution
        experience_distribution = dict(
            VolunteerProfile.objects.values('experience_level')
            .annotate(count=Count('id'))
            .values_list('experience_level', 'count')
        )
        
        # Availability distribution
        availability_distribution = dict(
            VolunteerProfile.objects.values('availability_level')
            .annotate(count=Count('id'))
            .values_list('availability_level', 'count')
        )
        
        # Recent registrations (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_registrations = VolunteerProfile.objects.filter(
            application_date__gte=thirty_days_ago
        ).count()
        
        # Registration trend (daily for last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        registration_trend = list(
            VolunteerProfile.objects.filter(application_date__gte=seven_days_ago)
            .extra(select={'day': 'date(application_date)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        # Corporate volunteers
        corporate_volunteers = VolunteerProfile.objects.filter(
            is_corporate_volunteer=True
        ).count()
        
        # Background check status
        background_check_stats = dict(
            VolunteerProfile.objects.values('background_check_status')
            .annotate(count=Count('id'))
            .values_list('background_check_status', 'count')
        )
        
        # Performance ratings
        avg_performance = VolunteerProfile.objects.filter(
            performance_rating__isnull=False
        ).aggregate(avg_rating=Avg('performance_rating'))['avg_rating']
        
        metrics = {
            'total_volunteers': total_volunteers,
            'active_volunteers': active_volunteers,
            'pending_applications': pending_applications,
            'under_review': under_review,
            'recent_registrations': recent_registrations,
            'corporate_volunteers': corporate_volunteers,
            'average_performance_rating': round(avg_performance, 2) if avg_performance else None,
            'status_distribution': status_distribution,
            'experience_distribution': experience_distribution,
            'availability_distribution': availability_distribution,
            'background_check_stats': background_check_stats,
            'registration_trend': registration_trend,
            'approval_rate': cls._calculate_approval_rate(),
            'retention_metrics': cls._calculate_retention_metrics()
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_event_metrics(cls) -> Dict[str, Any]:
        """Get comprehensive event statistics."""
        cache_key = "dashboard_event_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Basic counts
        total_events = Event.objects.count()
        active_events = Event.objects.filter(status='ACTIVE').count()
        upcoming_events = Event.objects.filter(
            status='ACTIVE',
            start_date__gt=timezone.now()
        ).count()
        
        # Event status distribution
        status_distribution = dict(
            Event.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
        
        # Events by type
        type_distribution = dict(
            Event.objects.values('event_type')
            .annotate(count=Count('id'))
            .values_list('event_type', 'count')
        )
        
        # Venue utilization
        venue_stats = list(
            Event.objects.values('venue__name')
            .annotate(
                event_count=Count('id'),
                total_capacity=Sum('venue__capacity')
            )
            .order_by('-event_count')[:10]
        )
        
        # Event timeline (next 30 days)
        thirty_days_ahead = timezone.now() + timedelta(days=30)
        upcoming_timeline = list(
            Event.objects.filter(
                start_date__gte=timezone.now(),
                start_date__lte=thirty_days_ahead
            )
            .extra(select={'day': 'date(start_date)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        metrics = {
            'total_events': total_events,
            'active_events': active_events,
            'upcoming_events': upcoming_events,
            'status_distribution': status_distribution,
            'type_distribution': type_distribution,
            'venue_stats': venue_stats,
            'upcoming_timeline': upcoming_timeline,
            'capacity_utilization': cls._calculate_event_capacity_utilization()
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_assignment_metrics(cls) -> Dict[str, Any]:
        """Get comprehensive assignment statistics."""
        cache_key = "dashboard_assignment_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Basic counts
        total_assignments = Assignment.objects.count()
        confirmed_assignments = Assignment.objects.filter(status='CONFIRMED').count()
        pending_assignments = Assignment.objects.filter(status='PENDING').count()
        
        # Assignment status distribution
        status_distribution = dict(
            Assignment.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
        
        # Role popularity
        role_stats = list(
            Assignment.objects.values('role__name')
            .annotate(
                assignment_count=Count('id'),
                confirmed_count=Count(Case(
                    When(status='CONFIRMED', then=1),
                    output_field=IntegerField()
                ))
            )
            .order_by('-assignment_count')[:10]
        )
        
        # Assignment timeline
        seven_days_ago = timezone.now() - timedelta(days=7)
        assignment_trend = list(
            Assignment.objects.filter(created_at__gte=seven_days_ago)
            .extra(select={'day': 'date(created_at)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        # Fulfillment rate by role
        role_fulfillment = list(
            Role.objects.annotate(
                total_assignments=Count('assignments'),
                confirmed_assignments=Count(
                    Case(
                        When(assignments__status='CONFIRMED', then=1),
                        output_field=IntegerField()
                    )
                ),
                fulfillment_rate=Case(
                    When(total_assignments=0, then=0),
                    default=F('confirmed_assignments') * 100 / F('total_assignments'),
                    output_field=IntegerField()
                )
            )
            .values('name', 'capacity', 'total_assignments', 'confirmed_assignments', 'fulfillment_rate')
            .order_by('-fulfillment_rate')[:10]
        )
        
        metrics = {
            'total_assignments': total_assignments,
            'confirmed_assignments': confirmed_assignments,
            'pending_assignments': pending_assignments,
            'status_distribution': status_distribution,
            'role_stats': role_stats,
            'assignment_trend': assignment_trend,
            'role_fulfillment': role_fulfillment,
            'confirmation_rate': cls._calculate_confirmation_rate()
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_task_metrics(cls) -> Dict[str, Any]:
        """Get comprehensive task statistics."""
        cache_key = "dashboard_task_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Basic counts
        total_tasks = Task.objects.count()
        active_tasks = Task.objects.filter(is_active=True).count()
        total_completions = TaskCompletion.objects.count()
        
        # Task type distribution
        type_distribution = dict(
            Task.objects.values('task_type')
            .annotate(count=Count('id'))
            .values_list('task_type', 'count')
        )
        
        # Completion status distribution
        completion_status = dict(
            TaskCompletion.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
        
        # Task completion trend
        seven_days_ago = timezone.now() - timedelta(days=7)
        completion_trend = list(
            TaskCompletion.objects.filter(created_at__gte=seven_days_ago)
            .extra(select={'day': 'date(created_at)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        # Most active tasks
        popular_tasks = list(
            Task.objects.annotate(
                completion_count=Count('completions')
            )
            .values('title', 'task_type', 'completion_count')
            .order_by('-completion_count')[:10]
        )
        
        # Average completion time (for completed tasks)
        avg_completion_time = TaskCompletion.objects.filter(
            status='COMPLETED',
            completed_at__isnull=False
        ).aggregate(
            avg_time=Avg(F('completed_at') - F('created_at'))
        )['avg_time']
        
        metrics = {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'total_completions': total_completions,
            'type_distribution': type_distribution,
            'completion_status': completion_status,
            'completion_trend': completion_trend,
            'popular_tasks': popular_tasks,
            'average_completion_time': str(avg_completion_time) if avg_completion_time else None,
            'completion_rate': cls._calculate_task_completion_rate()
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_system_metrics(cls) -> Dict[str, Any]:
        """Get system performance and usage statistics."""
        cache_key = "dashboard_system_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # User activity
        total_users = User.objects.count()
        active_users_today = User.objects.filter(
            last_login__date=timezone.now().date()
        ).count()
        
        # Admin overrides
        total_overrides = AdminOverride.objects.count()
        active_overrides = AdminOverride.objects.filter(status='ACTIVE').count()
        pending_overrides = AdminOverride.objects.filter(status='PENDING').count()
        
        # Override risk distribution
        override_risk_distribution = dict(
            AdminOverride.objects.values('risk_level')
            .annotate(count=Count('id'))
            .values_list('risk_level', 'count')
        )
        
        # Audit log statistics
        total_audit_logs = AuditLog.objects.count()
        audit_logs_today = AuditLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).count()
        
        # Critical operations
        critical_operations = AuditLog.objects.filter(
            metadata__critical_operation=True
        ).count()
        
        # Security events
        security_events = AuditLog.objects.filter(
            metadata__category='SECURITY_OPERATIONS'
        ).count()
        
        # System activity trend
        seven_days_ago = timezone.now() - timedelta(days=7)
        activity_trend = list(
            AuditLog.objects.filter(timestamp__gte=seven_days_ago)
            .extra(select={'day': 'date(timestamp)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        metrics = {
            'total_users': total_users,
            'active_users_today': active_users_today,
            'total_overrides': total_overrides,
            'active_overrides': active_overrides,
            'pending_overrides': pending_overrides,
            'override_risk_distribution': override_risk_distribution,
            'total_audit_logs': total_audit_logs,
            'audit_logs_today': audit_logs_today,
            'critical_operations': critical_operations,
            'security_events': security_events,
            'activity_trend': activity_trend,
            'system_health': cls._get_system_health_status()
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_integration_metrics(cls) -> Dict[str, Any]:
        """Get integration system statistics."""
        cache_key = "dashboard_integration_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # JustGo sync statistics
        total_syncs = JustGoSync.objects.count()
        successful_syncs = JustGoSync.objects.filter(status='SUCCESS').count()
        failed_syncs = JustGoSync.objects.filter(status='FAILED').count()
        
        # Recent sync activity
        recent_syncs = JustGoSync.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Integration logs
        total_integration_logs = IntegrationLog.objects.count()
        error_logs = IntegrationLog.objects.filter(level='ERROR').count()
        
        # Sync success rate
        success_rate = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
        
        # Last sync status
        last_sync = JustGoSync.objects.order_by('-created_at').first()
        
        metrics = {
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'recent_syncs': recent_syncs,
            'total_integration_logs': total_integration_logs,
            'error_logs': error_logs,
            'success_rate': round(success_rate, 2),
            'last_sync': {
                'status': last_sync.status if last_sync else None,
                'timestamp': last_sync.created_at.isoformat() if last_sync else None,
                'records_processed': last_sync.records_processed if last_sync else 0
            } if last_sync else None
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_performance_metrics(cls) -> Dict[str, Any]:
        """Get system performance metrics."""
        cache_key = "dashboard_performance_metrics"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Database query performance from audit logs
        performance_logs = AuditLog.objects.filter(
            duration_ms__isnull=False,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        )
        
        if performance_logs.exists():
            avg_response_time = performance_logs.aggregate(
                avg_duration=Avg('duration_ms')
            )['avg_duration']
            
            max_response_time = performance_logs.aggregate(
                max_duration=Max('duration_ms')
            )['max_duration']
            
            slow_operations = performance_logs.filter(duration_ms__gt=1000).count()
        else:
            avg_response_time = None
            max_response_time = None
            slow_operations = 0
        
        # Error rate
        total_operations = AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        failed_operations = AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24),
            response_status__gte=400
        ).count()
        
        error_rate = (failed_operations / total_operations * 100) if total_operations > 0 else 0
        
        metrics = {
            'avg_response_time_ms': round(avg_response_time, 2) if avg_response_time else None,
            'max_response_time_ms': max_response_time,
            'slow_operations_24h': slow_operations,
            'error_rate_24h': round(error_rate, 2),
            'total_operations_24h': total_operations,
            'failed_operations_24h': failed_operations
        }
        
        cache.set(cache_key, metrics, cls.CACHE_TIMEOUT_SHORT)
        return metrics
    
    @classmethod
    def get_recent_activity(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent system activity."""
        cache_key = f"dashboard_recent_activity_{limit}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        recent_logs = AuditLog.objects.select_related('user', 'content_type').order_by('-timestamp')[:limit]
        
        activity = []
        for log in recent_logs:
            activity.append({
                'timestamp': log.timestamp.isoformat(),
                'action': log.action_type,
                'description': log.action_description,
                'user': log.user.get_full_name() if log.user else 'System',
                'user_type': 'superuser' if log.user and log.user.is_superuser else 'staff' if log.user and log.user.is_staff else 'user',
                'critical': log.metadata.get('critical_operation', False),
                'ip_address': log.ip_address,
                'duration_ms': log.duration_ms
            })
        
        cache.set(cache_key, activity, cls.CACHE_TIMEOUT_SHORT)
        return activity
    
    @classmethod
    def get_alerts_and_notifications(cls) -> Dict[str, Any]:
        """Get system alerts and notifications."""
        cache_key = "dashboard_alerts_notifications"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        alerts = []
        
        # Pending admin overrides
        pending_overrides = AdminOverride.objects.filter(status='PENDING').count()
        if pending_overrides > 0:
            alerts.append({
                'type': 'warning',
                'title': 'Pending Admin Overrides',
                'message': f'{pending_overrides} admin override(s) require approval',
                'count': pending_overrides,
                'priority': 'medium'
            })
        
        # High-risk active overrides
        high_risk_overrides = AdminOverride.objects.filter(
            status='ACTIVE',
            risk_level='HIGH'
        ).count()
        if high_risk_overrides > 0:
            alerts.append({
                'type': 'error',
                'title': 'High-Risk Active Overrides',
                'message': f'{high_risk_overrides} high-risk override(s) are currently active',
                'count': high_risk_overrides,
                'priority': 'high'
            })
        
        # Recent security events
        recent_security_events = AuditLog.objects.filter(
            metadata__category='SECURITY_OPERATIONS',
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        if recent_security_events > 5:
            alerts.append({
                'type': 'warning',
                'title': 'High Security Activity',
                'message': f'{recent_security_events} security events in the last 24 hours',
                'count': recent_security_events,
                'priority': 'medium'
            })
        
        # Failed integrations
        failed_syncs = JustGoSync.objects.filter(
            status='FAILED',
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        if failed_syncs > 0:
            alerts.append({
                'type': 'error',
                'title': 'Integration Failures',
                'message': f'{failed_syncs} JustGo sync failure(s) in the last 24 hours',
                'count': failed_syncs,
                'priority': 'high'
            })
        
        # Pending volunteer applications
        pending_applications = VolunteerProfile.objects.filter(
            status='PENDING',
            application_date__lte=timezone.now() - timedelta(days=7)
        ).count()
        if pending_applications > 10:
            alerts.append({
                'type': 'info',
                'title': 'Pending Applications',
                'message': f'{pending_applications} volunteer applications pending for over 7 days',
                'count': pending_applications,
                'priority': 'low'
            })
        
        notifications = {
            'alerts': alerts,
            'total_alerts': len(alerts),
            'high_priority': len([a for a in alerts if a['priority'] == 'high']),
            'medium_priority': len([a for a in alerts if a['priority'] == 'medium']),
            'low_priority': len([a for a in alerts if a['priority'] == 'low'])
        }
        
        cache.set(cache_key, notifications, cls.CACHE_TIMEOUT_SHORT)
        return notifications
    
    @classmethod
    def get_trend_data(cls) -> Dict[str, Any]:
        """Get trend analysis data."""
        cache_key = "dashboard_trend_data"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # 30-day trends
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Volunteer registration trend
        volunteer_trend = list(
            VolunteerProfile.objects.filter(application_date__gte=thirty_days_ago)
            .extra(select={'day': 'date(application_date)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        # System activity trend
        activity_trend = list(
            AuditLog.objects.filter(timestamp__gte=thirty_days_ago)
            .extra(select={'day': 'date(timestamp)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        # Assignment trend
        assignment_trend = list(
            Assignment.objects.filter(created_at__gte=thirty_days_ago)
            .extra(select={'day': 'date(created_at)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        trends = {
            'volunteer_registrations': volunteer_trend,
            'system_activity': activity_trend,
            'assignments': assignment_trend,
            'period_days': 30
        }
        
        cache.set(cache_key, trends, cls.CACHE_TIMEOUT_MEDIUM)
        return trends
    
    @classmethod
    def get_key_performance_indicators(cls) -> Dict[str, Any]:
        """Get key performance indicators (KPIs)."""
        cache_key = "dashboard_kpis"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Calculate KPIs
        kpis = {
            'volunteer_satisfaction': cls._calculate_volunteer_satisfaction(),
            'event_capacity_utilization': cls._calculate_event_capacity_utilization(),
            'assignment_fulfillment_rate': cls._calculate_assignment_fulfillment_rate(),
            'system_uptime': cls._calculate_system_uptime(),
            'data_quality_score': cls._calculate_data_quality_score(),
            'integration_reliability': cls._calculate_integration_reliability(),
            'response_time_sla': cls._calculate_response_time_sla(),
            'security_compliance': cls._calculate_security_compliance()
        }
        
        cache.set(cache_key, kpis, cls.CACHE_TIMEOUT_MEDIUM)
        return kpis
    
    # Helper methods for calculations
    
    @classmethod
    def _calculate_approval_rate(cls) -> float:
        """Calculate volunteer application approval rate."""
        total_reviewed = VolunteerProfile.objects.filter(
            status__in=['APPROVED', 'REJECTED']
        ).count()
        
        if total_reviewed == 0:
            return 0.0
        
        approved = VolunteerProfile.objects.filter(status='APPROVED').count()
        return round(approved / total_reviewed * 100, 2)
    
    @classmethod
    def _calculate_retention_metrics(cls) -> Dict[str, Any]:
        """Calculate volunteer retention metrics."""
        # Active volunteers who have been active for more than 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        long_term_active = VolunteerProfile.objects.filter(
            status='ACTIVE',
            approval_date__lte=thirty_days_ago
        ).count()
        
        # Total approved volunteers from more than 30 days ago
        total_approved_30_days = VolunteerProfile.objects.filter(
            approval_date__lte=thirty_days_ago
        ).count()
        
        retention_rate = (long_term_active / total_approved_30_days * 100) if total_approved_30_days > 0 else 0
        
        return {
            'retention_rate': round(retention_rate, 2),
            'long_term_active': long_term_active,
            'total_approved_30_days': total_approved_30_days
        }
    
    @classmethod
    def _calculate_event_capacity_utilization(cls) -> float:
        """Calculate event capacity utilization rate."""
        events_with_assignments = Event.objects.filter(
            assignments__isnull=False
        ).distinct()
        
        if not events_with_assignments.exists():
            return 0.0
        
        total_capacity = 0
        total_assignments = 0
        
        for event in events_with_assignments:
            event_capacity = event.roles.aggregate(
                total=Sum('capacity')
            )['total'] or 0
            
            event_assignments = Assignment.objects.filter(
                role__event=event,
                status='CONFIRMED'
            ).count()
            
            total_capacity += event_capacity
            total_assignments += event_assignments
        
        return round(total_assignments / total_capacity * 100, 2) if total_capacity > 0 else 0.0
    
    @classmethod
    def _calculate_confirmation_rate(cls) -> float:
        """Calculate assignment confirmation rate."""
        total_assignments = Assignment.objects.count()
        if total_assignments == 0:
            return 0.0
        
        confirmed_assignments = Assignment.objects.filter(status='CONFIRMED').count()
        return round(confirmed_assignments / total_assignments * 100, 2)
    
    @classmethod
    def _calculate_task_completion_rate(cls) -> float:
        """Calculate task completion rate."""
        total_task_completions = TaskCompletion.objects.count()
        if total_task_completions == 0:
            return 0.0
        
        completed_tasks = TaskCompletion.objects.filter(status='COMPLETED').count()
        return round(completed_tasks / total_task_completions * 100, 2)
    
    @classmethod
    def _get_system_health_status(cls) -> Dict[str, Any]:
        """Get overall system health status."""
        # Check various system components
        health_checks = {
            'database': cls._check_database_health(),
            'cache': cls._check_cache_health(),
            'integrations': cls._check_integration_health(),
            'performance': cls._check_performance_health()
        }
        
        # Overall health score
        healthy_components = sum(1 for status in health_checks.values() if status['status'] == 'healthy')
        total_components = len(health_checks)
        health_score = round(healthy_components / total_components * 100, 2)
        
        overall_status = 'healthy' if health_score >= 90 else 'warning' if health_score >= 70 else 'critical'
        
        return {
            'overall_status': overall_status,
            'health_score': health_score,
            'components': health_checks
        }
    
    @classmethod
    def _check_database_health(cls) -> Dict[str, Any]:
        """Check database health."""
        try:
            # Simple query to test database connectivity
            User.objects.count()
            return {'status': 'healthy', 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': 'critical', 'message': f'Database error: {str(e)}'}
    
    @classmethod
    def _check_cache_health(cls) -> Dict[str, Any]:
        """Check cache health."""
        try:
            # Test cache connectivity
            cache.set('health_check', 'ok', 60)
            result = cache.get('health_check')
            if result == 'ok':
                return {'status': 'healthy', 'message': 'Cache connection OK'}
            else:
                return {'status': 'warning', 'message': 'Cache not responding correctly'}
        except Exception as e:
            return {'status': 'critical', 'message': f'Cache error: {str(e)}'}
    
    @classmethod
    def _check_integration_health(cls) -> Dict[str, Any]:
        """Check integration health."""
        # Check recent sync failures
        recent_failures = JustGoSync.objects.filter(
            status='FAILED',
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        if recent_failures == 0:
            return {'status': 'healthy', 'message': 'All integrations running smoothly'}
        elif recent_failures < 5:
            return {'status': 'warning', 'message': f'{recent_failures} integration failures in 24h'}
        else:
            return {'status': 'critical', 'message': f'{recent_failures} integration failures in 24h'}
    
    @classmethod
    def _check_performance_health(cls) -> Dict[str, Any]:
        """Check system performance health."""
        # Check average response time in last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        avg_response = AuditLog.objects.filter(
            timestamp__gte=one_hour_ago,
            duration_ms__isnull=False
        ).aggregate(avg_duration=Avg('duration_ms'))['avg_duration']
        
        if avg_response is None:
            return {'status': 'healthy', 'message': 'No performance data available'}
        elif avg_response < 500:
            return {'status': 'healthy', 'message': f'Average response time: {avg_response:.0f}ms'}
        elif avg_response < 1000:
            return {'status': 'warning', 'message': f'Average response time: {avg_response:.0f}ms'}
        else:
            return {'status': 'critical', 'message': f'Average response time: {avg_response:.0f}ms'}
    
    # KPI calculation methods
    
    @classmethod
    def _calculate_volunteer_satisfaction(cls) -> Dict[str, Any]:
        """Calculate volunteer satisfaction KPI."""
        avg_rating = VolunteerProfile.objects.filter(
            performance_rating__isnull=False
        ).aggregate(avg_rating=Avg('performance_rating'))['avg_rating']
        
        if avg_rating is None:
            return {'score': None, 'status': 'no_data', 'target': 4.0}
        
        score = round(avg_rating, 2)
        status = 'excellent' if score >= 4.5 else 'good' if score >= 4.0 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 4.0}
    
    @classmethod
    def _calculate_assignment_fulfillment_rate(cls) -> Dict[str, Any]:
        """Calculate assignment fulfillment rate KPI."""
        total_roles = Role.objects.count()
        if total_roles == 0:
            return {'score': None, 'status': 'no_data', 'target': 90.0}
        
        fulfilled_roles = Role.objects.filter(
            assignments__status='CONFIRMED'
        ).distinct().count()
        
        score = round(fulfilled_roles / total_roles * 100, 2)
        status = 'excellent' if score >= 95 else 'good' if score >= 85 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 90.0}
    
    @classmethod
    def _calculate_system_uptime(cls) -> Dict[str, Any]:
        """Calculate system uptime KPI."""
        # Based on successful operations vs failed operations
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        total_ops = AuditLog.objects.filter(timestamp__gte=twenty_four_hours_ago).count()
        
        if total_ops == 0:
            return {'score': None, 'status': 'no_data', 'target': 99.9}
        
        failed_ops = AuditLog.objects.filter(
            timestamp__gte=twenty_four_hours_ago,
            response_status__gte=500
        ).count()
        
        uptime = (total_ops - failed_ops) / total_ops * 100
        score = round(uptime, 2)
        status = 'excellent' if score >= 99.5 else 'good' if score >= 99.0 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 99.9}
    
    @classmethod
    def _calculate_data_quality_score(cls) -> Dict[str, Any]:
        """Calculate data quality score KPI."""
        # Check for complete volunteer profiles
        total_volunteers = VolunteerProfile.objects.count()
        if total_volunteers == 0:
            return {'score': None, 'status': 'no_data', 'target': 95.0}
        
        # Count profiles with essential fields completed
        complete_profiles = VolunteerProfile.objects.filter(
            emergency_contact_name__isnull=False,
            emergency_contact_phone__isnull=False,
            experience_level__isnull=False
        ).exclude(
            emergency_contact_name='',
            emergency_contact_phone='',
        ).count()
        
        score = round(complete_profiles / total_volunteers * 100, 2)
        status = 'excellent' if score >= 95 else 'good' if score >= 85 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 95.0}
    
    @classmethod
    def _calculate_integration_reliability(cls) -> Dict[str, Any]:
        """Calculate integration reliability KPI."""
        total_syncs = JustGoSync.objects.count()
        if total_syncs == 0:
            return {'score': None, 'status': 'no_data', 'target': 95.0}
        
        successful_syncs = JustGoSync.objects.filter(status='SUCCESS').count()
        score = round(successful_syncs / total_syncs * 100, 2)
        status = 'excellent' if score >= 98 else 'good' if score >= 95 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 95.0}
    
    @classmethod
    def _calculate_response_time_sla(cls) -> Dict[str, Any]:
        """Calculate response time SLA compliance KPI."""
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        total_requests = AuditLog.objects.filter(
            timestamp__gte=twenty_four_hours_ago,
            duration_ms__isnull=False
        ).count()
        
        if total_requests == 0:
            return {'score': None, 'status': 'no_data', 'target': 95.0}
        
        # SLA: 95% of requests should complete within 2 seconds
        sla_compliant = AuditLog.objects.filter(
            timestamp__gte=twenty_four_hours_ago,
            duration_ms__lte=2000
        ).count()
        
        score = round(sla_compliant / total_requests * 100, 2)
        status = 'excellent' if score >= 98 else 'good' if score >= 95 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 95.0}
    
    @classmethod
    def _calculate_security_compliance(cls) -> Dict[str, Any]:
        """Calculate security compliance KPI."""
        # Check for security events and admin overrides
        total_overrides = AdminOverride.objects.count()
        if total_overrides == 0:
            return {'score': 100.0, 'status': 'excellent', 'target': 95.0}
        
        # Properly justified overrides
        justified_overrides = AdminOverride.objects.exclude(
            justification__isnull=True
        ).exclude(justification='').count()
        
        score = round(justified_overrides / total_overrides * 100, 2)
        status = 'excellent' if score >= 98 else 'good' if score >= 95 else 'needs_improvement'
        
        return {'score': score, 'status': status, 'target': 95.0} 