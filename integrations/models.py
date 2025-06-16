from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
import uuid

User = get_user_model()


class JustGoSync(models.Model):
    """
    Model for tracking JustGo synchronization operations
    """
    
    class SyncType(models.TextChoices):
        LOCAL_TO_JUSTGO = 'LOCAL_TO_JUSTGO', _('Local to JustGo')
        JUSTGO_TO_LOCAL = 'JUSTGO_TO_LOCAL', _('JustGo to Local')
        BIDIRECTIONAL = 'BIDIRECTIONAL', _('Bidirectional')
        CREDENTIAL_SYNC = 'CREDENTIAL_SYNC', _('Credential Sync')
        BULK_SYNC = 'BULK_SYNC', _('Bulk Sync')
    
    class SyncStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        PARTIAL = 'PARTIAL', _('Partial Success')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Sync details
    sync_type = models.CharField(
        max_length=20,
        choices=SyncType.choices,
        help_text=_('Type of synchronization operation')
    )
    status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        help_text=_('Current status of the sync operation')
    )
    
    # User and timing
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_syncs',
        help_text=_('User who initiated the sync')
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the sync was started')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the sync was completed')
    )
    
    # Sync metrics
    total_records = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of records to sync')
    )
    processed_records = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of records processed')
    )
    successful_records = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of records successfully synced')
    )
    failed_records = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of records that failed to sync')
    )
    
    # Sync configuration and results
    sync_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Configuration parameters for the sync')
    )
    sync_results = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Detailed results of the sync operation')
    )
    error_details = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of errors encountered during sync')
    )
    
    # Admin override tracking
    is_admin_override = models.BooleanField(
        default=False,
        help_text=_('Whether this sync was performed with admin override')
    )
    override_justification = models.TextField(
        blank=True,
        help_text=_('Justification for admin override if applicable')
    )
    
    # Progress tracking
    progress_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=_('Progress percentage (0-100)')
    )
    current_operation = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Description of current operation')
    )
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', 'sync_type']),
            models.Index(fields=['initiated_by', 'started_at']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.started_at})"
    
    @property
    def duration(self):
        """Get sync duration"""
        if self.completed_at:
            return self.completed_at - self.started_at
        elif self.status == self.SyncStatus.IN_PROGRESS:
            return timezone.now() - self.started_at
        return None
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.processed_records > 0:
            return (self.successful_records / self.processed_records) * 100
        return 0.0
    
    def update_progress(self, processed: int, successful: int, failed: int, current_op: str = ''):
        """Update sync progress"""
        self.processed_records = processed
        self.successful_records = successful
        self.failed_records = failed
        self.current_operation = current_op
        
        if self.total_records > 0:
            self.progress_percentage = (processed / self.total_records) * 100
        
        self.save(update_fields=[
            'processed_records', 'successful_records', 'failed_records',
            'progress_percentage', 'current_operation'
        ])
    
    def complete(self, status: SyncStatus = None):
        """Mark sync as completed"""
        self.status = status or self.SyncStatus.COMPLETED
        self.completed_at = timezone.now()
        self.progress_percentage = 100.0
        self.save(update_fields=['status', 'completed_at', 'progress_percentage'])


class JustGoMemberMapping(models.Model):
    """
    Model for mapping local users to JustGo members
    """
    
    class MappingStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        INACTIVE = 'INACTIVE', _('Inactive')
        PENDING = 'PENDING', _('Pending Verification')
        CONFLICT = 'CONFLICT', _('Conflict Detected')
        ARCHIVED = 'ARCHIVED', _('Archived')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Local user reference
    local_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='justgo_mapping',
        help_text=_('Local user account')
    )
    
    # JustGo identifiers
    justgo_member_id = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('JustGo member GUID')
    )
    justgo_mid = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('JustGo Member ID (MID)')
    )
    justgo_member_doc_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('JustGo member document ID')
    )
    
    # Mapping metadata
    status = models.CharField(
        max_length=15,
        choices=MappingStatus.choices,
        default=MappingStatus.PENDING,
        help_text=_('Status of the mapping')
    )
    confidence_score = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Confidence score of the mapping (0-1)')
    )
    
    # Sync tracking
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the mapping was last synchronized')
    )
    last_sync_direction = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Direction of last sync (local_to_justgo, justgo_to_local)')
    )
    sync_conflicts = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of sync conflicts detected')
    )
    
    # Verification and audit
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_mappings',
        help_text=_('User who verified this mapping')
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the mapping was verified')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional metadata
    mapping_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional mapping metadata and configuration')
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['justgo_member_id']),
            models.Index(fields=['justgo_mid']),
            models.Index(fields=['status', 'confidence_score']),
            models.Index(fields=['last_synced_at']),
        ]
    
    def __str__(self):
        return f"{self.local_user.email} -> JustGo:{self.justgo_member_id}"
    
    def verify(self, verified_by: User):
        """Verify the mapping"""
        self.status = self.MappingStatus.ACTIVE
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.save(update_fields=['status', 'verified_by', 'verified_at'])
    
    def add_conflict(self, conflict_description: str):
        """Add a sync conflict"""
        if not self.sync_conflicts:
            self.sync_conflicts = []
        
        conflict = {
            'timestamp': timezone.now().isoformat(),
            'description': conflict_description
        }
        self.sync_conflicts.append(conflict)
        
        if self.status == self.MappingStatus.ACTIVE:
            self.status = self.MappingStatus.CONFLICT
        
        self.save(update_fields=['sync_conflicts', 'status'])
    
    def update_sync_info(self, direction: str):
        """Update sync information"""
        self.last_synced_at = timezone.now()
        self.last_sync_direction = direction
        self.save(update_fields=['last_synced_at', 'last_sync_direction'])


class IntegrationLog(models.Model):
    """
    Model for logging all JustGo API interactions
    """
    
    class LogLevel(models.TextChoices):
        DEBUG = 'DEBUG', _('Debug')
        INFO = 'INFO', _('Info')
        WARNING = 'WARNING', _('Warning')
        ERROR = 'ERROR', _('Error')
        CRITICAL = 'CRITICAL', _('Critical')
    
    class OperationType(models.TextChoices):
        AUTHENTICATION = 'AUTHENTICATION', _('Authentication')
        MEMBER_LOOKUP = 'MEMBER_LOOKUP', _('Member Lookup')
        MEMBER_CREATE = 'MEMBER_CREATE', _('Member Create')
        MEMBER_UPDATE = 'MEMBER_UPDATE', _('Member Update')
        CREDENTIAL_LOOKUP = 'CREDENTIAL_LOOKUP', _('Credential Lookup')
        SYNC_OPERATION = 'SYNC_OPERATION', _('Sync Operation')
        HEALTH_CHECK = 'HEALTH_CHECK', _('Health Check')
        ADMIN_OVERRIDE = 'ADMIN_OVERRIDE', _('Admin Override')
        OTHER = 'OTHER', _('Other')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Log details
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO,
        help_text=_('Log level')
    )
    operation_type = models.CharField(
        max_length=20,
        choices=OperationType.choices,
        help_text=_('Type of operation')
    )
    message = models.TextField(
        help_text=_('Log message')
    )
    
    # Context information
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='integration_logs',
        help_text=_('User associated with the operation')
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text=_('Session key')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('IP address of the request')
    )
    
    # API details
    api_endpoint = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('JustGo API endpoint called')
    )
    http_method = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('HTTP method used')
    )
    status_code = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('HTTP status code returned')
    )
    response_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('Response time in milliseconds')
    )
    
    # Request/Response data
    request_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Request data (sensitive data excluded)')
    )
    response_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Response data (sensitive data excluded)')
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Error details if applicable')
    )
    
    # Sync operation reference
    sync_operation = models.ForeignKey(
        JustGoSync,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        help_text=_('Associated sync operation')
    )
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional metadata')
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level', 'operation_type']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['api_endpoint', 'timestamp']),
            models.Index(fields=['status_code', 'timestamp']),
            models.Index(fields=['sync_operation', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_level_display()} - {self.get_operation_type_display()} ({self.timestamp})"


class JustGoCredentialCache(models.Model):
    """
    Model for caching JustGo credential information
    """
    
    class CredentialStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        EXPIRED = 'EXPIRED', _('Expired')
        PENDING = 'PENDING', _('Pending')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        REVOKED = 'REVOKED', _('Revoked')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Member reference
    member_mapping = models.ForeignKey(
        JustGoMemberMapping,
        on_delete=models.CASCADE,
        related_name='cached_credentials',
        help_text=_('Associated member mapping')
    )
    
    # Credential details
    justgo_credential_id = models.CharField(
        max_length=100,
        help_text=_('JustGo credential ID')
    )
    credential_type = models.CharField(
        max_length=100,
        help_text=_('Type of credential')
    )
    credential_name = models.CharField(
        max_length=255,
        help_text=_('Name of the credential')
    )
    status = models.CharField(
        max_length=15,
        choices=CredentialStatus.choices,
        help_text=_('Current status of the credential')
    )
    
    # Dates
    issued_date = models.DateField(
        null=True,
        blank=True,
        help_text=_('Date the credential was issued')
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_('Date the credential expires')
    )
    
    # Cache metadata
    cached_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When this credential was cached')
    )
    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When this credential was last verified with JustGo')
    )
    
    # Full credential data
    credential_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Full credential data from JustGo')
    )
    
    class Meta:
        ordering = ['-cached_at']
        unique_together = ['member_mapping', 'justgo_credential_id']
        indexes = [
            models.Index(fields=['credential_type', 'status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['status', 'expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.credential_name} - {self.get_status_display()}"
    
    @property
    def is_expired(self):
        """Check if credential is expired"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None
    
    def is_expiring_soon(self, days_ahead: int = 30):
        """Check if credential is expiring soon"""
        days_until = self.days_until_expiry
        return days_until is not None and 0 <= days_until <= days_ahead
