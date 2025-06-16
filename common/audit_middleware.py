"""
Comprehensive audit middleware for SOI Hub Volunteer Management System.

This middleware automatically captures and logs all critical admin operations
including model changes, bulk operations, user actions, and sensitive operations
for compliance and security monitoring.
"""

import json
import time
from typing import Dict, Any, Optional
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from .models import AuditLog
from .audit import AuditEvent, log_audit_event, log_security_event

User = get_user_model()


class AdminAuditMiddleware:
    """
    Middleware to automatically audit all admin operations and critical system actions.
    """
    
    # Critical models that require detailed audit logging
    CRITICAL_MODELS = {
        'accounts.User',
        'volunteers.VolunteerProfile', 
        'events.Event',
        'events.Venue',
        'events.Role',
        'events.Assignment',
        'tasks.Task',
        'tasks.TaskCompletion',
        'common.AdminOverride',
        'common.SystemConfig',
        'integrations.JustGoSync',
        'reporting.Report'
    }
    
    # Admin paths that require audit logging
    ADMIN_PATHS = [
        '/admin/',
        '/api/admin/',
        '/management/'
    ]
    
    # Sensitive operations that require enhanced logging
    SENSITIVE_OPERATIONS = {
        'bulk_update', 'bulk_delete', 'export_data', 'import_data',
        'override_apply', 'permission_change', 'user_impersonate',
        'system_config_change', 'emergency_access'
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Record start time for performance tracking
        start_time = time.time()
        
        # Pre-process request
        self._pre_process_request(request)
        
        # Get response
        response = self.get_response(request)
        
        # Post-process response
        self._post_process_response(request, response, start_time)
        
        return response
    
    def _pre_process_request(self, request: HttpRequest) -> None:
        """Pre-process request to capture initial state."""
        # Store request start time
        request._audit_start_time = time.time()
        
        # Capture request data for audit
        request._audit_data = self._capture_request_data(request)
        
        # Check for sensitive operations
        if self._is_sensitive_operation(request):
            self._log_sensitive_operation_start(request)
    
    def _post_process_response(self, request: HttpRequest, response: HttpResponse, start_time: float) -> None:
        """Post-process response to log completed operations."""
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Only audit admin operations and API calls
        if not self._should_audit_request(request):
            return
        
        # Log the operation
        self._log_admin_operation(request, response, duration_ms)
        
        # Log any model changes detected
        self._log_model_changes(request, response)
        
        # Log bulk operations
        if self._is_bulk_operation(request):
            self._log_bulk_operation(request, response)
    
    def _should_audit_request(self, request: HttpRequest) -> bool:
        """Determine if request should be audited."""
        path = request.path
        
        # Always audit admin paths
        if any(path.startswith(admin_path) for admin_path in self.ADMIN_PATHS):
            return True
        
        # Audit API calls to critical endpoints
        if path.startswith('/api/') and any(model in path for model in self.CRITICAL_MODELS):
            return True
        
        # Audit sensitive operations
        if self._is_sensitive_operation(request):
            return True
        
        return False
    
    def _is_sensitive_operation(self, request: HttpRequest) -> bool:
        """Check if request involves sensitive operations."""
        path = request.path.lower()
        
        # Check for sensitive operation keywords in path
        for operation in self.SENSITIVE_OPERATIONS:
            if operation in path:
                return True
        
        # Check for bulk operations in POST data
        if request.method == 'POST':
            action = request.POST.get('action', '')
            if any(sensitive in action for sensitive in self.SENSITIVE_OPERATIONS):
                return True
        
        return False
    
    def _is_bulk_operation(self, request: HttpRequest) -> bool:
        """Check if request is a bulk operation."""
        if request.method != 'POST':
            return False
        
        # Django admin bulk actions
        action = request.POST.get('action', '')
        selected_items = request.POST.getlist('_selected_action')
        
        return bool(action and selected_items)
    
    def _capture_request_data(self, request: HttpRequest) -> Dict[str, Any]:
        """Capture relevant request data for audit."""
        data = {
            'method': request.method,
            'path': request.path,
            'user_id': request.user.id if request.user.is_authenticated else None,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': self._get_client_ip(request),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Capture POST data (sanitized)
        if request.method == 'POST':
            data['post_data'] = self._sanitize_post_data(request.POST.dict())
        
        # Capture query parameters
        if request.GET:
            data['query_params'] = dict(request.GET)
        
        return data
    
    def _sanitize_post_data(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize POST data to remove sensitive information."""
        sensitive_fields = {
            'password', 'password1', 'password2', 'old_password',
            'new_password', 'confirm_password', 'csrfmiddlewaretoken',
            'api_key', 'secret_key', 'token', 'auth_token'
        }
        
        sanitized = {}
        for key, value in post_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _log_admin_operation(self, request: HttpRequest, response: HttpResponse, duration_ms: int) -> None:
        """Log admin operation to audit log."""
        try:
            # Determine operation type
            operation_type = self._determine_operation_type(request, response)
            
            # Create audit event
            event = AuditEvent(
                category=AuditEvent.USER_ACTION,
                event_type=operation_type,
                description=f"Admin operation: {request.method} {request.path}",
                user=request.user if request.user.is_authenticated else None,
                request=request,
                metadata={
                    'response_status': response.status_code,
                    'duration_ms': duration_ms,
                    'operation_type': operation_type,
                    'request_data': request._audit_data if hasattr(request, '_audit_data') else {}
                }
            )
            
            # Create AuditLog record
            self._create_audit_log_record(request, response, operation_type, duration_ms)
            
            # Log the event
            if response.status_code >= 400:
                log_security_event(event)
            else:
                log_audit_event(event)
                
        except Exception as e:
            # Don't let audit logging break the application
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to log admin operation: {str(e)}")
    
    def _determine_operation_type(self, request: HttpRequest, response: HttpResponse) -> str:
        """Determine the type of operation being performed."""
        method = request.method
        path = request.path
        
        # Admin operations
        if '/admin/' in path:
            if method == 'POST':
                action = request.POST.get('action', '')
                if action:
                    return f"BULK_{action.upper()}"
                elif 'add' in path:
                    return 'CREATE'
                elif 'change' in path:
                    return 'UPDATE'
                elif 'delete' in path:
                    return 'DELETE'
                else:
                    return 'ADMIN_ACTION'
            elif method == 'GET':
                if 'changelist' in path:
                    return 'LIST'
                elif 'change' in path:
                    return 'VIEW'
                elif 'add' in path:
                    return 'VIEW_ADD_FORM'
                else:
                    return 'VIEW'
        
        # API operations
        elif '/api/' in path:
            if method == 'POST':
                return 'API_CREATE'
            elif method == 'PUT' or method == 'PATCH':
                return 'API_UPDATE'
            elif method == 'DELETE':
                return 'API_DELETE'
            elif method == 'GET':
                return 'API_READ'
        
        return method
    
    def _create_audit_log_record(self, request: HttpRequest, response: HttpResponse, 
                                operation_type: str, duration_ms: int) -> None:
        """Create AuditLog database record."""
        try:
            # Determine target object if possible
            content_type = None
            object_id = None
            object_representation = ''
            
            # Try to extract model info from path
            path_parts = request.path.strip('/').split('/')
            if 'admin' in path_parts and len(path_parts) >= 4:
                app_label = path_parts[path_parts.index('admin') + 1]
                model_name = path_parts[path_parts.index('admin') + 2]
                
                try:
                    content_type = ContentType.objects.get(
                        app_label=app_label, 
                        model=model_name
                    )
                    
                    # Try to get object ID
                    if len(path_parts) > path_parts.index('admin') + 3:
                        potential_id = path_parts[path_parts.index('admin') + 3]
                        if potential_id.isdigit() or potential_id != 'add':
                            object_id = potential_id
                            
                except ContentType.DoesNotExist:
                    pass
            
            # Create audit log record
            AuditLog.objects.create(
                action_type=operation_type,
                action_description=f"{operation_type} operation on {request.path}",
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key if hasattr(request, 'session') else '',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                content_type=content_type,
                object_id=str(object_id) if object_id else '',
                object_representation=object_representation,
                request_method=request.method,
                request_path=request.path,
                request_data=request._audit_data if hasattr(request, '_audit_data') else {},
                response_status=response.status_code,
                duration_ms=duration_ms,
                metadata={
                    'operation_type': operation_type,
                    'admin_operation': '/admin/' in request.path,
                    'bulk_operation': self._is_bulk_operation(request),
                    'sensitive_operation': self._is_sensitive_operation(request)
                }
            )
            
        except Exception as e:
            # Don't let audit logging break the application
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to create audit log record: {str(e)}")
    
    def _log_model_changes(self, request: HttpRequest, response: HttpResponse) -> None:
        """Log model changes detected during request."""
        # This would integrate with Django's LogEntry system
        # For now, we rely on model-level audit logging
        pass
    
    def _log_bulk_operation(self, request: HttpRequest, response: HttpResponse) -> None:
        """Log bulk operations with details."""
        if request.method != 'POST':
            return
        
        action = request.POST.get('action', '')
        selected_items = request.POST.getlist('_selected_action')
        
        if not (action and selected_items):
            return
        
        try:
            # Create detailed bulk operation audit event
            event = AuditEvent(
                category=AuditEvent.USER_ACTION,
                event_type=AuditEvent.BULK_OPERATION,
                description=f"Bulk operation: {action} on {len(selected_items)} items",
                user=request.user if request.user.is_authenticated else None,
                request=request,
                metadata={
                    'bulk_action': action,
                    'affected_count': len(selected_items),
                    'selected_items': selected_items[:100],  # Limit to first 100 IDs
                    'response_status': response.status_code
                }
            )
            
            log_audit_event(event)
            
        except Exception as e:
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to log bulk operation: {str(e)}")
    
    def _log_sensitive_operation_start(self, request: HttpRequest) -> None:
        """Log the start of sensitive operations."""
        try:
            event = AuditEvent(
                category=AuditEvent.SECURITY_EVENT,
                event_type='SENSITIVE_OPERATION_START',
                description=f"Sensitive operation started: {request.method} {request.path}",
                user=request.user if request.user.is_authenticated else None,
                request=request,
                metadata={
                    'operation_path': request.path,
                    'request_method': request.method
                }
            )
            
            log_security_event(event)
            
        except Exception as e:
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to log sensitive operation start: {str(e)}")


class ModelChangeAuditMixin:
    """
    Mixin for Django models to automatically audit changes.
    """
    
    def save(self, *args, **kwargs):
        """Override save to audit changes."""
        # Determine if this is a create or update
        is_create = self.pk is None
        
        # Capture old values for updates
        old_values = {}
        if not is_create:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_values = self._get_field_values(old_instance)
            except self.__class__.DoesNotExist:
                is_create = True
        
        # Save the model
        result = super().save(*args, **kwargs)
        
        # Audit the change
        self._audit_model_change(is_create, old_values)
        
        return result
    
    def delete(self, *args, **kwargs):
        """Override delete to audit deletion."""
        # Capture values before deletion
        old_values = self._get_field_values(self)
        
        # Delete the model
        result = super().delete(*args, **kwargs)
        
        # Audit the deletion
        self._audit_model_deletion(old_values)
        
        return result
    
    def _get_field_values(self, instance) -> Dict[str, Any]:
        """Get field values for audit logging."""
        values = {}
        
        for field in instance._meta.fields:
            try:
                value = getattr(instance, field.name)
                # Convert to JSON-serializable format
                if hasattr(value, 'isoformat'):  # datetime objects
                    values[field.name] = value.isoformat()
                elif hasattr(value, '__dict__'):  # Related objects
                    values[field.name] = str(value)
                else:
                    values[field.name] = value
            except Exception:
                values[field.name] = '[ERROR_RETRIEVING_VALUE]'
        
        return values
    
    def _audit_model_change(self, is_create: bool, old_values: Dict[str, Any]) -> None:
        """Audit model changes."""
        try:
            new_values = self._get_field_values(self)
            
            # Create audit log record
            AuditLog.objects.create(
                action_type='CREATE' if is_create else 'UPDATE',
                action_description=f"{'Created' if is_create else 'Updated'} {self.__class__.__name__}: {str(self)}",
                content_type=ContentType.objects.get_for_model(self),
                object_id=str(self.pk),
                object_representation=str(self),
                old_values=old_values,
                new_values=new_values,
                changes=self._calculate_changes(old_values, new_values) if not is_create else {},
                metadata={
                    'model_name': self.__class__.__name__,
                    'is_create': is_create,
                    'auto_audit': True
                }
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to audit model change for {self.__class__.__name__}: {str(e)}")
    
    def _audit_model_deletion(self, old_values: Dict[str, Any]) -> None:
        """Audit model deletion."""
        try:
            AuditLog.objects.create(
                action_type='DELETE',
                action_description=f"Deleted {self.__class__.__name__}: {str(self)}",
                content_type=ContentType.objects.get_for_model(self),
                object_id=str(self.pk),
                object_representation=str(self),
                old_values=old_values,
                metadata={
                    'model_name': self.__class__.__name__,
                    'is_delete': True,
                    'auto_audit': True
                }
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to audit model deletion for {self.__class__.__name__}: {str(e)}")
    
    def _calculate_changes(self, old_values: Dict[str, Any], new_values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Calculate what changed between old and new values."""
        changes = {}
        
        for field_name, new_value in new_values.items():
            old_value = old_values.get(field_name)
            if old_value != new_value:
                changes[field_name] = {
                    'old': old_value,
                    'new': new_value
                }
        
        return changes 