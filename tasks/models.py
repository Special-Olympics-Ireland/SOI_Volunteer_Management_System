import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
import json

User = get_user_model()


class Task(models.Model):
    """
    Task model for managing role-specific tasks with dynamic task types.
    Supports checkbox completion, photo upload, text submission, and custom fields.
    Provides comprehensive task management with due dates, priorities, and validation.
    """
    
    class TaskType(models.TextChoices):
        CHECKBOX = 'CHECKBOX', _('Checkbox Completion')
        PHOTO = 'PHOTO', _('Photo Upload')
        TEXT = 'TEXT', _('Text Submission')
        CUSTOM = 'CUSTOM', _('Custom Field')
    
    class TaskStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        ARCHIVED = 'ARCHIVED', _('Archived')
    
    class PriorityLevel(models.TextChoices):
        LOW = 'LOW', _('Low Priority')
        NORMAL = 'NORMAL', _('Normal Priority')
        HIGH = 'HIGH', _('High Priority')
        URGENT = 'URGENT', _('Urgent')
        CRITICAL = 'CRITICAL', _('Critical')
    
    class TaskCategory(models.TextChoices):
        TRAINING = 'TRAINING', _('Training & Certification')
        DOCUMENTATION = 'DOCUMENTATION', _('Documentation')
        VERIFICATION = 'VERIFICATION', _('Verification & Validation')
        PREPARATION = 'PREPARATION', _('Event Preparation')
        COMPLIANCE = 'COMPLIANCE', _('Compliance & Safety')
        COMMUNICATION = 'COMMUNICATION', _('Communication')
        EQUIPMENT = 'EQUIPMENT', _('Equipment & Supplies')
        REPORTING = 'REPORTING', _('Reporting & Feedback')
        OTHER = 'OTHER', _('Other')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Task relationships
    role = models.ForeignKey(
        'events.Role',
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text=_('Role this task is associated with')
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text=_('Event this task belongs to')
    )
    venue = models.ForeignKey(
        'events.Venue',
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True,
        help_text=_('Venue this task is specific to (optional)')
    )
    
    # Task definition
    title = models.CharField(
        max_length=200,
        help_text=_('Task title')
    )
    description = models.TextField(
        help_text=_('Detailed task description')
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Brief task summary for lists')
    )
    
    # Task type and configuration
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.CHECKBOX,
        help_text=_('Type of task')
    )
    task_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Task-specific configuration based on task type')
    )
    
    # Task categorization and priority
    category = models.CharField(
        max_length=20,
        choices=TaskCategory.choices,
        default=TaskCategory.OTHER,
        help_text=_('Task category')
    )
    priority = models.CharField(
        max_length=20,
        choices=PriorityLevel.choices,
        default=PriorityLevel.NORMAL,
        help_text=_('Task priority level')
    )
    
    # Status and lifecycle
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.DRAFT,
        help_text=_('Current task status')
    )
    
    # Scheduling and deadlines
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When task becomes available')
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Task due date')
    )
    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],  # Max 24 hours
        help_text=_('Estimated time to complete task (in minutes)')
    )
    
    # Assignment and requirements
    is_mandatory = models.BooleanField(
        default=False,
        help_text=_('Whether this task is mandatory for the role')
    )
    requires_verification = models.BooleanField(
        default=False,
        help_text=_('Whether task completion requires staff verification')
    )
    verification_instructions = models.TextField(
        blank=True,
        help_text=_('Instructions for staff verification')
    )
    
    # Prerequisites and dependencies
    prerequisite_tasks = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='dependent_tasks',
        help_text=_('Tasks that must be completed before this one')
    )
    
    # Completion tracking
    total_completions = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of completions')
    )
    verified_completions = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of verified completions')
    )
    
    # Notification and reminder settings
    send_reminders = models.BooleanField(
        default=True,
        help_text=_('Send reminder notifications for this task')
    )
    reminder_days_before = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text=_('Days before due date to send reminders')
    )
    
    # Content and resources
    instructions = models.TextField(
        blank=True,
        help_text=_('Detailed instructions for completing the task')
    )
    resources_links = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Links to resources, documents, or training materials')
    )
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text=_('File attachments for the task')
    )
    
    # Validation and acceptance criteria
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Validation rules for task completion')
    )
    acceptance_criteria = models.TextField(
        blank=True,
        help_text=_('Criteria for accepting task completion')
    )
    
    # Audit and management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        help_text=_('User who created this task')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status change tracking
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When status was last changed')
    )
    status_changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changed_tasks',
        help_text=_('User who last changed the status')
    )
    status_change_reason = models.TextField(
        blank=True,
        help_text=_('Reason for status change')
    )
    
    # Display and ordering
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_('Order for displaying tasks')
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Whether to feature this task prominently')
    )
    
    class Meta:
        db_table = 'tasks_task'
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
        ordering = ['display_order', 'priority', 'due_date', 'title']
        indexes = [
            models.Index(fields=['role', 'status']),
            models.Index(fields=['event', 'status']),
            models.Index(fields=['venue', 'status']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['category', 'priority']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['is_mandatory', 'status']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_date__lte=models.F('due_date')) | 
                      models.Q(start_date__isnull=True) | 
                      models.Q(due_date__isnull=True),
                name='task_start_before_due_date'
            ),
            models.CheckConstraint(
                check=models.Q(verified_completions__lte=models.F('total_completions')),
                name='task_verified_not_exceed_total'
            ),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_task_type_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to handle status changes and validation"""
        # Track status changes (only for existing objects)
        if self.pk:
            try:
                old_instance = Task.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.status_changed_at = timezone.now()
            except Task.DoesNotExist:
                # This shouldn't happen, but handle gracefully
                pass
        
        # Set default configuration based on task type
        if not self.task_configuration:
            self.task_configuration = self._get_default_configuration()
        
        # Set short description if not provided
        if not self.short_description:
            self.short_description = self.description[:500] if self.description else self.title
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate task data"""
        super().clean()
        
        # Validate date constraints
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError(_('Start date cannot be after due date'))
        
        # Validate task configuration based on type
        self._validate_task_configuration()
        
        # Validate prerequisite tasks don't create circular dependencies
        self._validate_prerequisites()
    
    def _get_default_configuration(self):
        """Get default configuration based on task type"""
        defaults = {
            self.TaskType.CHECKBOX: {
                'completion_text': 'Mark as completed',
                'requires_confirmation': True,
                'allow_notes': True,
            },
            self.TaskType.PHOTO: {
                'max_photos': 3,
                'min_photos': 1,
                'max_file_size_mb': 5,
                'allowed_formats': ['JPEG', 'JPG', 'PNG'],
                'require_description': False,
                'photo_requirements': 'Clear, well-lit photos required',
            },
            self.TaskType.TEXT: {
                'min_length': 10,
                'max_length': 1000,
                'placeholder_text': 'Enter your response here...',
                'allow_formatting': False,
                'required_fields': [],
            },
            self.TaskType.CUSTOM: {
                'fields': [],
                'validation_schema': {},
                'custom_instructions': '',
            }
        }
        return defaults.get(self.task_type, {})
    
    def _validate_task_configuration(self):
        """Validate task configuration based on task type"""
        config = self.task_configuration or {}
        
        if self.task_type == self.TaskType.PHOTO:
            max_photos = config.get('max_photos', 1)
            min_photos = config.get('min_photos', 1)
            if min_photos > max_photos:
                raise ValidationError(_('Minimum photos cannot exceed maximum photos'))
        
        elif self.task_type == self.TaskType.TEXT:
            min_length = config.get('min_length', 0)
            max_length = config.get('max_length', 1000)
            if min_length > max_length:
                raise ValidationError(_('Minimum length cannot exceed maximum length'))
    
    def _validate_prerequisites(self):
        """Validate that prerequisite tasks don't create circular dependencies"""
        if self.pk:
            # Check for circular dependencies
            visited = set()
            
            def has_circular_dependency(task_id, path):
                if task_id in path:
                    return True
                if task_id in visited:
                    return False
                
                visited.add(task_id)
                path.add(task_id)
                
                try:
                    task = Task.objects.get(pk=task_id)
                    for prereq in task.prerequisite_tasks.all():
                        if has_circular_dependency(prereq.pk, path.copy()):
                            return True
                except Task.DoesNotExist:
                    pass
                
                path.remove(task_id)
                return False
            
            for prereq in self.prerequisite_tasks.all():
                if has_circular_dependency(prereq.pk, {self.pk}):
                    raise ValidationError(_('Circular dependency detected in prerequisite tasks'))
    
    # Status management methods
    def activate(self, activated_by=None, reason=''):
        """Activate the task"""
        if self.status != self.TaskStatus.ACTIVE:
            self.status = self.TaskStatus.ACTIVE
            self.status_changed_at = timezone.now()
            self.status_changed_by = activated_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'status_change_reason'])
    
    def suspend(self, suspended_by=None, reason=''):
        """Suspend the task"""
        if self.status != self.TaskStatus.SUSPENDED:
            self.status = self.TaskStatus.SUSPENDED
            self.status_changed_at = timezone.now()
            self.status_changed_by = suspended_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'status_change_reason'])
    
    def cancel(self, cancelled_by=None, reason=''):
        """Cancel the task"""
        if self.status != self.TaskStatus.CANCELLED:
            self.status = self.TaskStatus.CANCELLED
            self.status_changed_at = timezone.now()
            self.status_changed_by = cancelled_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'status_change_reason'])
    
    def complete(self, completed_by=None, reason=''):
        """Mark task as completed"""
        if self.status != self.TaskStatus.COMPLETED:
            self.status = self.TaskStatus.COMPLETED
            self.status_changed_at = timezone.now()
            self.status_changed_by = completed_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'status_change_reason'])
    
    def archive(self, archived_by=None, reason=''):
        """Archive the task"""
        if self.status != self.TaskStatus.ARCHIVED:
            self.status = self.TaskStatus.ARCHIVED
            self.status_changed_at = timezone.now()
            self.status_changed_by = archived_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'status_change_reason'])
    
    # Status checking methods
    def is_active(self):
        """Check if task is active"""
        return self.status == self.TaskStatus.ACTIVE
    
    def is_available(self):
        """Check if task is available for completion"""
        if not self.is_active():
            return False
        
        # Check if start date has passed
        if self.start_date and self.start_date > timezone.now():
            return False
        
        # Check if prerequisites are met
        if not self.are_prerequisites_met():
            return False
        
        return True
    
    def is_overdue(self):
        """Check if task is overdue"""
        return (self.due_date and 
                self.due_date < timezone.now() and 
                self.status not in [self.TaskStatus.COMPLETED, self.TaskStatus.CANCELLED, self.TaskStatus.ARCHIVED])
    
    def is_due_soon(self, days=3):
        """Check if task is due within specified days"""
        if not self.due_date:
            return False
        
        days_until_due = (self.due_date - timezone.now()).days
        return 0 <= days_until_due <= days
    
    # Prerequisite and dependency methods
    def are_prerequisites_met(self, volunteer=None):
        """Check if all prerequisite tasks are completed"""
        if not self.prerequisite_tasks.exists():
            return True
        
        if volunteer:
            # Check if volunteer has completed all prerequisites
            for prereq in self.prerequisite_tasks.all():
                if not prereq.completions.filter(
                    volunteer=volunteer,
                    status__in=[TaskCompletion.CompletionStatus.APPROVED, TaskCompletion.CompletionStatus.VERIFIED]
                ).exists():
                    return False
            return True
        
        # General check - all prerequisites must be active
        return all(prereq.is_active() for prereq in self.prerequisite_tasks.all())
    
    def get_missing_prerequisites(self, volunteer=None):
        """Get list of missing prerequisite tasks"""
        if not volunteer:
            return list(self.prerequisite_tasks.exclude(status=self.TaskStatus.ACTIVE))
        
        # Return prerequisites that volunteer hasn't completed
        missing = []
        for prereq in self.prerequisite_tasks.all():
            if not prereq.completions.filter(
                volunteer=volunteer,
                status__in=[TaskCompletion.CompletionStatus.APPROVED, TaskCompletion.CompletionStatus.VERIFIED]
            ).exists():
                missing.append(prereq)
        return missing
    
    # Configuration and validation methods
    def get_configuration(self, key=None, default=None):
        """Get task configuration value"""
        if key:
            return self.task_configuration.get(key, default)
        return self.task_configuration
    
    def set_configuration(self, key, value):
        """Set task configuration value"""
        if not self.task_configuration:
            self.task_configuration = {}
        self.task_configuration[key] = value
        self.save(update_fields=['task_configuration'])
    
    def update_configuration(self, config_dict):
        """Update multiple configuration values"""
        if not self.task_configuration:
            self.task_configuration = {}
        self.task_configuration.update(config_dict)
        self.save(update_fields=['task_configuration'])
    
    def validate_completion_data(self, completion_data):
        """Validate completion data based on task type and configuration"""
        config = self.task_configuration or {}
        errors = []
        
        if self.task_type == self.TaskType.CHECKBOX:
            if not completion_data.get('completed'):
                errors.append(_('Task must be marked as completed'))
        
        elif self.task_type == self.TaskType.PHOTO:
            photos = completion_data.get('photos', [])
            min_photos = config.get('min_photos', 1)
            max_photos = config.get('max_photos', 3)
            
            if len(photos) < min_photos:
                errors.append(_(f'At least {min_photos} photo(s) required'))
            if len(photos) > max_photos:
                errors.append(_(f'Maximum {max_photos} photo(s) allowed'))
        
        elif self.task_type == self.TaskType.TEXT:
            text = completion_data.get('text', '')
            min_length = config.get('min_length', 0)
            max_length = config.get('max_length', 1000)
            
            if len(text) < min_length:
                errors.append(_(f'Text must be at least {min_length} characters'))
            if len(text) > max_length:
                errors.append(_(f'Text cannot exceed {max_length} characters'))
        
        elif self.task_type == self.TaskType.CUSTOM:
            # Validate custom fields based on configuration
            required_fields = config.get('required_fields', [])
            for field in required_fields:
                if field not in completion_data or not completion_data[field]:
                    errors.append(_(f'Field "{field}" is required'))
        
        return errors
    
    # Completion tracking methods
    def increment_completions(self, verified=False):
        """Increment completion counters"""
        self.total_completions += 1
        if verified:
            self.verified_completions += 1
        self.save(update_fields=['total_completions', 'verified_completions'])
    
    def decrement_completions(self, was_verified=False):
        """Decrement completion counters"""
        if self.total_completions > 0:
            self.total_completions -= 1
        if was_verified and self.verified_completions > 0:
            self.verified_completions -= 1
        self.save(update_fields=['total_completions', 'verified_completions'])
    
    def get_completion_rate(self):
        """Get completion rate percentage"""
        if self.total_completions == 0:
            return 0
        return round((self.verified_completions / self.total_completions) * 100, 1)
    
    # Utility methods
    def clone_for_role(self, new_role, created_by=None):
        """Clone task for a different role"""
        cloned_task = Task(
            role=new_role,
            event=new_role.event,
            venue=new_role.venue,
            title=self.title,
            description=self.description,
            short_description=self.short_description,
            task_type=self.task_type,
            task_configuration=self.task_configuration.copy(),
            category=self.category,
            priority=self.priority,
            start_date=self.start_date,
            due_date=self.due_date,
            estimated_duration_minutes=self.estimated_duration_minutes,
            is_mandatory=self.is_mandatory,
            requires_verification=self.requires_verification,
            verification_instructions=self.verification_instructions,
            send_reminders=self.send_reminders,
            reminder_days_before=self.reminder_days_before,
            instructions=self.instructions,
            resources_links=self.resources_links.copy(),
            attachments=self.attachments.copy(),
            validation_rules=self.validation_rules.copy(),
            acceptance_criteria=self.acceptance_criteria,
            created_by=created_by,
            display_order=self.display_order,
        )
        cloned_task.save()
        
        # Clone prerequisite relationships (will need to be updated manually)
        return cloned_task
    
    def get_estimated_duration_display(self):
        """Get human-readable duration"""
        if not self.estimated_duration_minutes:
            return _('Not specified')
        
        hours = self.estimated_duration_minutes // 60
        minutes = self.estimated_duration_minutes % 60
        
        if hours > 0:
            if minutes > 0:
                return _(f'{hours}h {minutes}m')
            return _(f'{hours}h')
        return _(f'{minutes}m')
    
    def get_days_until_due(self):
        """Get days until due date"""
        if not self.due_date:
            return None
        
        delta = self.due_date - timezone.now()
        return delta.days
    
    def to_dict(self):
        """Convert task to dictionary representation"""
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'task_type': self.task_type,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'is_mandatory': self.is_mandatory,
            'requires_verification': self.requires_verification,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_duration': self.get_estimated_duration_display(),
            'completion_rate': self.get_completion_rate(),
            'is_overdue': self.is_overdue(),
            'is_available': self.is_available(),
        }
    
    def get_absolute_url(self):
        """Get absolute URL for task detail"""
        return reverse('tasks:task-detail', kwargs={'pk': self.pk})


class TaskCompletion(models.Model):
    """
    TaskCompletion model for tracking individual volunteer task progress.
    Supports different completion types based on task type with verification workflow.
    Provides comprehensive audit trail and status management.
    """
    
    class CompletionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Submission')
        SUBMITTED = 'SUBMITTED', _('Submitted for Review')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        REVISION_REQUIRED = 'REVISION_REQUIRED', _('Revision Required')
        VERIFIED = 'VERIFIED', _('Verified Complete')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    class CompletionType(models.TextChoices):
        CHECKBOX = 'CHECKBOX', _('Checkbox Completion')
        PHOTO_UPLOAD = 'PHOTO_UPLOAD', _('Photo Upload')
        TEXT_SUBMISSION = 'TEXT_SUBMISSION', _('Text Submission')
        CUSTOM_FIELDS = 'CUSTOM_FIELDS', _('Custom Field Submission')
        FILE_UPLOAD = 'FILE_UPLOAD', _('File Upload')
        EXTERNAL_VERIFICATION = 'EXTERNAL_VERIFICATION', _('External Verification')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='completions',
        help_text=_('Task being completed')
    )
    volunteer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_completions',
        help_text=_('Volunteer completing the task')
    )
    assignment = models.ForeignKey(
        'events.Assignment',
        on_delete=models.CASCADE,
        related_name='task_completions',
        null=True,
        blank=True,
        help_text=_('Assignment this completion is associated with')
    )
    
    # Completion details
    completion_type = models.CharField(
        max_length=25,
        choices=CompletionType.choices,
        help_text=_('Type of completion based on task type')
    )
    status = models.CharField(
        max_length=20,
        choices=CompletionStatus.choices,
        default=CompletionStatus.PENDING,
        help_text=_('Current completion status')
    )
    
    # Completion data (JSON field for flexibility)
    completion_data = models.JSONField(
        default=dict,
        help_text=_('Task completion data (photos, text, custom fields, etc.)')
    )
    
    # Submission tracking
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When task was submitted for review')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When task was marked as completed')
    )
    
    # Time tracking
    time_started = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer started working on task')
    )
    time_spent_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],  # Max 24 hours
        help_text=_('Actual time spent on task (in minutes)')
    )
    
    # Verification and review
    requires_verification = models.BooleanField(
        default=False,
        help_text=_('Whether this completion requires staff verification')
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_task_completions',
        help_text=_('Staff member who verified the completion')
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When completion was verified')
    )
    verification_notes = models.TextField(
        blank=True,
        help_text=_('Notes from verification process')
    )
    
    # Quality and feedback
    quality_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Quality score (1-5 stars)')
    )
    feedback_from_staff = models.TextField(
        blank=True,
        help_text=_('Feedback from staff/supervisors')
    )
    feedback_from_volunteer = models.TextField(
        blank=True,
        help_text=_('Feedback from volunteer about the task')
    )
    
    # Revision and resubmission
    revision_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times task was revised')
    )
    revision_notes = models.TextField(
        blank=True,
        help_text=_('Notes about required revisions')
    )
    previous_completion = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revisions',
        help_text=_('Previous completion if this is a revision')
    )
    
    # File attachments and evidence
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text=_('File attachments for task completion evidence')
    )
    photos = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Photo evidence for task completion')
    )
    
    # Location and context
    completion_location = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Location where task was completed')
    )
    completion_context = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional context about completion (weather, conditions, etc.)')
    )
    
    # Audit and tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status change tracking
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When status was last changed')
    )
    status_changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changed_completions',
        help_text=_('User who last changed the status')
    )
    status_change_reason = models.TextField(
        blank=True,
        help_text=_('Reason for status change')
    )
    
    # Notification settings
    send_notifications = models.BooleanField(
        default=True,
        help_text=_('Send notifications for status changes')
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Notification preferences for this completion')
    )
    
    class Meta:
        db_table = 'tasks_taskcompletion'
        verbose_name = _('Task Completion')
        verbose_name_plural = _('Task Completions')
        ordering = ['-created_at', 'task__title']
        indexes = [
            models.Index(fields=['task', 'volunteer']),
            models.Index(fields=['volunteer', 'status']),
            models.Index(fields=['task', 'status']),
            models.Index(fields=['assignment', 'status']),
            models.Index(fields=['completion_type', 'status']),
            models.Index(fields=['requires_verification', 'status']),
            models.Index(fields=['verified_by', 'verified_at']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quality_score__gte=1, quality_score__lte=5) | models.Q(quality_score__isnull=True),
                name='taskcompletion_quality_score_range'
            ),
            models.CheckConstraint(
                check=models.Q(time_spent_minutes__gte=1) | models.Q(time_spent_minutes__isnull=True),
                name='taskcompletion_time_spent_positive'
            ),
            models.CheckConstraint(
                check=models.Q(revision_count__gte=0),
                name='taskcompletion_revision_count_non_negative'
            ),
        ]
        unique_together = [
            ('task', 'volunteer', 'assignment'),  # One completion per task per volunteer per assignment
        ]
    
    def __str__(self):
        return f"{self.volunteer.get_full_name()} - {self.task.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to handle status changes and validation"""
        # Track status changes (only for existing objects)
        if self.pk:
            try:
                old_instance = TaskCompletion.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.status_changed_at = timezone.now()
                    
                    # Auto-set timestamps based on status
                    if self.status == self.CompletionStatus.SUBMITTED and not self.submitted_at:
                        self.submitted_at = timezone.now()
                    elif self.status in [self.CompletionStatus.APPROVED, self.CompletionStatus.VERIFIED] and not self.completed_at:
                        self.completed_at = timezone.now()
                    elif self.status == self.CompletionStatus.VERIFIED and not self.verified_at:
                        self.verified_at = timezone.now()
            except TaskCompletion.DoesNotExist:
                pass
        
        # Set completion type based on task type if not set
        if not self.completion_type and self.task:
            type_mapping = {
                Task.TaskType.CHECKBOX: self.CompletionType.CHECKBOX,
                Task.TaskType.PHOTO: self.CompletionType.PHOTO_UPLOAD,
                Task.TaskType.TEXT: self.CompletionType.TEXT_SUBMISSION,
                Task.TaskType.CUSTOM: self.CompletionType.CUSTOM_FIELDS,
            }
            self.completion_type = type_mapping.get(self.task.task_type, self.CompletionType.CHECKBOX)
        
        # Set verification requirement based on task
        if self.task and self.task.requires_verification:
            self.requires_verification = True
        
        super().save(*args, **kwargs)
        
        # Update task completion counters
        if self.pk and self.status in [self.CompletionStatus.APPROVED, self.CompletionStatus.VERIFIED]:
            self.task.increment_completions(verified=(self.status == self.CompletionStatus.VERIFIED))
    
    def clean(self):
        """Validate completion data"""
        super().clean()
        
        # Validate completion data based on task type
        if self.task and self.completion_data:
            errors = self.task.validate_completion_data(self.completion_data)
            if errors:
                raise ValidationError({'completion_data': errors})
        
        # Validate verification requirements
        if self.status == self.CompletionStatus.VERIFIED and not self.verified_by:
            raise ValidationError(_('Verified completions must have a verifier'))
        
        # Validate time tracking
        if self.time_started and self.completed_at and self.time_started > self.completed_at:
            raise ValidationError(_('Start time cannot be after completion time'))
    
    # Status management methods
    def submit(self, submitted_by=None):
        """Submit completion for review"""
        if self.status == self.CompletionStatus.PENDING:
            self.status = self.CompletionStatus.SUBMITTED
            self.submitted_at = timezone.now()
            self.status_changed_by = submitted_by
            self.save(update_fields=['status', 'submitted_at', 'status_changed_by', 'status_changed_at'])
    
    def approve(self, approved_by=None, notes=''):
        """Approve the completion"""
        if self.status in [self.CompletionStatus.SUBMITTED, self.CompletionStatus.UNDER_REVIEW]:
            self.status = self.CompletionStatus.APPROVED
            self.completed_at = timezone.now()
            self.status_changed_by = approved_by
            if notes:
                self.verification_notes = notes
            self.save(update_fields=['status', 'completed_at', 'status_changed_by', 'status_changed_at', 'verification_notes'])
    
    def reject(self, rejected_by=None, reason=''):
        """Reject the completion"""
        if self.status in [self.CompletionStatus.SUBMITTED, self.CompletionStatus.UNDER_REVIEW]:
            self.status = self.CompletionStatus.REJECTED
            self.status_changed_by = rejected_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_by', 'status_changed_at', 'status_change_reason'])
    
    def request_revision(self, requested_by=None, notes=''):
        """Request revision of the completion"""
        if self.status in [self.CompletionStatus.SUBMITTED, self.CompletionStatus.UNDER_REVIEW]:
            self.status = self.CompletionStatus.REVISION_REQUIRED
            self.revision_count += 1
            self.revision_notes = notes
            self.status_changed_by = requested_by
            self.save(update_fields=['status', 'revision_count', 'revision_notes', 'status_changed_by', 'status_changed_at'])
    
    def verify(self, verified_by=None, quality_score=None, notes=''):
        """Verify the completion"""
        if self.status == self.CompletionStatus.APPROVED:
            self.status = self.CompletionStatus.VERIFIED
            self.verified_by = verified_by
            self.verified_at = timezone.now()
            if quality_score:
                self.quality_score = quality_score
            if notes:
                self.verification_notes = notes
            self.save(update_fields=['status', 'verified_by', 'verified_at', 'quality_score', 'verification_notes'])
    
    def cancel(self, cancelled_by=None, reason=''):
        """Cancel the completion"""
        if self.status not in [self.CompletionStatus.VERIFIED, self.CompletionStatus.CANCELLED]:
            self.status = self.CompletionStatus.CANCELLED
            self.status_changed_by = cancelled_by
            self.status_change_reason = reason
            self.save(update_fields=['status', 'status_changed_by', 'status_changed_at', 'status_change_reason'])
    
    # Status checking methods
    def is_pending(self):
        """Check if completion is pending"""
        return self.status == self.CompletionStatus.PENDING
    
    def is_submitted(self):
        """Check if completion is submitted"""
        return self.status == self.CompletionStatus.SUBMITTED
    
    def is_approved(self):
        """Check if completion is approved"""
        return self.status in [self.CompletionStatus.APPROVED, self.CompletionStatus.VERIFIED]
    
    def is_verified(self):
        """Check if completion is verified"""
        return self.status == self.CompletionStatus.VERIFIED
    
    def is_rejected(self):
        """Check if completion is rejected"""
        return self.status == self.CompletionStatus.REJECTED
    
    def needs_revision(self):
        """Check if completion needs revision"""
        return self.status == self.CompletionStatus.REVISION_REQUIRED
    
    def is_complete(self):
        """Check if completion is in a final state"""
        return self.status in [
            self.CompletionStatus.APPROVED,
            self.CompletionStatus.VERIFIED,
            self.CompletionStatus.REJECTED,
            self.CompletionStatus.CANCELLED
        ]
    
    # Time tracking methods
    def start_work(self):
        """Mark start of work on task"""
        if not self.time_started:
            self.time_started = timezone.now()
            self.save(update_fields=['time_started'])
    
    def calculate_time_spent(self):
        """Calculate time spent on task"""
        if self.time_started and self.completed_at:
            delta = self.completed_at - self.time_started
            self.time_spent_minutes = int(delta.total_seconds() / 60)
            self.save(update_fields=['time_spent_minutes'])
            return self.time_spent_minutes
        return None
    
    def get_time_spent_display(self):
        """Get human-readable time spent"""
        if not self.time_spent_minutes:
            return _('Not tracked')
        
        hours = self.time_spent_minutes // 60
        minutes = self.time_spent_minutes % 60
        
        if hours > 0:
            if minutes > 0:
                return _(f'{hours}h {minutes}m')
            return _(f'{hours}h')
        return _(f'{minutes}m')
    
    # Data management methods
    def get_completion_data(self, key=None, default=None):
        """Get completion data value"""
        if key:
            return self.completion_data.get(key, default)
        return self.completion_data
    
    def set_completion_data(self, key, value):
        """Set completion data value"""
        if not self.completion_data:
            self.completion_data = {}
        self.completion_data[key] = value
        self.save(update_fields=['completion_data'])
    
    def update_completion_data(self, data_dict):
        """Update multiple completion data values"""
        if not self.completion_data:
            self.completion_data = {}
        self.completion_data.update(data_dict)
        self.save(update_fields=['completion_data'])
    
    def add_photo(self, photo_url, description=''):
        """Add photo to completion"""
        if not self.photos:
            self.photos = []
        self.photos.append({
            'url': photo_url,
            'description': description,
            'uploaded_at': timezone.now().isoformat()
        })
        self.save(update_fields=['photos'])
    
    def add_attachment(self, file_url, filename, file_type=''):
        """Add file attachment to completion"""
        if not self.attachments:
            self.attachments = []
        self.attachments.append({
            'url': file_url,
            'filename': filename,
            'file_type': file_type,
            'uploaded_at': timezone.now().isoformat()
        })
        self.save(update_fields=['attachments'])
    
    # Utility methods
    def create_revision(self, revised_by=None):
        """Create a new completion as revision of this one"""
        revision = TaskCompletion(
            task=self.task,
            volunteer=self.volunteer,
            assignment=self.assignment,
            completion_type=self.completion_type,
            completion_data=self.completion_data.copy(),
            requires_verification=self.requires_verification,
            previous_completion=self,
            revision_count=self.revision_count + 1,
            completion_location=self.completion_location,
            completion_context=self.completion_context.copy(),
        )
        revision.save()
        return revision
    
    def to_dict(self):
        """Convert completion to dictionary representation"""
        return {
            'id': str(self.id),
            'task_id': str(self.task.id),
            'task_title': self.task.title,
            'volunteer_name': self.volunteer.get_full_name(),
            'status': self.status,
            'completion_type': self.completion_type,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'quality_score': self.quality_score,
            'time_spent': self.get_time_spent_display(),
            'revision_count': self.revision_count,
            'requires_verification': self.requires_verification,
            'is_complete': self.is_complete(),
        }
    
    def get_absolute_url(self):
        """Get absolute URL for completion detail"""
        return reverse('tasks:completion-detail', kwargs={'pk': self.pk})
