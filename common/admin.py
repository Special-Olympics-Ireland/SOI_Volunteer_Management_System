from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.db import models
import csv
from datetime import datetime

from .models import AdminOverride, AuditLog, ContentItem, FAQ, VenueInformation, Theme, UserThemePreference
from .forms import ThemeForm, UserThemePreferenceForm
from .audit_service import AdminAuditService


@admin.register(AdminOverride)
class AdminOverrideAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for AdminOverride model with comprehensive management,
    approval workflow, and audit capabilities.
    """
    
    # List display configuration
    list_display = (
        'title', 'override_type', 'status_display', 'risk_display',
        'requested_by', 'priority_display', 'effective_period',
        'approval_status', 'created_at'
    )
    
    # Advanced filtering
    list_filter = (
        'override_type', 'status', 'risk_level', 'impact_level',
        'is_emergency', 'priority_level', 'requires_monitoring',
        ('created_at', admin.DateFieldListFilter),
        ('approved_at', admin.DateFieldListFilter),
        ('effective_from', admin.DateFieldListFilter),
        ('effective_until', admin.DateFieldListFilter),
        'requested_by', 'approved_by'
    )
    
    # Search fields
    search_fields = (
        'title', 'description', 'justification', 'business_case',
        'requested_by__username', 'approved_by__username',
        'tags', 'risk_assessment', 'impact_assessment'
    )
    
    # Ordering
    ordering = ('-is_emergency', '-priority_level', '-created_at')
    
    # Items per page
    list_per_page = 25
    
    # Fieldsets for organized form layout
    fieldsets = (
        (_('Override Details'), {
            'fields': ('title', 'override_type', 'description', 'justification'),
            'classes': ('wide',)
        }),
        (_('Target Object'), {
            'fields': ('content_type', 'object_id'),
            'classes': ('wide',)
        }),
        (_('Business Case & Assessment'), {
            'fields': ('business_case', 'risk_level', 'impact_level', 'risk_assessment', 'impact_assessment'),
            'classes': ('wide',)
        }),
        (_('Override Data'), {
            'fields': ('override_data', 'original_values', 'new_values'),
            'classes': ('collapse',)
        }),
        (_('Approval Workflow'), {
            'fields': (
                'status', 'requested_by', 'approved_by', 'reviewed_by',
                'approval_notes', 'review_notes', 'rejection_reason'
            ),
            'classes': ('wide',)
        }),
        (_('Timing & Duration'), {
            'fields': ('effective_from', 'effective_until', 'applied_at', 'revoked_at'),
            'classes': ('collapse',)
        }),
        (_('Priority & Emergency'), {
            'fields': (
                'is_emergency', 'priority_level', 'requires_immediate_action'
            ),
            'classes': ('collapse',)
        }),
        (_('Compliance & Documentation'), {
            'fields': (
                'compliance_notes', 'regulatory_impact',
                'documentation_required', 'documentation_provided'
            ),
            'classes': ('collapse',)
        }),
        (_('Monitoring & Follow-up'), {
            'fields': (
                'requires_monitoring', 'monitoring_frequency',
                'last_monitored_at', 'monitoring_notes'
            ),
            'classes': ('collapse',)
        }),
        (_('Communication'), {
            'fields': (
                'notification_sent', 'stakeholders_notified', 'communication_log'
            ),
            'classes': ('collapse',)
        }),
        (_('Status Tracking'), {
            'fields': (
                'status_changed_at', 'status_changed_by', 'status_change_reason'
            ),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('tags', 'external_references', 'custom_fields'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at', 'updated_at', 'requested_at', 'approved_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'requested_at', 'approved_at',
        'applied_at', 'revoked_at', 'status_changed_at', 'last_monitored_at'
    )
    
    # Raw ID fields
    raw_id_fields = (
        'requested_by', 'approved_by', 'reviewed_by', 'status_changed_by'
    )
    
    # Custom methods for list display
    def status_display(self, obj):
        """Display status with color coding and icons"""
        status_colors = {
            'PENDING': 'orange',
            'APPROVED': 'blue',
            'REJECTED': 'red',
            'ACTIVE': 'green',
            'EXPIRED': 'gray',
            'REVOKED': 'red',
            'COMPLETED': 'green'
        }
        
        status_icons = {
            'PENDING': '⏳',
            'APPROVED': '✅',
            'REJECTED': '❌',
            'ACTIVE': '🟢',
            'EXPIRED': '⏰',
            'REVOKED': '🚫',
            'COMPLETED': '✅'
        }
        
        color = status_colors.get(obj.status, 'black')
        icon = status_icons.get(obj.status, '❓')
        
        emergency_flag = ' 🚨' if obj.is_emergency else ''
        
        return format_html(
            '<span style="color: {};">{} {}{}</span>',
            color, icon, obj.get_status_display(), emergency_flag
        )
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'status'
    
    def risk_display(self, obj):
        """Display risk level with color coding"""
        risk_colors = {
            'LOW': 'green',
            'MEDIUM': 'orange',
            'HIGH': 'red',
            'CRITICAL': 'darkred'
        }
        
        risk_icons = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🔴',
            'CRITICAL': '🚨'
        }
        
        color = risk_colors.get(obj.risk_level, 'black')
        icon = risk_icons.get(obj.risk_level, '❓')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_risk_level_display()
        )
    risk_display.short_description = _('Risk Level')
    risk_display.admin_order_field = 'risk_level'
    
    def priority_display(self, obj):
        """Display priority level with visual indicators"""
        if obj.priority_level <= 2:
            color, icon = 'red', '🔥'
        elif obj.priority_level <= 4:
            color, icon = 'orange', '⚡'
        elif obj.priority_level <= 6:
            color, icon = 'blue', '➡️'
        else:
            color, icon = 'gray', '⬇️'
        
        return format_html(
            '<span style="color: {};">{} P{}</span>',
            color, icon, obj.priority_level
        )
    priority_display.short_description = _('Priority')
    priority_display.admin_order_field = 'priority_level'
    
    def effective_period(self, obj):
        """Display effective period"""
        if not obj.effective_from:
            return format_html('<span style="color: gray;">Not set</span>')
        
        now = timezone.now()
        
        if obj.effective_from > now:
            return format_html(
                '<span style="color: blue;">⏰ Starts {}</span>',
                obj.effective_from.strftime('%Y-%m-%d %H:%M')
            )
        elif obj.effective_until and obj.effective_until < now:
            return format_html(
                '<span style="color: red;">⏰ Expired {}</span>',
                obj.effective_until.strftime('%Y-%m-%d %H:%M')
            )
        elif obj.effective_until:
            return format_html(
                '<span style="color: green;">✅ Until {}</span>',
                obj.effective_until.strftime('%Y-%m-%d %H:%M')
            )
        else:
            return format_html('<span style="color: green;">✅ Indefinite</span>')
    effective_period.short_description = _('Effective Period')
    
    def approval_status(self, obj):
        """Display approval workflow status"""
        if obj.status == 'PENDING':
            return format_html('<span style="color: orange;">⏳ Awaiting Approval</span>')
        elif obj.approved_by:
            return format_html(
                '<span style="color: green;">✅ Approved by {}</span>',
                obj.approved_by.get_full_name() or obj.approved_by.username
            )
        elif obj.status == 'REJECTED':
            return format_html('<span style="color: red;">❌ Rejected</span>')
        else:
            return format_html('<span style="color: gray;">—</span>')
    approval_status.short_description = _('Approval Status')
    
    # Bulk actions
    actions = [
        'approve_overrides', 'reject_overrides', 'activate_overrides',
        'revoke_overrides', 'mark_emergency', 'unmark_emergency',
        'extend_validity', 'update_monitoring', 'export_override_data'
    ]
    
    def approve_overrides(self, request, queryset):
        """Bulk approve selected overrides"""
        pending_overrides = queryset.filter(status='PENDING')
        count = 0
        override_ids = []
        
        for override in pending_overrides:
            try:
                override.approve(request.user, f'Bulk approved by {request.user.username}')
                count += 1
                override_ids.append(str(override.id))
            except Exception as e:
                messages.error(request, f'Failed to approve {override.title}: {str(e)}')
        
        if count > 0:
            # Log bulk approval operation
            AdminAuditService.log_bulk_operation(
                operation='approve_overrides',
                user=request.user,
                model_class=AdminOverride,
                affected_count=count,
                criteria={'status': 'PENDING'},
                request=request,
                details={
                    'override_ids': override_ids,
                    'approval_method': 'bulk_admin_action',
                    'notes': f'Bulk approved by {request.user.username}'
                }
            )
            
            messages.success(request, f'Successfully approved {count} override(s).')
        else:
            messages.warning(request, 'No pending overrides were found to approve.')
    approve_overrides.short_description = _('Approve selected overrides')
    
    def reject_overrides(self, request, queryset):
        """Bulk reject selected overrides"""
        pending_overrides = queryset.filter(status='PENDING')
        count = 0
        
        for override in pending_overrides:
            try:
                override.reject(request.user, f'Bulk rejected by {request.user.username}')
                count += 1
            except Exception as e:
                messages.error(request, f'Failed to reject {override.title}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'Successfully rejected {count} override(s).')
        else:
            messages.warning(request, 'No pending overrides were found to reject.')
    reject_overrides.short_description = _('Reject selected overrides')
    
    def activate_overrides(self, request, queryset):
        """Bulk activate approved overrides"""
        approved_overrides = queryset.filter(status='APPROVED')
        count = 0
        
        for override in approved_overrides:
            try:
                override.activate(request.user)
                count += 1
            except Exception as e:
                messages.error(request, f'Failed to activate {override.title}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'Successfully activated {count} override(s).')
        else:
            messages.warning(request, 'No approved overrides were found to activate.')
    activate_overrides.short_description = _('Activate approved overrides')
    
    def revoke_overrides(self, request, queryset):
        """Bulk revoke active overrides"""
        active_overrides = queryset.filter(status='ACTIVE')
        count = 0
        
        for override in active_overrides:
            try:
                override.revoke(request.user, f'Bulk revoked by {request.user.username}')
                count += 1
            except Exception as e:
                messages.error(request, f'Failed to revoke {override.title}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'Successfully revoked {count} override(s).')
        else:
            messages.warning(request, 'No active overrides were found to revoke.')
    revoke_overrides.short_description = _('Revoke active overrides')
    
    def mark_emergency(self, request, queryset):
        """Mark selected overrides as emergency"""
        count = queryset.update(
            is_emergency=True,
            priority_level=1,
            requires_immediate_action=True
        )
        messages.success(request, f'Marked {count} override(s) as emergency.')
    mark_emergency.short_description = _('Mark as emergency')
    
    def unmark_emergency(self, request, queryset):
        """Unmark selected overrides as emergency"""
        count = queryset.update(
            is_emergency=False,
            requires_immediate_action=False
        )
        messages.success(request, f'Unmarked {count} override(s) as emergency.')
    unmark_emergency.short_description = _('Unmark as emergency')
    
    def extend_validity(self, request, queryset):
        """Extend validity period by 30 days"""
        from datetime import timedelta
        
        count = 0
        for override in queryset:
            if override.effective_until:
                override.effective_until += timedelta(days=30)
                override.save()
                count += 1
        
        messages.success(request, f'Extended validity for {count} override(s) by 30 days.')
    extend_validity.short_description = _('Extend validity by 30 days')
    
    def update_monitoring(self, request, queryset):
        """Update monitoring timestamp for selected overrides"""
        count = queryset.update(
            last_monitored_at=timezone.now(),
            monitoring_notes=f'Bulk monitoring update by {request.user.username} at {timezone.now()}'
        )
        messages.success(request, f'Updated monitoring for {count} override(s).')
    update_monitoring.short_description = _('Update monitoring timestamp')
    
    def export_override_data(self, request, queryset):
        """Export selected overrides to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="admin_overrides_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Title', 'Type', 'Status', 'Risk Level', 'Impact Level',
            'Requested By', 'Approved By', 'Created At', 'Effective From',
            'Effective Until', 'Is Emergency', 'Priority Level', 'Justification'
        ])
        
        record_count = 0
        for override in queryset:
            writer.writerow([
                str(override.id),
                override.title,
                override.get_override_type_display(),
                override.get_status_display(),
                override.get_risk_level_display(),
                override.get_impact_level_display(),
                override.requested_by.username if override.requested_by else '',
                override.approved_by.username if override.approved_by else '',
                override.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                override.effective_from.strftime('%Y-%m-%d %H:%M:%S') if override.effective_from else '',
                override.effective_until.strftime('%Y-%m-%d %H:%M:%S') if override.effective_until else '',
                'Yes' if override.is_emergency else 'No',
                override.priority_level,
                override.justification[:100] + '...' if len(override.justification) > 100 else override.justification
            ])
            record_count += 1
        
        # Log data export operation
        AdminAuditService.log_data_export(
            user=request.user,
            export_type='admin_overrides',
            model_class=AdminOverride,
            record_count=record_count,
            export_format='csv',
            request=request,
            details={
                'filename': f"admin_overrides_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                'export_method': 'admin_bulk_action'
            }
        )
        
        return response
    export_override_data.short_description = _('Export selected overrides to CSV')
    
    def save_model(self, request, obj, form, change):
        """Override save to track status changes and set defaults"""
        old_status = None
        if change:
            try:
                old_obj = AdminOverride.objects.get(pk=obj.pk)
                old_status = old_obj.status
            except AdminOverride.DoesNotExist:
                pass
        
        if not change:  # New object
            obj.requested_by = request.user
            obj.requested_at = timezone.now()
        
        # Track status changes
        if change and 'status' in form.changed_data:
            obj.status_changed_at = timezone.now()
            obj.status_changed_by = request.user
            
            # Auto-set approval/rejection timestamps
            if obj.status == 'APPROVED' and not obj.approved_at:
                obj.approved_at = timezone.now()
                obj.approved_by = request.user
            elif obj.status == 'ACTIVE' and not obj.applied_at:
                obj.applied_at = timezone.now()
            elif obj.status == 'REVOKED' and not obj.revoked_at:
                obj.revoked_at = timezone.now()
        
        super().save_model(request, obj, form, change)
        
        # Add communication log entry
        if change:
            obj.add_communication_log(
                f'Override updated by {request.user.username}',
                request.user
            )
        
        # Log admin override operations
        if not change:
            # New override creation
            AdminAuditService.log_system_management_operation(
                operation='admin_override_create',
                user=request.user,
                request=request,
                details={
                    'override_id': str(obj.id),
                    'override_type': obj.override_type,
                    'risk_level': obj.risk_level,
                    'is_emergency': obj.is_emergency,
                    'target_object_type': obj.content_type.model if obj.content_type else None,
                    'target_object_id': obj.object_id
                }
            )
        elif old_status != obj.status:
            # Status change
            AdminAuditService.log_admin_override(
                user=request.user,
                override_type=f'status_change_{obj.override_type}',
                target_object=obj,
                justification=f'Status changed from {old_status} to {obj.status}',
                original_value=old_status,
                new_value=obj.status,
                request=request,
                details={
                    'status_change': True,
                    'old_status': old_status,
                    'new_status': obj.status,
                    'changed_fields': list(form.changed_data)
                }
            )
        elif form.changed_data:
            # Other changes
            AdminAuditService.log_system_management_operation(
                operation='admin_override_update',
                user=request.user,
                request=request,
                details={
                    'override_id': str(obj.id),
                    'changed_fields': list(form.changed_data),
                    'override_type': obj.override_type,
                    'current_status': obj.status
                }
            )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'requested_by', 'approved_by', 'reviewed_by', 'status_changed_by'
        )
    
    def has_delete_permission(self, request, obj=None):
        """Restrict deletion of active or completed overrides"""
        if obj and obj.status in ['ACTIVE', 'COMPLETED']:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for AuditLog model with comprehensive filtering, search, and analytics.
    """
    
    # List display configuration
    list_display = (
        'timestamp', 'action_type_display', 'user_display', 'object_display',
        'ip_address', 'duration_display', 'status_display', 'critical_flag'
    )
    
    # Advanced filtering
    list_filter = (
        'action_type', 'content_type', 'response_status',
        ('timestamp', admin.DateFieldListFilter),
        ('user', admin.RelatedOnlyFieldListFilter),
        'tags'
    )
    
    # Search fields
    search_fields = (
        'user__username', 'user__email', 'object_representation',
        'ip_address', 'user_agent', 'action_description', 'tags'
    )
    
    # Ordering
    ordering = ('-timestamp',)
    
    # Items per page
    list_per_page = 50
    
    # Fieldsets for detailed view
    fieldsets = (
        (_('Action Details'), {
            'fields': ('action_type', 'action_description', 'timestamp'),
            'classes': ('wide',)
        }),
        (_('User & Session'), {
            'fields': ('user', 'session_key', 'ip_address', 'user_agent'),
            'classes': ('wide',)
        }),
        (_('Target Object'), {
            'fields': ('content_type', 'object_id', 'object_representation'),
            'classes': ('collapse',)
        }),
        (_('Request Information'), {
            'fields': ('request_method', 'request_path', 'request_data', 'response_status'),
            'classes': ('collapse',)
        }),
        (_('Data Changes'), {
            'fields': ('old_values', 'new_values', 'changes'),
            'classes': ('collapse',)
        }),
        (_('Performance & Metadata'), {
            'fields': ('duration_ms', 'tags', 'metadata'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields (all fields since audit logs shouldn't be modified)
    readonly_fields = (
        'action_type', 'action_description', 'user', 'session_key',
        'ip_address', 'user_agent', 'content_type', 'object_id',
        'object_representation', 'changes', 'old_values', 'new_values',
        'request_method', 'request_path', 'request_data', 'response_status',
        'timestamp', 'duration_ms', 'tags', 'metadata'
    )
    
    # Raw ID fields
    raw_id_fields = ('user', 'content_type')
    
    # Custom methods for list display
    def action_type_display(self, obj):
        """Display action type with color coding"""
        action_colors = {
            'CREATE': 'green',
            'UPDATE': 'blue',
            'DELETE': 'red',
            'VIEW': 'gray',
            'LOGIN': 'green',
            'LOGOUT': 'orange',
            'BULK_OPERATION': 'purple',
            'ADMIN_OVERRIDE': 'red',
            'DATA_EXPORT': 'orange'
        }
        
        action_icons = {
            'CREATE': '➕',
            'UPDATE': '✏️',
            'DELETE': '🗑️',
            'VIEW': '👁️',
            'LOGIN': '🔐',
            'LOGOUT': '🚪',
            'BULK_OPERATION': '📦',
            'ADMIN_OVERRIDE': '⚠️',
            'DATA_EXPORT': '📤'
        }
        
        color = action_colors.get(obj.action_type, 'black')
        icon = action_icons.get(obj.action_type, '❓')
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.action_type
        )
    action_type_display.short_description = _('Action')
    action_type_display.admin_order_field = 'action_type'
    
    def user_display(self, obj):
        """Display user with additional info"""
        if not obj.user:
            return format_html('<span style="color: gray;">Anonymous</span>')
        
        user_info = obj.user.get_full_name() or obj.user.username
        if obj.user.is_superuser:
            return format_html(
                '<span style="color: red; font-weight: bold;">👑 {}</span>',
                user_info
            )
        elif obj.user.is_staff:
            return format_html(
                '<span style="color: blue;">🛡️ {}</span>',
                user_info
            )
        else:
            return format_html('<span>{}</span>', user_info)
    user_display.short_description = _('User')
    user_display.admin_order_field = 'user__username'
    
    def object_display(self, obj):
        """Display target object with type"""
        if obj.content_type and obj.object_id:
            return format_html(
                '<span style="color: blue;">{}: {}</span>',
                obj.content_type.model.title(),
                obj.object_representation[:50] + '...' if len(obj.object_representation) > 50 else obj.object_representation
            )
        return format_html('<span style="color: gray;">—</span>')
    object_display.short_description = _('Target Object')
    
    def duration_display(self, obj):
        """Display request duration"""
        if obj.duration_ms is None:
            return format_html('<span style="color: gray;">—</span>')
        
        if obj.duration_ms < 100:
            color = 'green'
        elif obj.duration_ms < 1000:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{}ms</span>',
            color, obj.duration_ms
        )
    duration_display.short_description = _('Duration')
    duration_display.admin_order_field = 'duration_ms'
    
    def status_display(self, obj):
        """Display response status"""
        if obj.response_status is None:
            return format_html('<span style="color: gray;">—</span>')
        
        if obj.response_status < 300:
            color, icon = 'green', '✅'
        elif obj.response_status < 400:
            color, icon = 'blue', '↩️'
        elif obj.response_status < 500:
            color, icon = 'orange', '⚠️'
        else:
            color, icon = 'red', '❌'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.response_status
        )
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'response_status'
    
    def critical_flag(self, obj):
        """Display critical operation flag"""
        if obj.metadata.get('critical_operation'):
            return format_html('<span style="color: red; font-weight: bold;">🚨 CRITICAL</span>')
        elif obj.metadata.get('security_event'):
            return format_html('<span style="color: orange;">🔒 SECURITY</span>')
        elif obj.metadata.get('bulk_operation'):
            return format_html('<span style="color: blue;">📦 BULK</span>')
        return format_html('<span style="color: gray;">—</span>')
    critical_flag.short_description = _('Flags')
    
    # Bulk actions
    actions = [
        'export_audit_logs', 'generate_security_report', 'mark_reviewed'
    ]
    
    def export_audit_logs(self, request, queryset):
        """Export selected audit logs to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Timestamp', 'Action Type', 'User', 'Description', 'IP Address',
            'Target Object', 'Request Method', 'Request Path', 'Response Status',
            'Duration (ms)', 'Critical Operation', 'Tags'
        ])
        
        record_count = 0
        for log in queryset:
            writer.writerow([
                log.timestamp.isoformat(),
                log.action_type,
                log.user.username if log.user else 'Anonymous',
                log.action_description,
                log.ip_address,
                f"{log.content_type.model}: {log.object_representation}" if log.content_type else '',
                log.request_method,
                log.request_path,
                log.response_status or '',
                log.duration_ms or '',
                'Yes' if log.metadata.get('critical_operation') else 'No',
                ', '.join(log.tags) if log.tags else ''
            ])
            record_count += 1
        
        # Log the export operation
        AdminAuditService.log_data_export(
            user=request.user,
            export_type='audit_logs',
            model_class=AuditLog,
            record_count=record_count,
            export_format='csv',
            request=request,
            details={
                'filename': f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                'export_method': 'admin_bulk_action'
            }
        )
        
        return response
    export_audit_logs.short_description = _('Export selected audit logs to CSV')
    
    def generate_security_report(self, request, queryset):
        """Generate security report for selected logs"""
        security_logs = queryset.filter(
            models.Q(metadata__category='SECURITY_OPERATIONS') |
            models.Q(metadata__critical_operation=True) |
            models.Q(response_status__gte=400)
        )
        
        if not security_logs.exists():
            messages.warning(request, 'No security-related logs found in selection.')
            return
        
        # Generate summary
        summary = {
            'total_logs': security_logs.count(),
            'failed_operations': security_logs.filter(response_status__gte=400).count(),
            'critical_operations': security_logs.filter(metadata__critical_operation=True).count(),
            'unique_users': security_logs.values('user').distinct().count(),
            'unique_ips': security_logs.values('ip_address').distinct().count(),
        }
        
        messages.success(
            request,
            f'Security Report: {summary["total_logs"]} logs analyzed. '
            f'{summary["failed_operations"]} failed operations, '
            f'{summary["critical_operations"]} critical operations, '
            f'{summary["unique_users"]} unique users, '
            f'{summary["unique_ips"]} unique IP addresses.'
        )
        
        # Log the security report generation
        AdminAuditService.log_security_operation(
            operation='security_report_generation',
            user=request.user,
            request=request,
            details={
                'report_summary': summary,
                'logs_analyzed': security_logs.count()
            }
        )
    generate_security_report.short_description = _('Generate security report')
    
    def mark_reviewed(self, request, queryset):
        """Mark selected logs as reviewed"""
        count = queryset.update(
            metadata=models.F('metadata') | {'reviewed': True, 'reviewed_by': request.user.username, 'reviewed_at': timezone.now().isoformat()}
        )
        
        messages.success(request, f'Marked {count} audit log(s) as reviewed.')
        
        # Log the review action
        AdminAuditService.log_system_management_operation(
            operation='audit_logs_reviewed',
            user=request.user,
            request=request,
            details={
                'reviewed_count': count,
                'review_method': 'bulk_admin_action'
            }
        )
    mark_reviewed.short_description = _('Mark as reviewed')
    
    # Disable add/change permissions for audit logs
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only allow superusers to delete audit logs (for maintenance)
        return request.user.is_superuser


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for ContentItem with real-time content management capabilities.
    """
    
    # List display configuration
    list_display = (
        'title', 'content_type', 'status_display', 'priority_display',
        'author', 'publish_date', 'view_count', 'is_featured', 'is_pinned',
        'created_at'
    )
    
    # Advanced filtering
    list_filter = (
        'content_type', 'status', 'priority', 'is_featured', 'is_pinned',
        ('publish_date', admin.DateFieldListFilter),
        ('expire_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        'author', 'target_audience', 'tags'
    )
    
    # Search fields
    search_fields = (
        'title', 'slug', 'summary', 'content', 'tags',
        'meta_description', 'author__username'
    )
    
    # Ordering
    ordering = ('-is_pinned', '-priority', '-publish_date')
    
    # Items per page
    list_per_page = 25
    
    # Fieldsets for organized form layout
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'slug', 'content_type', 'summary'),
            'classes': ('wide',)
        }),
        (_('Content'), {
            'fields': ('content', 'featured_image'),
            'classes': ('wide',)
        }),
        (_('Publishing'), {
            'fields': (
                'status', 'priority', 'is_featured', 'is_pinned',
                'publish_date', 'expire_date'
            ),
            'classes': ('wide',)
        }),
        (_('Targeting & Relations'), {
            'fields': ('target_audience', 'related_events', 'related_venues'),
            'classes': ('collapse',)
        }),
        (_('SEO & Metadata'), {
            'fields': ('tags', 'meta_description'),
            'classes': ('collapse',)
        }),
        (_('Management'), {
            'fields': ('author', 'editor'),
            'classes': ('collapse',)
        }),
        (_('Statistics'), {
            'fields': ('view_count', 'like_count'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'published_at', 'view_count', 'like_count'
    )
    
    # Prepopulated fields
    prepopulated_fields = {'slug': ('title',)}
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ('related_events', 'related_venues')
    
    # Raw ID fields
    raw_id_fields = ('author', 'editor')
    
    # Custom methods for list display
    def status_display(self, obj):
        """Display status with color coding"""
        status_colors = {
            'DRAFT': 'gray',
            'PUBLISHED': 'green',
            'ARCHIVED': 'orange',
            'SCHEDULED': 'blue'
        }
        
        color = status_colors.get(obj.status, 'black')
        icon = '📝' if obj.status == 'DRAFT' else '✅' if obj.status == 'PUBLISHED' else '📅' if obj.status == 'SCHEDULED' else '📦'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'status'
    
    def priority_display(self, obj):
        """Display priority with visual indicators"""
        priority_colors = {
            'LOW': 'gray',
            'NORMAL': 'blue',
            'HIGH': 'orange',
            'URGENT': 'red'
        }
        
        priority_icons = {
            'LOW': '⬇️',
            'NORMAL': '➡️',
            'HIGH': '⬆️',
            'URGENT': '🚨'
        }
        
        color = priority_colors.get(obj.priority, 'black')
        icon = priority_icons.get(obj.priority, '➡️')
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_priority_display()
        )
    priority_display.short_description = _('Priority')
    priority_display.admin_order_field = 'priority'
    
    # Bulk actions
    actions = [
        'publish_content', 'unpublish_content', 'archive_content',
        'mark_featured', 'unmark_featured', 'pin_content', 'unpin_content',
        'duplicate_content', 'export_content_data'
    ]
    
    def publish_content(self, request, queryset):
        """Publish selected content items"""
        updated = queryset.filter(status__in=['DRAFT', 'SCHEDULED']).update(
            status='PUBLISHED',
            published_at=timezone.now()
        )
        
        self.message_user(
            request,
            f'{updated} content item(s) were published.',
            messages.SUCCESS
        )
    publish_content.short_description = _('Publish selected content')
    
    def unpublish_content(self, request, queryset):
        """Unpublish selected content items"""
        updated = queryset.filter(status='PUBLISHED').update(status='DRAFT')
        
        self.message_user(
            request,
            f'{updated} content item(s) were unpublished.',
            messages.SUCCESS
        )
    unpublish_content.short_description = _('Unpublish selected content')
    
    def archive_content(self, request, queryset):
        """Archive selected content items"""
        updated = queryset.exclude(status='ARCHIVED').update(status='ARCHIVED')
        
        self.message_user(
            request,
            f'{updated} content item(s) were archived.',
            messages.SUCCESS
        )
    archive_content.short_description = _('Archive selected content')
    
    def mark_featured(self, request, queryset):
        """Mark selected content as featured"""
        updated = queryset.filter(is_featured=False).update(is_featured=True)
        
        self.message_user(
            request,
            f'{updated} content item(s) marked as featured.',
            messages.SUCCESS
        )
    mark_featured.short_description = _('Mark as featured')
    
    def unmark_featured(self, request, queryset):
        """Unmark selected content as featured"""
        updated = queryset.filter(is_featured=True).update(is_featured=False)
        
        self.message_user(
            request,
            f'{updated} content item(s) unmarked as featured.',
            messages.SUCCESS
        )
    unmark_featured.short_description = _('Unmark as featured')
    
    def pin_content(self, request, queryset):
        """Pin selected content to top"""
        updated = queryset.filter(is_pinned=False).update(is_pinned=True)
        
        self.message_user(
            request,
            f'{updated} content item(s) pinned to top.',
            messages.SUCCESS
        )
    pin_content.short_description = _('Pin to top')
    
    def unpin_content(self, request, queryset):
        """Unpin selected content"""
        updated = queryset.filter(is_pinned=True).update(is_pinned=False)
        
        self.message_user(
            request,
            f'{updated} content item(s) unpinned.',
            messages.SUCCESS
        )
    unpin_content.short_description = _('Unpin content')
    
    def duplicate_content(self, request, queryset):
        """Duplicate selected content items"""
        duplicated = 0
        for item in queryset:
            item.pk = None
            item.title = f"{item.title} (Copy)"
            item.slug = f"{item.slug}-copy"
            item.status = 'DRAFT'
            item.published_at = None
            item.save()
            duplicated += 1
        
        self.message_user(
            request,
            f'{duplicated} content item(s) duplicated.',
            messages.SUCCESS
        )
    duplicate_content.short_description = _('Duplicate content')
    
    def export_content_data(self, request, queryset):
        """Export content data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="content_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Title', 'Type', 'Status', 'Priority', 'Author', 'Publish Date',
            'View Count', 'Featured', 'Pinned', 'Created'
        ])
        
        for item in queryset:
            writer.writerow([
                item.title,
                item.get_content_type_display(),
                item.get_status_display(),
                item.get_priority_display(),
                item.author.get_full_name() if item.author else '',
                item.publish_date,
                item.view_count,
                'Yes' if item.is_featured else 'No',
                'Yes' if item.is_pinned else 'No',
                item.created_at
            ])
        
        return response
    export_content_data.short_description = _('Export content data (CSV)')
    
    # Custom save logic
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new content
            obj.author = request.user
        else:  # Editing existing content
            obj.editor = request.user
        
        super().save_model(request, obj, form, change)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for FAQ management with categorization and analytics.
    """
    
    # List display configuration
    list_display = (
        'question_preview', 'category', 'target_audience_display',
        'helpfulness_display', 'view_count', 'is_active', 'order',
        'created_at'
    )
    
    # Filtering
    list_filter = (
        'category', 'is_active', 'target_audience',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter)
    )
    
    # Search fields
    search_fields = ('question', 'answer', 'tags')
    
    # Ordering
    ordering = ('category', 'order', 'question')
    
    # Fieldsets
    fieldsets = (
        (_('Question & Answer'), {
            'fields': ('question', 'answer'),
            'classes': ('wide',)
        }),
        (_('Categorization'), {
            'fields': ('category', 'tags', 'target_audience'),
            'classes': ('wide',)
        }),
        (_('Display Settings'), {
            'fields': ('is_active', 'order'),
            'classes': ('collapse',)
        }),
        (_('Analytics'), {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count'),
            'classes': ('collapse',)
        }),
        (_('Management'), {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'view_count', 'helpful_count', 'not_helpful_count',
        'created_at', 'updated_at'
    )
    
    # Raw ID fields
    raw_id_fields = ('created_by', 'updated_by')
    
    # Custom methods for list display
    def question_preview(self, obj):
        """Display question preview"""
        return obj.question[:80] + "..." if len(obj.question) > 80 else obj.question
    question_preview.short_description = _('Question')
    
    def target_audience_display(self, obj):
        """Display target audience"""
        if obj.target_audience:
            return ", ".join(obj.target_audience[:3])
        return "All"
    target_audience_display.short_description = _('Audience')
    
    def helpfulness_display(self, obj):
        """Display helpfulness ratio"""
        ratio = obj.get_helpfulness_ratio()
        total_votes = obj.helpful_count + obj.not_helpful_count
        
        if total_votes == 0:
            return format_html('<span style="color: gray;">No votes</span>')
        
        color = 'green' if ratio >= 70 else 'orange' if ratio >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{}% ({} votes)</span>',
            color, round(ratio, 1), total_votes
        )
    helpfulness_display.short_description = _('Helpfulness')
    
    # Bulk actions
    actions = [
        'activate_faqs', 'deactivate_faqs', 'reset_analytics',
        'export_faq_data'
    ]
    
    def activate_faqs(self, request, queryset):
        """Activate selected FAQs"""
        updated = queryset.filter(is_active=False).update(is_active=True)
        
        self.message_user(
            request,
            f'{updated} FAQ(s) were activated.',
            messages.SUCCESS
        )
    activate_faqs.short_description = _('Activate selected FAQs')
    
    def deactivate_faqs(self, request, queryset):
        """Deactivate selected FAQs"""
        updated = queryset.filter(is_active=True).update(is_active=False)
        
        self.message_user(
            request,
            f'{updated} FAQ(s) were deactivated.',
            messages.SUCCESS
        )
    deactivate_faqs.short_description = _('Deactivate selected FAQs')
    
    def reset_analytics(self, request, queryset):
        """Reset analytics for selected FAQs"""
        updated = queryset.update(
            view_count=0,
            helpful_count=0,
            not_helpful_count=0
        )
        
        self.message_user(
            request,
            f'Analytics reset for {updated} FAQ(s).',
            messages.SUCCESS
        )
    reset_analytics.short_description = _('Reset analytics')
    
    def export_faq_data(self, request, queryset):
        """Export FAQ data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="faqs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Question', 'Answer', 'Category', 'Active', 'View Count',
            'Helpful Count', 'Not Helpful Count', 'Helpfulness %', 'Created'
        ])
        
        for faq in queryset:
            writer.writerow([
                faq.question,
                faq.answer,
                faq.get_category_display(),
                'Yes' if faq.is_active else 'No',
                faq.view_count,
                faq.helpful_count,
                faq.not_helpful_count,
                round(faq.get_helpfulness_ratio(), 1),
                faq.created_at
            ])
        
        return response
    export_faq_data.short_description = _('Export FAQ data (CSV)')
    
    # Custom save logic
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new FAQ
            obj.created_by = request.user
        else:  # Editing existing FAQ
            obj.updated_by = request.user
        
        super().save_model(request, obj, form, change)


@admin.register(VenueInformation)
class VenueInformationAdmin(admin.ModelAdmin):
    list_display = ['venue', 'is_published', 'created_at', 'updated_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['venue__name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Venue', {
            'fields': ('venue',)
        }),
        ('Content', {
            'fields': ('description', 'facilities', 'accessibility_info', 'contact_info')
        }),
        ('Publishing', {
            'fields': ('is_published',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    """
    Admin interface for Theme management with color preview and CSS generation
    """
    form = ThemeForm
    
    list_display = [
        'name', 'theme_type', 'is_active', 'is_default', 'is_dark_mode', 
        'accessibility_compliant', 'created_at', 'color_preview'
    ]
    list_filter = [
        'theme_type', 'is_active', 'is_default', 'is_dark_mode', 
        'accessibility_compliant', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'css_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'theme_type', 'description'),
            'description': 'Basic theme identification and purpose'
        }),
        ('🎨 Primary Colors', {
            'fields': ('primary_color', 'secondary_color', 'accent_color'),
            'classes': ('wide',),
            'description': 'Main brand colors that define the theme identity. Primary is used for headers and main actions, secondary for supporting elements, and accent for highlights.'
        }),
        ('🖼️ Background Colors', {
            'fields': ('background_color', 'surface_color'),
            'classes': ('wide',),
            'description': 'Background colors for different interface areas. Background is the main page color, surface is for cards and panels.'
        }),
        ('📝 Text Colors', {
            'fields': ('text_primary', 'text_secondary', 'text_on_primary'),
            'classes': ('wide',),
            'description': 'Text colors for optimal readability. Ensure good contrast ratios for accessibility compliance.'
        }),
        ('🚦 Status Colors', {
            'fields': ('success_color', 'warning_color', 'error_color', 'info_color'),
            'classes': ('wide',),
            'description': 'Colors for system messages and status indicators. Follow standard conventions: green for success, yellow for warnings, red for errors, blue for information.'
        }),
        ('✍️ Typography & Readability', {
            'fields': ('font_family_primary', 'font_family_secondary', 'font_size_base'),
            'classes': ('collapse',),
            'description': 'Font settings that affect readability. Use web-safe fonts and appropriate sizes for accessibility.'
        }),
        ('📐 Layout & Spacing', {
            'fields': ('border_radius', 'box_shadow'),
            'classes': ('collapse',),
            'description': 'Visual styling for interface elements. Border radius affects the modern look, box shadow adds depth.'
        }),
        ('🏢 Branding Assets', {
            'fields': ('logo_url', 'favicon_url'),
            'classes': ('collapse',),
            'description': 'Brand assets and logos. Use high-quality images optimized for web.'
        }),
        ('🎛️ Advanced Customization', {
            'fields': ('custom_css',),
            'classes': ('collapse',),
            'description': 'Custom CSS for advanced styling. Use with caution and test thoroughly.'
        }),
        ('⚙️ Theme Settings', {
            'fields': ('is_active', 'is_default', 'is_dark_mode', 'accessibility_compliant'),
            'description': 'Theme activation and accessibility settings. Only one theme can be default per type.'
        }),
        ('📊 Management Info', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('👀 Generated CSS Preview', {
            'fields': ('css_preview',),
            'classes': ('collapse',),
            'description': 'Preview of the CSS that will be generated from this theme configuration.'
        }),
    )
    
    actions = ['activate_theme', 'deactivate_theme', 'set_as_default', 'export_css']
    
    def color_preview(self, obj):
        """Display enhanced color swatches for the theme"""
        return format_html(
            '<div class="theme-list-color-preview" style="display: flex; gap: 4px; align-items: center;">'
            '<div style="width: 24px; height: 24px; background: {}; border: 2px solid #fff; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" title="Primary: {}"></div>'
            '<div style="width: 24px; height: 24px; background: {}; border: 2px solid #fff; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" title="Secondary: {}"></div>'
            '<div style="width: 24px; height: 24px; background: {}; border: 2px solid #fff; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" title="Accent: {}"></div>'
            '<div style="width: 16px; height: 16px; background: {}; border: 1px solid #ddd; border-radius: 3px; margin-left: 4px;" title="Background: {}"></div>'
            '<div style="width: 16px; height: 16px; background: {}; border: 1px solid #ddd; border-radius: 3px;" title="Text: {}"></div>'
            '</div>',
            obj.primary_color, obj.primary_color,
            obj.secondary_color, obj.secondary_color,
            obj.accent_color, obj.accent_color,
            obj.background_color, obj.background_color,
            obj.text_primary, obj.text_primary
        )
    color_preview.short_description = 'Color Palette'
    
    def css_preview(self, obj):
        """Display generated CSS for preview"""
        css = obj.generate_css()
        return format_html(
            '<textarea readonly style="width: 100%; height: 200px; font-family: monospace; font-size: 12px;">{}</textarea>',
            css
        )
    css_preview.short_description = 'Generated CSS'
    
    def activate_theme(self, request, queryset):
        """Activate selected themes"""
        updated = 0
        for theme in queryset:
            if not theme.is_active:
                theme.is_active = True
                theme.save()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully activated {updated} theme(s).',
            messages.SUCCESS
        )
    activate_theme.short_description = 'Activate selected themes'
    
    def deactivate_theme(self, request, queryset):
        """Deactivate selected themes"""
        updated = 0
        for theme in queryset:
            if theme.is_active:
                theme.is_active = False
                theme.save()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully deactivated {updated} theme(s).',
            messages.SUCCESS
        )
    deactivate_theme.short_description = 'Deactivate selected themes'
    
    def set_as_default(self, request, queryset):
        """Set selected themes as default for their type"""
        updated = 0
        for theme in queryset:
            if not theme.is_default:
                theme.is_default = True
                theme.save()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully set {updated} theme(s) as default.',
            messages.SUCCESS
        )
    set_as_default.short_description = 'Set as default theme'
    
    def export_css(self, request, queryset):
        """Export CSS for selected themes"""
        if queryset.count() == 1:
            theme = queryset.first()
            css_content = theme.generate_css()
            
            response = HttpResponse(css_content, content_type='text/css')
            response['Content-Disposition'] = f'attachment; filename="{theme.name.lower().replace(" ", "_")}_theme.css"'
            return response
        else:
            self.message_user(
                request,
                'Please select exactly one theme to export CSS.',
                messages.WARNING
            )
    export_css.short_description = 'Export CSS file'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new themes"""
        if not change:  # Creating new theme
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/theme-admin.css',)
        }
        js = ('admin/js/theme-admin.js',)


@admin.register(UserThemePreference)
class UserThemePreferenceAdmin(admin.ModelAdmin):
    """
    Admin interface for User Theme Preferences
    """
    list_display = [
        'user', 'admin_theme', 'mobile_theme', 'use_dark_mode', 
        'use_high_contrast', 'font_size_preference', 'updated_at'
    ]
    list_filter = [
        'use_dark_mode', 'use_high_contrast', 'font_size_preference',
        'admin_theme__theme_type', 'mobile_theme__theme_type'
    ]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Theme Preferences', {
            'fields': ('admin_theme', 'mobile_theme')
        }),
        ('Accessibility', {
            'fields': ('use_dark_mode', 'use_high_contrast', 'font_size_preference')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['reset_to_defaults', 'enable_dark_mode', 'enable_high_contrast']
    
    def reset_to_defaults(self, request, queryset):
        """Reset selected preferences to system defaults"""
        updated = 0
        for preference in queryset:
            preference.admin_theme = None
            preference.mobile_theme = None
            preference.use_dark_mode = False
            preference.use_high_contrast = False
            preference.font_size_preference = 'NORMAL'
            preference.save()
            updated += 1
        
        self.message_user(
            request,
            f'Successfully reset {updated} user preference(s) to defaults.',
            messages.SUCCESS
        )
    reset_to_defaults.short_description = 'Reset to default preferences'
    
    def enable_dark_mode(self, request, queryset):
        """Enable dark mode for selected users"""
        updated = queryset.update(use_dark_mode=True)
        self.message_user(
            request,
            f'Successfully enabled dark mode for {updated} user(s).',
            messages.SUCCESS
        )
    enable_dark_mode.short_description = 'Enable dark mode'
    
    def enable_high_contrast(self, request, queryset):
        """Enable high contrast for selected users"""
        updated = queryset.update(use_high_contrast=True)
        self.message_user(
            request,
            f'Successfully enabled high contrast for {updated} user(s).',
            messages.SUCCESS
        )
    enable_high_contrast.short_description = 'Enable high contrast' 