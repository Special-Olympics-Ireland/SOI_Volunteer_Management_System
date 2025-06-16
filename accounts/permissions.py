"""
User permissions for accounts app.
Implements role-based access control for user management.
"""

from rest_framework import permissions
from .models import User


class UserPermissions(permissions.BasePermission):
    """
    Custom permission class for user management.
    
    Rules:
    - Anyone can create a user (registration)
    - Users can view/edit their own profile
    - Staff can view all users
    - Admin can perform all operations
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access the view"""
        
        # Allow registration (POST to create)
        if view.action == 'create':
            return True
        
        # Require authentication for all other actions
        if not request.user.is_authenticated:
            return False
        
        # Admin users have full access
        if request.user.user_type == User.UserType.ADMIN:
            return True
        
        # Staff users can view users and get stats
        if request.user.is_staff:
            if view.action in ['list', 'retrieve', 'stats']:
                return True
            # Staff can approve/reject if they're VMT or higher
            if view.action in ['approve', 'reject']:
                return request.user.user_type in [
                    User.UserType.VMT, User.UserType.CVT, User.UserType.GOC, User.UserType.ADMIN
                ]
        
        # Regular users can only access their own data
        if view.action in ['retrieve', 'update', 'partial_update']:
            return True  # Object-level permission will be checked
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific user object"""
        
        # Admin users have full access
        if request.user.user_type == User.UserType.ADMIN:
            return True
        
        # Users can access their own profile
        if obj == request.user:
            return True
        
        # Staff users can view other users
        if request.user.is_staff and view.action == 'retrieve':
            return True
        
        # VMT and higher can approve/reject users
        if view.action in ['approve', 'reject']:
            return request.user.user_type in [
                User.UserType.VMT, User.UserType.CVT, User.UserType.GOC, User.UserType.ADMIN
            ]
        
        # Staff can update volunteer profiles if they're VMT or higher
        if view.action in ['update', 'partial_update']:
            if request.user.user_type in [User.UserType.VMT, User.UserType.CVT, User.UserType.GOC]:
                return obj.user_type == User.UserType.VOLUNTEER
        
        return False


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Permission that allows users to access their own data or staff to access any data.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.user_type == User.UserType.ADMIN:
            return True
        
        # Users can access their own data
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        elif obj == request.user:
            return True
        
        # Staff users have read access
        if request.user.is_staff and request.method in permissions.SAFE_METHODS:
            return True
        
        return False


class IsVolunteerManagerOrAbove(permissions.BasePermission):
    """
    Permission for volunteer management operations.
    Requires VMT level or above.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.user_type in [
            User.UserType.VMT, User.UserType.CVT, User.UserType.GOC, User.UserType.ADMIN
        ]


class IsEventManagerOrAbove(permissions.BasePermission):
    """
    Permission for event management operations.
    Requires staff level or above.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission that allows read access to authenticated users
    and write access only to admin users.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for admin
        return request.user.user_type == User.UserType.ADMIN


class CanManageVolunteers(permissions.BasePermission):
    """
    Permission for managing volunteer-related operations.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin and VMT+ can manage volunteers
        if request.user.user_type in [
            User.UserType.VMT, User.UserType.CVT, User.UserType.GOC, User.UserType.ADMIN
        ]:
            return True
        
        # Staff can view volunteers
        if request.user.is_staff and request.method in permissions.SAFE_METHODS:
            return True
        
        return False


class CanManageEvents(permissions.BasePermission):
    """
    Permission for managing event-related operations.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin and staff can manage events
        if request.user.is_staff:
            return True
        
        return False


class CanViewReports(permissions.BasePermission):
    """
    Permission for viewing reports and analytics.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff and above can view reports
        return request.user.is_staff


class CanManageSystem(permissions.BasePermission):
    """
    Permission for system management operations.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Only admin users can manage system
        return request.user.user_type == User.UserType.ADMIN 