"""
Comprehensive audit service for SOI Hub Volunteer Management System.

This service provides high-level functions for logging critical admin operations
with proper categorization, metadata, and integration with the audit middleware.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone
from django.db.models import Model, Q
from django.core.serializers.json import DjangoJSONEncoder

from .models import AuditLog
from .audit import AuditEvent, log_audit_event, log_security_event

User = get_user_model()


class AdminAuditService:
    """
    Service class for comprehensive admin operation audit logging.
    """
    
    # Critical operations that require enhanced audit logging
    CRITICAL_OPERATIONS = {
        'USER_MANAGEMENT': [
            'user_create', 'user_update', 'user_delete', 'user_activate', 
            'user_deactivate', 'permission_grant', 'permission_revoke',
            'role_assign', 'role_remove', 'password_reset', 'account_lock'
        ],
        'VOLUNTEER_MANAGEMENT': [
            'volunteer_create', 'volunteer_update', 'volunteer_delete',
            'volunteer_assign', 'volunteer_unassign', 'eoi_approve',
            'eoi_reject', 'profile_verify', 'credential_override'
        ],
        'EVENT_MANAGEMENT': [
            'event_create', 'event_update', 'event_delete', 'event_publish',
            'event_cancel', 'venue_assign', 'capacity_change', 'role_modify'
        ],
        'SYSTEM_MANAGEMENT': [
            'config_change', 'system_override', 'bulk_operation',
            'data_export', 'data_import', 'backup_create', 'restore_execute'
        ],
        'SECURITY_OPERATIONS': [
            'admin_login', 'admin_logout', 'permission_escalation',
            'emergency_access', 'security_override', 'audit_access'
        ]
    }
    
    @classmethod
    def log_user_management_operation(cls, operation: str, user: User, target_user: User,
                                    request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log user management operations."""
        cls._log_critical_operation(
            category='USER_MANAGEMENT',
            operation=operation,
            user=user,
            request=request,
            target_object=target_user,
            details=details or {},
            description=f"User management: {operation} for user {target_user.username}"
        )
    
    @classmethod
    def log_volunteer_management_operation(cls, operation: str, user: User, volunteer_profile,
                                         request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log volunteer management operations."""
        cls._log_critical_operation(
            category='VOLUNTEER_MANAGEMENT',
            operation=operation,
            user=user,
            request=request,
            target_object=volunteer_profile,
            details=details or {},
            description=f"Volunteer management: {operation} for volunteer {volunteer_profile.id}"
        )
    
    @classmethod
    def log_event_management_operation(cls, operation: str, user: User, event,
                                     request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log event management operations."""
        cls._log_critical_operation(
            category='EVENT_MANAGEMENT',
            operation=operation,
            user=user,
            request=request,
            target_object=event,
            details=details or {},
            description=f"Event management: {operation} for event {event.name}"
        )
    
    @classmethod
    def log_system_management_operation(cls, operation: str, user: User, 
                                      request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log system management operations."""
        cls._log_critical_operation(
            category='SYSTEM_MANAGEMENT',
            operation=operation,
            user=user,
            request=request,
            details=details or {},
            description=f"System management: {operation}"
        )
    
    @classmethod
    def log_security_operation(cls, operation: str, user: User,
                             request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log security operations."""
        cls._log_critical_operation(
            category='SECURITY_OPERATIONS',
            operation=operation,
            user=user,
            request=request,
            details=details or {},
            description=f"Security operation: {operation}",
            is_security_event=True
        )
    
    @classmethod
    def log_bulk_operation(cls, user: User, operation_type: str, affected_count: int,
                          operation_details: Dict[str, Any] = None, request: HttpRequest = None,
                          details: Dict[str, Any] = None) -> None:
        """Log bulk operations with detailed information."""
        bulk_details = {
            'operation_type': operation_type,
            'affected_count': affected_count,
            'operation_details': operation_details or {},
            'bulk_operation': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SYSTEM_MANAGEMENT',
            operation='bulk_operation',
            user=user,
            request=request,
            details=bulk_details,
            description=f"Bulk operation: {operation_type} affecting {affected_count} records"
        )
    
    @classmethod
    def log_data_export(cls, user: User, export_type: str, data_type: str = None,
                       record_count: int = 0, file_format: str = 'csv',
                       request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log data export operations."""
        export_details = {
            'export_type': export_type,
            'data_type': data_type or 'unknown',
            'record_count': record_count,
            'file_format': file_format,
            'data_export': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SYSTEM_MANAGEMENT',
            operation='data_export',
            user=user,
            request=request,
            details=export_details,
            description=f"Data export: {export_type} - {record_count} {data_type} records as {file_format}"
        )
    
    @classmethod
    def log_report_generation(cls, user: User, report_type: str, report_name: str,
                            parameters: Dict[str, Any] = None, request: HttpRequest = None,
                            details: Dict[str, Any] = None) -> None:
        """Log report generation operations."""
        report_details = {
            'report_type': report_type,
            'report_name': report_name,
            'parameters': parameters or {},
            'report_generation': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SYSTEM_MANAGEMENT',
            operation='report_generation',
            user=user,
            request=request,
            details=report_details,
            description=f"Report generation: {report_type} - {report_name}"
        )
    
    @classmethod
    def log_admin_override(cls, user: User, override_type: str, target_object: Model,
                          justification: str, original_value: Any = None, new_value: Any = None,
                          request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log admin override operations."""
        override_details = {
            'override_type': override_type,
            'justification': justification,
            'original_value': original_value,
            'new_value': new_value,
            'admin_override': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SYSTEM_MANAGEMENT',
            operation='admin_override',
            user=user,
            request=request,
            target_object=target_object,
            details=override_details,
            description=f"Admin override: {override_type} on {target_object.__class__.__name__} {target_object.pk}",
            is_security_event=True
        )
    
    @classmethod
    def log_permission_change(cls, user: User, target_user: User, permission_change: str,
                            permissions: List[str], request: HttpRequest = None,
                            details: Dict[str, Any] = None) -> None:
        """Log permission changes."""
        permission_details = {
            'permission_change': permission_change,
            'permissions': permissions,
            'target_user_id': target_user.id,
            'target_username': target_user.username,
            'permission_operation': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SECURITY_OPERATIONS',
            operation='permission_change',
            user=user,
            request=request,
            target_object=target_user,
            details=permission_details,
            description=f"Permission change: {permission_change} for user {target_user.username}",
            is_security_event=True
        )
    
    @classmethod
    def log_emergency_access(cls, user: User, access_type: str, justification: str,
                           request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log emergency access operations."""
        emergency_details = {
            'access_type': access_type,
            'justification': justification,
            'emergency_access': True,
            'requires_review': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SECURITY_OPERATIONS',
            operation='emergency_access',
            user=user,
            request=request,
            details=emergency_details,
            description=f"Emergency access: {access_type} - {justification}",
            is_security_event=True
        )
    
    @classmethod
    def log_system_configuration_change(cls, user: User, config_key: str, 
                                      old_value: Any, new_value: Any,
                                      request: HttpRequest = None, details: Dict[str, Any] = None) -> None:
        """Log system configuration changes."""
        config_details = {
            'config_key': config_key,
            'old_value': old_value,
            'new_value': new_value,
            'config_change': True,
            'requires_monitoring': True,
            **(details or {})
        }
        
        cls._log_critical_operation(
            category='SYSTEM_MANAGEMENT',
            operation='config_change',
            user=user,
            request=request,
            details=config_details,
            description=f"System configuration change: {config_key}",
            is_security_event=True
        )
    
    @classmethod
    def _log_critical_operation(cls, category: str, operation: str, user: User,
                              request: HttpRequest = None, target_object: Model = None,
                              details: Dict[str, Any] = None, description: str = None,
                              is_security_event: bool = False) -> None:
        """Internal method to log critical operations."""
        try:
            # Prepare metadata
            metadata = {
                'category': category,
                'operation': operation,
                'critical_operation': True,
                'timestamp': timezone.now().isoformat(),
                **(details or {})
            }
            
            # Add request information if available
            if request:
                metadata.update({
                    'request_method': request.method,
                    'request_path': request.path,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': cls._get_client_ip(request)
                })
            
            # Create audit event
            event = AuditEvent(
                category=AuditEvent.SECURITY_EVENT if is_security_event else AuditEvent.USER_ACTION,
                event_type=operation.upper(),
                description=description or f"{category}: {operation}",
                user=user,
                request=request,
                resource_type=target_object.__class__.__name__ if target_object else None,
                resource_id=target_object.pk if target_object else None,
                metadata=metadata
            )
            
            # Create database audit log
            audit_log = AuditLog.objects.create(
                action_type=operation.upper(),
                action_description=description or f"{category}: {operation}",
                user=user,
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                ip_address=cls._get_client_ip(request) if request else '',
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
                content_type=ContentType.objects.get_for_model(target_object) if target_object else None,
                object_id=str(target_object.pk) if target_object else '',
                object_representation=str(target_object) if target_object else '',
                request_method=request.method if request else '',
                request_path=request.path if request else '',
                request_data=cls._sanitize_request_data(request) if request else {},
                metadata=metadata,
                tags=[category.lower(), operation.lower(), 'critical_operation']
            )
            
            # Log the event
            if is_security_event:
                log_security_event(event)
            else:
                log_audit_event(event)
            
            return audit_log
            
        except Exception as e:
            # Don't let audit logging break the application
            import logging
            logger = logging.getLogger('soi_hub.audit')
            logger.error(f"Failed to log critical operation {operation}: {str(e)}")
    
    @classmethod
    def _get_client_ip(cls, request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    @classmethod
    def _sanitize_request_data(cls, request: HttpRequest) -> Dict[str, Any]:
        """Sanitize request data for audit logging."""
        sensitive_fields = {
            'password', 'password1', 'password2', 'old_password',
            'new_password', 'confirm_password', 'csrfmiddlewaretoken',
            'api_key', 'secret_key', 'token', 'auth_token'
        }
        
        data = {}
        
        # Sanitize POST data
        if request.method == 'POST' and hasattr(request, 'POST'):
            post_data = {}
            for key, value in request.POST.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    post_data[key] = '[REDACTED]'
                else:
                    post_data[key] = value
            data['post_data'] = post_data
        
        # Add query parameters
        if request.GET:
            data['query_params'] = dict(request.GET)
        
        return data
    
    @classmethod
    def get_audit_summary(cls, days: int = 7) -> Dict[str, Any]:
        """Get audit summary for the specified number of days."""
        start_date = timezone.now() - timedelta(days=days)
        
        # Get audit logs for the period
        audit_logs = AuditLog.objects.filter(timestamp__gte=start_date)
        
        # Calculate summary statistics
        summary = {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
            'total_operations': audit_logs.count(),
            'operations_by_type': {},
            'operations_by_user': {},
            'critical_operations': 0,
            'security_events': 0,
            'failed_operations': 0,
            'top_users': [],
            'recent_critical_operations': []
        }
        
        # Count operations by type
        for log in audit_logs:
            action_type = log.action_type
            summary['operations_by_type'][action_type] = summary['operations_by_type'].get(action_type, 0) + 1
            
            # Count by user
            if log.user:
                username = log.user.username
                summary['operations_by_user'][username] = summary['operations_by_user'].get(username, 0) + 1
            
            # Count critical operations
            if log.metadata.get('critical_operation'):
                summary['critical_operations'] += 1
            
            # Count security events
            if log.metadata.get('category') == 'SECURITY_OPERATIONS':
                summary['security_events'] += 1
            
            # Count failed operations
            if log.response_status and log.response_status >= 400:
                summary['failed_operations'] += 1
        
        # Get top users
        user_counts = sorted(summary['operations_by_user'].items(), key=lambda x: x[1], reverse=True)
        summary['top_users'] = user_counts[:10]
        
        # Get recent critical operations
        critical_logs = audit_logs.filter(
            metadata__critical_operation=True
        ).order_by('-timestamp')[:10]
        
        summary['recent_critical_operations'] = [
            {
                'timestamp': log.timestamp.isoformat(),
                'user': log.user.username if log.user else 'Anonymous',
                'action': log.action_type,
                'description': log.action_description,
                'object': log.object_representation
            }
            for log in critical_logs
        ]
        
        return summary
    
    @classmethod
    def get_security_alerts(cls, hours: int = 24) -> List[Dict[str, Any]]:
        """Get security alerts for the specified number of hours."""
        start_time = timezone.now() - timedelta(hours=hours)
        
        # Get security-related audit logs
        security_logs = AuditLog.objects.filter(
            timestamp__gte=start_time,
            metadata__category='SECURITY_OPERATIONS'
        ).order_by('-timestamp')
        
        alerts = []
        for log in security_logs:
            alerts.append({
                'timestamp': log.timestamp.isoformat(),
                'user': log.user.username if log.user else 'Anonymous',
                'action': log.action_type,
                'description': log.action_description,
                'ip_address': log.ip_address,
                'severity': cls._determine_alert_severity(log),
                'metadata': log.metadata
            })
        
        return alerts
    
    @classmethod
    def _determine_alert_severity(cls, audit_log: AuditLog) -> str:
        """Determine the severity of a security alert."""
        high_risk_operations = {
            'EMERGENCY_ACCESS', 'PERMISSION_ESCALATION', 'ADMIN_OVERRIDE',
            'SECURITY_OVERRIDE', 'BULK_DELETE', 'DATA_EXPORT'
        }
        
        if audit_log.action_type in high_risk_operations:
            return 'HIGH'
        elif audit_log.metadata.get('emergency_access'):
            return 'HIGH'
        elif audit_log.metadata.get('admin_override'):
            return 'MEDIUM'
        elif audit_log.response_status and audit_log.response_status >= 400:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    @classmethod
    def export_audit_logs(cls, start_date: datetime, end_date: datetime,
                         format: str = 'csv') -> str:
        """Export audit logs for the specified date range."""
        import csv
        import io
        
        # Get audit logs for the period
        audit_logs = AuditLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('-timestamp')
        
        if format.lower() == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Timestamp', 'User', 'Action Type', 'Description',
                'Object Type', 'Object ID', 'IP Address', 'User Agent',
                'Request Method', 'Request Path', 'Response Status',
                'Duration (ms)', 'Metadata'
            ])
            
            # Write data
            for log in audit_logs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    log.user.username if log.user else 'Anonymous',
                    log.action_type,
                    log.action_description,
                    log.content_type.model if log.content_type else '',
                    log.object_id,
                    log.ip_address,
                    log.user_agent,
                    log.request_method,
                    log.request_path,
                    log.response_status or '',
                    log.duration_ms or '',
                    json.dumps(log.metadata, cls=DjangoJSONEncoder)
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}") 