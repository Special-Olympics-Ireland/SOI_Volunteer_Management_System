"""
Notification models for real-time notification system
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

User = get_user_model()


class NotificationTemplate(models.Model):
    """Template for notification messages"""
    
    class NotificationType(models.TextChoices):
        VOLUNTEER_APPLICATION = 'volunteer_application', 'Volunteer Application'
        VOLUNTEER_APPROVED = 'volunteer_approved', 'Volunteer Approved'
        VOLUNTEER_REJECTED = 'volunteer_rejected', 'Volunteer Rejected'
        EVENT_ASSIGNMENT = 'event_assignment', 'Event Assignment'
        EVENT_REMINDER = 'event_reminder', 'Event Reminder'
        EVENT_CANCELLED = 'event_cancelled', 'Event Cancelled'
        TASK_ASSIGNED = 'task_assigned', 'Task Assigned'
        TASK_COMPLETED = 'task_completed', 'Task Completed'
        TASK_OVERDUE = 'task_overdue', 'Task Overdue'
        ADMIN_OVERRIDE = 'admin_override', 'Admin Override'
        SYSTEM_ALERT = 'system_alert', 'System Alert'
        TRAINING_REMINDER = 'training_reminder', 'Training Reminder'
        DOCUMENT_REQUIRED = 'document_required', 'Document Required'
        PROFILE_UPDATE = 'profile_update', 'Profile Update'
        BULK_OPERATION = 'bulk_operation', 'Bulk Operation'
        INTEGRATION_ERROR = 'integration_error', 'Integration Error'
        REPORT_READY = 'report_ready', 'Report Ready'
        CUSTOM = 'custom', 'Custom'
    
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'
        CRITICAL = 'CRITICAL', 'Critical'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(max_length=50, choices=NotificationType.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Template content
    title_template = models.CharField(max_length=255, help_text="Template for notification title with {variables}")
    message_template = models.TextField(help_text="Template for notification message with {variables}")
    
    # Configuration
    default_priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    is_email_enabled = models.BooleanField(default=True)
    is_push_enabled = models.BooleanField(default=True)
    is_in_app_enabled = models.BooleanField(default=True)
    
    # Targeting
    target_user_types = models.JSONField(default=list, help_text="List of user types to send to")
    target_roles = models.JSONField(default=list, help_text="List of roles to send to")
    
    # Timing
    delay_minutes = models.IntegerField(default=0, help_text="Delay before sending notification")
    expires_after_hours = models.IntegerField(default=72, help_text="Hours after which notification expires")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'notification_templates'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        ordering = ['notification_type', 'name']
        indexes = [
            models.Index(fields=['notification_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.name}"
    
    def render_title(self, context):
        """Render title template with context variables"""
        try:
            return self.title_template.format(**context)
        except KeyError as e:
            return f"Template Error: Missing variable {e}"
    
    def render_message(self, context):
        """Render message template with context variables"""
        try:
            return self.message_template.format(**context)
        except KeyError as e:
            return f"Template Error: Missing variable {e}"


class Notification(models.Model):
    """Individual notification instance"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        READ = 'READ', 'Read'
        FAILED = 'FAILED', 'Failed'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    class Channel(models.TextChoices):
        IN_APP = 'IN_APP', 'In-App'
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push'
        SMS = 'SMS', 'SMS'
        WEBSOCKET = 'WEBSOCKET', 'WebSocket'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template and content
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Targeting
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    
    # Related object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Configuration
    priority = models.CharField(max_length=20, choices=NotificationTemplate.Priority.choices, default=NotificationTemplate.Priority.MEDIUM)
    channels = models.JSONField(default=list, help_text="List of channels to send through")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Timing
    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    context_data = models.JSONField(default=dict, help_text="Context data used for rendering")
    delivery_attempts = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_as_read(self):
        """Mark notification as read"""
        if self.status != self.Status.READ:
            self.status = self.Status.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at', 'updated_at'])
    
    def mark_as_failed(self, error_message=""):
        """Mark notification as failed"""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.delivery_attempts += 1
        self.save(update_fields=['status', 'error_message', 'delivery_attempts', 'updated_at'])
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_retry(self):
        """Check if notification can be retried"""
        return self.status == self.Status.FAILED and self.delivery_attempts < 3 and not self.is_expired()


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Global settings
    is_enabled = models.BooleanField(default=True)
    
    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    
    # Notification type preferences
    volunteer_notifications = models.BooleanField(default=True)
    event_notifications = models.BooleanField(default=True)
    task_notifications = models.BooleanField(default=True)
    admin_notifications = models.BooleanField(default=True)
    system_notifications = models.BooleanField(default=True)
    training_notifications = models.BooleanField(default=True)
    
    # Timing preferences
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours (no notifications)")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours")
    timezone = models.CharField(max_length=50, default='Europe/Dublin')
    
    # Frequency settings
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('IMMEDIATE', 'Immediate'),
            ('HOURLY', 'Hourly'),
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('DISABLED', 'Disabled'),
        ],
        default='IMMEDIATE'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def is_notification_allowed(self, notification_type, channel):
        """Check if a notification type and channel is allowed for this user"""
        if not self.is_enabled:
            return False
        
        # Check channel preferences
        if channel == 'EMAIL' and not self.email_enabled:
            return False
        elif channel == 'PUSH' and not self.push_enabled:
            return False
        elif channel == 'IN_APP' and not self.in_app_enabled:
            return False
        elif channel == 'SMS' and not self.sms_enabled:
            return False
        
        # Check notification type preferences
        type_mapping = {
            'volunteer_application': self.volunteer_notifications,
            'volunteer_approved': self.volunteer_notifications,
            'volunteer_rejected': self.volunteer_notifications,
            'event_assignment': self.event_notifications,
            'event_reminder': self.event_notifications,
            'event_cancelled': self.event_notifications,
            'task_assigned': self.task_notifications,
            'task_completed': self.task_notifications,
            'task_overdue': self.task_notifications,
            'admin_override': self.admin_notifications,
            'system_alert': self.system_notifications,
            'training_reminder': self.training_notifications,
        }
        
        return type_mapping.get(notification_type, True)
    
    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        import pytz
        user_tz = pytz.timezone(self.timezone)
        current_time = timezone.now().astimezone(user_tz).time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:  # Quiet hours span midnight
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end


class NotificationChannel(models.Model):
    """Configuration for notification delivery channels"""
    
    class ChannelType(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push Notification'
        SMS = 'SMS', 'SMS'
        WEBHOOK = 'WEBHOOK', 'Webhook'
        SLACK = 'SLACK', 'Slack'
        TEAMS = 'TEAMS', 'Microsoft Teams'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    channel_type = models.CharField(max_length=20, choices=ChannelType.choices)
    
    # Configuration
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, help_text="Channel-specific configuration")
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=60)
    rate_limit_per_hour = models.IntegerField(default=1000)
    
    # Retry configuration
    max_retries = models.IntegerField(default=3)
    retry_delay_seconds = models.IntegerField(default=300)  # 5 minutes
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_channels'
        verbose_name = 'Notification Channel'
        verbose_name_plural = 'Notification Channels'
        unique_together = ['name', 'channel_type']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class NotificationLog(models.Model):
    """Log of notification delivery attempts"""
    
    class LogLevel(models.TextChoices):
        DEBUG = 'DEBUG', 'Debug'
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'
        CRITICAL = 'CRITICAL', 'Critical'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    channel = models.ForeignKey(NotificationChannel, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Log details
    level = models.CharField(max_length=20, choices=LogLevel.choices, default=LogLevel.INFO)
    message = models.TextField()
    
    # Delivery details
    channel_type = models.CharField(max_length=20)
    delivery_status = models.CharField(max_length=50)
    response_data = models.JSONField(default=dict, blank=True)
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification_logs'
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['notification', 'timestamp']),
            models.Index(fields=['level', 'timestamp']),
            models.Index(fields=['channel_type', 'delivery_status']),
        ]
    
    def __str__(self):
        return f"{self.level} - {self.notification.title} via {self.channel_type}" 