"""
Audit logging utilities for SOI Hub Volunteer Management System.

This module provides standardized audit logging functionality for tracking
all critical operations, user actions, and system events for compliance
and security monitoring.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils import timezone

User = get_user_model()

# Get specialized loggers
audit_logger = logging.getLogger('soi_hub.audit')
security_logger = logging.getLogger('soi_hub.security')


class AuditEvent:
    """Standardized audit event structure."""
    
    # Event categories
    USER_ACTION = 'USER_ACTION'
    SYSTEM_EVENT = 'SYSTEM_EVENT'
    SECURITY_EVENT = 'SECURITY_EVENT'
    DATA_CHANGE = 'DATA_CHANGE'
    API_CALL = 'API_CALL'
    ADMIN_OVERRIDE = 'ADMIN_OVERRIDE'
    
    # Event types
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    VIEW = 'VIEW'
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    FAILED_LOGIN = 'FAILED_LOGIN'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    EOI_SUBMIT = 'EOI_SUBMIT'
    VOLUNTEER_ASSIGN = 'VOLUNTEER_ASSIGN'
    JUSTGO_SYNC = 'JUSTGO_SYNC'
    ADMIN_OVERRIDE_APPLIED = 'ADMIN_OVERRIDE_APPLIED'
    BULK_OPERATION = 'BULK_OPERATION'
    EXPORT_DATA = 'EXPORT_DATA'
    
    def __init__(self, 
                 category: str,
                 event_type: str,
                 description: str,
                 user: Optional[Union[User, str]] = None,
                 request: Optional[HttpRequest] = None,
                 resource_type: Optional[str] = None,
                 resource_id: Optional[Union[int, str]] = None,
                 old_values: Optional[Dict[str, Any]] = None,
                 new_values: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        
        self.category = category
        self.event_type = event_type
        self.description = description
        self.timestamp = timezone.now()
        
        # User information
        if isinstance(user, str):
            self.user_id = None
            self.username = user
            self.user_email = None
        elif user:
            self.user_id = user.id
            self.username = user.username
            self.user_email = getattr(user, 'email', None)
        else:
            self.user_id = None
            self.username = 'anonymous'
            self.user_email = None
        
        # Request information
        if request:
            self.ip_address = self._get_client_ip(request)
            self.user_agent = request.META.get('HTTP_USER_AGENT', '')
            self.request_method = request.method
            self.request_path = request.path
        else:
            self.ip_address = None
            self.user_agent = None
            self.request_method = None
            self.request_path = None
        
        # Resource information
        self.resource_type = resource_type
        self.resource_id = str(resource_id) if resource_id else None
        
        # Data changes
        self.old_values = old_values or {}
        self.new_values = new_values or {}
        
        # Additional metadata
        self.metadata = metadata or {}
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for logging."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'category': self.category,
            'event_type': self.event_type,
            'description': self.description,
            'user_id': self.user_id,
            'username': self.username,
            'user_email': self.user_email,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'metadata': self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


def log_audit_event(event: AuditEvent) -> None:
    """Log an audit event."""
    audit_logger.info(f"{event.description} | {event.to_json()}")


def log_security_event(event: AuditEvent) -> None:
    """Log a security-related event."""
    security_logger.warning(f"{event.description} | {event.to_json()}")


# Convenience functions for common audit events

def log_user_login(user: User, request: HttpRequest, success: bool = True) -> None:
    """Log user login attempt."""
    event = AuditEvent(
        category=AuditEvent.SECURITY_EVENT,
        event_type=AuditEvent.LOGIN if success else AuditEvent.FAILED_LOGIN,
        description=f"User {'login successful' if success else 'login failed'}",
        user=user,
        request=request,
        metadata={'success': success}
    )
    
    if success:
        log_audit_event(event)
    else:
        log_security_event(event)


def log_user_logout(user: User, request: HttpRequest) -> None:
    """Log user logout."""
    event = AuditEvent(
        category=AuditEvent.SECURITY_EVENT,
        event_type=AuditEvent.LOGOUT,
        description="User logout",
        user=user,
        request=request
    )
    log_audit_event(event)


def log_permission_denied(user: User, request: HttpRequest, resource: str) -> None:
    """Log permission denied event."""
    event = AuditEvent(
        category=AuditEvent.SECURITY_EVENT,
        event_type=AuditEvent.PERMISSION_DENIED,
        description=f"Permission denied for resource: {resource}",
        user=user,
        request=request,
        metadata={'resource': resource}
    )
    log_security_event(event)


def log_data_change(user: User, request: HttpRequest, resource_type: str, 
                   resource_id: Union[int, str], action: str,
                   old_values: Optional[Dict] = None, 
                   new_values: Optional[Dict] = None) -> None:
    """Log data change event."""
    event = AuditEvent(
        category=AuditEvent.DATA_CHANGE,
        event_type=action,
        description=f"{action} {resource_type} {resource_id}",
        user=user,
        request=request,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values
    )
    log_audit_event(event)


def log_eoi_submission(user: User, request: HttpRequest, volunteer_id: int, 
                      volunteer_type: str) -> None:
    """Log EOI submission."""
    event = AuditEvent(
        category=AuditEvent.USER_ACTION,
        event_type=AuditEvent.EOI_SUBMIT,
        description=f"EOI submitted for {volunteer_type} volunteer",
        user=user,
        request=request,
        resource_type='volunteer',
        resource_id=volunteer_id,
        metadata={'volunteer_type': volunteer_type}
    )
    log_audit_event(event)


def log_volunteer_assignment(admin_user: User, request: HttpRequest, 
                           volunteer_id: int, role_id: int, event_id: int,
                           assignment_type: str = 'manual') -> None:
    """Log volunteer assignment."""
    event = AuditEvent(
        category=AuditEvent.USER_ACTION,
        event_type=AuditEvent.VOLUNTEER_ASSIGN,
        description=f"Volunteer {volunteer_id} assigned to role {role_id} for event {event_id}",
        user=admin_user,
        request=request,
        resource_type='assignment',
        metadata={
            'volunteer_id': volunteer_id,
            'role_id': role_id,
            'event_id': event_id,
            'assignment_type': assignment_type
        }
    )
    log_audit_event(event)


def log_admin_override(admin_user: User, request: HttpRequest, 
                      override_type: str, resource_type: str, 
                      resource_id: Union[int, str], justification: str,
                      original_value: Any = None, new_value: Any = None) -> None:
    """Log admin override action."""
    event = AuditEvent(
        category=AuditEvent.ADMIN_OVERRIDE,
        event_type=AuditEvent.ADMIN_OVERRIDE_APPLIED,
        description=f"Admin override applied: {override_type}",
        user=admin_user,
        request=request,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values={'value': original_value} if original_value is not None else None,
        new_values={'value': new_value} if new_value is not None else None,
        metadata={
            'override_type': override_type,
            'justification': justification
        }
    )
    log_audit_event(event)


def log_justgo_sync(user: User, sync_type: str, success: bool, 
                   records_processed: int = 0, errors: Optional[list] = None) -> None:
    """Log JustGo synchronization event."""
    event = AuditEvent(
        category=AuditEvent.API_CALL,
        event_type=AuditEvent.JUSTGO_SYNC,
        description=f"JustGo {sync_type} sync {'completed' if success else 'failed'}",
        user=user,
        metadata={
            'sync_type': sync_type,
            'success': success,
            'records_processed': records_processed,
            'errors': errors or []
        }
    )
    log_audit_event(event)


def log_bulk_operation(admin_user: User, request: HttpRequest, 
                      operation_type: str, resource_type: str,
                      affected_count: int, criteria: Dict[str, Any]) -> None:
    """Log bulk operation."""
    event = AuditEvent(
        category=AuditEvent.USER_ACTION,
        event_type=AuditEvent.BULK_OPERATION,
        description=f"Bulk {operation_type} on {affected_count} {resource_type} records",
        user=admin_user,
        request=request,
        resource_type=resource_type,
        metadata={
            'operation_type': operation_type,
            'affected_count': affected_count,
            'criteria': criteria
        }
    )
    log_audit_event(event)


def log_data_export(user: User, request: HttpRequest, export_type: str,
                   resource_type: str, record_count: int, 
                   export_format: str = 'csv') -> None:
    """Log data export event."""
    event = AuditEvent(
        category=AuditEvent.USER_ACTION,
        event_type=AuditEvent.EXPORT_DATA,
        description=f"Data export: {export_type} ({record_count} {resource_type} records)",
        user=user,
        request=request,
        resource_type=resource_type,
        metadata={
            'export_type': export_type,
            'record_count': record_count,
            'export_format': export_format
        }
    )
    log_audit_event(event)


# Decorator for automatic audit logging
def audit_action(category: str, event_type: str, description: str,
                resource_type: Optional[str] = None):
    """Decorator to automatically log audit events for view functions."""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # Execute the original function
            result = func(request, *args, **kwargs)
            
            # Log the audit event
            resource_id = kwargs.get('pk') or kwargs.get('id')
            event = AuditEvent(
                category=category,
                event_type=event_type,
                description=description,
                user=getattr(request, 'user', None),
                request=request,
                resource_type=resource_type,
                resource_id=resource_id
            )
            log_audit_event(event)
            
            return result
        return wrapper
    return decorator 