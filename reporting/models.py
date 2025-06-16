from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json

User = get_user_model()


class Report(models.Model):
    """
    Main model for managing different types of reports with export capabilities.
    """
    
    class ReportType(models.TextChoices):
        VOLUNTEER_SUMMARY = 'VOLUNTEER_SUMMARY', _('Volunteer Summary Report')
        VOLUNTEER_DETAILED = 'VOLUNTEER_DETAILED', _('Detailed Volunteer Report')
        EVENT_SUMMARY = 'EVENT_SUMMARY', _('Event Summary Report')
        EVENT_DETAILED = 'EVENT_DETAILED', _('Detailed Event Report')
        VENUE_UTILIZATION = 'VENUE_UTILIZATION', _('Venue Utilization Report')
        ROLE_ASSIGNMENT = 'ROLE_ASSIGNMENT', _('Role Assignment Report')
        TRAINING_STATUS = 'TRAINING_STATUS', _('Training Status Report')
        BACKGROUND_CHECK = 'BACKGROUND_CHECK', _('Background Check Report')
        JUSTGO_SYNC = 'JUSTGO_SYNC', _('JustGo Synchronization Report')
        EOI_ANALYTICS = 'EOI_ANALYTICS', _('EOI Analytics Report')
        PERFORMANCE_METRICS = 'PERFORMANCE_METRICS', _('Performance Metrics Report')
        ATTENDANCE_TRACKING = 'ATTENDANCE_TRACKING', _('Attendance Tracking Report')
        CUSTOM = 'CUSTOM', _('Custom Report')
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        GENERATING = 'GENERATING', _('Generating')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        EXPIRED = 'EXPIRED', _('Expired')
    
    class ExportFormat(models.TextChoices):
        CSV = 'CSV', _('CSV (Comma Separated Values)')
        EXCEL = 'EXCEL', _('Excel (.xlsx)')
        PDF = 'PDF', _('PDF Document')
        JSON = 'JSON', _('JSON Data')
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text=_('Report name'))
    description = models.TextField(blank=True, help_text=_('Report description'))
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    
    # Configuration
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Report parameters and filters')
    )
    export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV
    )
    
    # Status and Processing
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Results
    total_records = models.PositiveIntegerField(default=0)
    file_path = models.CharField(max_length=500, blank=True, help_text=_('Path to generated file'))
    file_size = models.PositiveIntegerField(default=0, help_text=_('File size in bytes'))
    
    # Metadata
    generation_time = models.DurationField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_reports'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()}: {self.name}"
    
    def save(self, *args, **kwargs):
        # Set expiration date (30 days from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if report has expired"""
        return self.expires_at and timezone.now() > self.expires_at
    
    def get_file_size_display(self):
        """Get human-readable file size"""
        if self.file_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        size = self.file_size
        i = 0
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def get_download_url(self):
        """Get download URL for the report"""
        if self.file_path and self.status == self.Status.COMPLETED:
            return f"/api/reports/{self.id}/download/"
        return None


class ReportTemplate(models.Model):
    """
    Model for storing reusable report templates with predefined configurations.
    """
    
    # Basic Information
    name = models.CharField(max_length=200, help_text=_('Template name'))
    description = models.TextField(blank=True, help_text=_('Template description'))
    report_type = models.CharField(max_length=30, choices=Report.ReportType.choices)
    
    # Configuration
    default_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Default parameters for this template')
    )
    default_export_format = models.CharField(
        max_length=10,
        choices=Report.ExportFormat.choices,
        default=Report.ExportFormat.CSV
    )
    
    # Template Settings
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False, help_text=_('Available to all users'))
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_report_templates'
    )
    
    # Usage Statistics
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['report_type', 'is_active']),
            models.Index(fields=['is_public', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()}: {self.name}"
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])


class ReportSchedule(models.Model):
    """
    Model for scheduling automatic report generation.
    """
    
    class Frequency(models.TextChoices):
        DAILY = 'DAILY', _('Daily')
        WEEKLY = 'WEEKLY', _('Weekly')
        MONTHLY = 'MONTHLY', _('Monthly')
        QUARTERLY = 'QUARTERLY', _('Quarterly')
        YEARLY = 'YEARLY', _('Yearly')
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        PAUSED = 'PAUSED', _('Paused')
        DISABLED = 'DISABLED', _('Disabled')
    
    # Basic Information
    name = models.CharField(max_length=200, help_text=_('Schedule name'))
    description = models.TextField(blank=True, help_text=_('Schedule description'))
    
    # Report Configuration
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    
    # Schedule Configuration
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    start_date = models.DateField(help_text=_('When to start generating reports'))
    end_date = models.DateField(null=True, blank=True, help_text=_('When to stop (optional)'))
    
    # Time Configuration
    run_time = models.TimeField(default='09:00:00', help_text=_('Time of day to run'))
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # Recipients
    email_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Email addresses to send reports to')
    )
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_report_schedules'
    )
    
    # Execution Tracking
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['status', 'next_run']),
            models.Index(fields=['frequency', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def calculate_next_run(self):
        """Calculate the next run time based on frequency"""
        from datetime import timedelta
        
        if not self.last_run:
            base_date = timezone.now().date()
        else:
            base_date = self.last_run.date()
        
        if self.frequency == self.Frequency.DAILY:
            next_date = base_date + timedelta(days=1)
        elif self.frequency == self.Frequency.WEEKLY:
            next_date = base_date + timedelta(weeks=1)
        elif self.frequency == self.Frequency.MONTHLY:
            # Add one month (approximate)
            next_date = base_date + timedelta(days=30)
        elif self.frequency == self.Frequency.QUARTERLY:
            next_date = base_date + timedelta(days=90)
        elif self.frequency == self.Frequency.YEARLY:
            next_date = base_date + timedelta(days=365)
        else:
            next_date = base_date + timedelta(days=1)
        
        # Combine with run time
        next_datetime = timezone.datetime.combine(next_date, self.run_time)
        self.next_run = timezone.make_aware(next_datetime)
        
        return self.next_run


class ReportMetrics(models.Model):
    """
    Model for storing report generation metrics and analytics.
    """
    
    # Report Reference
    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Performance Metrics
    query_time = models.DurationField(null=True, blank=True)
    processing_time = models.DurationField(null=True, blank=True)
    export_time = models.DurationField(null=True, blank=True)
    
    # Resource Usage
    memory_usage_mb = models.PositiveIntegerField(default=0)
    cpu_usage_percent = models.FloatField(default=0.0)
    
    # Data Metrics
    rows_processed = models.PositiveIntegerField(default=0)
    columns_included = models.PositiveIntegerField(default=0)
    filters_applied = models.JSONField(default=list, blank=True)
    
    # Quality Metrics
    data_completeness_percent = models.FloatField(
        default=100.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    error_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    
    # User Interaction
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Metrics for {self.report.name}"
    
    def increment_download_count(self):
        """Increment download count and update last downloaded timestamp"""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded'])


class ReportShare(models.Model):
    """
    Model for managing report sharing with external users or systems.
    """
    
    class ShareType(models.TextChoices):
        LINK = 'LINK', _('Shareable Link')
        EMAIL = 'EMAIL', _('Email Share')
        API = 'API', _('API Access')
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        EXPIRED = 'EXPIRED', _('Expired')
        REVOKED = 'REVOKED', _('Revoked')
    
    # Basic Information
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    share_type = models.CharField(max_length=10, choices=ShareType.choices)
    
    # Access Configuration
    share_token = models.UUIDField(default=uuid.uuid4, unique=True)
    password_protected = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=128, blank=True)
    
    # Permissions
    can_download = models.BooleanField(default=True)
    can_view_metrics = models.BooleanField(default=False)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # Usage Tracking
    access_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_report_shares'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['share_token']),
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Share: {self.report.name} ({self.get_share_type_display()})"
    
    def is_valid(self):
        """Check if share is still valid"""
        if self.status != self.Status.ACTIVE:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        
        return True
    
    def get_share_url(self):
        """Get the shareable URL"""
        return f"/reports/shared/{self.share_token}/"
    
    def increment_access(self):
        """Increment access count and update last accessed timestamp"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])
    
    def increment_download(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])
