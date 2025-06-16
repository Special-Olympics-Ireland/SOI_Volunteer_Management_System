from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Task, TaskCompletion

User = get_user_model()


# Task Serializers

class TaskListSerializer(serializers.ModelSerializer):
    """Serializer for task list view with essential information"""
    
    role_name = serializers.CharField(source='role.name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    completion_rate = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'task_type', 'task_type_display',
            'category', 'priority', 'priority_display', 'status', 'status_display',
            'is_mandatory', 'requires_verification', 'is_active',
            'due_date', 'estimated_duration_minutes', 'role_name', 'event_name',
            'total_completions', 'verified_completions', 'completion_rate',
            'is_overdue', 'is_available', 'days_until_due', 'created_at'
        ]
    
    def get_completion_rate(self, obj):
        return obj.get_completion_rate()
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_is_available(self, obj):
        return obj.is_available()
    
    def get_days_until_due(self, obj):
        return obj.get_days_until_due()


class TaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed task view with all information"""
    
    role_name = serializers.CharField(source='role.name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    estimated_duration_display = serializers.CharField(source='get_estimated_duration_display', read_only=True)
    
    # Computed fields
    completion_rate = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()
    completion_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'task_type', 'task_type_display',
            'category', 'priority', 'priority_display', 'status', 'status_display',
            'is_mandatory', 'requires_verification', 'is_active',
            'due_date', 'estimated_duration_minutes', 'estimated_duration_display',
            'role', 'role_name', 'event', 'event_name',
            'instructions', 'resources_links', 'attachments',
            'validation_rules', 'acceptance_criteria',
            'total_completions', 'verified_completions', 'completion_rate',
            'send_reminders', 'reminder_days_before',
            'is_overdue', 'is_available', 'days_until_due',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'status_changed_at', 'status_changed_by', 'status_changed_by_name',
            'completion_stats'
        ]
    
    def get_completion_rate(self, obj):
        return obj.get_completion_rate()
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_is_available(self, obj):
        return obj.is_available()
    
    def get_days_until_due(self, obj):
        return obj.get_days_until_due()
    
    def get_completion_stats(self, obj):
        """Get completion statistics for this task"""
        completions = obj.completions.all()
        
        status_counts = {}
        for status_choice in TaskCompletion.CompletionStatus.choices:
            status_code = status_choice[0]
            status_counts[status_code] = completions.filter(status=status_code).count()
        
        return {
            'total_completions': completions.count(),
            'status_breakdown': status_counts,
            'pending_review': completions.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
            'pending_verification': completions.filter(status='APPROVED', requires_verification=True).count()
        }


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new tasks"""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'task_type', 'category', 'priority',
            'is_mandatory', 'requires_verification', 'is_active',
            'due_date', 'estimated_duration_minutes', 'role', 'event',
            'instructions', 'resources_links', 'attachments',
            'validation_rules', 'acceptance_criteria',
            'send_reminders', 'reminder_days_before'
        ]
    
    def validate(self, data):
        """Validate task creation data"""
        # Validate due date
        if data.get('due_date') and data['due_date'] <= timezone.now():
            raise serializers.ValidationError({
                'due_date': 'Due date must be in the future'
            })
        
        # Validate role and event consistency
        if data.get('role') and data.get('event'):
            if data['role'].event != data['event']:
                raise serializers.ValidationError({
                    'role': 'Role must belong to the specified event'
                })
        
        return data


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing tasks"""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'task_type', 'category', 'priority',
            'is_mandatory', 'requires_verification', 'is_active',
            'due_date', 'estimated_duration_minutes',
            'instructions', 'resources_links', 'attachments',
            'validation_rules', 'acceptance_criteria',
            'send_reminders', 'reminder_days_before'
        ]
    
    def validate(self, data):
        """Validate task update data"""
        # Validate due date
        if data.get('due_date') and data['due_date'] <= timezone.now():
            raise serializers.ValidationError({
                'due_date': 'Due date must be in the future'
            })
        
        return data


class TaskStatusSerializer(serializers.ModelSerializer):
    """Serializer for task status updates"""
    
    status_change_reason = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Task
        fields = ['status', 'is_active', 'status_change_reason']
    
    def update(self, instance, validated_data):
        """Update task status with tracking"""
        status_change_reason = validated_data.pop('status_change_reason', '')
        
        # Track status change
        if 'status' in validated_data and instance.status != validated_data['status']:
            instance.status_changed_at = timezone.now()
            instance.status_changed_by = self.context['request'].user
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class TaskStatsSerializer(serializers.Serializer):
    """Serializer for task statistics"""
    
    task_id = serializers.UUIDField(read_only=True)
    task_title = serializers.CharField(read_only=True)
    summary = serializers.DictField(read_only=True)
    status_breakdown = serializers.DictField(read_only=True)
    task_info = serializers.DictField(read_only=True)


class TaskAssignmentSerializer(serializers.Serializer):
    """Serializer for task assignments"""
    
    volunteer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of volunteer IDs to assign task to"
    )
    assignment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of assignment IDs to assign task to"
    )
    
    def validate(self, data):
        """Validate assignment data"""
        if not data.get('volunteer_ids') and not data.get('assignment_ids'):
            raise serializers.ValidationError(
                'Either volunteer_ids or assignment_ids must be provided'
            )
        return data


# TaskCompletion Serializers

class TaskCompletionListSerializer(serializers.ModelSerializer):
    """Serializer for task completion list view"""
    
    task_title = serializers.CharField(source='task.title', read_only=True)
    task_type = serializers.CharField(source='task.task_type', read_only=True)
    volunteer_name = serializers.CharField(source='volunteer.get_full_name', read_only=True)
    volunteer_email = serializers.CharField(source='volunteer.email', read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    completion_type_display = serializers.CharField(source='get_completion_type_display', read_only=True)
    time_spent_display = serializers.CharField(source='get_time_spent_display', read_only=True)
    
    # Computed fields
    is_complete = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskCompletion
        fields = [
            'id', 'task', 'task_title', 'task_type',
            'volunteer', 'volunteer_name', 'volunteer_email',
            'completion_type', 'completion_type_display',
            'status', 'status_display',
            'submitted_at', 'completed_at', 'verified_at',
            'time_spent_minutes', 'time_spent_display',
            'quality_score', 'requires_verification',
            'is_complete', 'is_overdue', 'created_at'
        ]
    
    def get_is_complete(self, obj):
        return obj.is_complete()
    
    def get_is_overdue(self, obj):
        if obj.task.due_date and obj.task.due_date < timezone.now():
            return obj.status not in ['APPROVED', 'VERIFIED', 'CANCELLED']
        return False


class TaskCompletionDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed task completion view"""
    
    task_title = serializers.CharField(source='task.title', read_only=True)
    task_description = serializers.CharField(source='task.description', read_only=True)
    volunteer_name = serializers.CharField(source='volunteer.get_full_name', read_only=True)
    volunteer_email = serializers.CharField(source='volunteer.email', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    completion_type_display = serializers.CharField(source='get_completion_type_display', read_only=True)
    time_spent_display = serializers.CharField(source='get_time_spent_display', read_only=True)
    
    # Computed fields
    is_complete = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    available_transitions = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskCompletion
        fields = [
            'id', 'task', 'task_title', 'task_description',
            'volunteer', 'volunteer_name', 'volunteer_email',
            'assignment', 'completion_type', 'completion_type_display',
            'status', 'status_display', 'completion_data',
            'submitted_at', 'completed_at', 'verified_at',
            'time_started', 'time_spent_minutes', 'time_spent_display',
            'requires_verification', 'verified_by', 'verified_by_name',
            'verification_notes', 'quality_score',
            'attachments', 'photos', 'feedback_from_volunteer',
            'revision_count', 'revision_notes',
            'status_changed_at', 'status_changed_by', 'status_changed_by_name',
            'status_change_reason', 'send_notifications',
            'is_complete', 'is_overdue', 'available_transitions',
            'created_at', 'updated_at'
        ]
    
    def get_is_complete(self, obj):
        return obj.is_complete()
    
    def get_is_overdue(self, obj):
        if obj.task.due_date and obj.task.due_date < timezone.now():
            return obj.status not in ['APPROVED', 'VERIFIED', 'CANCELLED']
        return False
    
    def get_available_transitions(self, obj):
        """Get available status transitions"""
        current_status = obj.status
        
        transitions = {
            'PENDING': ['SUBMITTED', 'CANCELLED'],
            'SUBMITTED': ['UNDER_REVIEW', 'APPROVED', 'REJECTED', 'REVISION_REQUIRED'],
            'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'REVISION_REQUIRED'],
            'APPROVED': ['VERIFIED'] if obj.requires_verification else [],
            'REJECTED': ['PENDING'],
            'REVISION_REQUIRED': ['SUBMITTED'],
            'VERIFIED': [],
            'CANCELLED': []
        }
        
        return transitions.get(current_status, [])


class TaskCompletionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new task completions"""
    
    class Meta:
        model = TaskCompletion
        fields = [
            'task', 'volunteer', 'assignment', 'completion_type',
            'completion_data', 'requires_verification',
            'send_notifications', 'notification_preferences'
        ]
    
    def validate(self, data):
        """Validate task completion creation"""
        # Check if completion already exists for this task/volunteer combination
        if TaskCompletion.objects.filter(
            task=data['task'],
            volunteer=data['volunteer']
        ).exists():
            raise serializers.ValidationError(
                'Task completion already exists for this volunteer and task'
            )
        
        # Validate completion data based on task type
        task = data['task']
        completion_data = data.get('completion_data', {})
        
        if task.task_type == Task.TaskType.PHOTO and not completion_data.get('photos'):
            raise serializers.ValidationError({
                'completion_data': 'Photo tasks require photo uploads'
            })
        
        return data


class TaskCompletionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating task completions"""
    
    class Meta:
        model = TaskCompletion
        fields = [
            'completion_data', 'attachments', 'photos', 'feedback_from_volunteer',
            'time_spent_minutes', 'send_notifications'
        ]
    
    def validate_completion_data(self, value):
        """Validate completion data based on task type"""
        if self.instance and self.instance.task:
            task = self.instance.task
            
            # Validate based on task type
            if task.task_type == Task.TaskType.PHOTO and not value.get('photos'):
                raise serializers.ValidationError(
                    'Photo tasks require photo uploads'
                )
            elif task.task_type == Task.TaskType.TEXT and not value.get('text_content'):
                raise serializers.ValidationError(
                    'Text tasks require text content'
                )
        
        return value


class TaskCompletionStatusSerializer(serializers.ModelSerializer):
    """Serializer for task completion status updates"""
    
    status_change_reason = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = TaskCompletion
        fields = ['status', 'status_change_reason']
    
    def validate_status(self, value):
        """Validate status transition"""
        if self.instance:
            current_status = self.instance.status
            
            # Define valid transitions
            valid_transitions = {
                'PENDING': ['SUBMITTED', 'CANCELLED'],
                'SUBMITTED': ['UNDER_REVIEW', 'APPROVED', 'REJECTED', 'REVISION_REQUIRED'],
                'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'REVISION_REQUIRED'],
                'APPROVED': ['VERIFIED'] if self.instance.requires_verification else [],
                'REJECTED': ['PENDING'],
                'REVISION_REQUIRED': ['SUBMITTED'],
                'VERIFIED': [],
                'CANCELLED': []
            }
            
            if value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f'Cannot transition from {current_status} to {value}'
                )
        
        return value
    
    def update(self, instance, validated_data):
        """Update status with tracking"""
        status_change_reason = validated_data.pop('status_change_reason', '')
        
        # Track status change
        if 'status' in validated_data and instance.status != validated_data['status']:
            instance.status_changed_at = timezone.now()
            instance.status_changed_by = self.context['request'].user
            instance.status_change_reason = status_change_reason
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class TaskCompletionWorkflowSerializer(serializers.Serializer):
    """Serializer for task completion workflow actions"""
    
    WORKFLOW_ACTIONS = [
        ('submit', 'Submit for Review'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('request_revision', 'Request Revision'),
        ('verify', 'Verify'),
        ('cancel', 'Cancel')
    ]
    
    action = serializers.ChoiceField(choices=WORKFLOW_ACTIONS)
    notes = serializers.CharField(required=False, allow_blank=True)
    quality_score = serializers.IntegerField(
        required=False, 
        min_value=1, 
        max_value=10,
        help_text="Quality score from 1-10 (for verification)"
    )
    
    def validate(self, data):
        """Validate workflow action"""
        completion = self.context.get('completion')
        action = data['action']
        
        if not completion:
            raise serializers.ValidationError('Completion context required')
        
        # Validate action is allowed for current status
        current_status = completion.status
        
        valid_actions = {
            'PENDING': ['submit', 'cancel'],
            'SUBMITTED': ['approve', 'reject', 'request_revision'],
            'UNDER_REVIEW': ['approve', 'reject', 'request_revision'],
            'APPROVED': ['verify'] if completion.requires_verification else [],
            'REJECTED': [],
            'REVISION_REQUIRED': ['submit'],
            'VERIFIED': [],
            'CANCELLED': []
        }
        
        if action not in valid_actions.get(current_status, []):
            raise serializers.ValidationError(
                f'Action "{action}" not allowed for status "{current_status}"'
            )
        
        # Verify action requires quality score
        if action == 'verify' and not data.get('quality_score'):
            raise serializers.ValidationError({
                'quality_score': 'Quality score required for verification'
            })
        
        return data


class TaskProgressSerializer(serializers.ModelSerializer):
    """Serializer for task completion progress tracking"""
    
    time_spent_display = serializers.CharField(source='get_time_spent_display', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskCompletion
        fields = [
            'id', 'time_started', 'time_spent_minutes', 'time_spent_display',
            'completion_data', 'feedback_from_volunteer', 'progress_percentage'
        ]
    
    def get_progress_percentage(self, obj):
        """Calculate progress percentage based on status"""
        status_progress = {
            'PENDING': 0,
            'SUBMITTED': 50,
            'UNDER_REVIEW': 75,
            'APPROVED': 90,
            'VERIFIED': 100,
            'REJECTED': 0,
            'REVISION_REQUIRED': 25,
            'CANCELLED': 0
        }
        return status_progress.get(obj.status, 0)


class TaskVerificationSerializer(serializers.ModelSerializer):
    """Serializer for task completion verification"""
    
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = TaskCompletion
        fields = [
            'requires_verification', 'verified_by', 'verified_by_name',
            'verified_at', 'verification_notes', 'quality_score'
        ]
        read_only_fields = ['verified_by', 'verified_at']
    
    def validate_quality_score(self, value):
        """Validate quality score range"""
        if value is not None and (value < 1 or value > 10):
            raise serializers.ValidationError(
                'Quality score must be between 1 and 10'
            )
        return value


class TaskCompletionBulkSerializer(serializers.Serializer):
    """Serializer for bulk task completion operations"""
    
    BULK_ACTIONS = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('verify', 'Verify'),
        ('send_notification', 'Send Notification')
    ]
    
    completion_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of completion IDs to perform action on"
    )
    action = serializers.ChoiceField(choices=BULK_ACTIONS)
    notes = serializers.CharField(required=False, allow_blank=True)
    quality_score = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        help_text="Quality score for verification actions"
    )
    
    def validate(self, data):
        """Validate bulk operation data"""
        if not data.get('completion_ids'):
            raise serializers.ValidationError({
                'completion_ids': 'At least one completion ID is required'
            })
        
        # Verify action requires quality score
        if data['action'] == 'verify' and not data.get('quality_score'):
            raise serializers.ValidationError({
                'quality_score': 'Quality score required for verification actions'
            })
        
        return data 