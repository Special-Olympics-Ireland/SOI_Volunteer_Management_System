from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsStaffOrVMTOrCVT(permissions.BasePermission):
    """
    Permission that allows access to staff users, VMT, or CVT members
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff users have access
        if request.user.is_staff:
            return True
        
        # Check for VMT or CVT user types
        if hasattr(request.user, 'user_type'):
            return request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        
        return False


class VolunteerProfilePermission(permissions.BasePermission):
    """
    Custom permission for volunteer profiles
    - Staff/VMT/CVT can view and modify all profiles
    - Volunteers can only view their own profile
    - Anonymous users have no access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        # VMT/CVT users have full access
        if hasattr(request.user, 'user_type') and request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']:
            return True
        
        # Volunteers have limited access (handled in has_object_permission)
        return True
    
    def has_object_permission(self, request, view, obj):
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        # VMT/CVT users have full access
        if hasattr(request.user, 'user_type') and request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']:
            return True
        
        # Volunteers can only access their own profile
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class VolunteerProfileManagementPermission(permissions.BasePermission):
    """
    Permission for volunteer profile management operations
    Only staff, VMT, CVT, GOC, and ADMIN users can perform management operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff users have access
        if request.user.is_staff:
            return True
        
        # Check for management user types
        if hasattr(request.user, 'user_type'):
            return request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        
        return False


class VolunteerProfileStatusPermission(permissions.BasePermission):
    """
    Permission for changing volunteer profile status
    Only staff, VMT, CVT, GOC, and ADMIN users can change status
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff users have access
        if request.user.is_staff:
            return True
        
        # Check for authorized user types
        if hasattr(request.user, 'user_type'):
            return request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        
        return False


class VolunteerBulkOperationPermission(permissions.BasePermission):
    """
    Permission for bulk operations on volunteer profiles
    Only staff, VMT, CVT, GOC, and ADMIN users can perform bulk operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff users have access
        if request.user.is_staff:
            return True
        
        # Check for authorized user types
        if hasattr(request.user, 'user_type'):
            return request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        
        return False


class VolunteerStatsPermission(permissions.BasePermission):
    """
    Permission for viewing volunteer statistics
    Staff, VMT, CVT, GOC, and ADMIN users can view global stats
    Volunteers can view their own stats
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff users have access
        if request.user.is_staff:
            return True
        
        # Check for authorized user types
        if hasattr(request.user, 'user_type'):
            return request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']
        
        # Volunteers have limited access (for their own stats)
        return True
    
    def has_object_permission(self, request, view, obj):
        # Staff users have full access
        if request.user.is_staff:
            return True
        
        # Management users have full access
        if hasattr(request.user, 'user_type') and request.user.user_type in ['VMT', 'CVT', 'GOC', 'ADMIN']:
            return True
        
        # Volunteers can only access their own stats
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False 