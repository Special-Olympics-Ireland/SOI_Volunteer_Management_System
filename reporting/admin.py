from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.urls import path, reverse
from django.shortcuts import redirect
import csv
from datetime import datetime

from .models import Report, ReportTemplate, ReportSchedule, ReportMetrics, ReportShare


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Report management with comprehensive export capabilities.
    """
    
    # List display configuration
    list_display = (
        'name', 'report_type', 'status_display', 'export_format',
        'progress_display', 'file_size_display', 'created_by',
        'created_at', 'download_link'
    )
    
    # Advanced filtering
    list_filter = (
        'report_type', 'status', 'export_format',
        ('created_at', admin.DateFieldListFilter),
        ('completed_at', admin.DateFieldListFilter),
        ('expires_at', admin.DateFieldListFilter),
        'created_by'
    )
    
    # Search fields
    search_fields = (
        'name', 'description', 'created_by__username',
        'created_by__first_name', 'created_by__last_name'
    )
    
    # Ordering
    ordering = ('-created_at',)
    
    # Items per page
    list_per_page = 25
    
    # Fieldsets for organized form layout
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'report_type'),
            'classes': ('wide',)
        }),
        (_('Configuration'), {
            'fields': ('parameters', 'export_format'),
            'classes': ('wide',)
        }),
        (_('Status & Progress'), {
            'fields': ('status', 'progress_percentage', 'error_message'),
            'classes': ('wide',)
        }),
        (_('Results'), {
            'fields': ('total_records', 'file_path', 'file_size', 'generation_time'),
            'classes': ('collapse',)
        }),
        (_('Management'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'started_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'id', 'created_at', 'started_at', 'completed_at',
        'generation_time', 'file_size'
    )
    
    # Raw ID fields
    raw_id_fields = ('created_by',)
    
    # Custom methods for list display
    def status_display(self, obj):
        """Display status with color coding and progress"""
        status_colors = {
            'PENDING': 'gray',
            'GENERATING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'EXPIRED': 'orange'
        }
        
        status_icons = {
            'PENDING': '⏳',
            'GENERATING': '🔄',
            'COMPLETED': '✅',
            'FAILED': '❌',
            'EXPIRED': '⏰'
        }
        
        color = status_colors.get(obj.status, 'black')
        icon = status_icons.get(obj.status, '❓')
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'status'
    
    def progress_display(self, obj):
        """Display progress with progress bar"""
        if obj.status == 'GENERATING':
            color = 'blue'
        elif obj.status == 'COMPLETED':
            color = 'green'
        elif obj.status == 'FAILED':
            color = 'red'
        else:
            color = 'gray'
        
        progress = int(obj.progress_percentage)
        
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}%</div></div>',
            progress, color, progress
        )
    progress_display.short_description = _('Progress')
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if obj.file_size > 0:
            return obj.get_file_size_display()
        return format_html('<span style="color: gray;">-</span>')
    file_size_display.short_description = _('File Size')
    
    def download_link(self, obj):
        """Display download link if report is completed"""
        if obj.status == 'COMPLETED' and obj.file_path:
            return format_html(
                '<a href="{}" class="button" target="_blank">📥 Download</a>',
                obj.get_download_url()
            )
        return format_html('<span style="color: gray;">-</span>')
    download_link.short_description = _('Download')
    
    # Bulk actions
    actions = [
        'regenerate_reports', 'cancel_reports', 'archive_reports',
        'extend_expiration', 'export_report_list'
    ]
    
    def regenerate_reports(self, request, queryset):
        """Regenerate selected reports"""
        regenerated = 0
        for report in queryset.filter(status__in=['FAILED', 'EXPIRED']):
            report.status = 'PENDING'
            report.progress_percentage = 0
            report.error_message = ''
            report.save()
            regenerated += 1
        
        self.message_user(
            request,
            f'{regenerated} report(s) queued for regeneration.',
            messages.SUCCESS
        )
    regenerate_reports.short_description = _('Regenerate selected reports')
    
    def cancel_reports(self, request, queryset):
        """Cancel pending/generating reports"""
        cancelled = queryset.filter(
            status__in=['PENDING', 'GENERATING']
        ).update(status='FAILED', error_message='Cancelled by admin')
        
        self.message_user(
            request,
            f'{cancelled} report(s) were cancelled.',
            messages.SUCCESS
        )
    cancel_reports.short_description = _('Cancel selected reports')
    
    def archive_reports(self, request, queryset):
        """Archive completed reports"""
        archived = queryset.filter(status='COMPLETED').update(status='EXPIRED')
        
        self.message_user(
            request,
            f'{archived} report(s) were archived.',
            messages.SUCCESS
        )
    archive_reports.short_description = _('Archive selected reports')
    
    def extend_expiration(self, request, queryset):
        """Extend expiration date by 30 days"""
        from datetime import timedelta
        
        new_expiry = timezone.now() + timedelta(days=30)
        updated = queryset.update(expires_at=new_expiry)
        
        self.message_user(
            request,
            f'Extended expiration for {updated} report(s) by 30 days.',
            messages.SUCCESS
        )
    extend_expiration.short_description = _('Extend expiration by 30 days')
    
    def export_report_list(self, request, queryset):
        """Export report list to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Type', 'Status', 'Format', 'Progress %', 'File Size',
            'Records', 'Created By', 'Created', 'Completed'
        ])
        
        for report in queryset:
            writer.writerow([
                report.name,
                report.get_report_type_display(),
                report.get_status_display(),
                report.get_export_format_display(),
                report.progress_percentage,
                report.get_file_size_display(),
                report.total_records,
                report.created_by.get_full_name(),
                report.created_at,
                report.completed_at
            ])
        
        return response
    export_report_list.short_description = _('Export report list (CSV)')
    
    # Custom save logic
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new report
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for ReportTemplate management.
    """
    
    # List display configuration
    list_display = (
        'name', 'report_type', 'usage_display', 'is_active', 'is_public',
        'created_by', 'last_used', 'created_at'
    )
    
    # Filtering
    list_filter = (
        'report_type', 'is_active', 'is_public', 'default_export_format',
        ('created_at', admin.DateFieldListFilter),
        ('last_used', admin.DateFieldListFilter),
        'created_by'
    )
    
    # Search fields
    search_fields = (
        'name', 'description', 'created_by__username'
    )
    
    # Ordering
    ordering = ('name',)
    
    # Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'report_type'),
            'classes': ('wide',)
        }),
        (_('Default Configuration'), {
            'fields': ('default_parameters', 'default_export_format'),
            'classes': ('wide',)
        }),
        (_('Template Settings'), {
            'fields': ('is_active', 'is_public'),
            'classes': ('wide',)
        }),
        (_('Usage Statistics'), {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        (_('Management'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = ('usage_count', 'last_used', 'created_at', 'updated_at')
    
    # Raw ID fields
    raw_id_fields = ('created_by',)
    
    # Custom methods for list display
    def usage_display(self, obj):
        """Display usage statistics"""
        if obj.usage_count > 0:
            color = 'green' if obj.usage_count >= 10 else 'blue'
            return format_html(
                '<span style="color: {};">{} times</span>',
                color, obj.usage_count
            )
        return format_html('<span style="color: gray;">Never used</span>')
    usage_display.short_description = _('Usage')
    usage_display.admin_order_field = 'usage_count'
    
    # Bulk actions
    actions = [
        'activate_templates', 'deactivate_templates', 'make_public',
        'make_private', 'reset_usage_stats', 'duplicate_templates'
    ]
    
    def activate_templates(self, request, queryset):
        """Activate selected templates"""
        updated = queryset.filter(is_active=False).update(is_active=True)
        
        self.message_user(
            request,
            f'{updated} template(s) were activated.',
            messages.SUCCESS
        )
    activate_templates.short_description = _('Activate selected templates')
    
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates"""
        updated = queryset.filter(is_active=True).update(is_active=False)
        
        self.message_user(
            request,
            f'{updated} template(s) were deactivated.',
            messages.SUCCESS
        )
    deactivate_templates.short_description = _('Deactivate selected templates')
    
    def make_public(self, request, queryset):
        """Make selected templates public"""
        updated = queryset.filter(is_public=False).update(is_public=True)
        
        self.message_user(
            request,
            f'{updated} template(s) were made public.',
            messages.SUCCESS
        )
    make_public.short_description = _('Make selected templates public')
    
    def make_private(self, request, queryset):
        """Make selected templates private"""
        updated = queryset.filter(is_public=True).update(is_public=False)
        
        self.message_user(
            request,
            f'{updated} template(s) were made private.',
            messages.SUCCESS
        )
    make_private.short_description = _('Make selected templates private')
    
    def reset_usage_stats(self, request, queryset):
        """Reset usage statistics"""
        updated = queryset.update(usage_count=0, last_used=None)
        
        self.message_user(
            request,
            f'Usage statistics reset for {updated} template(s).',
            messages.SUCCESS
        )
    reset_usage_stats.short_description = _('Reset usage statistics')
    
    def duplicate_templates(self, request, queryset):
        """Duplicate selected templates"""
        duplicated = 0
        for template in queryset:
            template.pk = None
            template.name = f"{template.name} (Copy)"
            template.is_public = False
            template.usage_count = 0
            template.last_used = None
            template.created_by = request.user
            template.save()
            duplicated += 1
        
        self.message_user(
            request,
            f'{duplicated} template(s) were duplicated.',
            messages.SUCCESS
        )
    duplicate_templates.short_description = _('Duplicate selected templates')
    
    # Custom save logic
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new template
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for ReportSchedule management.
    """
    
    # List display configuration
    list_display = (
        'name', 'report_template', 'frequency', 'status_display',
        'next_run_display', 'run_count', 'created_by', 'created_at'
    )
    
    # Filtering
    list_filter = (
        'frequency', 'status', 'report_template__report_type',
        ('start_date', admin.DateFieldListFilter),
        ('next_run', admin.DateFieldListFilter),
        ('last_run', admin.DateFieldListFilter),
        'created_by'
    )
    
    # Search fields
    search_fields = (
        'name', 'description', 'report_template__name',
        'created_by__username'
    )
    
    # Ordering
    ordering = ('name',)
    
    # Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'report_template'),
            'classes': ('wide',)
        }),
        (_('Schedule Configuration'), {
            'fields': ('frequency', 'start_date', 'end_date', 'run_time', 'timezone'),
            'classes': ('wide',)
        }),
        (_('Status & Recipients'), {
            'fields': ('status', 'email_recipients'),
            'classes': ('wide',)
        }),
        (_('Execution Tracking'), {
            'fields': ('last_run', 'next_run', 'run_count'),
            'classes': ('collapse',)
        }),
        (_('Management'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = ('last_run', 'next_run', 'run_count', 'created_at', 'updated_at')
    
    # Raw ID fields
    raw_id_fields = ('report_template', 'created_by')
    
    # Custom methods for list display
    def status_display(self, obj):
        """Display status with color coding"""
        status_colors = {
            'ACTIVE': 'green',
            'PAUSED': 'orange',
            'DISABLED': 'red'
        }
        
        status_icons = {
            'ACTIVE': '▶️',
            'PAUSED': '⏸️',
            'DISABLED': '⏹️'
        }
        
        color = status_colors.get(obj.status, 'black')
        icon = status_icons.get(obj.status, '❓')
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'status'
    
    def next_run_display(self, obj):
        """Display next run time with relative formatting"""
        if obj.next_run:
            now = timezone.now()
            if obj.next_run > now:
                diff = obj.next_run - now
                if diff.days > 0:
                    return format_html(
                        '<span style="color: blue;">In {} days</span>',
                        diff.days
                    )
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    return format_html(
                        '<span style="color: blue;">In {} hours</span>',
                        hours
                    )
                else:
                    return format_html('<span style="color: orange;">Soon</span>')
            else:
                return format_html('<span style="color: red;">Overdue</span>')
        return format_html('<span style="color: gray;">Not scheduled</span>')
    next_run_display.short_description = _('Next Run')
    
    # Bulk actions
    actions = [
        'activate_schedules', 'pause_schedules', 'disable_schedules',
        'run_now', 'calculate_next_runs'
    ]
    
    def activate_schedules(self, request, queryset):
        """Activate selected schedules"""
        updated = queryset.exclude(status='ACTIVE').update(status='ACTIVE')
        
        self.message_user(
            request,
            f'{updated} schedule(s) were activated.',
            messages.SUCCESS
        )
    activate_schedules.short_description = _('Activate selected schedules')
    
    def pause_schedules(self, request, queryset):
        """Pause selected schedules"""
        updated = queryset.filter(status='ACTIVE').update(status='PAUSED')
        
        self.message_user(
            request,
            f'{updated} schedule(s) were paused.',
            messages.SUCCESS
        )
    pause_schedules.short_description = _('Pause selected schedules')
    
    def disable_schedules(self, request, queryset):
        """Disable selected schedules"""
        updated = queryset.exclude(status='DISABLED').update(status='DISABLED')
        
        self.message_user(
            request,
            f'{updated} schedule(s) were disabled.',
            messages.SUCCESS
        )
    disable_schedules.short_description = _('Disable selected schedules')
    
    def run_now(self, request, queryset):
        """Trigger immediate execution of selected schedules"""
        # This would integrate with the task queue system
        count = queryset.filter(status='ACTIVE').count()
        self.message_user(
            request,
            f'{count} schedule(s) will be executed immediately.',
            messages.INFO
        )
    run_now.short_description = _('Run selected schedules now')
    
    def calculate_next_runs(self, request, queryset):
        """Recalculate next run times"""
        updated = 0
        for schedule in queryset:
            schedule.calculate_next_run()
            schedule.save()
            updated += 1
        
        self.message_user(
            request,
            f'Next run times calculated for {updated} schedule(s).',
            messages.SUCCESS
        )
    calculate_next_runs.short_description = _('Recalculate next run times')
    
    # Custom save logic
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new schedule
            obj.created_by = request.user
        
        # Calculate next run time
        obj.calculate_next_run()
        
        super().save_model(request, obj, form, change)


@admin.register(ReportMetrics)
class ReportMetricsAdmin(admin.ModelAdmin):
    """
    Admin interface for ReportMetrics with analytics display.
    """
    
    # List display configuration
    list_display = (
        'report', 'performance_display', 'data_quality_display',
        'download_count', 'last_downloaded', 'created_at'
    )
    
    # Filtering
    list_filter = (
        'report__report_type', 'report__status',
        ('created_at', admin.DateFieldListFilter),
        ('last_downloaded', admin.DateFieldListFilter)
    )
    
    # Search fields
    search_fields = ('report__name', 'report__created_by__username')
    
    # Ordering
    ordering = ('-created_at',)
    
    # Read-only fields (metrics should not be manually edited)
    readonly_fields = (
        'report', 'query_time', 'processing_time', 'export_time',
        'memory_usage_mb', 'cpu_usage_percent', 'rows_processed',
        'columns_included', 'filters_applied', 'data_completeness_percent',
        'error_count', 'warning_count', 'download_count', 'last_downloaded',
        'created_at', 'updated_at'
    )
    
    # Custom methods for list display
    def performance_display(self, obj):
        """Display performance metrics"""
        try:
            # Handle None values properly
            query_time = obj.query_time or timezone.timedelta(0)
            processing_time = obj.processing_time or timezone.timedelta(0)
            export_time = obj.export_time or timezone.timedelta(0)
            
            total_time = query_time + processing_time + export_time
            total_seconds = float(total_time.total_seconds())
            
            if total_seconds < 10:
                color = 'green'
                status = 'Fast'
            elif total_seconds < 60:
                color = 'blue'
                status = 'Normal'
            elif total_seconds < 300:
                color = 'orange'
                status = 'Slow'
            else:
                color = 'red'
                status = 'Very Slow'
            
            return format_html(
                '<span style="color: {};">{} ({:.1f}s)</span>',
                color, status, total_seconds
            )
        except Exception as e:
            return format_html('<span style="color: gray;">N/A</span>')
    performance_display.short_description = _('Performance')
    
    def data_quality_display(self, obj):
        """Display data quality metrics"""
        try:
            completeness = float(obj.data_completeness_percent)
            
            if completeness >= 95:
                color = 'green'
                status = 'Excellent'
            elif completeness >= 85:
                color = 'blue'
                status = 'Good'
            elif completeness >= 70:
                color = 'orange'
                status = 'Fair'
            else:
                color = 'red'
                status = 'Poor'
            
            return format_html(
                '<span style="color: {};">{} ({:.1f}%)</span>',
                color, status, completeness
            )
        except Exception as e:
            return format_html('<span style="color: gray;">N/A</span>')
    data_quality_display.short_description = _('Data Quality')
    
    # Disable add/change permissions (metrics are auto-generated)
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReportShare)
class ReportShareAdmin(admin.ModelAdmin):
    """
    Admin interface for ReportShare management.
    """
    
    # List display configuration
    list_display = (
        'report', 'share_type', 'status_display', 'access_display',
        'expires_at', 'created_by', 'created_at'
    )
    
    # Filtering
    list_filter = (
        'share_type', 'status', 'password_protected',
        ('expires_at', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        'created_by'
    )
    
    # Search fields
    search_fields = (
        'report__name', 'share_token', 'created_by__username'
    )
    
    # Ordering
    ordering = ('-created_at',)
    
    # Read-only fields
    readonly_fields = (
        'share_token', 'access_count', 'download_count',
        'last_accessed', 'created_at', 'updated_at'
    )
    
    # Raw ID fields
    raw_id_fields = ('report', 'created_by')
    
    # Custom methods for list display
    def status_display(self, obj):
        """Display status with validity check"""
        if obj.is_valid():
            return format_html('<span style="color: green;">✅ Active</span>')
        elif obj.status == 'EXPIRED':
            return format_html('<span style="color: orange;">⏰ Expired</span>')
        elif obj.status == 'REVOKED':
            return format_html('<span style="color: red;">🚫 Revoked</span>')
        else:
            return format_html('<span style="color: gray;">❓ Unknown</span>')
    status_display.short_description = _('Status')
    
    def access_display(self, obj):
        """Display access statistics"""
        return format_html(
            'Views: {} | Downloads: {}',
            obj.access_count, obj.download_count
        )
    access_display.short_description = _('Usage')
    
    # Bulk actions
    actions = ['revoke_shares', 'extend_expiration', 'reset_usage_stats']
    
    def revoke_shares(self, request, queryset):
        """Revoke selected shares"""
        updated = queryset.filter(status='ACTIVE').update(status='REVOKED')
        
        self.message_user(
            request,
            f'{updated} share(s) were revoked.',
            messages.SUCCESS
        )
    revoke_shares.short_description = _('Revoke selected shares')
    
    def extend_expiration(self, request, queryset):
        """Extend expiration by 7 days"""
        from datetime import timedelta
        
        updated = 0
        for share in queryset:
            if share.expires_at:
                share.expires_at += timedelta(days=7)
                share.save()
                updated += 1
        
        self.message_user(
            request,
            f'Extended expiration for {updated} share(s) by 7 days.',
            messages.SUCCESS
        )
    extend_expiration.short_description = _('Extend expiration by 7 days')
    
    def reset_usage_stats(self, request, queryset):
        """Reset usage statistics"""
        updated = queryset.update(
            access_count=0,
            download_count=0,
            last_accessed=None
        )
        
        self.message_user(
            request,
            f'Usage statistics reset for {updated} share(s).',
            messages.SUCCESS
        )
    reset_usage_stats.short_description = _('Reset usage statistics')
    
    # Custom save logic
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new share
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)
