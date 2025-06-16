from rest_framework import permissions

class IsEventManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_admin() or request.user.is_vmt())

class CanManageVenues(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_admin() or request.user.is_vmt())

class CanManageRoles(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_admin() or request.user.is_vmt()) 