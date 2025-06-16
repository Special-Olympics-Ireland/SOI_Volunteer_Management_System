"""
Comprehensive Task Management Service for SOI Hub Volunteer Management System.

This service provides role-specific task management including task creation,
assignment workflows, progress tracking, completion validation, and reporting.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from django.db.models import Count, Q, Avg, Sum, Max, Min, F, Case, When, IntegerField
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings

from .models import Task, TaskCompletion
from events.models import Event, Role, Assignment
from volunteers.models import VolunteerProfile
from common.audit_service import AdminAuditService

User = get_user_model()


class TaskManagementService:
    """
    Comprehensive task management service for role-specific tasks.
    """
    
    # Task priority levels
    PRIORITY_LEVELS = {
        'LOW': 1,
        'MEDIUM': 2,
        'HIGH': 3,
        'CRITICAL': 4,
        'URGENT': 5
    }
    
    # Task completion statuses
    COMPLETION_STATUSES = [
        'NOT_STARTED',
        'IN_PROGRESS', 
        'PENDING_REVIEW',
        'COMPLETED',
        'FAILED',
        'CANCELLED'
    ]
    
    @classmethod
    def create_role_specific_task(cls, role_id: int, task_data: Dict[str, Any], 
                                 created_by: User) -> Task:
        """
        Create a new role-specific task.
        
        Args:
            role_id: ID of the role this task is for
            task_data: Dictionary containing task information
            created_by: User creating the task
            
        Returns:
            Created Task instance
        """
        try:
            from events.models import Role
            role = Role.objects.get(id=role_id)
            
            # Validate task data
            cls._validate_task_data(task_data)
            
            # Create the task
            task = Task.objects.create(
                title=task_data['title'],
                description=task_data['description'],
                task_type=task_data.get('task_type', 'CHECKBOX'),
                role=role,
                event=role.event,
                priority=task_data.get('priority', 'MEDIUM'),
                due_date=task_data.get('due_date'),
                estimated_duration=task_data.get('estimated_duration', 30),
                instructions=task_data.get('instructions', ''),
                required_skills=task_data.get('required_skills', []),
                prerequisites=task_data.get('prerequisites', []),
                is_mandatory=task_data.get('is_mandatory', False),
                is_repeatable=task_data.get('is_repeatable', False),
                max_attempts=task_data.get('max_attempts', 1),
                points_value=task_data.get('points_value', 0),
                created_by=created_by,
                metadata=task_data.get('metadata', {})
            )
            
            # Create task dependencies if specified
            if 'dependencies' in task_data:
                cls._create_task_dependencies(task, task_data['dependencies'])
            
            # Auto-assign to existing role assignments if specified
            if task_data.get('auto_assign', False):
                cls._auto_assign_task_to_role(task, role)
            
            # Log the task creation
            AdminAuditService.log_system_management_operation(
                operation='task_creation',
                user=created_by,
                details={
                    'task_id': task.id,
                    'task_title': task.title,
                    'role_id': role.id,
                    'role_name': role.name,
                    'event_id': role.event.id,
                    'task_type': task.task_type,
                    'priority': task.priority,
                    'is_mandatory': task.is_mandatory
                }
            )
            
            return task
            
        except Exception as e:
            raise ValidationError(f"Failed to create role-specific task: {str(e)}")
    
    @classmethod
    def assign_task_to_volunteer(cls, task_id: int, volunteer_id: int, 
                               assigned_by: User, due_date: Optional[datetime] = None) -> TaskCompletion:
        """
        Assign a task to a specific volunteer.
        
        Args:
            task_id: ID of the task to assign
            volunteer_id: ID of the volunteer to assign to
            assigned_by: User making the assignment
            due_date: Optional custom due date
            
        Returns:
            Created TaskCompletion instance
        """
        try:
            task = Task.objects.get(id=task_id)
            volunteer = VolunteerProfile.objects.get(id=volunteer_id)
            
            # Check if volunteer is assigned to the role
            if not Assignment.objects.filter(
                volunteer=volunteer,
                role=task.role,
                status='CONFIRMED'
            ).exists():
                raise ValidationError(
                    f"Volunteer {volunteer.user.get_full_name()} is not assigned to role {task.role.name}"
                )
            
            # Check if task is already assigned to this volunteer
            existing_completion = TaskCompletion.objects.filter(
                task=task,
                volunteer=volunteer,
                status__in=['NOT_STARTED', 'IN_PROGRESS', 'PENDING_REVIEW']
            ).first()
            
            if existing_completion:
                raise ValidationError(
                    f"Task '{task.title}' is already assigned to {volunteer.user.get_full_name()}"
                )
            
            # Check prerequisites
            if not cls._check_task_prerequisites(task, volunteer):
                raise ValidationError(
                    f"Volunteer {volunteer.user.get_full_name()} does not meet task prerequisites"
                )
            
            # Create task completion record
            task_completion = TaskCompletion.objects.create(
                task=task,
                volunteer=volunteer,
                assigned_by=assigned_by,
                assigned_at=timezone.now(),
                due_date=due_date or task.due_date,
                status='NOT_STARTED',
                metadata={
                    'assignment_method': 'manual',
                    'assigned_by_name': assigned_by.get_full_name()
                }
            )
            
            # Send notification to volunteer
            cls._send_task_assignment_notification(task_completion)
            
            # Log the assignment
            AdminAuditService.log_volunteer_management_operation(
                operation='task_assignment',
                volunteer=volunteer,
                user=assigned_by,
                details={
                    'task_id': task.id,
                    'task_title': task.title,
                    'completion_id': task_completion.id,
                    'due_date': due_date.isoformat() if due_date else None,
                    'assignment_method': 'manual'
                }
            )
            
            return task_completion
            
        except Exception as e:
            raise ValidationError(f"Failed to assign task to volunteer: {str(e)}")
    
    @classmethod
    def bulk_assign_tasks(cls, task_ids: List[int], volunteer_ids: List[int], 
                         assigned_by: User) -> Dict[str, Any]:
        """
        Bulk assign multiple tasks to multiple volunteers.
        
        Args:
            task_ids: List of task IDs to assign
            volunteer_ids: List of volunteer IDs to assign to
            assigned_by: User making the assignments
            
        Returns:
            Dictionary with assignment results
        """
        results = {
            'successful_assignments': [],
            'failed_assignments': [],
            'total_attempted': len(task_ids) * len(volunteer_ids),
            'total_successful': 0,
            'total_failed': 0
        }
        
        with transaction.atomic():
            for task_id in task_ids:
                for volunteer_id in volunteer_ids:
                    try:
                        completion = cls.assign_task_to_volunteer(
                            task_id, volunteer_id, assigned_by
                        )
                        results['successful_assignments'].append({
                            'task_id': task_id,
                            'volunteer_id': volunteer_id,
                            'completion_id': completion.id
                        })
                        results['total_successful'] += 1
                        
                    except Exception as e:
                        results['failed_assignments'].append({
                            'task_id': task_id,
                            'volunteer_id': volunteer_id,
                            'error': str(e)
                        })
                        results['total_failed'] += 1
        
        # Log bulk assignment
        AdminAuditService.log_bulk_operation(
            operation='bulk_task_assignment',
            user=assigned_by,
            affected_count=results['total_successful'],
            details={
                'task_ids': task_ids,
                'volunteer_ids': volunteer_ids,
                'successful_count': results['total_successful'],
                'failed_count': results['total_failed']
            }
        )
        
        return results
    
    @classmethod
    def update_task_progress(cls, completion_id: int, progress_data: Dict[str, Any], 
                           updated_by: User) -> TaskCompletion:
        """
        Update task completion progress.
        
        Args:
            completion_id: ID of the TaskCompletion to update
            progress_data: Dictionary containing progress information
            updated_by: User making the update
            
        Returns:
            Updated TaskCompletion instance
        """
        try:
            completion = TaskCompletion.objects.get(id=completion_id)
            
            # Store old status for comparison
            old_status = completion.status
            
            # Update progress fields
            if 'status' in progress_data:
                completion.status = progress_data['status']
            
            if 'progress_percentage' in progress_data:
                completion.progress_percentage = progress_data['progress_percentage']
            
            if 'notes' in progress_data:
                completion.notes = progress_data['notes']
            
            if 'completion_data' in progress_data:
                completion.completion_data = progress_data['completion_data']
            
            if 'time_spent' in progress_data:
                completion.time_spent = progress_data['time_spent']
            
            # Handle status-specific updates
            if completion.status == 'IN_PROGRESS' and old_status == 'NOT_STARTED':
                completion.started_at = timezone.now()
            
            elif completion.status == 'COMPLETED':
                completion.completed_at = timezone.now()
                completion.progress_percentage = 100
                
                # Validate completion based on task type
                cls._validate_task_completion(completion, progress_data)
            
            elif completion.status == 'PENDING_REVIEW':
                completion.submitted_at = timezone.now()
                completion.progress_percentage = 100
            
            # Update metadata
            if 'metadata' in progress_data:
                completion.metadata.update(progress_data['metadata'])
            
            completion.updated_at = timezone.now()
            completion.save()
            
            # Handle status change notifications
            if old_status != completion.status:
                cls._handle_status_change_notifications(completion, old_status)
            
            # Check for task completion rewards/points
            if completion.status == 'COMPLETED':
                cls._award_task_completion_points(completion)
            
            # Log the progress update
            AdminAuditService.log_volunteer_management_operation(
                operation='task_progress_update',
                volunteer=completion.volunteer,
                user=updated_by,
                details={
                    'completion_id': completion.id,
                    'task_id': completion.task.id,
                    'old_status': old_status,
                    'new_status': completion.status,
                    'progress_percentage': completion.progress_percentage,
                    'updated_fields': list(progress_data.keys())
                }
            )
            
            return completion
            
        except Exception as e:
            raise ValidationError(f"Failed to update task progress: {str(e)}")
    
    @classmethod
    def get_volunteer_tasks(cls, volunteer_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get all tasks for a specific volunteer with filtering options.
        
        Args:
            volunteer_id: ID of the volunteer
            filters: Optional filters (status, priority, event, etc.)
            
        Returns:
            Dictionary containing task information
        """
        try:
            volunteer = VolunteerProfile.objects.get(id=volunteer_id)
            
            # Base queryset
            queryset = TaskCompletion.objects.filter(
                volunteer=volunteer
            ).select_related(
                'task', 'task__role', 'task__event', 'assigned_by'
            ).order_by('-assigned_at')
            
            # Apply filters
            if filters:
                if 'status' in filters:
                    queryset = queryset.filter(status=filters['status'])
                
                if 'priority' in filters:
                    queryset = queryset.filter(task__priority=filters['priority'])
                
                if 'event_id' in filters:
                    queryset = queryset.filter(task__event_id=filters['event_id'])
                
                if 'role_id' in filters:
                    queryset = queryset.filter(task__role_id=filters['role_id'])
                
                if 'task_type' in filters:
                    queryset = queryset.filter(task__task_type=filters['task_type'])
                
                if 'due_date_from' in filters:
                    queryset = queryset.filter(due_date__gte=filters['due_date_from'])
                
                if 'due_date_to' in filters:
                    queryset = queryset.filter(due_date__lte=filters['due_date_to'])
                
                if 'overdue' in filters and filters['overdue']:
                    queryset = queryset.filter(
                        due_date__lt=timezone.now(),
                        status__in=['NOT_STARTED', 'IN_PROGRESS']
                    )
            
            # Get task completions
            completions = list(queryset)
            
            # Calculate statistics
            stats = cls._calculate_volunteer_task_stats(completions)
            
            # Group tasks by status
            tasks_by_status = {}
            for status in cls.COMPLETION_STATUSES:
                tasks_by_status[status] = [
                    cls._serialize_task_completion(completion)
                    for completion in completions
                    if completion.status == status
                ]
            
            return {
                'volunteer_id': volunteer_id,
                'volunteer_name': volunteer.user.get_full_name(),
                'total_tasks': len(completions),
                'statistics': stats,
                'tasks_by_status': tasks_by_status,
                'upcoming_deadlines': cls._get_upcoming_deadlines(completions),
                'overdue_tasks': cls._get_overdue_tasks(completions)
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to get volunteer tasks: {str(e)}")
    
    @classmethod
    def get_role_tasks(cls, role_id: int, include_completions: bool = True) -> Dict[str, Any]:
        """
        Get all tasks for a specific role.
        
        Args:
            role_id: ID of the role
            include_completions: Whether to include completion data
            
        Returns:
            Dictionary containing role task information
        """
        try:
            from events.models import Role
            role = Role.objects.get(id=role_id)
            
            # Get all tasks for this role
            tasks = Task.objects.filter(role=role).order_by('priority', 'due_date')
            
            role_data = {
                'role_id': role_id,
                'role_name': role.name,
                'event_id': role.event.id,
                'event_name': role.event.name,
                'total_tasks': tasks.count(),
                'tasks': []
            }
            
            for task in tasks:
                task_data = cls._serialize_task(task)
                
                if include_completions:
                    # Get completion statistics
                    completions = TaskCompletion.objects.filter(task=task)
                    task_data['completion_stats'] = cls._calculate_task_completion_stats(completions)
                    
                    # Get recent completions
                    recent_completions = completions.select_related(
                        'volunteer', 'volunteer__user'
                    ).order_by('-updated_at')[:5]
                    
                    task_data['recent_completions'] = [
                        cls._serialize_task_completion(completion)
                        for completion in recent_completions
                    ]
                
                role_data['tasks'].append(task_data)
            
            # Calculate role-level statistics
            if include_completions:
                role_data['role_statistics'] = cls._calculate_role_task_stats(role)
            
            return role_data
            
        except Exception as e:
            raise ValidationError(f"Failed to get role tasks: {str(e)}")
    
    # TaskTemplate methods commented out as TaskTemplate model doesn't exist
    # @classmethod
    # def create_task_template(cls, template_data: Dict[str, Any], created_by: User) -> TaskTemplate:
    #     """Create a reusable task template."""
    #     pass
    
    # @classmethod
    # def create_task_from_template(cls, template_id: int, role_id: int, 
    #                              customizations: Dict[str, Any], created_by: User) -> Task:
    #     """Create a task from a template with customizations."""
    #     pass
    
    @classmethod
    def get_task_analytics(cls, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get comprehensive task analytics and reporting data.
        
        Args:
            filters: Optional filters for the analytics
            
        Returns:
            Dictionary containing analytics data
        """
        try:
            # Base querysets
            tasks_qs = Task.objects.all()
            completions_qs = TaskCompletion.objects.all()
            
            # Apply filters
            if filters:
                if 'event_id' in filters:
                    tasks_qs = tasks_qs.filter(event_id=filters['event_id'])
                    completions_qs = completions_qs.filter(task__event_id=filters['event_id'])
                
                if 'role_id' in filters:
                    tasks_qs = tasks_qs.filter(role_id=filters['role_id'])
                    completions_qs = completions_qs.filter(task__role_id=filters['role_id'])
                
                if 'date_from' in filters:
                    completions_qs = completions_qs.filter(assigned_at__gte=filters['date_from'])
                
                if 'date_to' in filters:
                    completions_qs = completions_qs.filter(assigned_at__lte=filters['date_to'])
            
            # Calculate analytics
            analytics = {
                'overview': {
                    'total_tasks': tasks_qs.count(),
                    'total_assignments': completions_qs.count(),
                    'completion_rate': cls._calculate_overall_completion_rate(completions_qs),
                    'average_completion_time': cls._calculate_average_completion_time(completions_qs),
                    'overdue_tasks': cls._count_overdue_tasks(completions_qs)
                },
                'task_distribution': {
                    'by_type': cls._get_task_distribution_by_type(tasks_qs),
                    'by_priority': cls._get_task_distribution_by_priority(tasks_qs),
                    'by_status': cls._get_completion_distribution_by_status(completions_qs)
                },
                'performance_metrics': {
                    'top_performers': cls._get_top_performing_volunteers(completions_qs),
                    'task_completion_trends': cls._get_completion_trends(completions_qs),
                    'average_time_by_task_type': cls._get_average_time_by_task_type(completions_qs)
                },
                'role_analysis': cls._get_role_task_analysis(tasks_qs, completions_qs),
                'bottlenecks': cls._identify_task_bottlenecks(completions_qs)
            }
            
            return analytics
            
        except Exception as e:
            raise ValidationError(f"Failed to generate task analytics: {str(e)}")
    
    # Helper methods
    
    @classmethod
    def _validate_task_data(cls, task_data: Dict[str, Any]) -> None:
        """Validate task creation data."""
        required_fields = ['title', 'description']
        for field in required_fields:
            if field not in task_data or not task_data[field]:
                raise ValidationError(f"Required field '{field}' is missing or empty")
        
        if 'priority' in task_data and task_data['priority'] not in cls.PRIORITY_LEVELS:
            raise ValidationError(f"Invalid priority level: {task_data['priority']}")
        
        if 'task_type' in task_data and task_data['task_type'] not in ['CHECKBOX', 'PHOTO', 'TEXT', 'CUSTOM']:
            raise ValidationError(f"Invalid task type: {task_data['task_type']}")
    
    @classmethod
    def _create_task_dependencies(cls, task: Task, dependencies: List[int]) -> None:
        """Create task dependencies."""
        # TaskDependency model doesn't exist, using task.prerequisite_tasks instead
        for dep_task_id in dependencies:
            try:
                dep_task = Task.objects.get(id=dep_task_id)
                task.prerequisite_tasks.add(dep_task)
            except Task.DoesNotExist:
                continue
    
    @classmethod
    def _auto_assign_task_to_role(cls, task: Task, role: Role) -> None:
        """Auto-assign task to all volunteers in the role."""
        assignments = Assignment.objects.filter(role=role, status='CONFIRMED')
        
        for assignment in assignments:
            try:
                TaskCompletion.objects.create(
                    task=task,
                    volunteer=assignment.volunteer,
                    assigned_by=task.created_by,
                    assigned_at=timezone.now(),
                    due_date=task.due_date,
                    status='NOT_STARTED',
                    metadata={
                        'assignment_method': 'auto',
                        'auto_assigned': True
                    }
                )
            except Exception:
                continue  # Skip if assignment fails
    
    @classmethod
    def _check_task_prerequisites(cls, task: Task, volunteer: VolunteerProfile) -> bool:
        """Check if volunteer meets task prerequisites."""
        if not task.prerequisites:
            return True
        
        # Check completed tasks
        completed_tasks = TaskCompletion.objects.filter(
            volunteer=volunteer,
            status='COMPLETED',
            task_id__in=task.prerequisites
        ).values_list('task_id', flat=True)
        
        return set(task.prerequisites).issubset(set(completed_tasks))
    
    @classmethod
    def _send_task_assignment_notification(cls, completion: TaskCompletion) -> None:
        """Send notification email for task assignment."""
        try:
            context = {
                'volunteer_name': completion.volunteer.user.get_full_name(),
                'task_title': completion.task.title,
                'task_description': completion.task.description,
                'due_date': completion.due_date,
                'role_name': completion.task.role.name,
                'event_name': completion.task.event.name,
                'instructions': completion.task.instructions
            }
            
            subject = f"New Task Assignment: {completion.task.title}"
            message = render_to_string('tasks/task_assignment_email.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[completion.volunteer.user.email],
                html_message=message
            )
        except Exception:
            pass  # Don't fail task assignment if email fails
    
    @classmethod
    def _validate_task_completion(cls, completion: TaskCompletion, progress_data: Dict[str, Any]) -> None:
        """Validate task completion based on task type."""
        task = completion.task
        
        if task.task_type == 'PHOTO':
            if 'completion_data' not in progress_data or 'photo_url' not in progress_data['completion_data']:
                raise ValidationError("Photo tasks require photo upload for completion")
        
        elif task.task_type == 'TEXT':
            if 'completion_data' not in progress_data or 'text_response' not in progress_data['completion_data']:
                raise ValidationError("Text tasks require text response for completion")
        
        elif task.task_type == 'CUSTOM':
            # Custom validation based on task metadata
            if 'validation_rules' in task.metadata:
                cls._validate_custom_task_completion(completion, progress_data, task.metadata['validation_rules'])
    
    @classmethod
    def _validate_custom_task_completion(cls, completion: TaskCompletion, 
                                       progress_data: Dict[str, Any], 
                                       validation_rules: Dict[str, Any]) -> None:
        """Validate custom task completion based on rules."""
        # Implement custom validation logic based on rules
        pass
    
    @classmethod
    def _handle_status_change_notifications(cls, completion: TaskCompletion, old_status: str) -> None:
        """Handle notifications for status changes."""
        if completion.status == 'COMPLETED':
            cls._send_task_completion_notification(completion)
        elif completion.status == 'PENDING_REVIEW':
            cls._send_task_review_notification(completion)
    
    @classmethod
    def _send_task_completion_notification(cls, completion: TaskCompletion) -> None:
        """Send notification for task completion."""
        # Implementation for completion notification
        pass
    
    @classmethod
    def _send_task_review_notification(cls, completion: TaskCompletion) -> None:
        """Send notification for task review."""
        # Implementation for review notification
        pass
    
    @classmethod
    def _award_task_completion_points(cls, completion: TaskCompletion) -> None:
        """Award points for task completion."""
        if completion.task.points_value > 0:
            # Implementation for points system
            pass
    
    @classmethod
    def _calculate_volunteer_task_stats(cls, completions: List[TaskCompletion]) -> Dict[str, Any]:
        """Calculate statistics for volunteer tasks."""
        if not completions:
            return {}
        
        total = len(completions)
        completed = len([c for c in completions if c.status == 'COMPLETED'])
        in_progress = len([c for c in completions if c.status == 'IN_PROGRESS'])
        overdue = len([c for c in completions if c.due_date and c.due_date < timezone.now() and c.status in ['NOT_STARTED', 'IN_PROGRESS']])
        
        return {
            'total_tasks': total,
            'completed_tasks': completed,
            'in_progress_tasks': in_progress,
            'overdue_tasks': overdue,
            'completion_rate': round(completed / total * 100, 2) if total > 0 else 0,
            'average_completion_time': cls._calculate_average_completion_time_for_completions(completions)
        }
    
    @classmethod
    def _serialize_task_completion(cls, completion: TaskCompletion) -> Dict[str, Any]:
        """Serialize TaskCompletion for API responses."""
        return {
            'id': completion.id,
            'task': cls._serialize_task(completion.task),
            'status': completion.status,
            'progress_percentage': completion.progress_percentage,
            'assigned_at': completion.assigned_at.isoformat() if completion.assigned_at else None,
            'due_date': completion.due_date.isoformat() if completion.due_date else None,
            'started_at': completion.started_at.isoformat() if completion.started_at else None,
            'completed_at': completion.completed_at.isoformat() if completion.completed_at else None,
            'time_spent': completion.time_spent,
            'notes': completion.notes,
            'assigned_by': completion.assigned_by.get_full_name() if completion.assigned_by else None
        }
    
    @classmethod
    def _serialize_task(cls, task: Task) -> Dict[str, Any]:
        """Serialize Task for API responses."""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'task_type': task.task_type,
            'priority': task.priority,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'estimated_duration': task.estimated_duration,
            'is_mandatory': task.is_mandatory,
            'points_value': task.points_value,
            'role_name': task.role.name if task.role else None,
            'event_name': task.event.name if task.event else None
        }
    
    @classmethod
    def _get_upcoming_deadlines(cls, completions: List[TaskCompletion]) -> List[Dict[str, Any]]:
        """Get upcoming task deadlines."""
        upcoming = []
        now = timezone.now()
        
        for completion in completions:
            if (completion.due_date and 
                completion.due_date > now and 
                completion.status in ['NOT_STARTED', 'IN_PROGRESS']):
                
                days_until_due = (completion.due_date - now).days
                upcoming.append({
                    'completion_id': completion.id,
                    'task_title': completion.task.title,
                    'due_date': completion.due_date.isoformat(),
                    'days_until_due': days_until_due,
                    'priority': completion.task.priority
                })
        
        return sorted(upcoming, key=lambda x: x['days_until_due'])[:5]
    
    @classmethod
    def _get_overdue_tasks(cls, completions: List[TaskCompletion]) -> List[Dict[str, Any]]:
        """Get overdue tasks."""
        overdue = []
        now = timezone.now()
        
        for completion in completions:
            if (completion.due_date and 
                completion.due_date < now and 
                completion.status in ['NOT_STARTED', 'IN_PROGRESS']):
                
                days_overdue = (now - completion.due_date).days
                overdue.append({
                    'completion_id': completion.id,
                    'task_title': completion.task.title,
                    'due_date': completion.due_date.isoformat(),
                    'days_overdue': days_overdue,
                    'priority': completion.task.priority
                })
        
        return sorted(overdue, key=lambda x: x['days_overdue'], reverse=True)
    
    @classmethod
    def _calculate_task_completion_stats(cls, completions) -> Dict[str, Any]:
        """Calculate completion statistics for a task."""
        total = completions.count()
        if total == 0:
            return {'total_assignments': 0}
        
        completed = completions.filter(status='COMPLETED').count()
        in_progress = completions.filter(status='IN_PROGRESS').count()
        pending_review = completions.filter(status='PENDING_REVIEW').count()
        
        return {
            'total_assignments': total,
            'completed': completed,
            'in_progress': in_progress,
            'pending_review': pending_review,
            'completion_rate': round(completed / total * 100, 2)
        }
    
    @classmethod
    def _calculate_role_task_stats(cls, role: Role) -> Dict[str, Any]:
        """Calculate task statistics for a role."""
        tasks = Task.objects.filter(role=role)
        completions = TaskCompletion.objects.filter(task__role=role)
        
        return {
            'total_tasks': tasks.count(),
            'total_assignments': completions.count(),
            'completion_rate': cls._calculate_overall_completion_rate(completions),
            'average_completion_time': cls._calculate_average_completion_time(completions)
        }
    
    # Analytics helper methods
    
    @classmethod
    def _calculate_overall_completion_rate(cls, completions_qs) -> float:
        """Calculate overall completion rate."""
        total = completions_qs.count()
        if total == 0:
            return 0.0
        
        completed = completions_qs.filter(status='COMPLETED').count()
        return round(completed / total * 100, 2)
    
    @classmethod
    def _calculate_average_completion_time(cls, completions_qs) -> Optional[float]:
        """Calculate average completion time in hours."""
        completed = completions_qs.filter(
            status='COMPLETED',
            started_at__isnull=False,
            completed_at__isnull=False
        )
        
        if not completed.exists():
            return None
        
        total_time = 0
        count = 0
        
        for completion in completed:
            if completion.time_spent:
                total_time += completion.time_spent
                count += 1
            elif completion.started_at and completion.completed_at:
                duration = completion.completed_at - completion.started_at
                total_time += duration.total_seconds() / 3600  # Convert to hours
                count += 1
        
        return round(total_time / count, 2) if count > 0 else None
    
    @classmethod
    def _calculate_average_completion_time_for_completions(cls, completions: List[TaskCompletion]) -> Optional[float]:
        """Calculate average completion time for a list of completions."""
        completed = [c for c in completions if c.status == 'COMPLETED']
        
        if not completed:
            return None
        
        total_time = 0
        count = 0
        
        for completion in completed:
            if completion.time_spent:
                total_time += completion.time_spent
                count += 1
            elif completion.started_at and completion.completed_at:
                duration = completion.completed_at - completion.started_at
                total_time += duration.total_seconds() / 3600
                count += 1
        
        return round(total_time / count, 2) if count > 0 else None
    
    @classmethod
    def _count_overdue_tasks(cls, completions_qs) -> int:
        """Count overdue tasks."""
        return completions_qs.filter(
            due_date__lt=timezone.now(),
            status__in=['NOT_STARTED', 'IN_PROGRESS']
        ).count()
    
    @classmethod
    def _get_task_distribution_by_type(cls, tasks_qs) -> Dict[str, int]:
        """Get task distribution by type."""
        return dict(
            tasks_qs.values('task_type')
            .annotate(count=Count('id'))
            .values_list('task_type', 'count')
        )
    
    @classmethod
    def _get_task_distribution_by_priority(cls, tasks_qs) -> Dict[str, int]:
        """Get task distribution by priority."""
        return dict(
            tasks_qs.values('priority')
            .annotate(count=Count('id'))
            .values_list('priority', 'count')
        )
    
    @classmethod
    def _get_completion_distribution_by_status(cls, completions_qs) -> Dict[str, int]:
        """Get completion distribution by status."""
        return dict(
            completions_qs.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
    
    @classmethod
    def _get_top_performing_volunteers(cls, completions_qs) -> List[Dict[str, Any]]:
        """Get top performing volunteers."""
        return list(
            completions_qs.filter(status='COMPLETED')
            .values('volunteer__user__first_name', 'volunteer__user__last_name')
            .annotate(
                completed_tasks=Count('id'),
                avg_completion_time=Avg('time_spent')
            )
            .order_by('-completed_tasks')[:10]
        )
    
    @classmethod
    def _get_completion_trends(cls, completions_qs) -> List[Dict[str, Any]]:
        """Get task completion trends over time."""
        # Implementation for completion trends
        return []
    
    @classmethod
    def _get_average_time_by_task_type(cls, completions_qs) -> Dict[str, float]:
        """Get average completion time by task type."""
        return dict(
            completions_qs.filter(
                status='COMPLETED',
                time_spent__isnull=False
            )
            .values('task__task_type')
            .annotate(avg_time=Avg('time_spent'))
            .values_list('task__task_type', 'avg_time')
        )
    
    @classmethod
    def _get_role_task_analysis(cls, tasks_qs, completions_qs) -> List[Dict[str, Any]]:
        """Get task analysis by role."""
        # Implementation for role analysis
        return []
    
    @classmethod
    def _identify_task_bottlenecks(cls, completions_qs) -> List[Dict[str, Any]]:
        """Identify task bottlenecks."""
        # Implementation for bottleneck identification
        return [] 