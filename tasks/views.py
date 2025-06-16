from django.shortcuts import render
from rest_framework import generics, viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.core.exceptions import ValidationError

from .models import Task, TaskCompletion
from .serializers import (
    TaskListSerializer, TaskDetailSerializer, TaskCreateSerializer,
    TaskUpdateSerializer, TaskStatusSerializer, TaskStatsSerializer,
    TaskCompletionListSerializer, TaskCompletionDetailSerializer,
    TaskCompletionCreateSerializer, TaskCompletionUpdateSerializer,
    TaskCompletionStatusSerializer, TaskCompletionWorkflowSerializer,
    TaskCompletionBulkSerializer, TaskAssignmentSerializer,
    TaskProgressSerializer, TaskVerificationSerializer
)
from .permissions import TaskManagementPermission
from accounts.permissions import CanManageEvents
from common.permissions import TaskManagementPermission as CommonTaskPermission
from common.audit_service import AdminAuditService
from .task_management_service import TaskManagementService

# Initialize audit service
audit_service = AdminAuditService()


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Task management with full CRUD operations and completion tracking.
    
    Provides:
    - List tasks with filtering and search
    - Create new tasks
    - Retrieve task details
    - Update tasks
    - Delete tasks
    - Custom actions for status management, statistics, and assignments
    """
    queryset = Task.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'task_type', 'category', 'priority', 'status', 'is_mandatory',
        'requires_verification', 'role', 'event', 'created_by'
    ]
    search_fields = [
        'title', 'description', 'instructions', 'category',
        'role__name', 'event__name'
    ]
    ordering_fields = [
        'title', 'priority', 'due_date', 'estimated_duration_minutes',
        'total_completions', 'verified_completions', 'created_at'
    ]
    ordering = ['priority', 'due_date', 'title']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        elif self.action == 'status':
            return TaskStatusSerializer
        elif self.action == 'stats':
            return TaskStatsSerializer
        elif self.action == 'assignments':
            return TaskAssignmentSerializer
        else:
            return TaskDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [CommonTaskPermission]
        elif self.action in ['status', 'assignments', 'bulk_operations']:
            permission_classes = [CommonTaskPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return filtered queryset based on user permissions"""
        queryset = Task.objects.select_related(
            'role', 'event', 'created_by'
        ).prefetch_related(
            'completions',
            'role__assignments'
        )
        
        # Filter based on user permissions
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        
        # Volunteers can only see tasks assigned to them
        if hasattr(user, 'volunteer_profile'):
            # Get tasks through assignments
            from events.models import Assignment
            assigned_roles = Assignment.objects.filter(
                volunteer=user,
                status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']
            ).values_list('role', flat=True)
            return queryset.filter(role__in=assigned_roles, status=Task.TaskStatus.ACTIVE)
        
        # Staff can see tasks they manage
        if user.is_staff:
            # Event managers can see tasks in their events
            if hasattr(user, 'managed_events'):
                managed_events = user.managed_events.all()
                if managed_events.exists():
                    queryset = queryset.filter(event__in=managed_events)
            
            # Role coordinators can see tasks for their roles
            if hasattr(user, 'coordinated_roles'):
                coordinated_roles = user.coordinated_roles.all()
                if coordinated_roles.exists():
                    queryset = queryset.filter(role__in=coordinated_roles)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create task with audit logging"""
        task = serializer.save(created_by=self.request.user)
        
        # Log task creation
        audit_service.log_event_management_operation(
            operation='TASK_CREATED',
            user=self.request.user,
            event=task.event,
            details={
                'task_id': str(task.id),
                'task_title': task.title,
                'task_type': task.task_type,
                'category': task.category,
                'priority': task.priority,
                'role_name': task.role.name if task.role else None,
                'event_name': task.event.name if task.event else None,
                'is_mandatory': task.is_mandatory,
                'requires_verification': task.requires_verification,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update task with audit logging"""
        old_data = {
            'status': serializer.instance.status,
            'priority': serializer.instance.priority,
            'due_date': serializer.instance.due_date,
            'is_active': serializer.instance.is_active
        }
        
        task = serializer.save()
        
        # Log significant changes
        changes = {}
        for field, old_value in old_data.items():
            new_value = getattr(task, field)
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
        
        if changes:
            audit_service.log_event_management_operation(
                operation='TASK_UPDATED',
                user=self.request.user,
                event=task.event,
                details={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'role_name': task.role.name if task.role else None,
                    'event_name': task.event.name if task.event else None,
                    'changes': changes,
                    'via_api': True
                }
            )
    
    def perform_destroy(self, instance):
        """Delete task with audit logging"""
        audit_service.log_event_management_operation(
            operation='TASK_DELETED',
            user=self.request.user,
            event=instance.event,
            details={
                'task_id': str(instance.id),
                'task_title': instance.title,
                'task_type': instance.task_type,
                'role_name': instance.role.name if instance.role else None,
                'event_name': instance.event.name if instance.event else None,
                'total_completions': instance.total_completions,
                'via_api': True
            }
        )
        
        instance.delete()
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def status(self, request, pk=None):
        """
        Get or update task status.
        
        GET: Returns current status and availability
        PUT/PATCH: Updates status with validation
        """
        task = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'task_id': str(task.id),
                'title': task.title,
                'current_status': task.status,
                'status_display': task.get_status_display(),
                'is_active': task.is_active,
                'is_available': task.is_available(),
                'is_overdue': task.is_overdue(),
                'status_changed_at': task.status_changed_at,
                'status_changed_by': task.status_changed_by.get_full_name() if task.status_changed_by else None,
                'completion_info': {
                    'total_completions': task.total_completions,
                    'verified_completions': task.verified_completions,
                    'completion_rate': task.get_completion_rate()
                }
            })
        
        else:
            # Update status
            serializer = TaskStatusSerializer(
                task, 
                data=request.data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                old_status = task.status
                serializer.save()
                
                # Log status change
                audit_service.log_event_management_operation(
                    operation='TASK_STATUS_CHANGED',
                    user=request.user,
                    event=task.event,
                    details={
                        'task_id': str(task.id),
                        'task_title': task.title,
                        'role_name': task.role.name if task.role else None,
                        'event_name': task.event.name if task.event else None,
                        'old_status': old_status,
                        'new_status': task.status,
                        'reason': request.data.get('status_change_reason', ''),
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get comprehensive task statistics"""
        task = self.get_object()
        
        # Get all completions for this task
        completions = task.completions.all()
        
        # Calculate statistics
        total_completions = completions.count()
        status_counts = {}
        for status_choice in TaskCompletion.CompletionStatus.choices:
            status_code = status_choice[0]
            status_counts[status_code] = completions.filter(status=status_code).count()
        
        # Time statistics
        completed_completions = completions.filter(
            status__in=['APPROVED', 'VERIFIED'],
            time_spent_minutes__isnull=False
        )
        
        avg_time_spent = completed_completions.aggregate(
            avg_time=Avg('time_spent_minutes')
        )['avg_time']
        
        total_time_spent = completed_completions.aggregate(
            total_time=Sum('time_spent_minutes')
        )['total_time']
        
        # Quality statistics
        quality_scores = completions.filter(
            quality_score__isnull=False
        ).values_list('quality_score', flat=True)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        return Response({
            'task_id': str(task.id),
            'task_title': task.title,
            'summary': {
                'total_completions': total_completions,
                'verified_completions': task.verified_completions,
                'completion_rate': task.get_completion_rate(),
                'average_time_spent_minutes': round(avg_time_spent, 1) if avg_time_spent else None,
                'total_time_spent_minutes': total_time_spent or 0,
                'average_quality_score': round(avg_quality, 1) if avg_quality else None
            },
            'status_breakdown': status_counts,
            'task_info': {
                'task_type': task.task_type,
                'category': task.category,
                'priority': task.priority,
                'is_mandatory': task.is_mandatory,
                'requires_verification': task.requires_verification,
                'estimated_duration_minutes': task.estimated_duration_minutes,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'is_overdue': task.is_overdue()
            }
        })
    
    @action(detail=True, methods=['get', 'post'])
    def assignments(self, request, pk=None):
        """
        Get or create task assignments for volunteers.
        
        GET: List current assignments
        POST: Create new assignments
        """
        task = self.get_object()
        
        if request.method == 'GET':
            # Get all completions (assignments) for this task
            completions = task.completions.select_related(
                'volunteer', 'assignment'
            ).order_by('-created_at')
            
            serializer = TaskCompletionListSerializer(completions, many=True, context={'request': request})
            
            return Response({
                'task_id': str(task.id),
                'task_title': task.title,
                'total_assignments': completions.count(),
                'assignments': serializer.data
            })
        
        else:
            # Create new assignments
            volunteer_ids = request.data.get('volunteer_ids', [])
            assignment_ids = request.data.get('assignment_ids', [])
            
            if not volunteer_ids and not assignment_ids:
                return Response({
                    'error': 'Either volunteer_ids or assignment_ids must be provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                if volunteer_ids:
                    # Assign to specific volunteers
                    results = TaskManagementService.bulk_assign_tasks(
                        [str(task.id)], volunteer_ids, request.user
                    )
                else:
                    # Assign to volunteers through their assignments
                    from events.models import Assignment
                    assignments = Assignment.objects.filter(
                        id__in=assignment_ids
                    ).select_related('volunteer')
                    
                    volunteer_ids = [str(assignment.volunteer.id) for assignment in assignments]
                    results = TaskManagementService.bulk_assign_tasks(
                        [str(task.id)], volunteer_ids, request.user
                    )
                
                # Log bulk assignment
                audit_service.log_event_management_operation(
                    operation='TASK_BULK_ASSIGNED',
                    user=request.user,
                    event=task.event,
                    details={
                        'task_id': str(task.id),
                        'task_title': task.title,
                        'total_assigned': results['total_successful'],
                        'total_failed': results['total_failed'],
                        'via_api': True
                    }
                )
                
                return Response(results)
                
            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get tasks filtered by role"""
        role_id = request.query_params.get('role_id')
        if not role_id:
            return Response(
                {'error': 'role_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tasks = self.get_queryset().filter(role_id=role_id)
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get tasks filtered by event"""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tasks = self.get_queryset().filter(event_id=event_id)
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def mandatory(self, request):
        """Get mandatory tasks"""
        tasks = self.get_queryset().filter(is_mandatory=True, is_active=True)
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue tasks"""
        tasks = self.get_queryset().filter(
            due_date__lt=timezone.now(),
            is_active=True
        ).order_by('due_date')
        
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def high_priority(self, request):
        """Get high priority tasks"""
        tasks = self.get_queryset().filter(
            priority='HIGH',
            is_active=True
        ).order_by('due_date')
        
        serializer = TaskListSerializer(tasks, many=True, context={'request': request})
        return Response(serializer.data)


class TaskCompletionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TaskCompletion management with full CRUD operations and status workflows.
    
    Provides:
    - List completions with filtering and search
    - Create new completions
    - Retrieve completion details
    - Update completions
    - Delete completions
    - Custom actions for status workflows, verification, and progress tracking
    """
    queryset = TaskCompletion.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'task', 'volunteer', 'assignment', 'completion_type', 'status',
        'requires_verification', 'verified_by', 'submitted_at', 'completed_at'
    ]
    search_fields = [
        'task__title', 'volunteer__first_name', 'volunteer__last_name',
        'volunteer__email', 'verification_notes', 'notes'
    ]
    ordering_fields = [
        'created_at', 'submitted_at', 'completed_at', 'verified_at',
        'quality_score', 'time_spent_minutes'
    ]
    ordering = ['-created_at', 'task__priority']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TaskCompletionListSerializer
        elif self.action == 'create':
            return TaskCompletionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskCompletionUpdateSerializer
        elif self.action == 'status':
            return TaskCompletionStatusSerializer
        elif self.action == 'workflow':
            return TaskCompletionWorkflowSerializer
        elif self.action == 'progress':
            return TaskProgressSerializer
        elif self.action == 'verification':
            return TaskVerificationSerializer
        elif self.action == 'bulk_operations':
            return TaskCompletionBulkSerializer
        else:
            return TaskCompletionDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]  # Volunteers can manage their own
        elif self.action in ['status', 'workflow', 'verification', 'bulk_operations']:
            permission_classes = [CommonTaskPermission]  # Staff only
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return filtered queryset based on user permissions"""
        queryset = TaskCompletion.objects.select_related(
            'task', 'volunteer', 'assignment', 'verified_by'
        ).prefetch_related(
            'task__role',
            'task__event'
        )
        
        # Filter based on user permissions
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        
        # Volunteers can only see their own completions
        if hasattr(user, 'volunteer_profile'):
            return queryset.filter(volunteer=user)
        
        # Staff can see completions they manage
        if user.is_staff:
            # Event managers can see completions in their events
            if hasattr(user, 'managed_events'):
                managed_events = user.managed_events.all()
                if managed_events.exists():
                    queryset = queryset.filter(task__event__in=managed_events)
            
            # Role coordinators can see completions for their roles
            if hasattr(user, 'coordinated_roles'):
                coordinated_roles = user.coordinated_roles.all()
                if coordinated_roles.exists():
                    queryset = queryset.filter(task__role__in=coordinated_roles)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create completion with audit logging"""
        completion = serializer.save()
        
        # Log completion creation
        audit_service.log_event_management_operation(
            operation='TASK_COMPLETION_CREATED',
            user=self.request.user,
            event=completion.task.event,
            details={
                'completion_id': str(completion.id),
                'task_title': completion.task.title,
                'volunteer_name': completion.volunteer.get_full_name(),
                'completion_type': completion.completion_type,
                'status': completion.status,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update completion with audit logging"""
        old_data = {
            'status': serializer.instance.status,
            'completion_data': serializer.instance.completion_data,
            'time_spent_minutes': serializer.instance.time_spent_minutes
        }
        
        completion = serializer.save()
        
        # Log significant changes
        changes = {}
        for field, old_value in old_data.items():
            new_value = getattr(completion, field)
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
        
        if changes:
            audit_service.log_event_management_operation(
                operation='TASK_COMPLETION_UPDATED',
                user=self.request.user,
                event=completion.task.event,
                details={
                    'completion_id': str(completion.id),
                    'task_title': completion.task.title,
                    'volunteer_name': completion.volunteer.get_full_name(),
                    'changes': changes,
                    'via_api': True
                }
            )
    
    def perform_destroy(self, instance):
        """Delete completion with audit logging"""
        audit_service.log_event_management_operation(
            operation='TASK_COMPLETION_DELETED',
            user=self.request.user,
            event=instance.task.event,
            details={
                'completion_id': str(instance.id),
                'task_title': instance.task.title,
                'volunteer_name': instance.volunteer.get_full_name(),
                'status': instance.status,
                'via_api': True
            }
        )
        
        instance.delete()
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def status(self, request, pk=None):
        """
        Get or update completion status with workflow validation.
        
        GET: Returns current status and available transitions
        PUT/PATCH: Updates status with workflow validation
        """
        completion = self.get_object()
        
        if request.method == 'GET':
            # Return current status and available transitions
            available_transitions = self._get_available_status_transitions(completion)
            
            return Response({
                'completion_id': str(completion.id),
                'task_title': completion.task.title,
                'volunteer_name': completion.volunteer.get_full_name(),
                'current_status': completion.status,
                'status_display': completion.get_status_display(),
                'status_changed_at': completion.status_changed_at,
                'status_changed_by': completion.status_changed_by.get_full_name() if completion.status_changed_by else None,
                'available_transitions': available_transitions,
                'requires_verification': completion.requires_verification,
                'is_complete': completion.is_complete(),
                'workflow_info': {
                    'can_submit': completion.status == completion.CompletionStatus.PENDING,
                    'can_approve': completion.status in [completion.CompletionStatus.SUBMITTED, completion.CompletionStatus.UNDER_REVIEW],
                    'can_verify': completion.status == completion.CompletionStatus.APPROVED and completion.requires_verification,
                    'can_reject': completion.status in [completion.CompletionStatus.SUBMITTED, completion.CompletionStatus.UNDER_REVIEW]
                }
            })
        
        else:
            # Update status
            serializer = TaskCompletionStatusSerializer(
                completion, 
                data=request.data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                old_status = completion.status
                serializer.save()
                
                # Log status change
                audit_service.log_event_management_operation(
                    operation='TASK_COMPLETION_STATUS_CHANGED',
                    user=request.user,
                    event=completion.task.event,
                    details={
                        'completion_id': str(completion.id),
                        'task_title': completion.task.title,
                        'volunteer_name': completion.volunteer.get_full_name(),
                        'old_status': old_status,
                        'new_status': completion.status,
                        'reason': request.data.get('status_change_reason', ''),
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def workflow(self, request, pk=None):
        """
        Execute workflow actions on completion.
        
        Supported actions: submit, approve, reject, request_revision, verify, cancel
        """
        completion = self.get_object()
        
        serializer = TaskCompletionWorkflowSerializer(
            data=request.data,
            context={'request': request, 'completion': completion}
        )
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            quality_score = serializer.validated_data.get('quality_score')
            
            try:
                # Execute workflow action
                if action == 'submit':
                    completion.submit(submitted_by=request.user)
                elif action == 'approve':
                    completion.approve(approved_by=request.user, notes=notes)
                elif action == 'reject':
                    completion.reject(rejected_by=request.user, reason=notes)
                elif action == 'request_revision':
                    completion.request_revision(requested_by=request.user, notes=notes)
                elif action == 'verify':
                    completion.verify(verified_by=request.user, notes=notes, quality_score=quality_score)
                elif action == 'cancel':
                    completion.cancel(cancelled_by=request.user, reason=notes)
                
                # Log workflow action
                audit_service.log_event_management_operation(
                    operation=f'TASK_COMPLETION_{action.upper()}',
                    user=request.user,
                    event=completion.task.event,
                    details={
                        'completion_id': str(completion.id),
                        'task_title': completion.task.title,
                        'volunteer_name': completion.volunteer.get_full_name(),
                        'action': action,
                        'notes': notes,
                        'quality_score': quality_score,
                        'new_status': completion.status,
                        'via_api': True
                    }
                )
                
                return Response({
                    'success': True,
                    'message': f'Task completion {action} successful',
                    'completion_id': str(completion.id),
                    'new_status': completion.status,
                    'status_display': completion.get_status_display()
                })
                
            except ValidationError as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def progress(self, request, pk=None):
        """
        Get or update completion progress.
        
        Handles progress tracking, time spent, and completion data.
        """
        completion = self.get_object()
        
        if request.method == 'GET':
            serializer = TaskProgressSerializer(completion)
            return Response(serializer.data)
        
        else:
            serializer = TaskProgressSerializer(
                completion,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                
                # Log progress update
                audit_service.log_event_management_operation(
                    operation='TASK_COMPLETION_PROGRESS_UPDATED',
                    user=request.user,
                    event=completion.task.event,
                    details={
                        'completion_id': str(completion.id),
                        'task_title': completion.task.title,
                        'volunteer_name': completion.volunteer.get_full_name(),
                        'time_spent_minutes': completion.time_spent_minutes,
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None):
        """Start work on task completion"""
        completion = self.get_object()
        
        if completion.time_started:
            return Response({
                'error': 'Work already started on this task'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        completion.start_work()
        
        # Log work start
        audit_service.log_event_management_operation(
            operation='TASK_COMPLETION_WORK_STARTED',
            user=request.user,
            event=completion.task.event,
            details={
                'completion_id': str(completion.id),
                'task_title': completion.task.title,
                'volunteer_name': completion.volunteer.get_full_name(),
                'started_at': completion.time_started.isoformat(),
                'via_api': True
            }
        )
        
        return Response({
            'success': True,
            'message': 'Work started on task',
            'started_at': completion.time_started
        })
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def verification(self, request, pk=None):
        """
        Get or update verification information.
        
        Handles verification notes, quality scores, and verification status.
        """
        completion = self.get_object()
        
        if request.method == 'GET':
            serializer = TaskVerificationSerializer(completion)
            return Response(serializer.data)
        
        else:
            serializer = TaskVerificationSerializer(
                completion,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                
                # Log verification update
                audit_service.log_event_management_operation(
                    operation='TASK_COMPLETION_VERIFICATION_UPDATED',
                    user=request.user,
                    event=completion.task.event,
                    details={
                        'completion_id': str(completion.id),
                        'task_title': completion.task.title,
                        'volunteer_name': completion.volunteer.get_full_name(),
                        'verified_by': completion.verified_by.get_full_name() if completion.verified_by else None,
                        'quality_score': completion.quality_score,
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on multiple completions.
        
        Supported actions: approve, reject, verify, send_notification
        """
        serializer = TaskCompletionBulkSerializer(data=request.data)
        
        if serializer.is_valid():
            completion_ids = serializer.validated_data['completion_ids']
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            
            completions = TaskCompletion.objects.filter(id__in=completion_ids)
            
            if completions.count() != len(completion_ids):
                return Response({
                    'error': 'Some completion IDs were not found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results = {
                'total_requested': len(completion_ids),
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for completion in completions:
                try:
                    if action == 'approve':
                        completion.approve(approved_by=request.user, notes=notes)
                    elif action == 'reject':
                        completion.reject(rejected_by=request.user, reason=notes)
                    elif action == 'verify':
                        completion.verify(verified_by=request.user, notes=notes)
                    elif action == 'send_notification':
                        # Would integrate with notification system
                        pass
                    
                    results['successful'] += 1
                    
                except ValidationError as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'completion_id': str(completion.id),
                        'task_title': completion.task.title,
                        'volunteer_name': completion.volunteer.get_full_name(),
                        'error': str(e)
                    })
            
            # Log bulk operation
            audit_service.log_event_management_operation(
                operation=f'TASK_COMPLETION_BULK_{action.upper()}',
                user=request.user,
                details={
                    'action': action,
                    'total_requested': results['total_requested'],
                    'successful': results['successful'],
                    'failed': results['failed'],
                    'notes': notes,
                    'via_api': True
                }
            )
            
            return Response(results)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_volunteer(self, request):
        """Get completions filtered by volunteer"""
        volunteer_id = request.query_params.get('volunteer_id')
        if not volunteer_id:
            return Response(
                {'error': 'volunteer_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        completions = self.get_queryset().filter(volunteer_id=volunteer_id)
        serializer = TaskCompletionListSerializer(completions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_task(self, request):
        """Get completions filtered by task"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        completions = self.get_queryset().filter(task_id=task_id)
        serializer = TaskCompletionListSerializer(completions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get completions pending review"""
        completions = self.get_queryset().filter(
            status__in=['SUBMITTED', 'UNDER_REVIEW']
        ).order_by('submitted_at')
        
        serializer = TaskCompletionListSerializer(completions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_verification(self, request):
        """Get completions pending verification"""
        completions = self.get_queryset().filter(
            status='APPROVED',
            requires_verification=True
        ).order_by('completed_at')
        
        serializer = TaskCompletionListSerializer(completions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue completions"""
        from django.utils import timezone
        today = timezone.now()
        
        completions = self.get_queryset().filter(
            task__due_date__lt=today,
            status__in=['PENDING', 'SUBMITTED', 'UNDER_REVIEW']
        ).order_by('task__due_date')
        
        serializer = TaskCompletionListSerializer(completions, many=True, context={'request': request})
        return Response(serializer.data)
    
    def _get_available_status_transitions(self, completion):
        """Get available status transitions for completion"""
        current_status = completion.status
        
        transitions = {
            'PENDING': ['SUBMITTED', 'CANCELLED'],
            'SUBMITTED': ['UNDER_REVIEW', 'APPROVED', 'REJECTED', 'REVISION_REQUIRED'],
            'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'REVISION_REQUIRED'],
            'APPROVED': ['VERIFIED'] if completion.requires_verification else [],
            'REJECTED': ['PENDING'],
            'REVISION_REQUIRED': ['SUBMITTED'],
            'VERIFIED': [],
            'CANCELLED': []
        }
        
        return transitions.get(current_status, [])


# Additional Task Management API Views

class TaskStatsView(generics.GenericAPIView):
    """Get comprehensive task statistics and analytics"""
    permission_classes = [CommonTaskPermission]
    serializer_class = TaskStatsSerializer
    
    def get(self, request):
        """
        Get comprehensive task statistics.
        
        Provides counts by status, type, priority, and completion metrics.
        """
        # Get query parameters for filtering
        event_id = request.query_params.get('event_id')
        role_id = request.query_params.get('role_id')
        volunteer_id = request.query_params.get('volunteer_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Base queryset
        task_queryset = Task.objects.all()
        completion_queryset = TaskCompletion.objects.all()
        
        # Apply filters
        if event_id:
            task_queryset = task_queryset.filter(event_id=event_id)
            completion_queryset = completion_queryset.filter(task__event_id=event_id)
        if role_id:
            task_queryset = task_queryset.filter(role_id=role_id)
            completion_queryset = completion_queryset.filter(task__role_id=role_id)
        if volunteer_id:
            completion_queryset = completion_queryset.filter(volunteer_id=volunteer_id)
        if date_from:
            task_queryset = task_queryset.filter(created_at__gte=date_from)
            completion_queryset = completion_queryset.filter(created_at__gte=date_from)
        if date_to:
            task_queryset = task_queryset.filter(created_at__lte=date_to)
            completion_queryset = completion_queryset.filter(created_at__lte=date_to)
        
        # Calculate task statistics
        total_tasks = task_queryset.count()
        active_tasks = task_queryset.filter(status=Task.TaskStatus.ACTIVE).count()
        overdue_tasks = task_queryset.filter(
            due_date__lt=timezone.now(),
            status=Task.TaskStatus.ACTIVE
        ).count()
        
        # Task type breakdown
        type_counts = {}
        for type_choice in Task.TaskType.choices:
            type_code = type_choice[0]
            type_counts[type_code] = task_queryset.filter(task_type=type_code).count()
        
        # Priority breakdown
        priority_counts = {}
        for priority_choice in Task.Priority.choices:
            priority_code = priority_choice[0]
            priority_counts[priority_code] = task_queryset.filter(priority=priority_code).count()
        
        # Calculate completion statistics
        total_completions = completion_queryset.count()
        
        # Status breakdown
        status_counts = {}
        for status_choice in TaskCompletion.CompletionStatus.choices:
            status_code = status_choice[0]
            status_counts[status_code] = completion_queryset.filter(status=status_code).count()
        
        # Performance metrics
        completed_completions = completion_queryset.filter(
            status__in=['APPROVED', 'VERIFIED']
        )
        
        avg_time_spent = completed_completions.aggregate(
            avg_time=Avg('time_spent_minutes')
        )['avg_time']
        
        avg_quality_score = completion_queryset.filter(
            quality_score__isnull=False
        ).aggregate(
            avg_quality=Avg('quality_score')
        )['avg_quality']
        
        # Verification metrics
        pending_verification = completion_queryset.filter(
            status='APPROVED',
            requires_verification=True
        ).count()
        
        verified_completions = completion_queryset.filter(
            status='VERIFIED'
        ).count()
        
        return Response({
            'task_summary': {
                'total_tasks': total_tasks,
                'active_tasks': active_tasks,
                'overdue_tasks': overdue_tasks,
                'completion_rate': round(completed_completions.count() / total_completions * 100, 1) if total_completions > 0 else 0
            },
            'completion_summary': {
                'total_completions': total_completions,
                'completed_completions': completed_completions.count(),
                'pending_verification': pending_verification,
                'verified_completions': verified_completions,
                'average_time_spent_minutes': round(avg_time_spent, 1) if avg_time_spent else None,
                'average_quality_score': round(avg_quality_score, 1) if avg_quality_score else None
            },
            'task_type_breakdown': type_counts,
            'priority_breakdown': priority_counts,
            'completion_status_breakdown': status_counts,
            'filters_applied': {
                'event_id': event_id,
                'role_id': role_id,
                'volunteer_id': volunteer_id,
                'date_from': date_from,
                'date_to': date_to
            }
        })
