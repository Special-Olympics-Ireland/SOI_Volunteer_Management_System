from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import csv

from .models import Task, TaskCompletion
from .task_management_service import TaskManagementService
from common.audit_service import AdminAuditService


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'get_task_type_display', 'get_role_display', 'get_event_display', 
        'get_priority_display', 'get_due_date_display', 'get_completion_stats', 
        'is_mandatory', 'status', 'created_at'
    ]
    list_filter = [
        'task_type', 'priority', 'is_mandatory', 'status', 'category',
        'role__event', 'role__name', 'created_at'
    ]
    search_fields = ['title', 'description', 'role__name', 'event__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    filter_horizontal = ['prerequisite_tasks']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'task_type', 'role', 'event')
        }),
        ('Task Configuration', {
            'fields': (
                'priority', 'category', 'due_date', 'estimated_duration_minutes', 'instructions',
                'is_mandatory', 'requires_verification', 'status'
            )
        }),
        ('Requirements & Dependencies', {
            'fields': ('prerequisite_tasks',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('task_configuration',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'bulk_assign_to_role', 'mark_as_mandatory', 'mark_as_optional',
        'duplicate_tasks', 'export_tasks_csv'
    ]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('task-management/', self.admin_site.admin_view(self.task_management_view), 
                 name='tasks_task_management'),
            path('<int:task_id>/assign-volunteers/', self.admin_site.admin_view(self.assign_volunteers_view),
                 name='tasks_task_assign_volunteers'),
            path('<int:task_id>/completion-stats/', self.admin_site.admin_view(self.completion_stats_view),
                 name='tasks_task_completion_stats'),
            path('bulk-assign/', self.admin_site.admin_view(self.bulk_assign_view),
                 name='tasks_task_bulk_assign'),
            path('analytics/', self.admin_site.admin_view(self.analytics_view),
                 name='tasks_task_analytics'),
        ]
        return custom_urls + urls
    
    def get_task_type_display(self, obj):
        """Display task type with icon."""
        icons = {
            'CHECKBOX': '☑️',
            'PHOTO': '📷',
            'TEXT': '📝',
            'CUSTOM': '⚙️'
        }
        return format_html(
            '<span title="{}">{} {}</span>',
            obj.get_task_type_display(),
            icons.get(obj.task_type, '❓'),
            obj.get_task_type_display()
        )
    get_task_type_display.short_description = 'Type'
    
    def get_role_display(self, obj):
        """Display role with event context."""
        if obj.role:
            return format_html(
                '<a href="{}" title="View Role">{}</a>',
                reverse('admin:events_role_change', args=[obj.role.id]),
                obj.role.name
            )
        return '-'
    get_role_display.short_description = 'Role'
    
    def get_event_display(self, obj):
        """Display event with link."""
        if obj.event:
            return format_html(
                '<a href="{}" title="View Event">{}</a>',
                reverse('admin:events_event_change', args=[obj.event.id]),
                obj.event.name
            )
        return '-'
    get_event_display.short_description = 'Event'
    
    def get_priority_display(self, obj):
        """Display priority with color coding."""
        colors = {
            'LOW': '#4caf50',
            'MEDIUM': '#ff9800', 
            'HIGH': '#f44336',
            'CRITICAL': '#9c27b0',
            'URGENT': '#e91e63'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#666'),
            obj.priority
        )
    get_priority_display.short_description = 'Priority'
    
    def get_due_date_display(self, obj):
        """Display due date with status indicator."""
        if not obj.due_date:
            return '-'
        
        now = timezone.now()
        if obj.due_date < now:
            color = '#f44336'  # Red for overdue
            status = 'OVERDUE'
        elif obj.due_date < now + timedelta(days=3):
            color = '#ff9800'  # Orange for due soon
            status = 'DUE SOON'
        else:
            color = '#4caf50'  # Green for future
            status = 'FUTURE'
        
        return format_html(
            '<span style="color: {};" title="{}">{}</span>',
            color,
            status,
            obj.due_date.strftime('%Y-%m-%d %H:%M')
        )
    get_due_date_display.short_description = 'Due Date'
    
    def get_completion_stats(self, obj):
        """Display completion statistics."""
        completions = TaskCompletion.objects.filter(task=obj)
        total = completions.count()
        
        if total == 0:
            return format_html('<span style="color: #666;">No assignments</span>')
        
        completed = completions.filter(status='COMPLETED').count()
        in_progress = completions.filter(status='IN_PROGRESS').count()
        
        completion_rate = round(completed / total * 100, 1) if total > 0 else 0
        
        color = '#4caf50' if completion_rate >= 80 else '#ff9800' if completion_rate >= 50 else '#f44336'
        
        return format_html(
            '<div title="Total: {}, Completed: {}, In Progress: {}">'
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>'
            '<br><small>{}/{} completed</small>'
            '</div>',
            total, completed, in_progress,
            color, completion_rate,
            completed, total
        )
    get_completion_stats.short_description = 'Completion'
    
    def bulk_assign_to_role(self, request, queryset):
        """Bulk assign selected tasks to all volunteers in their roles."""
        count = 0
        for task in queryset:
            if task.role:
                try:
                    TaskManagementService._auto_assign_task_to_role(task, task.role)
                    count += 1
                except Exception as e:
                    messages.error(request, f"Failed to assign task '{task.title}': {str(e)}")
        
        if count > 0:
            messages.success(request, f"Successfully assigned {count} tasks to role volunteers.")
            
            # Log bulk assignment
            AdminAuditService.log_bulk_operation(
                operation='bulk_task_assignment_to_roles',
                user=request.user,
                affected_count=count,
                details={
                    'task_ids': list(queryset.values_list('id', flat=True)),
                    'method': 'admin_bulk_action'
                }
            )
    bulk_assign_to_role.short_description = "Assign selected tasks to all role volunteers"
    
    def mark_as_mandatory(self, request, queryset):
        """Mark selected tasks as mandatory."""
        updated = queryset.update(is_mandatory=True)
        messages.success(request, f"Marked {updated} tasks as mandatory.")
        
        AdminAuditService.log_bulk_operation(
            operation='mark_tasks_mandatory',
            user=request.user,
            affected_count=updated,
            details={'task_ids': list(queryset.values_list('id', flat=True))}
        )
    mark_as_mandatory.short_description = "Mark as mandatory"
    
    def mark_as_optional(self, request, queryset):
        """Mark selected tasks as optional."""
        updated = queryset.update(is_mandatory=False)
        messages.success(request, f"Marked {updated} tasks as optional.")
        
        AdminAuditService.log_bulk_operation(
            operation='mark_tasks_optional',
            user=request.user,
            affected_count=updated,
            details={'task_ids': list(queryset.values_list('id', flat=True))}
        )
    mark_as_optional.short_description = "Mark as optional"
    
    def duplicate_tasks(self, request, queryset):
        """Duplicate selected tasks."""
        count = 0
        for task in queryset:
            try:
                task.pk = None
                task.title = f"{task.title} (Copy)"
                task.created_by = request.user
                task.save()
                count += 1
            except Exception as e:
                messages.error(request, f"Failed to duplicate task '{task.title}': {str(e)}")
        
        if count > 0:
            messages.success(request, f"Successfully duplicated {count} tasks.")
    duplicate_tasks.short_description = "Duplicate selected tasks"
    
    def export_tasks_csv(self, request, queryset):
        """Export selected tasks to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tasks_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Title', 'Description', 'Type', 'Role', 'Event', 'Priority',
            'Due Date', 'Estimated Duration', 'Is Mandatory', 'Points Value',
            'Created At', 'Created By'
        ])
        
        for task in queryset:
            writer.writerow([
                task.title,
                task.description,
                task.task_type,
                task.role.name if task.role else '',
                task.event.name if task.event else '',
                task.priority,
                task.due_date.isoformat() if task.due_date else '',
                task.estimated_duration,
                task.is_mandatory,
                task.points_value,
                task.created_at.isoformat(),
                task.created_by.get_full_name() if task.created_by else ''
            ])
        
        # Log export
        AdminAuditService.log_data_export(
            user=request.user,
            export_type='tasks_csv',
            model_class=Task,
            record_count=queryset.count(),
            export_format='csv',
            request=request,
            details={'exported_task_ids': list(queryset.values_list('id', flat=True))}
        )
        
        return response
    export_tasks_csv.short_description = "Export to CSV"
    
    def task_management_view(self, request):
        """Main task management dashboard."""
        context = {
            'title': 'Task Management Dashboard',
            'has_permission': True,
            'opts': self.model._meta,
        }
        
        # Get task statistics
        total_tasks = Task.objects.count()
        active_tasks = Task.objects.filter(is_active=True).count()
        overdue_tasks = Task.objects.filter(
            due_date__lt=timezone.now(),
            is_active=True
        ).count()
        
        # Get completion statistics
        total_completions = TaskCompletion.objects.count()
        completed_tasks = TaskCompletion.objects.filter(status='COMPLETED').count()
        pending_review = TaskCompletion.objects.filter(status='PENDING_REVIEW').count()
        
        context.update({
            'stats': {
                'total_tasks': total_tasks,
                'active_tasks': active_tasks,
                'overdue_tasks': overdue_tasks,
                'total_completions': total_completions,
                'completed_tasks': completed_tasks,
                'pending_review': pending_review,
                'completion_rate': round(completed_tasks / total_completions * 100, 1) if total_completions > 0 else 0
            }
        })
        
        return render(request, 'admin/tasks/task_management.html', context)
    
    def assign_volunteers_view(self, request, task_id):
        """View for assigning volunteers to a task."""
        task = get_object_or_404(Task, id=task_id)
        
        if request.method == 'POST':
            volunteer_ids = request.POST.getlist('volunteers')
            
            try:
                results = TaskManagementService.bulk_assign_tasks(
                    [task_id], volunteer_ids, request.user
                )
                
                messages.success(
                    request, 
                    f"Successfully assigned task to {results['total_successful']} volunteers."
                )
                
                if results['total_failed'] > 0:
                    messages.warning(
                        request,
                        f"{results['total_failed']} assignments failed."
                    )
                
                return redirect('admin:tasks_task_changelist')
                
            except Exception as e:
                messages.error(request, f"Assignment failed: {str(e)}")
        
        # Get available volunteers (those assigned to the task's role)
        from events.models import Assignment
        available_volunteers = Assignment.objects.filter(
            role=task.role,
            status='CONFIRMED'
        ).select_related('volunteer', 'volunteer__user')
        
        # Get already assigned volunteers
        assigned_volunteers = TaskCompletion.objects.filter(
            task=task
        ).values_list('volunteer_id', flat=True)
        
        context = {
            'title': f'Assign Volunteers to: {task.title}',
            'task': task,
            'available_volunteers': available_volunteers,
            'assigned_volunteers': assigned_volunteers,
            'has_permission': True,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/tasks/assign_volunteers.html', context)
    
    def completion_stats_view(self, request, task_id):
        """View for task completion statistics."""
        task = get_object_or_404(Task, id=task_id)
        
        completions = TaskCompletion.objects.filter(task=task).select_related(
            'volunteer', 'volunteer__user'
        )
        
        # Calculate statistics
        stats = TaskManagementService._calculate_task_completion_stats(completions)
        
        context = {
            'title': f'Completion Stats: {task.title}',
            'task': task,
            'completions': completions,
            'stats': stats,
            'has_permission': True,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/tasks/completion_stats.html', context)
    
    def bulk_assign_view(self, request):
        """View for bulk task assignment."""
        if request.method == 'POST':
            task_ids = request.POST.getlist('tasks')
            volunteer_ids = request.POST.getlist('volunteers')
            
            try:
                results = TaskManagementService.bulk_assign_tasks(
                    task_ids, volunteer_ids, request.user
                )
                
                messages.success(
                    request,
                    f"Bulk assignment completed: {results['total_successful']} successful, "
                    f"{results['total_failed']} failed."
                )
                
                return redirect('admin:tasks_task_changelist')
                
            except Exception as e:
                messages.error(request, f"Bulk assignment failed: {str(e)}")
        
        # Get available tasks and volunteers
        tasks = Task.objects.filter(is_active=True).select_related('role', 'event')
        
        from volunteers.models import VolunteerProfile
        volunteers = VolunteerProfile.objects.filter(
            status='ACTIVE'
        ).select_related('user')
        
        context = {
            'title': 'Bulk Task Assignment',
            'tasks': tasks,
            'volunteers': volunteers,
            'has_permission': True,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/tasks/bulk_assign.html', context)
    
    def analytics_view(self, request):
        """View for task analytics."""
        try:
            analytics = TaskManagementService.get_task_analytics()
            
            context = {
                'title': 'Task Analytics',
                'analytics': analytics,
                'has_permission': True,
                'opts': self.model._meta,
            }
            
            return render(request, 'admin/tasks/analytics.html', context)
            
        except Exception as e:
            messages.error(request, f"Failed to load analytics: {str(e)}")
            return redirect('admin:tasks_task_changelist')
    
    def save_model(self, request, obj, form, change):
        """Override save to add audit logging."""
        if not change:  # New object
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)
        
        # Log the task creation/update
        operation = 'task_update' if change else 'task_creation'
        AdminAuditService.log_system_management_operation(
            operation=operation,
            user=request.user,
            details={
                'task_id': obj.id,
                'task_title': obj.title,
                'role_id': obj.role.id if obj.role else None,
                'event_id': obj.event.id if obj.event else None,
                'is_new': not change
            }
        )


@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = [
        'get_task_display', 'get_volunteer_display', 'get_status_display',
        'get_progress_display', 'submitted_at', 'completed_at', 'get_time_spent_display'
    ]
    list_filter = [
        'status', 'task__priority', 'task__task_type', 'task__role__event',
        'submitted_at', 'completed_at'
    ]
    search_fields = [
        'task__title', 'volunteer__first_name', 'volunteer__last_name',
        'volunteer__email'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'submitted_at', 'completed_at']
    
    fieldsets = (
        ('Assignment Information', {
            'fields': ('task', 'volunteer', 'assignment', 'completion_type')
        }),
        ('Progress Tracking', {
            'fields': ('status', 'time_started', 'submitted_at', 'completed_at', 'time_spent_minutes')
        }),
        ('Completion Data', {
            'fields': ('completion_data', 'attachments', 'photos'),
            'classes': ('collapse',)
        }),
        ('Review Information', {
            'fields': ('verified_by', 'verified_at', 'verification_notes', 'quality_score'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_completed', 'mark_as_in_progress', 'mark_for_review',
        'export_completions_csv', 'send_reminder_emails'
    ]
    
    def get_task_display(self, obj):
        """Display task with link and type icon."""
        icons = {
            'CHECKBOX': '☑️',
            'PHOTO': '📷',
            'TEXT': '📝',
            'CUSTOM': '⚙️'
        }
        return format_html(
            '<a href="{}" title="View Task">{} {}</a>',
            reverse('admin:tasks_task_change', args=[obj.task.id]),
            icons.get(obj.task.task_type, '❓'),
            obj.task.title
        )
    get_task_display.short_description = 'Task'
    
    def get_volunteer_display(self, obj):
        """Display volunteer with link."""
        return format_html(
            '<a href="{}" title="View Volunteer">{}</a>',
            reverse('admin:volunteers_volunteerprofile_change', args=[obj.volunteer.id]),
            obj.volunteer.user.get_full_name()
        )
    get_volunteer_display.short_description = 'Volunteer'
    
    def get_status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'NOT_STARTED': '#666',
            'IN_PROGRESS': '#2196f3',
            'PENDING_REVIEW': '#ff9800',
            'COMPLETED': '#4caf50',
            'FAILED': '#f44336',
            'CANCELLED': '#9e9e9e'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    get_status_display.short_description = 'Status'
    
    def get_progress_display(self, obj):
        """Display progress with visual bar."""
        percentage = obj.progress_percentage or 0
        color = '#4caf50' if percentage >= 80 else '#ff9800' if percentage >= 50 else '#f44336'
        
        return format_html(
            '<div style="width: 100px; background: #eee; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; height: 20px; background: {}; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold;">'
            '{}%'
            '</div>'
            '</div>',
            percentage, color, percentage
        )
    get_progress_display.short_description = 'Progress'
    
    def get_due_date_display(self, obj):
        """Display due date with status indicator."""
        if not obj.due_date:
            return '-'
        
        now = timezone.now()
        if obj.due_date < now and obj.status not in ['COMPLETED', 'CANCELLED']:
            color = '#f44336'  # Red for overdue
            status = 'OVERDUE'
        elif obj.due_date < now + timedelta(days=1) and obj.status not in ['COMPLETED', 'CANCELLED']:
            color = '#ff9800'  # Orange for due soon
            status = 'DUE SOON'
        else:
            color = '#4caf50'  # Green for future or completed
            status = 'OK'
        
        return format_html(
            '<span style="color: {};" title="{}">{}</span>',
            color,
            status,
            obj.due_date.strftime('%Y-%m-%d %H:%M')
        )
    get_due_date_display.short_description = 'Due Date'
    
    def get_time_spent_display(self, obj):
        """Display time spent in human-readable format."""
        if not obj.time_spent:
            return '-'
        
        hours = int(obj.time_spent)
        minutes = int((obj.time_spent - hours) * 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    get_time_spent_display.short_description = 'Time Spent'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected completions as completed."""
        updated = 0
        for completion in queryset:
            if completion.status not in ['COMPLETED', 'CANCELLED']:
                try:
                    TaskManagementService.update_task_progress(
                        completion.id,
                        {'status': 'COMPLETED', 'progress_percentage': 100},
                        request.user
                    )
                    updated += 1
                except Exception as e:
                    messages.error(request, f"Failed to complete task for {completion.volunteer.user.get_full_name()}: {str(e)}")
        
        if updated > 0:
            messages.success(request, f"Marked {updated} tasks as completed.")
    mark_as_completed.short_description = "Mark as completed"
    
    def mark_as_in_progress(self, request, queryset):
        """Mark selected completions as in progress."""
        updated = 0
        for completion in queryset:
            if completion.status == 'NOT_STARTED':
                try:
                    TaskManagementService.update_task_progress(
                        completion.id,
                        {'status': 'IN_PROGRESS'},
                        request.user
                    )
                    updated += 1
                except Exception as e:
                    messages.error(request, f"Failed to update task for {completion.volunteer.user.get_full_name()}: {str(e)}")
        
        if updated > 0:
            messages.success(request, f"Marked {updated} tasks as in progress.")
    mark_as_in_progress.short_description = "Mark as in progress"
    
    def mark_for_review(self, request, queryset):
        """Mark selected completions for review."""
        updated = 0
        for completion in queryset:
            if completion.status == 'IN_PROGRESS':
                try:
                    TaskManagementService.update_task_progress(
                        completion.id,
                        {'status': 'PENDING_REVIEW', 'progress_percentage': 100},
                        request.user
                    )
                    updated += 1
                except Exception as e:
                    messages.error(request, f"Failed to mark task for review for {completion.volunteer.user.get_full_name()}: {str(e)}")
        
        if updated > 0:
            messages.success(request, f"Marked {updated} tasks for review.")
    mark_for_review.short_description = "Mark for review"
    
    def export_completions_csv(self, request, queryset):
        """Export selected completions to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="task_completions_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Task Title', 'Volunteer Name', 'Volunteer Email', 'Status',
            'Progress %', 'Assigned Date', 'Due Date', 'Started Date',
            'Completed Date', 'Time Spent (hours)', 'Notes'
        ])
        
        for completion in queryset:
            writer.writerow([
                completion.task.title,
                completion.volunteer.user.get_full_name(),
                completion.volunteer.user.email,
                completion.status,
                completion.progress_percentage or 0,
                completion.assigned_at.isoformat() if completion.assigned_at else '',
                completion.due_date.isoformat() if completion.due_date else '',
                completion.started_at.isoformat() if completion.started_at else '',
                completion.completed_at.isoformat() if completion.completed_at else '',
                completion.time_spent or 0,
                completion.notes or ''
            ])
        
        # Log export
        AdminAuditService.log_data_export(
            user=request.user,
            export_type='task_completions_csv',
            model_class=TaskCompletion,
            record_count=queryset.count(),
            export_format='csv',
            request=request,
            details={'exported_completion_ids': list(queryset.values_list('id', flat=True))}
        )
        
        return response
    export_completions_csv.short_description = "Export to CSV"
    
    def send_reminder_emails(self, request, queryset):
        """Send reminder emails for overdue or due soon tasks."""
        sent_count = 0
        
        for completion in queryset:
            if (completion.due_date and 
                completion.due_date <= timezone.now() + timedelta(days=1) and
                completion.status in ['NOT_STARTED', 'IN_PROGRESS']):
                
                try:
                    # Implementation for sending reminder email
                    # TaskManagementService._send_task_reminder_notification(completion)
                    sent_count += 1
                except Exception as e:
                    messages.error(request, f"Failed to send reminder to {completion.volunteer.user.get_full_name()}: {str(e)}")
        
        if sent_count > 0:
            messages.success(request, f"Sent {sent_count} reminder emails.")
        else:
            messages.info(request, "No reminder emails were sent (no eligible tasks found).")
    send_reminder_emails.short_description = "Send reminder emails"


# TaskTemplate and TaskDependency admin classes removed as models don't exist
