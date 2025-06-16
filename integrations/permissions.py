from rest_framework import permissions

class CanManageIntegrations(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_admin()

class CanViewIntegrationLogs(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_admin() or 
                               request.user.is_vmt()) 