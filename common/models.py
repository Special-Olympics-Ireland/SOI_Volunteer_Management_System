from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from django.utils.text import slugify


class AdminOverride(models.Model):
    """
    AdminOverride model for tracking administrative overrides of system rules.
    Provides comprehensive audit trail and justification requirements for all
    override actions with approval workflow and impact assessment.
    """
    
    class OverrideType(models.TextChoices):
        AGE_REQUIREMENT = 'AGE_REQUIREMENT', _('Age Requirement Override')
        CREDENTIAL_REQUIREMENT = 'CREDENTIAL_REQUIREMENT', _('Credential Requirement Override')
        CAPACITY_LIMIT = 'CAPACITY_LIMIT', _('Capacity Limit Override')
        DEADLINE_EXTENSION = 'DEADLINE_EXTENSION', _('Deadline Extension')
        STATUS_CHANGE = 'STATUS_CHANGE', _('Status Change Override')
        ASSIGNMENT_RULE = 'ASSIGNMENT_RULE', _('Assignment Rule Override')
        VERIFICATION_BYPASS = 'VERIFICATION_BYPASS', _('Verification Bypass')
        PREREQUISITE_SKIP = 'PREREQUISITE_SKIP', _('Prerequisite Skip')
        ROLE_RESTRICTION = 'ROLE_RESTRICTION', _('Role Restriction Override')
        SYSTEM_RULE = 'SYSTEM_RULE', _('System Rule Override')
        DATA_MODIFICATION = 'DATA_MODIFICATION', _('Data Modification Override')
        EMERGENCY_ACCESS = 'EMERGENCY_ACCESS', _('Emergency Access Override')
        OTHER = 'OTHER', _('Other Override')
    
    class OverrideStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Approval')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        ACTIVE = 'ACTIVE', _('Active Override')
        EXPIRED = 'EXPIRED', _('Expired')
        REVOKED = 'REVOKED', _('Revoked')
        COMPLETED = 'COMPLETED', _('Completed')
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', _('Low Risk')
        MEDIUM = 'MEDIUM', _('Medium Risk')
        HIGH = 'HIGH', _('High Risk')
        CRITICAL = 'CRITICAL', _('Critical Risk')
    
    class ImpactLevel(models.TextChoices):
        MINIMAL = 'MINIMAL', _('Minimal Impact')
        LOW = 'LOW', _('Low Impact')
        MEDIUM = 'MEDIUM', _('Medium Impact')
        HIGH = 'HIGH', _('High Impact')
        SEVERE = 'SEVERE', _('Severe Impact')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Override classification
    override_type = models.CharField(
        max_length=30,
        choices=OverrideType.choices,
        help_text=_('Type of override being applied')
    )
    status = models.CharField(
        max_length=20,
        choices=OverrideStatus.choices,
        default=OverrideStatus.PENDING,
        help_text=_('Current status of the override')
    )
    
    # Target object (using generic foreign key for flexibility)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text=_('Type of object being overridden')
    )
    object_id = models.CharField(
        max_length=255,
        help_text=_('ID of the object being overridden')
    )
    target_object = GenericForeignKey('content_type', 'object_id')
    
    # Override details
    title = models.CharField(
        max_length=200,
        help_text=_('Brief title describing the override')
    )
    description = models.TextField(
        help_text=_('Detailed description of what is being overridden')
    )
    justification = models.TextField(
        help_text=_('Required justification for the override')
    )
    business_case = models.TextField(
        blank=True,
        help_text=_('Business case or reasoning for the override')
    )
    
    # Risk and impact assessment
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
        help_text=_('Assessed risk level of this override')
    )
    impact_level = models.CharField(
        max_length=20,
        choices=ImpactLevel.choices,
        default=ImpactLevel.LOW,
        help_text=_('Assessed impact level of this override')
    )
    risk_assessment = models.TextField(
        blank=True,
        help_text=_('Detailed risk assessment and mitigation measures')
    )
    impact_assessment = models.TextField(
        blank=True,
        help_text=_('Detailed impact assessment on system and users')
    )
    
    # Override data and configuration
    override_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Specific override data and parameters')
    )
    original_values = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Original values before override')
    )
    new_values = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('New values after override')
    )
    
    # Approval workflow
    requested_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_overrides',
        help_text=_('User who requested the override')
    )
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_overrides',
        help_text=_('User who approved the override')
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_overrides',
        help_text=_('User who reviewed the override')
    )
    
    # Timing and duration
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the override was requested')
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the override was approved')
    )
    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the override becomes effective')
    )
    effective_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the override expires')
    )
    applied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the override was actually applied')
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the override was revoked')
    )
    
    # Approval and review notes
    approval_notes = models.TextField(
        blank=True,
        help_text=_('Notes from the approval process')
    )
    review_notes = models.TextField(
        blank=True,
        help_text=_('Notes from the review process')
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text=_('Reason for rejection if applicable')
    )
    
    # Emergency and priority handling
    is_emergency = models.BooleanField(
        default=False,
        help_text=_('Whether this is an emergency override')
    )
    priority_level = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_('Priority level (1=highest, 10=lowest)')
    )
    requires_immediate_action = models.BooleanField(
        default=False,
        help_text=_('Whether this override requires immediate action')
    )
    
    # Compliance and documentation
    compliance_notes = models.TextField(
        blank=True,
        help_text=_('Compliance considerations and documentation')
    )
    regulatory_impact = models.TextField(
        blank=True,
        help_text=_('Impact on regulatory compliance')
    )
    documentation_required = models.BooleanField(
        default=True,
        help_text=_('Whether additional documentation is required')
    )
    documentation_provided = models.BooleanField(
        default=False,
        help_text=_('Whether required documentation has been provided')
    )
    
    # Monitoring and follow-up
    requires_monitoring = models.BooleanField(
        default=True,
        help_text=_('Whether this override requires ongoing monitoring')
    )
    monitoring_frequency = models.CharField(
        max_length=20,
        choices=[
            ('HOURLY', _('Hourly')),
            ('DAILY', _('Daily')),
            ('WEEKLY', _('Weekly')),
            ('MONTHLY', _('Monthly')),
            ('AS_NEEDED', _('As Needed')),
        ],
        default='DAILY',
        help_text=_('Frequency of monitoring required')
    )
    last_monitored_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the override was last monitored')
    )
    monitoring_notes = models.TextField(
        blank=True,
        help_text=_('Notes from monitoring activities')
    )
    
    # Notification and communication
    notification_sent = models.BooleanField(
        default=False,
        help_text=_('Whether notifications have been sent')
    )
    stakeholders_notified = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of stakeholders who have been notified')
    )
    communication_log = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Log of communications regarding this override')
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
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changed_overrides',
        help_text=_('User who last changed the status')
    )
    status_change_reason = models.TextField(
        blank=True,
        help_text=_('Reason for status change')
    )
    
    # Additional metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Tags for categorization and search')
    )
    external_references = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('External system references and IDs')
    )
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Custom fields for specific override types')
    )
    
    class Meta:
        verbose_name = _('admin override')
        verbose_name_plural = _('admin overrides')
        ordering = ['-created_at', '-priority_level', 'status']
        indexes = [
            models.Index(fields=['override_type', 'status']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(fields=['approved_by', 'approved_at']),
            models.Index(fields=['risk_level', 'impact_level']),
            models.Index(fields=['is_emergency', 'priority_level']),
            models.Index(fields=['effective_from', 'effective_until']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['requires_monitoring', 'last_monitored_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(priority_level__gte=1, priority_level__lte=10),
                name='adminoverride_priority_level_range'
            ),
            models.CheckConstraint(
                check=models.Q(effective_from__lte=models.F('effective_until')) | 
                      models.Q(effective_until__isnull=True),
                name='adminoverride_effective_dates_valid'
            ),
        ]
    
    def __str__(self):
        return f"{self.get_override_type_display()} - {self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Enhanced save method with validation and auto-population"""
        # Set effective_from to now if not set and status is approved
        if self.status == self.OverrideStatus.APPROVED and not self.effective_from:
            self.effective_from = timezone.now()
        
        # Set applied_at when status changes to active
        if self.status == self.OverrideStatus.ACTIVE and not self.applied_at:
            self.applied_at = timezone.now()
        
        # Auto-expire if past effective_until date
        if (self.effective_until and 
            timezone.now() > self.effective_until and 
            self.status == self.OverrideStatus.ACTIVE):
            self.status = self.OverrideStatus.EXPIRED
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate override data"""
        super().clean()
        
        # Validate effective dates
        if (self.effective_from and self.effective_until and 
            self.effective_from > self.effective_until):
            raise ValidationError(_('Effective from date cannot be after effective until date'))
        
        # Validate approval requirements
        if self.status == self.OverrideStatus.APPROVED and not self.approved_by:
            raise ValidationError(_('Approved overrides must have an approver'))
        
        # Validate justification for high-risk overrides
        if (self.risk_level in [self.RiskLevel.HIGH, self.RiskLevel.CRITICAL] and 
            not self.justification.strip()):
            raise ValidationError(_('High and critical risk overrides require detailed justification'))
    
    # Status management methods
    def approve(self, approved_by, notes=''):
        """Approve the override"""
        if self.status == self.OverrideStatus.PENDING:
            self.status = self.OverrideStatus.APPROVED
            self.approved_by = approved_by
            self.approved_at = timezone.now()
            self.approval_notes = notes
            self.status_changed_at = timezone.now()
            self.status_changed_by = approved_by
            self.save(update_fields=[
                'status', 'approved_by', 'approved_at', 'approval_notes',
                'status_changed_at', 'status_changed_by'
            ])
    
    def reject(self, rejected_by, reason):
        """Reject the override"""
        if self.status == self.OverrideStatus.PENDING:
            self.status = self.OverrideStatus.REJECTED
            self.rejection_reason = reason
            self.status_changed_at = timezone.now()
            self.status_changed_by = rejected_by
            self.save(update_fields=[
                'status', 'rejection_reason', 'status_changed_at', 'status_changed_by'
            ])
    
    def activate(self, activated_by=None):
        """Activate the override"""
        if self.status == self.OverrideStatus.APPROVED:
            self.status = self.OverrideStatus.ACTIVE
            self.applied_at = timezone.now()
            if not self.effective_from:
                self.effective_from = timezone.now()
            if activated_by:
                self.status_changed_by = activated_by
            self.status_changed_at = timezone.now()
            self.save(update_fields=[
                'status', 'applied_at', 'effective_from', 
                'status_changed_at', 'status_changed_by'
            ])
    
    def revoke(self, revoked_by, reason=''):
        """Revoke the override"""
        if self.status in [self.OverrideStatus.APPROVED, self.OverrideStatus.ACTIVE]:
            self.status = self.OverrideStatus.REVOKED
            self.revoked_at = timezone.now()
            self.status_changed_at = timezone.now()
            self.status_changed_by = revoked_by
            if reason:
                self.status_change_reason = reason
            self.save(update_fields=[
                'status', 'revoked_at', 'status_changed_at', 
                'status_changed_by', 'status_change_reason'
            ])
    
    def complete(self, completed_by=None):
        """Mark override as completed"""
        if self.status == self.OverrideStatus.ACTIVE:
            self.status = self.OverrideStatus.COMPLETED
            self.status_changed_at = timezone.now()
            if completed_by:
                self.status_changed_by = completed_by
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by'])
    
    # Status checking methods
    def is_pending(self):
        """Check if override is pending approval"""
        return self.status == self.OverrideStatus.PENDING
    
    def is_approved(self):
        """Check if override is approved"""
        return self.status == self.OverrideStatus.APPROVED
    
    def is_active(self):
        """Check if override is currently active"""
        return self.status == self.OverrideStatus.ACTIVE
    
    def is_expired(self):
        """Check if override has expired"""
        return (self.status == self.OverrideStatus.EXPIRED or
                (self.effective_until and timezone.now() > self.effective_until))
    
    def is_revoked(self):
        """Check if override has been revoked"""
        return self.status == self.OverrideStatus.REVOKED
    
    def is_effective(self):
        """Check if override is currently effective"""
        now = timezone.now()
        return (self.status == self.OverrideStatus.ACTIVE and
                (not self.effective_from or now >= self.effective_from) and
                (not self.effective_until or now <= self.effective_until))
    
    # Utility methods
    def get_duration(self):
        """Get override duration in days"""
        if self.effective_from and self.effective_until:
            return (self.effective_until - self.effective_from).days
        return None
    
    def get_time_remaining(self):
        """Get time remaining until expiration"""
        if self.effective_until and self.status == self.OverrideStatus.ACTIVE:
            remaining = self.effective_until - timezone.now()
            return remaining if remaining.total_seconds() > 0 else None
        return None
    
    def add_communication_log(self, message, user=None):
        """Add entry to communication log"""
        if not self.communication_log:
            self.communication_log = []
        
        entry = {
            'timestamp': timezone.now().isoformat(),
            'message': message,
            'user': user.get_full_name() if user else 'System',
            'user_id': str(user.id) if user else None
        }
        self.communication_log.append(entry)
        self.save(update_fields=['communication_log'])
    
    def update_monitoring(self, notes='', monitored_by=None):
        """Update monitoring information"""
        self.last_monitored_at = timezone.now()
        if notes:
            self.monitoring_notes = notes
        
        # Add to communication log
        if monitored_by:
            self.add_communication_log(f"Monitoring update: {notes}", monitored_by)
        
        self.save(update_fields=['last_monitored_at', 'monitoring_notes'])
    
    def to_dict(self):
        """Convert override to dictionary representation"""
        return {
            'id': str(self.id),
            'override_type': self.override_type,
            'override_type_display': self.get_override_type_display(),
            'status': self.status,
            'status_display': self.get_status_display(),
            'title': self.title,
            'description': self.description,
            'justification': self.justification,
            'risk_level': self.risk_level,
            'impact_level': self.impact_level,
            'is_emergency': self.is_emergency,
            'priority_level': self.priority_level,
            'requested_by': self.requested_by.get_full_name() if self.requested_by else None,
            'approved_by': self.approved_by.get_full_name() if self.approved_by else None,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_until': self.effective_until.isoformat() if self.effective_until else None,
            'is_effective': self.is_effective(),
            'duration_days': self.get_duration(),
            'requires_monitoring': self.requires_monitoring,
            'last_monitored_at': self.last_monitored_at.isoformat() if self.last_monitored_at else None,
        }
    
    def get_absolute_url(self):
        """Get absolute URL for override detail"""
        from django.urls import reverse
        return reverse('common:adminoverride-detail', kwargs={'pk': self.pk})


class AuditLog(models.Model):
    """
    AuditLog model for tracking all system activities and changes.
    Provides comprehensive audit trail for compliance and security monitoring.
    """
    
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        VIEW = 'VIEW', _('View')
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        EXPORT = 'EXPORT', _('Export')
        IMPORT = 'IMPORT', _('Import')
        APPROVE = 'APPROVE', _('Approve')
        REJECT = 'REJECT', _('Reject')
        OVERRIDE = 'OVERRIDE', _('Override')
        SYNC = 'SYNC', _('Synchronize')
        BACKUP = 'BACKUP', _('Backup')
        RESTORE = 'RESTORE', _('Restore')
        OTHER = 'OTHER', _('Other')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Action details
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        help_text=_('Type of action performed')
    )
    action_description = models.TextField(
        help_text=_('Detailed description of the action')
    )
    
    # User and session information
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_('User who performed the action')
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text=_('Session key for the action')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('IP address of the user')
    )
    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )
    
    # Target object information
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_('Type of object affected')
    )
    object_id = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('ID of the object affected')
    )
    target_object = GenericForeignKey('content_type', 'object_id')
    object_representation = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('String representation of the object')
    )
    
    # Change tracking
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Details of changes made')
    )
    old_values = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Previous values before change')
    )
    new_values = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('New values after change')
    )
    
    # Request and response information
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('HTTP request method')
    )
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Request path')
    )
    request_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Request data (sanitized)')
    )
    response_status = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('HTTP response status code')
    )
    
    # Timing and performance
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the action occurred')
    )
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Duration of the action in milliseconds')
    )
    
    # Additional context
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Tags for categorization')
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional metadata')
    )
    
    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.get_full_name() if self.user else 'Anonymous'
        return f"{user_str} - {self.get_action_type_display()} - {self.timestamp}"


class SystemConfig(models.Model):
    """
    SystemConfig model for storing system-wide configuration settings.
    Provides centralized configuration management with validation and versioning.
    """
    
    class ConfigType(models.TextChoices):
        SYSTEM = 'SYSTEM', _('System Configuration')
        FEATURE = 'FEATURE', _('Feature Configuration')
        INTEGRATION = 'INTEGRATION', _('Integration Configuration')
        SECURITY = 'SECURITY', _('Security Configuration')
        NOTIFICATION = 'NOTIFICATION', _('Notification Configuration')
        WORKFLOW = 'WORKFLOW', _('Workflow Configuration')
        UI = 'UI', _('User Interface Configuration')
        API = 'API', _('API Configuration')
        OTHER = 'OTHER', _('Other Configuration')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Configuration details
    key = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Unique configuration key')
    )
    name = models.CharField(
        max_length=200,
        help_text=_('Human-readable configuration name')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Description of the configuration setting')
    )
    config_type = models.CharField(
        max_length=20,
        choices=ConfigType.choices,
        default=ConfigType.SYSTEM,
        help_text=_('Type of configuration')
    )
    
    # Configuration value
    value = models.JSONField(
        help_text=_('Configuration value (can be any JSON type)')
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Default value for this configuration')
    )
    
    # Validation and constraints
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Validation rules for the configuration value')
    )
    allowed_values = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of allowed values (if restricted)')
    )
    
    # Status and visibility
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this configuration is active')
    )
    is_public = models.BooleanField(
        default=False,
        help_text=_('Whether this configuration is publicly visible')
    )
    is_editable = models.BooleanField(
        default=True,
        help_text=_('Whether this configuration can be edited')
    )
    requires_restart = models.BooleanField(
        default=False,
        help_text=_('Whether changing this config requires system restart')
    )
    
    # Versioning and change tracking
    version = models.PositiveIntegerField(
        default=1,
        help_text=_('Configuration version number')
    )
    previous_value = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Previous configuration value')
    )
    change_reason = models.TextField(
        blank=True,
        help_text=_('Reason for the last change')
    )
    
    # Management and ownership
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_configs',
        help_text=_('User who created this configuration')
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_configs',
        help_text=_('User who last updated this configuration')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Tags for categorization')
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional metadata')
    )
    
    class Meta:
        verbose_name = _('system configuration')
        verbose_name_plural = _('system configurations')
        ordering = ['config_type', 'key']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['config_type', 'is_active']),
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"{self.key} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method with versioning"""
        # Track version changes
        if self.pk:
            try:
                old_instance = SystemConfig.objects.get(pk=self.pk)
                if old_instance.value != self.value:
                    self.previous_value = old_instance.value
                    self.version += 1
            except SystemConfig.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate configuration value"""
        super().clean()
        
        # Validate against allowed values
        if self.allowed_values and self.value not in self.allowed_values:
            raise ValidationError(f'Value must be one of: {self.allowed_values}')
        
        # Apply validation rules (basic implementation)
        if self.validation_rules:
            # This could be expanded with more sophisticated validation
            if 'type' in self.validation_rules:
                expected_type = self.validation_rules['type']
                if expected_type == 'string' and not isinstance(self.value, str):
                    raise ValidationError('Value must be a string')
                elif expected_type == 'number' and not isinstance(self.value, (int, float)):
                    raise ValidationError('Value must be a number')
                elif expected_type == 'boolean' and not isinstance(self.value, bool):
                    raise ValidationError('Value must be a boolean')
    
    def reset_to_default(self):
        """Reset configuration to default value"""
        if self.default_value is not None:
            self.value = self.default_value
            self.change_reason = 'Reset to default value'
            self.save()
    
    def to_dict(self):
        """Convert configuration to dictionary representation"""
        return {
            'id': str(self.id),
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'config_type': self.config_type,
            'value': self.value,
            'default_value': self.default_value,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'is_editable': self.is_editable,
            'requires_restart': self.requires_restart,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ContentItem(models.Model):
    """
    Model for managing dynamic content items like news, FAQs, announcements, etc.
    """
    
    class ContentType(models.TextChoices):
        NEWS = 'NEWS', _('News Article')
        FAQ = 'FAQ', _('Frequently Asked Question')
        ANNOUNCEMENT = 'ANNOUNCEMENT', _('Announcement')
        GUIDE = 'GUIDE', _('Guide/Tutorial')
        POLICY = 'POLICY', _('Policy Document')
        VENUE_INFO = 'VENUE_INFO', _('Venue Information')
        EVENT_UPDATE = 'EVENT_UPDATE', _('Event Update')
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PUBLISHED = 'PUBLISHED', _('Published')
        ARCHIVED = 'ARCHIVED', _('Archived')
        SCHEDULED = 'SCHEDULED', _('Scheduled')
    
    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        NORMAL = 'NORMAL', _('Normal')
        HIGH = 'HIGH', _('High')
        URGENT = 'URGENT', _('Urgent')
    
    # Basic Information
    title = models.CharField(max_length=200, help_text=_('Content title'))
    slug = models.SlugField(max_length=220, unique=True, help_text=_('URL-friendly version of title'))
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.NEWS)
    
    # Content
    summary = models.TextField(max_length=500, blank=True, help_text=_('Brief summary or excerpt'))
    content = models.TextField(help_text=_('Main content (supports HTML)'))
    featured_image = models.ImageField(upload_to='content/images/', blank=True, null=True)
    
    # Publishing
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    is_featured = models.BooleanField(default=False, help_text=_('Show in featured content'))
    is_pinned = models.BooleanField(default=False, help_text=_('Pin to top of list'))
    
    # Scheduling
    publish_date = models.DateTimeField(default=timezone.now, help_text=_('When to publish this content'))
    expire_date = models.DateTimeField(blank=True, null=True, help_text=_('When to automatically archive'))
    
    # Targeting
    target_audience = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Target audience types (volunteers, staff, public, etc.)')
    )
    related_events = models.ManyToManyField(
        'events.Event',
        blank=True,
        help_text=_('Events this content relates to')
    )
    related_venues = models.ManyToManyField(
        'events.Venue',
        blank=True,
        help_text=_('Venues this content relates to')
    )
    
    # Metadata
    tags = models.JSONField(default=list, blank=True, help_text=_('Content tags for categorization'))
    meta_description = models.CharField(max_length=160, blank=True, help_text=_('SEO meta description'))
    
    # Engagement
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    
    # Management
    author = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='authored_content',
        help_text=_('Content author')
    )
    editor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_content',
        help_text=_('Last editor')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-is_pinned', '-priority', '-publish_date']
        indexes = [
            models.Index(fields=['content_type', 'status']),
            models.Index(fields=['publish_date', 'status']),
            models.Index(fields=['is_featured', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_content_type_display()}: {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Set published_at when status changes to PUBLISHED
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def is_published(self):
        """Check if content is currently published"""
        if self.status != self.Status.PUBLISHED:
            return False
        
        now = timezone.now()
        if self.publish_date > now:
            return False
        
        if self.expire_date and self.expire_date < now:
            return False
        
        return True
    
    def get_absolute_url(self):
        """Get URL for this content item"""
        return f"/content/{self.content_type.lower()}/{self.slug}/"
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class FAQ(models.Model):
    """
    Specialized model for Frequently Asked Questions with categorization.
    """
    
    class Category(models.TextChoices):
        GENERAL = 'GENERAL', _('General')
        REGISTRATION = 'REGISTRATION', _('Registration')
        TRAINING = 'TRAINING', _('Training')
        EVENTS = 'EVENTS', _('Events')
        VENUES = 'VENUES', _('Venues')
        ROLES = 'ROLES', _('Roles & Responsibilities')
        TRANSPORT = 'TRANSPORT', _('Transport')
        ACCOMMODATION = 'ACCOMMODATION', _('Accommodation')
        FOOD = 'FOOD', _('Food & Catering')
        UNIFORMS = 'UNIFORMS', _('Uniforms & Equipment')
        JUSTGO = 'JUSTGO', _('JustGo Integration')
        TECHNICAL = 'TECHNICAL', _('Technical Support')
    
    # Content
    question = models.CharField(max_length=300, help_text=_('The question'))
    answer = models.TextField(help_text=_('The answer (supports HTML)'))
    
    # Categorization
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    tags = models.JSONField(default=list, blank=True, help_text=_('Tags for better searchability'))
    
    # Targeting
    target_audience = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Who this FAQ is for (volunteers, staff, public)')
    )
    
    # Management
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text=_('Display order within category'))
    
    # Engagement
    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Management
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_faqs'
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_faqs'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'order', 'question']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_active', 'order']),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.question[:50]}..."
    
    def get_helpfulness_ratio(self):
        """Calculate helpfulness ratio"""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100


class VenueInformation(models.Model):
    """
    Venue information for public display
    """
    venue = models.OneToOneField(
        'events.Venue',
        on_delete=models.CASCADE,
        related_name='public_info'
    )
    description = models.TextField(
        default="Venue information will be updated soon.",
        help_text="Public description of the venue"
    )
    facilities = models.JSONField(
        default=dict,
        help_text="Available facilities (JSON format)"
    )
    accessibility_info = models.TextField(
        blank=True,
        help_text="Accessibility information"
    )
    contact_info = models.JSONField(
        default=dict,
        help_text="Contact information (JSON format)"
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this venue info is publicly visible"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Venue Information"
        verbose_name_plural = "Venue Information"

    def __str__(self):
        return f"Info for {self.venue.name}"


class Theme(models.Model):
    """
    Dynamic theme management for the admin interface and public site
    """
    THEME_TYPES = [
        ('ADMIN', 'Admin Interface'),
        ('PUBLIC', 'Public Website'),
        ('MOBILE', 'Mobile Interface'),
        ('EMAIL', 'Email Templates'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Theme name (e.g., 'SOI Default', 'Dark Mode', 'High Contrast')"
    )
    
    theme_type = models.CharField(
        max_length=20,
        choices=THEME_TYPES,
        default='ADMIN',
        help_text="Type of interface this theme applies to"
    )
    
    # Primary Colors
    primary_color = models.CharField(
        max_length=7,
        default='#2E7D32',
        help_text="Primary brand color (hex format: #RRGGBB)"
    )
    
    secondary_color = models.CharField(
        max_length=7,
        default='#1B5E20',
        help_text="Secondary brand color (hex format: #RRGGBB)"
    )
    
    accent_color = models.CharField(
        max_length=7,
        default='#FFD700',
        help_text="Accent color for highlights (hex format: #RRGGBB)"
    )
    
    # Background Colors
    background_color = models.CharField(
        max_length=7,
        default='#FFFFFF',
        help_text="Main background color (hex format: #RRGGBB)"
    )
    
    surface_color = models.CharField(
        max_length=7,
        default='#F8F9FA',
        help_text="Surface/card background color (hex format: #RRGGBB)"
    )
    
    # Text Colors
    text_primary = models.CharField(
        max_length=7,
        default='#212529',
        help_text="Primary text color (hex format: #RRGGBB)"
    )
    
    text_secondary = models.CharField(
        max_length=7,
        default='#6C757D',
        help_text="Secondary text color (hex format: #RRGGBB)"
    )
    
    text_on_primary = models.CharField(
        max_length=7,
        default='#FFFFFF',
        help_text="Text color on primary background (hex format: #RRGGBB)"
    )
    
    # Status Colors
    success_color = models.CharField(
        max_length=7,
        default='#28A745',
        help_text="Success/positive action color (hex format: #RRGGBB)"
    )
    
    warning_color = models.CharField(
        max_length=7,
        default='#FFC107',
        help_text="Warning/caution color (hex format: #RRGGBB)"
    )
    
    error_color = models.CharField(
        max_length=7,
        default='#DC3545',
        help_text="Error/danger color (hex format: #RRGGBB)"
    )
    
    info_color = models.CharField(
        max_length=7,
        default='#17A2B8',
        help_text="Information color (hex format: #RRGGBB)"
    )
    
    # Typography
    font_family_primary = models.CharField(
        max_length=200,
        default="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        help_text="Primary font family CSS declaration"
    )
    
    font_family_secondary = models.CharField(
        max_length=200,
        default="'Courier New', monospace",
        help_text="Secondary font family for code/monospace text"
    )
    
    font_size_base = models.CharField(
        max_length=10,
        default='14px',
        help_text="Base font size (e.g., '14px', '1rem')"
    )
    
    # Layout
    border_radius = models.CharField(
        max_length=10,
        default='6px',
        help_text="Default border radius for rounded corners"
    )
    
    box_shadow = models.CharField(
        max_length=100,
        default='0 2px 8px rgba(0,0,0,0.1)',
        help_text="Default box shadow CSS"
    )
    
    # Branding
    logo_url = models.URLField(
        blank=True,
        help_text="URL to logo image (optional)"
    )
    
    favicon_url = models.URLField(
        blank=True,
        help_text="URL to favicon (optional)"
    )
    
    # Custom CSS
    custom_css = models.TextField(
        blank=True,
        help_text="Additional custom CSS rules (advanced users only)"
    )
    
    # Theme Settings
    is_active = models.BooleanField(
        default=False,
        help_text="Whether this theme is currently active"
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default theme for new users"
    )
    
    is_dark_mode = models.BooleanField(
        default=False,
        help_text="Whether this is a dark mode theme"
    )
    
    accessibility_compliant = models.BooleanField(
        default=True,
        help_text="Whether this theme meets accessibility standards"
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        help_text="Description of this theme"
    )
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_themes',
        help_text="User who created this theme"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Theme"
        verbose_name_plural = "Themes"
        ordering = ['theme_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['theme_type', 'is_active'],
                condition=models.Q(is_active=True),
                name='unique_active_theme_per_type'
            ),
            models.UniqueConstraint(
                fields=['theme_type', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_theme_per_type'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_theme_type_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one active theme per type"""
        if self.is_active:
            # Deactivate other themes of the same type
            Theme.objects.filter(
                theme_type=self.theme_type,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        
        if self.is_default:
            # Ensure only one default theme per type
            Theme.objects.filter(
                theme_type=self.theme_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def get_css_variables(self):
        """Generate CSS custom properties for this theme"""
        return {
            '--soi-primary': self.primary_color,
            '--soi-secondary': self.secondary_color,
            '--soi-accent': self.accent_color,
            '--soi-background': self.background_color,
            '--soi-surface': self.surface_color,
            '--soi-text-primary': self.text_primary,
            '--soi-text-secondary': self.text_secondary,
            '--soi-text-on-primary': self.text_on_primary,
            '--soi-success': self.success_color,
            '--soi-warning': self.warning_color,
            '--soi-error': self.error_color,
            '--soi-info': self.info_color,
            '--soi-font-primary': self.font_family_primary,
            '--soi-font-secondary': self.font_family_secondary,
            '--soi-font-size-base': self.font_size_base,
            '--soi-border-radius': self.border_radius,
            '--soi-box-shadow': self.box_shadow,
        }
    
    def generate_css(self):
        """Generate complete CSS for this theme with enhanced readability"""
        css_vars = self.get_css_variables()
        
        css = ":root {\n"
        for var, value in css_vars.items():
            css += f"  {var}: {value};\n"
        css += "}\n\n"
        
        # Add enhanced theme styles with focus on readability
        css += """
/* SOI Hub Dynamic Theme Styles - Enhanced for Readability */

/* Base Typography and Readability */
body, .form-row, .form-row p, .help, .helptext {
    font-family: var(--soi-font-family-primary) !important;
    font-size: var(--soi-font-size-base) !important;
    line-height: 1.6 !important;
    color: var(--soi-text-primary) !important;
}

/* Enhanced Text Contrast and Readability */
.form-row label, .form-row .label, th, .column-header {
    font-weight: 600 !important;
    color: var(--soi-text-primary) !important;
    font-size: calc(var(--soi-font-size-base) + 1px) !important;
}

/* Improved Input Field Readability */
input[type="text"], input[type="email"], input[type="password"], 
input[type="number"], input[type="url"], input[type="tel"], 
textarea, select {
    font-family: var(--soi-font-family-primary) !important;
    font-size: var(--soi-font-size-base) !important;
    line-height: 1.5 !important;
    padding: 8px 12px !important;
    border: 2px solid #e0e0e0 !important;
    border-radius: var(--soi-border-radius) !important;
    background-color: var(--soi-background) !important;
    color: var(--soi-text-primary) !important;
}

input:focus, textarea:focus, select:focus {
    border-color: var(--soi-primary) !important;
    box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.1) !important;
    outline: none !important;
}

/* Enhanced Table Readability */
.results table, .change-list table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
    background: var(--soi-background) !important;
}

.results th, .change-list th {
    background: var(--soi-surface) !important;
    color: var(--soi-text-primary) !important;
    font-weight: 600 !important;
    padding: 12px 8px !important;
    border-bottom: 2px solid var(--soi-primary) !important;
    font-size: calc(var(--soi-font-size-base) + 1px) !important;
}

.results td, .change-list td {
    padding: 10px 8px !important;
    border-bottom: 1px solid #f0f0f0 !important;
    background: var(--soi-background) !important;
    color: var(--soi-text-primary) !important;
    line-height: 1.5 !important;
}

.results tr:hover td, .change-list tr:hover td {
    background: var(--soi-surface) !important;
}

/* Enhanced Link Readability */
a, a:link {
    color: var(--soi-primary) !important;
    text-decoration: underline !important;
    font-weight: 500 !important;
}

a:hover {
    color: var(--soi-secondary) !important;
    text-decoration: underline !important;
}

a:visited {
    color: #1B5E20 !important;
}

/* Theme Utility Classes */
.soi-theme-primary {
    background-color: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
}

.soi-theme-secondary {
    background-color: var(--soi-secondary) !important;
    color: var(--soi-text-on-primary) !important;
}

.soi-theme-accent {
    background-color: var(--soi-accent) !important;
    color: var(--soi-text-primary) !important;
}

.soi-theme-surface {
    background-color: var(--soi-surface) !important;
    color: var(--soi-text-primary) !important;
}

.soi-text-primary {
    color: var(--soi-text-primary) !important;
}

.soi-text-secondary {
    color: var(--soi-text-secondary) !important;
}

.soi-border-primary {
    border-color: var(--soi-primary) !important;
}

.soi-rounded {
    border-radius: var(--soi-border-radius) !important;
}

.soi-shadow {
    box-shadow: var(--soi-box-shadow) !important;
}

/* Enhanced Admin Interface Styling */
#header {
    background: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    padding: 15px 20px !important;
}

#header h1, #header h1 a {
    color: var(--soi-text-on-primary) !important;
    font-weight: 600 !important;
    font-size: 1.4em !important;
}

/* Enhanced Module Headers */
.module h2, .module caption, .inline-group h2 {
    background: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    font-weight: 600 !important;
    font-size: 1.1em !important;
    padding: 12px 15px !important;
    border-radius: var(--soi-border-radius) var(--soi-border-radius) 0 0 !important;
}

/* Enhanced Button Styling */
.button, input[type=submit], input[type=button], .submit-row input, a.button {
    background: var(--soi-primary) !important;
    border: 2px solid var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    font-weight: 600 !important;
    font-size: var(--soi-font-size-base) !important;
    padding: 10px 20px !important;
    border-radius: var(--soi-border-radius) !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

.button:hover, input[type=submit]:hover, input[type=button]:hover, 
.submit-row input:hover, a.button:hover {
    background: var(--soi-secondary) !important;
    border-color: var(--soi-secondary) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
}

/* Enhanced Navigation and Breadcrumbs */
.breadcrumbs {
    background: var(--soi-surface) !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: var(--soi-border-radius) !important;
    padding: 12px 15px !important;
    margin-bottom: 20px !important;
    font-size: calc(var(--soi-font-size-base) + 1px) !important;
}

.breadcrumbs a {
    color: var(--soi-primary) !important;
    font-weight: 500 !important;
}

/* Enhanced Object Tools */
.object-tools {
    margin-bottom: 15px !important;
}

.object-tools a {
    background: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    padding: 8px 15px !important;
    border-radius: var(--soi-border-radius) !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    margin-left: 10px !important;
    transition: all 0.2s ease !important;
}

.object-tools a:hover {
    background: var(--soi-secondary) !important;
    transform: translateY(-1px) !important;
}

/* Enhanced Form Styling */
.form-row {
    margin-bottom: 15px !important;
    padding: 10px 0 !important;
}

.form-row .help, .form-row .helptext {
    color: var(--soi-text-secondary) !important;
    font-size: calc(var(--soi-font-size-base) - 1px) !important;
    line-height: 1.5 !important;
    margin-top: 5px !important;
}

/* Enhanced Error and Success Messages */
.errorlist {
    background: #ffebee !important;
    border: 1px solid var(--soi-error) !important;
    border-radius: var(--soi-border-radius) !important;
    padding: 10px 15px !important;
    margin: 10px 0 !important;
    color: #c62828 !important;
    font-weight: 500 !important;
}

.messagelist .success {
    background: #e8f5e8 !important;
    border: 1px solid var(--soi-success) !important;
    color: #2e7d32 !important;
}

.messagelist .warning {
    background: #fff8e1 !important;
    border: 1px solid var(--soi-warning) !important;
    color: #f57c00 !important;
}

.messagelist .error {
    background: #ffebee !important;
    border: 1px solid var(--soi-error) !important;
    color: #c62828 !important;
}

/* Enhanced Selector Widgets */
.selector-chosen h2 {
    background: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
}

.selector .selector-available, .selector .selector-chosen {
    background: var(--soi-background) !important;
    border: 1px solid #e0e0e0 !important;
}

/* Enhanced Calendar and Time Widgets */
.calendar td.selected a {
    background: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    font-weight: 600 !important;
}

.timelist a {
    color: var(--soi-primary) !important;
    font-weight: 500 !important;
}

/* Enhanced Filter Sidebar */
#changelist-filter {
    background: var(--soi-surface) !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: var(--soi-border-radius) !important;
}

#changelist-filter h2 {
    background: var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    font-weight: 600 !important;
    padding: 10px 15px !important;
}

#changelist-filter h3 {
    color: var(--soi-text-primary) !important;
    font-weight: 600 !important;
    font-size: calc(var(--soi-font-size-base) + 1px) !important;
}

/* Enhanced Search Box */
#changelist-search input[type="text"] {
    font-size: var(--soi-font-size-base) !important;
    padding: 10px 15px !important;
    border: 2px solid #e0e0e0 !important;
    border-radius: var(--soi-border-radius) !important;
}

#changelist-search input[type="submit"] {
    background: var(--soi-primary) !important;
    border: 2px solid var(--soi-primary) !important;
    color: var(--soi-text-on-primary) !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: var(--soi-border-radius) !important;
}

/* Accessibility Enhancements */
:focus {
    outline: 3px solid rgba(46, 125, 50, 0.3) !important;
    outline-offset: 2px !important;
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
    input, textarea, select {
        border-width: 3px !important;
    }
    
    .button, input[type=submit], input[type=button] {
        border-width: 3px !important;
        font-weight: 700 !important;
    }
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
"""
        
        # Add custom CSS if provided
        if self.custom_css:
            css += "\n/* Custom CSS */\n"
            css += self.custom_css
        
        return css
    
    @classmethod
    def get_active_theme(cls, theme_type='ADMIN'):
        """Get the currently active theme for a given type"""
        try:
            return cls.objects.get(theme_type=theme_type, is_active=True)
        except cls.DoesNotExist:
            # Return default theme or create one if none exists
            return cls.get_or_create_default_theme(theme_type)
    
    @classmethod
    def get_or_create_default_theme(cls, theme_type='ADMIN'):
        """Get or create the default SOI theme"""
        theme, created = cls.objects.get_or_create(
            name=f'SOI Default {theme_type.title()}',
            theme_type=theme_type,
            defaults={
                'description': f'Default SOI Hub theme for {theme_type.lower()} interface',
                'is_active': True,
                'is_default': True,
                'accessibility_compliant': True,
            }
        )
        return theme


class UserThemePreference(models.Model):
    """
    User-specific theme preferences
    """
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='theme_preference'
    )
    
    admin_theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_users',
        limit_choices_to={'theme_type': 'ADMIN'},
        help_text="Preferred admin interface theme"
    )
    
    mobile_theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mobile_users',
        limit_choices_to={'theme_type': 'MOBILE'},
        help_text="Preferred mobile interface theme"
    )
    
    use_dark_mode = models.BooleanField(
        default=False,
        help_text="Prefer dark mode themes when available"
    )
    
    use_high_contrast = models.BooleanField(
        default=False,
        help_text="Use high contrast themes for accessibility"
    )
    
    font_size_preference = models.CharField(
        max_length=20,
        choices=[
            ('SMALL', 'Small (12px)'),
            ('NORMAL', 'Normal (14px)'),
            ('LARGE', 'Large (16px)'),
            ('EXTRA_LARGE', 'Extra Large (18px)'),
        ],
        default='NORMAL',
        help_text="Preferred font size"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Theme Preference"
        verbose_name_plural = "User Theme Preferences"
    
    def __str__(self):
        return f"Theme preferences for {self.user.username}"
    
    def get_effective_theme(self, theme_type='ADMIN'):
        """Get the effective theme for this user and theme type"""
        if theme_type == 'ADMIN' and self.admin_theme:
            return self.admin_theme
        elif theme_type == 'MOBILE' and self.mobile_theme:
            return self.mobile_theme
        else:
            # Fall back to system default
            return Theme.get_active_theme(theme_type) 