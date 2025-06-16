from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class TaskManagementPermission(permissions.BasePermission):
    """
    Permission class for task management operations.
    
    Allows:
    - Staff users to manage all tasks
    - Event managers to manage tasks in their events
    - Role coordinators to manage tasks for their roles
    - Volunteers to view tasks assigned to them
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access task management"""
        if not request.user.is_authenticated:
            return False
        
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        # Volunteers can view tasks assigned to them
        if hasattr(request.user, 'volunteer_profile'):
            # Read-only access for volunteers
            return request.method in permissions.SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific task"""
        if not request.user.is_authenticated:
            return False
        
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        # Volunteers can only access tasks assigned to them
        if hasattr(request.user, 'volunteer_profile'):
            # Check if volunteer has assignment for this task's role
            from events.models import Assignment
            
            if hasattr(obj, 'role'):  # Task object
                return Assignment.objects.filter(
                    volunteer=request.user,
                    role=obj.role,
                    status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']
                ).exists()
            elif hasattr(obj, 'task'):  # TaskCompletion object
                return Assignment.objects.filter(
                    volunteer=request.user,
                    role=obj.task.role,
                    status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']
                ).exists()
        
        return False


class TaskCompletionPermission(permissions.BasePermission):
    """
    Permission class for task completion operations.
    
    Allows:
    - Staff users to manage all completions
    - Volunteers to manage their own completions
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access task completions"""
        if not request.user.is_authenticated:
            return False
        
        # All authenticated users can access completions
        # (object-level permissions will filter appropriately)
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific completion"""
        if not request.user.is_authenticated:
            return False
        
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        # Volunteers can only access their own completions
        if hasattr(request.user, 'volunteer_profile'):
            return obj.volunteer == request.user
        
        return False


class TaskVerificationPermission(permissions.BasePermission):
    """
    Permission class for task verification operations.
    
    Only allows staff users to verify task completions.
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to verify tasks"""
        if not request.user.is_authenticated:
            return False
        
        # Only staff users can verify tasks
        return request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to verify specific completion"""
        if not request.user.is_authenticated:
            return False
        
        # Only staff users can verify tasks
        if not request.user.is_staff:
            return False
        
        # Event managers can verify completions in their events
        if hasattr(request.user, 'managed_events'):
            managed_events = request.user.managed_events.all()
            if managed_events.exists():
                if hasattr(obj, 'task'):  # TaskCompletion object
                    return obj.task.event in managed_events
        
        # Role coordinators can verify completions for their roles
        if hasattr(request.user, 'coordinated_roles'):
            coordinated_roles = request.user.coordinated_roles.all()
            if coordinated_roles.exists():
                if hasattr(obj, 'task'):  # TaskCompletion object
                    return obj.task.role in coordinated_roles
        
        # Superusers and admin staff have full access
        return request.user.is_superuser


class TaskBulkOperationPermission(permissions.BasePermission):
    """
    Permission class for bulk task operations.
    
    Only allows staff users to perform bulk operations.
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to perform bulk operations"""
        if not request.user.is_authenticated:
            return False
        
        # Only staff users can perform bulk operations
        return request.user.is_staff


class TaskStatsPermission(permissions.BasePermission):
    """
    Permission class for task statistics and analytics.
    
    Allows staff users to view task statistics.
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to view task statistics"""
        if not request.user.is_authenticated:
            return False
        
        # Only staff users can view comprehensive statistics
        return request.user.is_staff 