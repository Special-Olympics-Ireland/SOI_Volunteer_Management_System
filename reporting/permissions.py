from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsStaffOrVMTOrCVT(permissions.BasePermission):
    """
    Permission that allows access to staff, VMT, CVT, GOC, and Admin users.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow staff users and specific user types
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )


class ReportPermission(permissions.BasePermission):
    """
    Permission class for report management.
    - Staff/VMT/CVT/GOC/Admin can view all reports
    - Users can only view their own reports
    - Only staff/VMT/CVT can create reports
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for staff and management
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )
    
    def has_object_permission(self, request, view, obj):
        # Staff and management can access all reports
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only access their own reports
        return obj.created_by == request.user


class ReportTemplatePermission(permissions.BasePermission):
    """
    Permission class for report template management.
    - Staff/VMT/CVT/GOC/Admin can manage all templates
    - Users can view public templates and their own templates
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for staff and management
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )
    
    def has_object_permission(self, request, view, obj):
        # Read permissions
        if request.method in permissions.SAFE_METHODS:
            # Staff and management can view all templates
            if (request.user.is_staff or 
                request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
                return True
            
            # Users can view public templates or their own templates
            return obj.is_public or obj.created_by == request.user
        
        # Write permissions
        # Staff and management can modify all templates
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only modify their own templates
        return obj.created_by == request.user


class ReportSchedulePermission(permissions.BasePermission):
    """
    Permission class for report schedule management.
    - Only staff/VMT/CVT/GOC/Admin can manage schedules
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only staff and management can access schedules
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )
    
    def has_object_permission(self, request, view, obj):
        # Staff and management can access all schedules
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only access their own schedules
        return obj.created_by == request.user


class ReportSharePermission(permissions.BasePermission):
    """
    Permission class for report sharing.
    - Report creators can share their reports
    - Staff/VMT/CVT/GOC/Admin can share any report
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return True  # Basic authentication required
    
    def has_object_permission(self, request, view, obj):
        # Staff and management can manage all shares
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only manage shares they created
        return obj.created_by == request.user


class AnalyticsPermission(permissions.BasePermission):
    """
    Permission class for analytics access.
    - Staff/VMT/CVT/GOC/Admin can access all analytics
    - Regular users have limited analytics access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff and management have full access
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Regular users have limited access to analytics
        # Check if the view allows regular user access
        return getattr(view, 'allow_regular_users', False)


class BulkOperationPermission(permissions.BasePermission):
    """
    Permission class for bulk operations on reports.
    - Only staff/VMT/CVT/GOC/Admin can perform bulk operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only staff and management can perform bulk operations
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )


class ReportDownloadPermission(permissions.BasePermission):
    """
    Permission class for report downloads.
    - Report creators can download their reports
    - Staff/VMT/CVT/GOC/Admin can download any report
    - Shared reports can be downloaded by anyone with the share token
    """
    
    def has_permission(self, request, view):
        # Allow access for share token validation
        return True
    
    def has_object_permission(self, request, view, obj):
        # Check if accessing via share token
        share_token = request.GET.get('token') or request.data.get('token')
        if share_token:
            # Validate share token
            from .models import ReportShare
            try:
                share = ReportShare.objects.get(
                    report=obj,
                    share_token=share_token,
                    status='ACTIVE'
                )
                if share.is_valid() and share.can_download:
                    return True
            except ReportShare.DoesNotExist:
                pass
        
        # Regular permission check
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff and management can download all reports
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only download their own reports
        return obj.created_by == request.user


class SystemStatsPermission(permissions.BasePermission):
    """
    Permission class for system statistics access.
    - Only staff/VMT/CVT/GOC/Admin can access system stats
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only staff and management can access system statistics
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )


class ReportMetricsPermission(permissions.BasePermission):
    """
    Permission class for report metrics access.
    - Report creators can view metrics for their reports
    - Staff/VMT/CVT/GOC/Admin can view all report metrics
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return True  # Basic authentication required
    
    def has_object_permission(self, request, view, obj):
        # Staff and management can view all metrics
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only view metrics for their own reports
        return obj.report.created_by == request.user


class CustomReportPermission(permissions.BasePermission):
    """
    Permission class for custom report creation.
    - Only staff/VMT/CVT/GOC/Admin can create custom reports
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only staff and management can create custom reports
        return (
            request.user.is_staff or
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        )


class ReportExportPermission(permissions.BasePermission):
    """
    Permission class for report export functionality.
    - Report creators can export their reports
    - Staff/VMT/CVT/GOC/Admin can export any report
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return True  # Basic authentication required
    
    def has_object_permission(self, request, view, obj):
        # Staff and management can export all reports
        if (request.user.is_staff or 
            request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return True
        
        # Users can only export their own reports
        return obj.created_by == request.user


class DashboardPermission(permissions.BasePermission):
    """
    Permission class for dashboard access.
    - Staff/VMT/CVT/GOC/Admin can access full dashboard
    - Regular users can access limited dashboard
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return True  # All authenticated users can access some dashboard data
    
    def get_allowed_sections(self, user):
        """Get allowed dashboard sections for user"""
        if (user.is_staff or 
            user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']):
            return ['volunteers', 'events', 'assignments', 'tasks', 'reports', 'system']
        
        # Regular users get limited sections
        return ['volunteers', 'events', 'tasks'] 