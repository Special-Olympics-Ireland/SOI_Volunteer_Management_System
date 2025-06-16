"""
Role-based access control system for SOI Hub.

This module provides comprehensive permission classes for different
user types and access levels throughout the system.
"""

from rest_framework import permissions
from rest_framework.permissions import BasePermission
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

User = get_user_model()


class CanViewAuditLogs(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_admin()


class CanManageSystemConfig(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_admin()


class PowerBIAccessPermission(BasePermission):
    """
    Permission class for PowerBI integration access.
    
    Allows access to users with PowerBI integration permissions
    or admin/staff users with appropriate roles.
    """
    
    def has_permission(self, request, view):
        """Check if user has PowerBI access permission."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_superuser:
            return True
        
        # Staff users with specific permissions
        if request.user.is_staff:
            # Check for specific PowerBI permission
            if request.user.has_perm('common.view_powerbi_data'):
                return True
            
            # Check for analytics permissions
            if request.user.has_perm('common.view_analytics'):
                return True
            
            # Check user type permissions
            if hasattr(request.user, 'user_type'):
                allowed_types = ['ADMIN', 'STAFF', 'VMT', 'CVT', 'GOC']
                if request.user.user_type in allowed_types:
                    return True
        
        return False


class AnalyticsPermission(BasePermission):
    """
    Permission class for analytics access.
    """
    
    def has_permission(self, request, view):
        """Check if user has analytics access permission."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_superuser:
            return True
        
        # Staff users with analytics permissions
        if request.user.is_staff and request.user.has_perm('common.view_analytics'):
            return True
        
        # Specific user types
        if hasattr(request.user, 'user_type'):
            allowed_types = ['ADMIN', 'STAFF', 'VMT', 'CVT']
            if request.user.user_type in allowed_types:
                return True
        
        return False


class ReportingPermission(BasePermission):
    """
    Permission class for reporting access.
    """
    
    def has_permission(self, request, view):
        """Check if user has reporting access permission."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_superuser:
            return True
        
        # Staff users with reporting permissions
        if request.user.is_staff and request.user.has_perm('reporting.view_report'):
            return True
        
        # Specific user types
        if hasattr(request.user, 'user_type'):
            allowed_types = ['ADMIN', 'STAFF', 'VMT']
            if request.user.user_type in allowed_types:
                return True
        
        return False


class VolunteerManagementPermission(BasePermission):
    """
    Permission class for volunteer management access.
    """
    
    def has_permission(self, request, view):
        """Check if user has volunteer management permission."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_superuser:
            return True
        
        # Staff users with volunteer management permissions
        if request.user.is_staff and request.user.has_perm('volunteers.change_volunteerprofile'):
            return True
        
        # Specific user types
        if hasattr(request.user, 'user_type'):
            allowed_types = ['ADMIN', 'STAFF', 'VMT', 'CVT']
            if request.user.user_type in allowed_types:
                return True
        
        return False


class EventManagementPermission(BasePermission):
    """
    Permission class for event management access.
    """
    
    def has_permission(self, request, view):
        """Check if user has event management permission."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_superuser:
            return True
        
        # Staff users with event management permissions
        if request.user.is_staff and request.user.has_perm('events.change_event'):
            return True
        
        # Specific user types
        if hasattr(request.user, 'user_type'):
            allowed_types = ['ADMIN', 'STAFF', 'VMT']
            if request.user.user_type in allowed_types:
                return True
        
        return False


class TaskManagementPermission(BasePermission):
    """
    Permission class for task management access.
    """
    
    def has_permission(self, request, view):
        """Check if user has task management permission."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.is_superuser:
            return True
        
        # Staff users with task management permissions
        if request.user.is_staff and request.user.has_perm('tasks.change_task'):
            return True
        
        # Specific user types
        if hasattr(request.user, 'user_type'):
            allowed_types = ['ADMIN', 'STAFF', 'VMT', 'CVT']
            if request.user.user_type in allowed_types:
                return True
        
        return False


class IsStaffOrAdmin(permissions.BasePermission):
    """
    Permission that allows access to staff and admin users only
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.user_type in ['ADMIN', 'VMT', 'CVT', 'GOC'])
        )


class IsAdminOrVMT(permissions.BasePermission):
    """
    Permission that allows access to Admin and VMT users only
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['ADMIN', 'VMT']
        )


class AdminOverridePermission(permissions.BasePermission):
    """
    Comprehensive permission class for admin override management
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Only staff and above can access admin overrides
        if not request.user.is_staff and user_type not in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF']:
            return False
        
        # Different permissions based on action
        if view.action in ['list', 'retrieve']:
            # Staff and above can view overrides
            return user_type in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF'] or request.user.is_staff
        
        elif view.action == 'create':
            # Staff and above can create override requests
            return user_type in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF'] or request.user.is_staff
        
        elif view.action in ['update', 'partial_update']:
            # Only Admin and VMT can update overrides
            return user_type in ['ADMIN', 'VMT']
        
        elif view.action == 'destroy':
            # Only Admin can delete overrides
            return user_type == 'ADMIN'
        
        elif view.action in ['approve', 'reject', 'activate', 'revoke', 'complete']:
            # Only Admin and VMT can change override status
            return user_type in ['ADMIN', 'VMT']
        
        elif view.action in ['monitoring', 'bulk_operations']:
            # Admin and VMT can perform monitoring and bulk operations
            return user_type in ['ADMIN', 'VMT']
        
        elif view.action == 'statistics':
            # Staff and above can view statistics
            return user_type in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF'] or request.user.is_staff
        
        # Default to Admin only for unknown actions
        return user_type == 'ADMIN'
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Admin has full access
        if user_type == 'ADMIN':
            return True
        
        # VMT has most access
        if user_type == 'VMT':
            # VMT can't delete but can do everything else
            if view.action == 'destroy':
                return False
            return True
        
        # CVT and GOC can view and create their own overrides
        if user_type in ['CVT', 'GOC']:
            if view.action in ['list', 'retrieve']:
                return True
            elif view.action == 'create':
                return True
            elif view.action in ['update', 'partial_update']:
                # Can only update their own pending overrides
                return obj.requested_by == request.user and obj.status == 'PENDING'
            else:
                return False
        
        # Staff can view and create their own overrides
        if user_type == 'STAFF' or request.user.is_staff:
            if view.action in ['list', 'retrieve']:
                # Can view overrides they requested or that affect them
                return (
                    obj.requested_by == request.user or
                    obj.approved_by == request.user or
                    obj.reviewed_by == request.user
                )
            elif view.action == 'create':
                return True
            elif view.action in ['update', 'partial_update']:
                # Can only update their own pending overrides
                return obj.requested_by == request.user and obj.status == 'PENDING'
            else:
                return False
        
        return False


class AdminOverrideApprovalPermission(permissions.BasePermission):
    """
    Permission for approving/rejecting admin overrides
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Only Admin and VMT can approve/reject overrides
        return user_type in ['ADMIN', 'VMT']
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Admin can approve/reject any override
        if user_type == 'ADMIN':
            return True
        
        # VMT can approve/reject most overrides but not CRITICAL risk ones
        if user_type == 'VMT':
            # VMT cannot approve CRITICAL risk overrides
            if obj.risk_level == 'CRITICAL':
                return False
            # VMT cannot approve emergency overrides
            if obj.is_emergency:
                return False
            return True
        
        return False


class AdminOverrideBulkOperationPermission(permissions.BasePermission):
    """
    Permission for bulk operations on admin overrides
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Only Admin and VMT can perform bulk operations
        return user_type in ['ADMIN', 'VMT']


class AdminOverrideMonitoringPermission(permissions.BasePermission):
    """
    Permission for monitoring admin overrides
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Staff and above can perform monitoring
        return user_type in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF'] or request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Admin and VMT can monitor any override
        if user_type in ['ADMIN', 'VMT']:
            return True
        
        # Others can only monitor overrides they're involved with
        return (
            obj.requested_by == request.user or
            obj.approved_by == request.user or
            obj.reviewed_by == request.user
        )


class AdminOverrideStatsPermission(permissions.BasePermission):
    """
    Permission for viewing admin override statistics
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Staff and above can view statistics
        return user_type in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF'] or request.user.is_staff


class AuditLogPermission(permissions.BasePermission):
    """
    Permission for accessing audit logs
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        # Only Admin and VMT can access audit logs
        if view.action in ['list', 'retrieve']:
            return user_type in ['ADMIN', 'VMT']
        
        # No creation, update, or deletion of audit logs via API
        return False


class SystemConfigPermission(permissions.BasePermission):
    """
    Permission for system configuration management
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = getattr(request.user, 'user_type', None)
        
        if view.action in ['list', 'retrieve']:
            # Staff and above can view system config
            return user_type in ['ADMIN', 'VMT', 'CVT', 'GOC', 'STAFF'] or request.user.is_staff
        
        elif view.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only Admin can modify system config
            return user_type == 'ADMIN'
        
        return False


# Utility functions for permission management

def create_powerbi_permissions():
    """Create PowerBI-specific permissions."""
    try:
        # Get or create content type for common app
        content_type = ContentType.objects.get_or_create(
            app_label='common',
            model='powerbidata'
        )[0]
        
        # Create PowerBI permissions
        permissions = [
            ('view_powerbi_data', 'Can view PowerBI data'),
            ('export_powerbi_data', 'Can export PowerBI data'),
            ('manage_powerbi_cache', 'Can manage PowerBI cache'),
            ('view_analytics', 'Can view analytics data'),
            ('export_analytics', 'Can export analytics data'),
        ]
        
        created_permissions = []
        for codename, name in permissions:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                name=name,
                content_type=content_type
            )
            if created:
                created_permissions.append(permission)
        
        return created_permissions
        
    except Exception as e:
        print(f"Error creating PowerBI permissions: {str(e)}")
        return []


def assign_powerbi_permissions_to_user_types():
    """Assign PowerBI permissions to appropriate user types."""
    try:
        from django.contrib.auth.models import Group
        
        # Define permission mappings for user types
        user_type_permissions = {
            'ADMIN': [
                'view_powerbi_data',
                'export_powerbi_data', 
                'manage_powerbi_cache',
                'view_analytics',
                'export_analytics'
            ],
            'STAFF': [
                'view_powerbi_data',
                'export_powerbi_data',
                'view_analytics',
                'export_analytics'
            ],
            'VMT': [
                'view_powerbi_data',
                'view_analytics'
            ],
            'CVT': [
                'view_powerbi_data',
                'view_analytics'
            ],
            'GOC': [
                'view_powerbi_data',
                'export_powerbi_data',
                'view_analytics',
                'export_analytics'
            ]
        }
        
        # Create groups and assign permissions
        for user_type, permission_codenames in user_type_permissions.items():
            group, created = Group.objects.get_or_create(name=f'{user_type}_PowerBI')
            
            for codename in permission_codenames:
                try:
                    permission = Permission.objects.get(codename=codename)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    print(f"Permission {codename} not found")
            
            group.save()
        
        return True
        
    except Exception as e:
        print(f"Error assigning PowerBI permissions: {str(e)}")
        return False 