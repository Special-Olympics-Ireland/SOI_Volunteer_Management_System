from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import json

User = get_user_model()

class Event(models.Model):
    """
    Event model supporting ISG 2026 and future SOI events.
    Provides hierarchical Event → Venues → Roles → Assignments structure
    with flexible JSON configuration and comprehensive status management.
    """
    
    class EventStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PLANNING = 'PLANNING', _('Planning')
        REGISTRATION_OPEN = 'REGISTRATION_OPEN', _('Registration Open')
        REGISTRATION_CLOSED = 'REGISTRATION_CLOSED', _('Registration Closed')
        ACTIVE = 'ACTIVE', _('Active/Ongoing')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        ARCHIVED = 'ARCHIVED', _('Archived')
    
    class EventType(models.TextChoices):
        INTERNATIONAL_GAMES = 'INTERNATIONAL_GAMES', _('International Games')
        NATIONAL_GAMES = 'NATIONAL_GAMES', _('National Games')
        REGIONAL_GAMES = 'REGIONAL_GAMES', _('Regional Games')
        LOCAL_EVENT = 'LOCAL_EVENT', _('Local Event')
        TRAINING_EVENT = 'TRAINING_EVENT', _('Training Event')
        FUNDRAISING = 'FUNDRAISING', _('Fundraising Event')
        OTHER = 'OTHER', _('Other')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200,
        help_text=_('Event name (e.g., "ISG 2026")')
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text=_('URL-friendly event identifier')
    )
    short_name = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Short name for display (e.g., "ISG26")')
    )
    
    # Event classification
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        default=EventType.INTERNATIONAL_GAMES,
        help_text=_('Type of event')
    )
    status = models.CharField(
        max_length=30,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT,
        help_text=_('Current event status')
    )
    
    # Event details
    description = models.TextField(
        blank=True,
        help_text=_('Detailed event description')
    )
    tagline = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Event tagline or motto')
    )
    
    # Dates and timing
    start_date = models.DateField(
        help_text=_('Event start date')
    )
    end_date = models.DateField(
        help_text=_('Event end date')
    )
    registration_open_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer registration opens')
    )
    registration_close_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer registration closes')
    )
    
    # Location information
    host_city = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Primary host city')
    )
    host_country = models.CharField(
        max_length=100,
        default='Ireland',
        help_text=_('Host country')
    )
    timezone = models.CharField(
        max_length=50,
        default='Europe/Dublin',
        help_text=_('Event timezone')
    )
    
    # Volunteer management
    volunteer_target = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Target number of volunteers')
    )
    volunteer_minimum_age = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(13), MaxValueValidator(25)],
        help_text=_('Minimum age for volunteers')
    )
    
    # Configuration JSON fields for flexible setup
    event_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Event-specific configuration settings')
    )
    volunteer_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Volunteer management configuration')
    )
    venue_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Venue management configuration')
    )
    role_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Role and assignment configuration')
    )
    
    # Content management
    welcome_message = models.TextField(
        blank=True,
        help_text=_('Welcome message for volunteers')
    )
    instructions = models.TextField(
        blank=True,
        help_text=_('General instructions for volunteers')
    )
    contact_information = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Event contact information')
    )
    
    # Branding and assets
    logo = models.ImageField(
        upload_to='events/logos/',
        blank=True,
        null=True,
        help_text=_('Event logo')
    )
    banner_image = models.ImageField(
        upload_to='events/banners/',
        blank=True,
        null=True,
        help_text=_('Event banner image')
    )
    brand_colors = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Event brand colors (primary, secondary, etc.)')
    )
    
    # Features and capabilities
    features_enabled = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Enabled features for this event')
    )
    integrations_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Third-party integration configuration')
    )
    
    # Management and ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_events',
        help_text=_('User who created this event')
    )
    event_managers = models.ManyToManyField(
        User,
        blank=True,
        related_name='managed_events',
        help_text=_('Users who can manage this event')
    )
    
    # Status tracking
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this event is active')
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Whether this event should be featured')
    )
    is_public = models.BooleanField(
        default=True,
        help_text=_('Whether this event is publicly visible')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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
        related_name='status_changed_events',
        help_text=_('User who last changed the status')
    )
    
    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about this event')
    )
    external_references = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('External system references and IDs')
    )
    
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        ordering = ['-start_date', 'name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['event_type']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')),
                name='event_end_date_after_start_date'
            ),
            models.CheckConstraint(
                check=models.Q(volunteer_target__gte=0),
                name='event_volunteer_target_non_negative'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.start_date.year})"
    
    def save(self, *args, **kwargs):
        """Custom save method with validation and auto-updates"""
        # Update status change tracking
        if self.pk:
            try:
                old_instance = Event.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.status_changed_at = timezone.now()
                    # status_changed_by should be set by the view/admin
            except Event.DoesNotExist:
                # This is a new object, no need to track status changes
                pass
        
        # Set default configurations if empty
        if not self.event_configuration:
            self.event_configuration = self._get_default_event_configuration()
        
        if not self.volunteer_configuration:
            self.volunteer_configuration = self._get_default_volunteer_configuration()
        
        if not self.venue_configuration:
            self.venue_configuration = self._get_default_venue_configuration()
        
        if not self.role_configuration:
            self.role_configuration = self._get_default_role_configuration()
        
        if not self.features_enabled:
            self.features_enabled = self._get_default_features()
        
        if not self.brand_colors:
            self.brand_colors = self._get_default_brand_colors()
        
        super().save(*args, **kwargs)
    
    def _get_default_event_configuration(self):
        """Get default event configuration"""
        return {
            'allow_late_registration': False,
            'require_photo_upload': True,
            'require_emergency_contact': True,
            'enable_venue_preferences': True,
            'max_venue_preferences': 3,
            'enable_skill_matching': True,
            'enable_availability_tracking': True,
            'auto_assignment_enabled': False,
            'notification_preferences': {
                'email_confirmations': True,
                'sms_reminders': False,
                'assignment_notifications': True
            }
        }
    
    def _get_default_volunteer_configuration(self):
        """Get default volunteer configuration"""
        return {
            'types_enabled': [
                'GENERAL',
                'EXISTING_SOI',
                'CORPORATE',
                'COMMUNITY',
                'THIRD_PARTY',
                'ATHLETE'
            ],
            'approval_required': True,
            'background_check_required': True,
            'training_required': False,
            'uniform_required': True,
            'dietary_requirements_enabled': True,
            'accessibility_support_enabled': True,
            'transport_assistance_enabled': False,
            'accommodation_assistance_enabled': False
        }
    
    def _get_default_venue_configuration(self):
        """Get default venue configuration"""
        return {
            'capacity_tracking_enabled': True,
            'accessibility_info_required': True,
            'transport_info_required': True,
            'parking_info_required': True,
            'facilities_info_required': True,
            'contact_info_required': True,
            'emergency_procedures_required': True
        }
    
    def _get_default_role_configuration(self):
        """Get default role configuration"""
        return {
            'skill_matching_enabled': True,
            'experience_levels': ['Beginner', 'Intermediate', 'Advanced'],
            'shift_patterns_enabled': True,
            'task_management_enabled': True,
            'credential_validation_enabled': True,
            'capacity_limits_enabled': True,
            'waitlist_enabled': True,
            'auto_assignment_rules': {
                'prefer_experience': True,
                'prefer_skills_match': True,
                'prefer_venue_preference': True
            }
        }
    
    def _get_default_features(self):
        """Get default enabled features"""
        return {
            'volunteer_registration': True,
            'role_assignment': True,
            'task_management': True,
            'communication_tools': True,
            'reporting_analytics': True,
            'justgo_integration': True,
            'admin_overrides': True,
            'bulk_operations': True,
            'export_capabilities': True,
            'audit_logging': True
        }
    
    def _get_default_brand_colors(self):
        """Get default SOI brand colors"""
        return {
            'primary': '#228B22',      # SOI Green
            'secondary': '#FFD700',    # SOI Gold
            'accent': '#FFFFFF',       # White
            'text_primary': '#333333',
            'text_secondary': '#666666',
            'background': '#FFFFFF',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
            'info': '#17a2b8'
        }
    
    # Status management methods
    def can_register_volunteers(self):
        """Check if volunteer registration is currently open"""
        now = timezone.now()
        
        # Check status
        if self.status not in [self.EventStatus.REGISTRATION_OPEN, self.EventStatus.PLANNING]:
            return False
        
        # Check dates
        if self.registration_open_date and now < self.registration_open_date:
            return False
        
        if self.registration_close_date and now > self.registration_close_date:
            return False
        
        return self.is_active and self.is_public
    
    def is_upcoming(self):
        """Check if event is upcoming"""
        return self.start_date > timezone.now().date()
    
    def is_ongoing(self):
        """Check if event is currently ongoing"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    def is_past(self):
        """Check if event is in the past"""
        return self.end_date < timezone.now().date()
    
    def get_duration_days(self):
        """Get event duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    def get_registration_status(self):
        """Get current registration status"""
        if not self.can_register_volunteers():
            if self.registration_open_date and timezone.now() < self.registration_open_date:
                return 'not_yet_open'
            elif self.registration_close_date and timezone.now() > self.registration_close_date:
                return 'closed'
            else:
                return 'unavailable'
        return 'open'
    
    # Configuration management methods
    def get_configuration(self, config_type, key=None, default=None):
        """Get configuration value"""
        config_map = {
            'event': self.event_configuration,
            'volunteer': self.volunteer_configuration,
            'venue': self.venue_configuration,
            'role': self.role_configuration,
            'features': self.features_enabled,
            'integrations': self.integrations_config,
            'contact': self.contact_information,
            'brand': self.brand_colors,
            'external': self.external_references
        }
        
        config = config_map.get(config_type, {})
        
        if key is None:
            return config
        
        return config.get(key, default)
    
    def set_configuration(self, config_type, key, value):
        """Set configuration value"""
        config_map = {
            'event': 'event_configuration',
            'volunteer': 'volunteer_configuration',
            'venue': 'venue_configuration',
            'role': 'role_configuration',
            'features': 'features_enabled',
            'integrations': 'integrations_config',
            'contact': 'contact_information',
            'brand': 'brand_colors',
            'external': 'external_references'
        }
        
        field_name = config_map.get(config_type)
        if field_name:
            config = getattr(self, field_name, {})
            config[key] = value
            setattr(self, field_name, config)
            self.save(update_fields=[field_name])
    
    def update_configuration(self, config_type, updates):
        """Update multiple configuration values"""
        config_map = {
            'event': 'event_configuration',
            'volunteer': 'volunteer_configuration',
            'venue': 'venue_configuration',
            'role': 'role_configuration',
            'features': 'features_enabled',
            'integrations': 'integrations_config',
            'contact': 'contact_information',
            'brand': 'brand_colors',
            'external': 'external_references'
        }
        
        field_name = config_map.get(config_type)
        if field_name:
            config = getattr(self, field_name, {})
            config.update(updates)
            setattr(self, field_name, config)
            self.save(update_fields=[field_name])
    
    # Relationship methods
    def get_venue_count(self):
        """Get number of venues for this event"""
        return self.venues.count()
    
    def get_role_count(self):
        """Get total number of roles across all venues"""
        # Return 0 until Role model is implemented in Task 2.4
        return 0
    
    def get_volunteer_count(self):
        """Get total number of assigned volunteers"""
        # Return 0 until Assignment model is implemented in Task 2.5
        return 0
    
    def get_volunteer_target_progress(self):
        """Get volunteer recruitment progress percentage"""
        if self.volunteer_target == 0:
            return 0
        return min(100, (self.get_volunteer_count() / self.volunteer_target) * 100)
    
    # Status change methods
    def change_status(self, new_status, changed_by=None, notes=None):
        """Change event status with audit trail"""
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.status_changed_by = changed_by
        
        if notes:
            self.notes = f"{self.notes}\n\n[{timezone.now()}] Status changed from {old_status} to {new_status}: {notes}".strip()
        
        self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'notes'])
    
    def activate(self, activated_by=None):
        """Activate the event"""
        self.is_active = True
        if activated_by:
            self.notes = f"{self.notes}\n\n[{timezone.now()}] Event activated by {activated_by}".strip()
        self.save(update_fields=['is_active', 'notes'])
    
    def deactivate(self, deactivated_by=None, reason=None):
        """Deactivate the event"""
        self.is_active = False
        note = f"[{timezone.now()}] Event deactivated by {deactivated_by}"
        if reason:
            note += f": {reason}"
        self.notes = f"{self.notes}\n\n{note}".strip()
        self.save(update_fields=['is_active', 'notes'])
    
    # Utility methods
    def clone(self, new_name, new_slug, created_by=None):
        """Create a copy of this event with new name and slug"""
        new_event = Event(
            name=new_name,
            slug=new_slug,
            short_name=self.short_name,
            event_type=self.event_type,
            description=self.description,
            tagline=self.tagline,
            start_date=self.start_date,
            end_date=self.end_date,
            host_city=self.host_city,
            host_country=self.host_country,
            timezone=self.timezone,
            volunteer_target=self.volunteer_target,
            volunteer_minimum_age=self.volunteer_minimum_age,
            event_configuration=self.event_configuration.copy(),
            volunteer_configuration=self.volunteer_configuration.copy(),
            venue_configuration=self.venue_configuration.copy(),
            role_configuration=self.role_configuration.copy(),
            welcome_message=self.welcome_message,
            instructions=self.instructions,
            contact_information=self.contact_information.copy(),
            brand_colors=self.brand_colors.copy(),
            features_enabled=self.features_enabled.copy(),
            integrations_config=self.integrations_config.copy(),
            created_by=created_by,
            status=self.EventStatus.DRAFT
        )
        new_event.save()
        return new_event
    
    def get_absolute_url(self):
        """Get absolute URL for this event"""
        from django.urls import reverse
        return reverse('events:event-detail', kwargs={'slug': self.slug})
    
    def to_dict(self):
        """Convert event to dictionary for API responses"""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'short_name': self.short_name,
            'event_type': self.event_type,
            'status': self.status,
            'description': self.description,
            'tagline': self.tagline,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'host_city': self.host_city,
            'host_country': self.host_country,
            'volunteer_target': self.volunteer_target,
            'volunteer_count': self.get_volunteer_count(),
            'venue_count': self.get_venue_count(),
            'role_count': self.get_role_count(),
            'registration_status': self.get_registration_status(),
            'is_active': self.is_active,
            'is_public': self.is_public,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Venue(models.Model):
    """
    Venue model supporting detailed venue management for events.
    Provides comprehensive address, capacity, and configuration management
    with accessibility and facility information.
    """
    
    class VenueType(models.TextChoices):
        SPORTS_FACILITY = 'SPORTS_FACILITY', _('Sports Facility')
        STADIUM = 'STADIUM', _('Stadium')
        ARENA = 'ARENA', _('Arena')
        GYMNASIUM = 'GYMNASIUM', _('Gymnasium')
        POOL = 'POOL', _('Swimming Pool')
        FIELD = 'FIELD', _('Playing Field')
        COURT = 'COURT', _('Court')
        TRACK = 'TRACK', _('Track')
        CONFERENCE_CENTER = 'CONFERENCE_CENTER', _('Conference Center')
        HOTEL = 'HOTEL', _('Hotel')
        ACCOMMODATION = 'ACCOMMODATION', _('Accommodation')
        TRANSPORT_HUB = 'TRANSPORT_HUB', _('Transport Hub')
        MEDICAL_FACILITY = 'MEDICAL_FACILITY', _('Medical Facility')
        CATERING_FACILITY = 'CATERING_FACILITY', _('Catering Facility')
        MEDIA_CENTER = 'MEDIA_CENTER', _('Media Center')
        VOLUNTEER_CENTER = 'VOLUNTEER_CENTER', _('Volunteer Center')
        STORAGE = 'STORAGE', _('Storage Facility')
        OTHER = 'OTHER', _('Other')
    
    class VenueStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PLANNING = 'PLANNING', _('Planning')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        SETUP = 'SETUP', _('Setup in Progress')
        ACTIVE = 'ACTIVE', _('Active/Operational')
        BREAKDOWN = 'BREAKDOWN', _('Breakdown in Progress')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    class AccessibilityLevel(models.TextChoices):
        FULL = 'FULL', _('Fully Accessible')
        PARTIAL = 'PARTIAL', _('Partially Accessible')
        LIMITED = 'LIMITED', _('Limited Accessibility')
        NOT_ACCESSIBLE = 'NOT_ACCESSIBLE', _('Not Accessible')
        UNKNOWN = 'UNKNOWN', _('Accessibility Unknown')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='venues',
        help_text=_('Event this venue belongs to')
    )
    name = models.CharField(
        max_length=200,
        help_text=_('Venue name (e.g., "Aviva Stadium")')
    )
    slug = models.SlugField(
        max_length=200,
        help_text=_('URL-friendly venue identifier')
    )
    short_name = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Short name for display (e.g., "Aviva")')
    )
    
    # Venue classification
    venue_type = models.CharField(
        max_length=30,
        choices=VenueType.choices,
        default=VenueType.SPORTS_FACILITY,
        help_text=_('Type of venue')
    )
    status = models.CharField(
        max_length=30,
        choices=VenueStatus.choices,
        default=VenueStatus.DRAFT,
        help_text=_('Current venue status')
    )
    
    # Venue details
    description = models.TextField(
        blank=True,
        help_text=_('Detailed venue description')
    )
    purpose = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Primary purpose or sport for this venue')
    )
    
    # Address and location
    address_line_1 = models.CharField(
        max_length=200,
        help_text=_('Street address line 1')
    )
    address_line_2 = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Street address line 2 (optional)')
    )
    city = models.CharField(
        max_length=100,
        help_text=_('City')
    )
    county = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('County/State/Province')
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Postal/ZIP code')
    )
    country = models.CharField(
        max_length=100,
        default='Ireland',
        help_text=_('Country')
    )
    
    # Geographic coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_('Latitude coordinate')
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_('Longitude coordinate')
    )
    
    # Capacity and space management
    total_capacity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Total venue capacity')
    )
    volunteer_capacity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Maximum number of volunteers for this venue')
    )
    spectator_capacity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Spectator capacity')
    )
    
    # Accessibility information
    accessibility_level = models.CharField(
        max_length=20,
        choices=AccessibilityLevel.choices,
        default=AccessibilityLevel.UNKNOWN,
        help_text=_('Overall accessibility level')
    )
    wheelchair_accessible = models.BooleanField(
        default=False,
        help_text=_('Wheelchair accessible')
    )
    accessible_parking = models.BooleanField(
        default=False,
        help_text=_('Accessible parking available')
    )
    accessible_toilets = models.BooleanField(
        default=False,
        help_text=_('Accessible toilet facilities')
    )
    hearing_loop = models.BooleanField(
        default=False,
        help_text=_('Hearing loop system available')
    )
    
    # Transport and parking
    public_transport_access = models.TextField(
        blank=True,
        help_text=_('Public transport access information')
    )
    parking_spaces = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Number of parking spaces')
    )
    parking_cost = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Parking cost information')
    )
    
    # Facilities and amenities
    facilities = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Available facilities and amenities')
    )
    catering_available = models.BooleanField(
        default=False,
        help_text=_('Catering facilities available')
    )
    wifi_available = models.BooleanField(
        default=False,
        help_text=_('WiFi available')
    )
    first_aid_station = models.BooleanField(
        default=False,
        help_text=_('First aid station on site')
    )
    
    # Venue-specific configuration
    venue_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Venue-specific configuration settings')
    )
    operational_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Venue operational hours by day')
    )
    equipment_available = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Available equipment and resources')
    )
    
    # Contact information
    venue_manager = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Venue manager name')
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Venue contact phone number')
    )
    contact_email = models.EmailField(
        blank=True,
        help_text=_('Venue contact email')
    )
    emergency_contact = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Emergency contact information')
    )
    
    # Media and documentation
    venue_image = models.ImageField(
        upload_to='venues/images/',
        blank=True,
        null=True,
        help_text=_('Main venue image')
    )
    floor_plan = models.FileField(
        upload_to='venues/floor_plans/',
        blank=True,
        null=True,
        help_text=_('Venue floor plan document')
    )
    venue_map = models.FileField(
        upload_to='venues/maps/',
        blank=True,
        null=True,
        help_text=_('Venue location map')
    )
    
    # Management and ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_venues',
        help_text=_('User who created this venue')
    )
    venue_coordinators = models.ManyToManyField(
        User,
        blank=True,
        related_name='coordinated_venues',
        help_text=_('Users who coordinate this venue')
    )
    
    # Status tracking
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this venue is active')
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_('Whether this is a primary venue for the event')
    )
    requires_security_clearance = models.BooleanField(
        default=False,
        help_text=_('Whether venue requires security clearance')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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
        related_name='status_changed_venues',
        help_text=_('User who last changed the status')
    )
    
    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about this venue')
    )
    external_references = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('External system references and IDs')
    )
    
    class Meta:
        verbose_name = _('venue')
        verbose_name_plural = _('venues')
        ordering = ['event', 'name']
        unique_together = [['event', 'slug']]
        indexes = [
            models.Index(fields=['event']),
            models.Index(fields=['status']),
            models.Index(fields=['venue_type']),
            models.Index(fields=['city', 'country']),
            models.Index(fields=['is_active', 'is_primary']),
            models.Index(fields=['accessibility_level']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_capacity__gte=0),
                name='venue_total_capacity_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(volunteer_capacity__gte=0),
                name='venue_volunteer_capacity_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(spectator_capacity__gte=0),
                name='venue_spectator_capacity_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(parking_spaces__gte=0),
                name='venue_parking_spaces_non_negative'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.event.name})"
    
    def save(self, *args, **kwargs):
        """Custom save method with validation and auto-updates"""
        # Update status change tracking
        if self.pk:
            try:
                old_instance = Venue.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.status_changed_at = timezone.now()
                    # status_changed_by should be set by the view/admin
            except Venue.DoesNotExist:
                # This is a new object, no need to track status changes
                pass
        
        # Set default configurations if empty
        if not self.venue_configuration:
            self.venue_configuration = self._get_default_venue_configuration()
        
        if not self.facilities:
            self.facilities = self._get_default_facilities()
        
        if not self.operational_hours:
            self.operational_hours = self._get_default_operational_hours()
        
        if not self.equipment_available:
            self.equipment_available = self._get_default_equipment()
        
        if not self.emergency_contact:
            self.emergency_contact = self._get_default_emergency_contact()
        
        super().save(*args, **kwargs)
    
    def _get_default_venue_configuration(self):
        """Get default venue configuration"""
        return {
            'check_in_required': True,
            'security_level': 'standard',
            'volunteer_break_area': True,
            'uniform_storage': True,
            'equipment_checkout': False,
            'meal_service': False,
            'transport_provided': False,
            'overnight_storage': False,
            'weather_contingency': True,
            'capacity_monitoring': True,
            'role_rotation_enabled': True,
            'shift_handover_required': True
        }
    
    def _get_default_facilities(self):
        """Get default facilities list"""
        return {
            'toilets': False,
            'changing_rooms': False,
            'showers': False,
            'lockers': False,
            'storage': False,
            'meeting_rooms': False,
            'break_area': False,
            'kitchen': False,
            'medical_room': False,
            'security_office': False,
            'lost_and_found': False,
            'information_desk': False,
            'merchandise_area': False,
            'media_area': False,
            'vip_area': False,
            'broadcast_facilities': False,
            'sound_system': False,
            'lighting_system': False,
            'air_conditioning': False,
            'heating': False
        }
    
    def _get_default_operational_hours(self):
        """Get default operational hours"""
        return {
            'monday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'tuesday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'wednesday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'thursday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'friday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'saturday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'sunday': {'open': '08:00', 'close': '18:00', 'closed': False},
            'event_days': {'open': '06:00', 'close': '22:00', 'closed': False}
        }
    
    def _get_default_equipment(self):
        """Get default equipment list"""
        return [
            'Tables',
            'Chairs',
            'Barriers',
            'Signage',
            'First Aid Kit',
            'Communication Equipment',
            'Cleaning Supplies'
        ]
    
    def _get_default_emergency_contact(self):
        """Get default emergency contact structure"""
        return {
            'primary': {'name': '', 'phone': '', 'role': ''},
            'secondary': {'name': '', 'phone': '', 'role': ''},
            'emergency_services': {'phone': '999', 'local_station': ''},
            'venue_security': {'phone': '', 'location': ''},
            'medical': {'phone': '', 'location': ''}
        }
    
    # Address and location methods
    def get_full_address(self):
        """Get complete formatted address"""
        address_parts = [self.address_line_1]
        
        if self.address_line_2:
            address_parts.append(self.address_line_2)
        
        address_parts.append(self.city)
        
        if self.county:
            address_parts.append(self.county)
        
        if self.postal_code:
            address_parts.append(self.postal_code)
        
        address_parts.append(self.country)
        
        return ', '.join(address_parts)
    
    def get_coordinates(self):
        """Get latitude and longitude as tuple"""
        if self.latitude and self.longitude:
            return (float(self.latitude), float(self.longitude))
        return None
    
    def has_coordinates(self):
        """Check if venue has geographic coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    # Capacity and availability methods
    def get_capacity_utilization(self):
        """Get current capacity utilization percentage"""
        if self.volunteer_capacity == 0:
            return 0
        
        # This will be updated when Role and Assignment models are implemented
        assigned_volunteers = self.get_assigned_volunteer_count()
        return min(100, (assigned_volunteers / self.volunteer_capacity) * 100)
    
    def get_assigned_volunteer_count(self):
        """Get number of currently assigned volunteers"""
        # Return 0 until Role and Assignment models are implemented in Tasks 2.4 and 2.5
        return 0
    
    def get_available_capacity(self):
        """Get remaining volunteer capacity"""
        return max(0, self.volunteer_capacity - self.get_assigned_volunteer_count())
    
    def is_at_capacity(self):
        """Check if venue is at volunteer capacity"""
        return self.get_assigned_volunteer_count() >= self.volunteer_capacity
    
    def can_accommodate_volunteers(self, count=1):
        """Check if venue can accommodate additional volunteers"""
        return self.get_available_capacity() >= count
    
    # Role and assignment methods
    def get_role_count(self):
        """Get number of roles for this venue"""
        # Return 0 until Role model is implemented in Task 2.4
        return 0
    
    def get_active_role_count(self):
        """Get number of active roles for this venue"""
        # Return 0 until Role model is implemented in Task 2.4
        return 0
    
    # Accessibility methods
    def is_fully_accessible(self):
        """Check if venue is fully accessible"""
        return self.accessibility_level == self.AccessibilityLevel.FULL
    
    def has_basic_accessibility(self):
        """Check if venue has basic accessibility features"""
        return (self.wheelchair_accessible and 
                self.accessible_toilets and 
                self.accessible_parking)
    
    def get_accessibility_features(self):
        """Get list of accessibility features"""
        features = []
        
        if self.wheelchair_accessible:
            features.append('Wheelchair Accessible')
        if self.accessible_parking:
            features.append('Accessible Parking')
        if self.accessible_toilets:
            features.append('Accessible Toilets')
        if self.hearing_loop:
            features.append('Hearing Loop')
        
        return features
    
    # Configuration management methods
    def get_configuration(self, key=None, default=None):
        """Get venue configuration value"""
        if key is None:
            return self.venue_configuration
        return self.venue_configuration.get(key, default)
    
    def set_configuration(self, key, value):
        """Set venue configuration value"""
        self.venue_configuration[key] = value
        self.save(update_fields=['venue_configuration'])
    
    def update_configuration(self, updates):
        """Update multiple configuration values"""
        self.venue_configuration.update(updates)
        self.save(update_fields=['venue_configuration'])
    
    def get_facility(self, facility_name):
        """Check if specific facility is available"""
        return self.facilities.get(facility_name, False)
    
    def set_facility(self, facility_name, available=True):
        """Set facility availability"""
        self.facilities[facility_name] = available
        self.save(update_fields=['facilities'])
    
    def get_operational_hours(self, day=None):
        """Get operational hours for specific day or all days"""
        if day is None:
            return self.operational_hours
        return self.operational_hours.get(day.lower(), {})
    
    def is_open_on_day(self, day):
        """Check if venue is open on specific day"""
        day_hours = self.get_operational_hours(day.lower())
        return not day_hours.get('closed', True)
    
    # Status management methods
    def change_status(self, new_status, changed_by=None, notes=None):
        """Change venue status with audit trail"""
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.status_changed_by = changed_by
        
        if notes:
            self.notes = f"{self.notes}\n\n[{timezone.now()}] Status changed from {old_status} to {new_status}: {notes}".strip()
        
        self.save(update_fields=['status', 'status_changed_at', 'status_changed_by', 'notes'])
    
    def activate(self, activated_by=None):
        """Activate the venue"""
        self.is_active = True
        if activated_by:
            self.notes = f"{self.notes}\n\n[{timezone.now()}] Venue activated by {activated_by}".strip()
        self.save(update_fields=['is_active', 'notes'])
    
    def deactivate(self, deactivated_by=None, reason=None):
        """Deactivate the venue"""
        self.is_active = False
        note = f"[{timezone.now()}] Venue deactivated by {deactivated_by}"
        if reason:
            note += f": {reason}"
        self.notes = f"{self.notes}\n\n{note}".strip()
        self.save(update_fields=['is_active', 'notes'])
    
    def set_as_primary(self, set_by=None):
        """Set venue as primary for the event"""
        self.is_primary = True
        if set_by:
            self.notes = f"{self.notes}\n\n[{timezone.now()}] Set as primary venue by {set_by}".strip()
        self.save(update_fields=['is_primary', 'notes'])
    
    # Utility methods
    def get_distance_to(self, other_venue):
        """Calculate distance to another venue (requires coordinates)"""
        if not (self.has_coordinates() and other_venue.has_coordinates()):
            return None
        
        # Simple distance calculation (would use proper geospatial library in production)
        from math import sqrt, pow
        
        lat_diff = float(self.latitude) - float(other_venue.latitude)
        lon_diff = float(self.longitude) - float(other_venue.longitude)
        
        # Rough distance calculation (not accurate for large distances)
        return sqrt(pow(lat_diff, 2) + pow(lon_diff, 2)) * 111  # Approximate km per degree
    
    def clone_for_event(self, target_event, new_name=None, created_by=None):
        """Clone venue for another event"""
        new_venue = Venue(
            event=target_event,
            name=new_name or f"{self.name} (Copy)",
            slug=f"{self.slug}-copy",
            short_name=self.short_name,
            venue_type=self.venue_type,
            description=self.description,
            purpose=self.purpose,
            address_line_1=self.address_line_1,
            address_line_2=self.address_line_2,
            city=self.city,
            county=self.county,
            postal_code=self.postal_code,
            country=self.country,
            latitude=self.latitude,
            longitude=self.longitude,
            total_capacity=self.total_capacity,
            volunteer_capacity=self.volunteer_capacity,
            spectator_capacity=self.spectator_capacity,
            accessibility_level=self.accessibility_level,
            wheelchair_accessible=self.wheelchair_accessible,
            accessible_parking=self.accessible_parking,
            accessible_toilets=self.accessible_toilets,
            hearing_loop=self.hearing_loop,
            public_transport_access=self.public_transport_access,
            parking_spaces=self.parking_spaces,
            parking_cost=self.parking_cost,
            facilities=self.facilities.copy(),
            catering_available=self.catering_available,
            wifi_available=self.wifi_available,
            first_aid_station=self.first_aid_station,
            venue_configuration=self.venue_configuration.copy(),
            operational_hours=self.operational_hours.copy(),
            equipment_available=self.equipment_available.copy(),
            venue_manager=self.venue_manager,
            contact_phone=self.contact_phone,
            contact_email=self.contact_email,
            emergency_contact=self.emergency_contact.copy(),
            requires_security_clearance=self.requires_security_clearance,
            created_by=created_by,
            status=self.VenueStatus.DRAFT
        )
        new_venue.save()
        return new_venue
    
    def get_absolute_url(self):
        """Get absolute URL for this venue"""
        from django.urls import reverse
        return reverse('events:venue-detail', kwargs={
            'event_slug': self.event.slug,
            'venue_slug': self.slug
        })
    
    def to_dict(self):
        """Convert venue to dictionary for API responses"""
        return {
            'id': str(self.id),
            'event_id': str(self.event.id),
            'name': self.name,
            'slug': self.slug,
            'short_name': self.short_name,
            'venue_type': self.venue_type,
            'status': self.status,
            'description': self.description,
            'purpose': self.purpose,
            'full_address': self.get_full_address(),
            'coordinates': self.get_coordinates(),
            'total_capacity': self.total_capacity,
            'volunteer_capacity': self.volunteer_capacity,
            'spectator_capacity': self.spectator_capacity,
            'capacity_utilization': self.get_capacity_utilization(),
            'available_capacity': self.get_available_capacity(),
            'accessibility_level': self.accessibility_level,
            'accessibility_features': self.get_accessibility_features(),
            'role_count': self.get_role_count(),
            'assigned_volunteers': self.get_assigned_volunteer_count(),
            'is_active': self.is_active,
            'is_primary': self.is_primary,
            'requires_security_clearance': self.requires_security_clearance,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Role(models.Model):
    """
    Role model for volunteer positions within events and venues.
    Supports comprehensive role management with requirements, capacity limits,
    credential specifications, and flexible configuration.
    """
    
    class RoleType(models.TextChoices):
        # Sports and Competition Roles
        SPORT_OFFICIAL = 'SPORT_OFFICIAL', _('Sport Official')
        REFEREE = 'REFEREE', _('Referee')
        JUDGE = 'JUDGE', _('Judge')
        TIMEKEEPER = 'TIMEKEEPER', _('Timekeeper')
        SCORER = 'SCORER', _('Scorer')
        TECHNICAL_DELEGATE = 'TECHNICAL_DELEGATE', _('Technical Delegate')
        
        # Venue Operations
        VENUE_MANAGER = 'VENUE_MANAGER', _('Venue Manager')
        VENUE_COORDINATOR = 'VENUE_COORDINATOR', _('Venue Coordinator')
        VENUE_ASSISTANT = 'VENUE_ASSISTANT', _('Venue Assistant')
        SETUP_CREW = 'SETUP_CREW', _('Setup Crew')
        BREAKDOWN_CREW = 'BREAKDOWN_CREW', _('Breakdown Crew')
        
        # Athlete Support
        ATHLETE_ESCORT = 'ATHLETE_ESCORT', _('Athlete Escort')
        ATHLETE_LIAISON = 'ATHLETE_LIAISON', _('Athlete Liaison')
        WARM_UP_ASSISTANT = 'WARM_UP_ASSISTANT', _('Warm-up Assistant')
        EQUIPMENT_MANAGER = 'EQUIPMENT_MANAGER', _('Equipment Manager')
        
        # Medical and Safety
        MEDICAL_OFFICER = 'MEDICAL_OFFICER', _('Medical Officer')
        FIRST_AID = 'FIRST_AID', _('First Aid')
        SAFETY_OFFICER = 'SAFETY_OFFICER', _('Safety Officer')
        SECURITY = 'SECURITY', _('Security')
        
        # Transport and Logistics
        DRIVER = 'DRIVER', _('Driver')
        TRANSPORT_COORDINATOR = 'TRANSPORT_COORDINATOR', _('Transport Coordinator')
        LOGISTICS_ASSISTANT = 'LOGISTICS_ASSISTANT', _('Logistics Assistant')
        
        # Media and Communications
        PHOTOGRAPHER = 'PHOTOGRAPHER', _('Photographer')
        VIDEOGRAPHER = 'VIDEOGRAPHER', _('Videographer')
        MEDIA_LIAISON = 'MEDIA_LIAISON', _('Media Liaison')
        SOCIAL_MEDIA = 'SOCIAL_MEDIA', _('Social Media')
        COMMENTATOR = 'COMMENTATOR', _('Commentator')
        
        # Technology and Systems
        IT_SUPPORT = 'IT_SUPPORT', _('IT Support')
        RESULTS_SYSTEM = 'RESULTS_SYSTEM', _('Results System Operator')
        TIMING_SYSTEM = 'TIMING_SYSTEM', _('Timing System Operator')
        
        # Guest Services
        REGISTRATION = 'REGISTRATION', _('Registration')
        INFORMATION_DESK = 'INFORMATION_DESK', _('Information Desk')
        HOSPITALITY = 'HOSPITALITY', _('Hospitality')
        PROTOCOL = 'PROTOCOL', _('Protocol')
        
        # General Support
        GENERAL_VOLUNTEER = 'GENERAL_VOLUNTEER', _('General Volunteer')
        TEAM_LEADER = 'TEAM_LEADER', _('Team Leader')
        SUPERVISOR = 'SUPERVISOR', _('Supervisor')
        COORDINATOR = 'COORDINATOR', _('Coordinator')
        OTHER = 'OTHER', _('Other')
    
    class RoleStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        FULL = 'FULL', _('Full - No More Volunteers Needed')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        CANCELLED = 'CANCELLED', _('Cancelled')
        COMPLETED = 'COMPLETED', _('Completed')
    
    class SkillLevel(models.TextChoices):
        BEGINNER = 'BEGINNER', _('Beginner')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermediate')
        ADVANCED = 'ADVANCED', _('Advanced')
        EXPERT = 'EXPERT', _('Expert')
        ANY = 'ANY', _('Any Level')
    
    class CommitmentLevel(models.TextChoices):
        SINGLE_SESSION = 'SINGLE_SESSION', _('Single Session')
        DAILY = 'DAILY', _('Daily')
        MULTI_DAY = 'MULTI_DAY', _('Multi-Day')
        FULL_EVENT = 'FULL_EVENT', _('Full Event')
        FLEXIBLE = 'FLEXIBLE', _('Flexible')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='roles',
        help_text=_('Event this role belongs to')
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name='roles',
        null=True,
        blank=True,
        help_text=_('Venue this role is associated with (optional)')
    )
    
    # Role identification
    name = models.CharField(
        max_length=200,
        help_text=_('Role name (e.g., "Swimming Official", "Registration Volunteer")')
    )
    slug = models.SlugField(
        max_length=200,
        help_text=_('URL-friendly role identifier')
    )
    short_name = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Short name for display (e.g., "Swim Official")')
    )
    
    # Role classification
    role_type = models.CharField(
        max_length=30,
        choices=RoleType.choices,
        default=RoleType.GENERAL_VOLUNTEER,
        help_text=_('Type of role')
    )
    status = models.CharField(
        max_length=20,
        choices=RoleStatus.choices,
        default=RoleStatus.DRAFT,
        help_text=_('Current role status')
    )
    
    # Role details
    description = models.TextField(
        help_text=_('Detailed role description and responsibilities')
    )
    summary = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Brief role summary for listings')
    )
    
    # Requirements and qualifications
    minimum_age = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(13), MaxValueValidator(80)],
        help_text=_('Minimum age requirement')
    )
    maximum_age = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(16), MaxValueValidator(100)],
        help_text=_('Maximum age requirement (optional)')
    )
    
    skill_level_required = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.ANY,
        help_text=_('Required skill level')
    )
    
    # Physical and other requirements
    physical_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Physical requirements (e.g., standing, lifting, walking)')
    )
    language_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Language requirements')
    )
    
    # Credentials and certifications
    required_credentials = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Required credentials/certifications')
    )
    preferred_credentials = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred credentials/certifications')
    )
    justgo_credentials_required = models.JSONField(
        default=list,
        blank=True,
        help_text=_('JustGo credentials required for this role')
    )
    
    # Background checks and clearances
    requires_garda_vetting = models.BooleanField(
        default=False,
        help_text=_('Requires Garda vetting (background check)')
    )
    requires_child_protection = models.BooleanField(
        default=False,
        help_text=_('Requires child protection training')
    )
    requires_security_clearance = models.BooleanField(
        default=False,
        help_text=_('Requires security clearance')
    )
    
    # Capacity and scheduling
    total_positions = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Total number of positions available')
    )
    filled_positions = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('Number of positions currently filled')
    )
    minimum_volunteers = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Minimum number of volunteers needed')
    )
    
    # Time commitment
    commitment_level = models.CharField(
        max_length=20,
        choices=CommitmentLevel.choices,
        default=CommitmentLevel.FLEXIBLE,
        help_text=_('Expected time commitment level')
    )
    estimated_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.5), MaxValueValidator(24.0)],
        help_text=_('Estimated hours per day')
    )
    total_estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.5)],
        help_text=_('Total estimated hours for the role')
    )
    
    # Scheduling information
    schedule_requirements = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Specific scheduling requirements and constraints')
    )
    availability_windows = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Available time windows for this role')
    )
    
    # Training and preparation
    training_required = models.BooleanField(
        default=False,
        help_text=_('Whether training is required for this role')
    )
    training_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.5), MaxValueValidator(40.0)],
        help_text=_('Training duration in hours')
    )
    training_materials = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Training materials and resources')
    )
    
    # Equipment and uniform
    uniform_required = models.BooleanField(
        default=False,
        help_text=_('Whether uniform is required')
    )
    uniform_details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Uniform requirements and details')
    )
    equipment_provided = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Equipment provided to volunteers')
    )
    equipment_required = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Equipment volunteers must bring')
    )
    
    # Benefits and incentives
    benefits = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Benefits provided to volunteers in this role')
    )
    meal_provided = models.BooleanField(
        default=False,
        help_text=_('Whether meals are provided')
    )
    transport_provided = models.BooleanField(
        default=False,
        help_text=_('Whether transport is provided')
    )
    accommodation_provided = models.BooleanField(
        default=False,
        help_text=_('Whether accommodation is provided')
    )
    
    # Role configuration and customization
    role_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Role-specific configuration settings')
    )
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Custom fields for role-specific data')
    )
    
    # Contact and management
    role_supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_roles',
        help_text=_('Role supervisor/manager')
    )
    contact_person = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Contact person for this role')
    )
    contact_email = models.EmailField(
        blank=True,
        help_text=_('Contact email for role inquiries')
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Contact phone for role inquiries')
    )
    
    # Priority and visibility
    priority_level = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_('Priority level (1=highest, 10=lowest)')
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Whether this role should be featured')
    )
    is_urgent = models.BooleanField(
        default=False,
        help_text=_('Whether this role needs urgent filling')
    )
    is_public = models.BooleanField(
        default=True,
        help_text=_('Whether this role is publicly visible')
    )
    
    # Application and selection
    application_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Application deadline for this role')
    )
    selection_criteria = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Selection criteria for this role')
    )
    application_process = models.TextField(
        blank=True,
        help_text=_('Special application process instructions')
    )
    
    # Management and ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_roles',
        help_text=_('User who created this role')
    )
    role_coordinators = models.ManyToManyField(
        User,
        blank=True,
        related_name='coordinated_roles',
        help_text=_('Users who coordinate this role')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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
        related_name='status_changed_roles',
        help_text=_('User who last changed the status')
    )
    
    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about this role')
    )
    external_references = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('External system references')
    )
    
    class Meta:
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        ordering = ['event', 'venue', 'priority_level', 'name']
        unique_together = [['event', 'slug']]
        indexes = [
            models.Index(fields=['event']),
            models.Index(fields=['venue']),
            models.Index(fields=['role_type']),
            models.Index(fields=['status']),
            models.Index(fields=['priority_level']),
            models.Index(fields=['is_featured', 'is_urgent']),
            models.Index(fields=['application_deadline']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(filled_positions__lte=models.F('total_positions')),
                name='role_filled_positions_not_exceed_total'
            ),
            models.CheckConstraint(
                check=models.Q(minimum_volunteers__lte=models.F('total_positions')),
                name='role_minimum_not_exceed_total'
            ),
            models.CheckConstraint(
                check=models.Q(maximum_age__gt=models.F('minimum_age')),
                name='role_maximum_age_greater_than_minimum'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.event.short_name or self.event.name})"
    
    def save(self, *args, **kwargs):
        """Custom save method with validation and defaults"""
        # Set default configuration if empty
        if not self.role_configuration:
            self.role_configuration = self._get_default_role_configuration()
        
        # Set default physical requirements if empty
        if not self.physical_requirements:
            self.physical_requirements = self._get_default_physical_requirements()
        
        # Set default schedule requirements if empty
        if not self.schedule_requirements:
            self.schedule_requirements = self._get_default_schedule_requirements()
        
        # Set default uniform details if uniform is required
        if self.uniform_required and not self.uniform_details:
            self.uniform_details = self._get_default_uniform_details()
        
        # Auto-generate summary if not provided
        if not self.summary and self.description:
            self.summary = self.description[:497] + "..." if len(self.description) > 500 else self.description
        
        # Update status based on capacity
        if self.filled_positions >= self.total_positions and self.status == self.RoleStatus.ACTIVE:
            self.status = self.RoleStatus.FULL
        elif self.filled_positions < self.total_positions and self.status == self.RoleStatus.FULL:
            self.status = self.RoleStatus.ACTIVE
        
        super().save(*args, **kwargs)
    
    def _get_default_role_configuration(self):
        """Get default role configuration"""
        return {
            'auto_assign': False,
            'requires_approval': True,
            'allow_waitlist': True,
            'send_notifications': True,
            'track_attendance': True,
            'allow_substitutions': True,
            'require_confirmation': True,
        }
    
    def _get_default_physical_requirements(self):
        """Get default physical requirements based on role type"""
        physical_map = {
            self.RoleType.SPORT_OFFICIAL: ['standing', 'walking', 'good_vision'],
            self.RoleType.SETUP_CREW: ['lifting', 'carrying', 'physical_stamina'],
            self.RoleType.DRIVER: ['valid_license', 'good_vision', 'alertness'],
            self.RoleType.SECURITY: ['standing', 'walking', 'physical_fitness'],
            self.RoleType.MEDICAL_OFFICER: ['mobility', 'dexterity', 'alertness'],
        }
        return physical_map.get(self.role_type, ['basic_mobility'])
    
    def _get_default_schedule_requirements(self):
        """Get default schedule requirements"""
        return {
            'flexible_hours': True,
            'weekend_availability': False,
            'early_morning': False,
            'late_evening': False,
            'split_shifts': False,
            'consecutive_days': False,
        }
    
    def _get_default_uniform_details(self):
        """Get default uniform details"""
        return {
            'items': ['polo_shirt', 'id_badge'],
            'colors': ['green', 'white'],
            'sizes_available': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
            'provided_by': 'event_organizer',
            'return_required': True,
        }
    
    # Capacity and availability methods
    def get_available_positions(self):
        """Get number of available positions"""
        return max(0, self.total_positions - self.filled_positions)
    
    def get_capacity_percentage(self):
        """Get capacity utilization percentage"""
        if self.total_positions == 0:
            return 0
        return round((self.filled_positions / self.total_positions) * 100, 1)
    
    def is_full(self):
        """Check if role is at full capacity"""
        return self.filled_positions >= self.total_positions
    
    def is_understaffed(self):
        """Check if role is below minimum staffing"""
        return self.filled_positions < self.minimum_volunteers
    
    def can_accept_volunteers(self, count=1):
        """Check if role can accept additional volunteers"""
        return (self.get_available_positions() >= count and 
                self.status == self.RoleStatus.ACTIVE)
    
    # Requirement checking methods
    def check_age_requirement(self, age):
        """Check if age meets requirements"""
        if age < self.minimum_age:
            return False
        if self.maximum_age and age > self.maximum_age:
            return False
        return True
    
    def check_credential_requirements(self, user_credentials):
        """Check if user credentials meet requirements"""
        if not self.required_credentials:
            return True
        
        user_creds = set(user_credentials) if isinstance(user_credentials, list) else set()
        required_creds = set(self.required_credentials)
        
        return required_creds.issubset(user_creds)
    
    def check_justgo_requirements(self, justgo_credentials):
        """Check if JustGo credentials meet requirements"""
        if not self.justgo_credentials_required:
            return True
        
        justgo_creds = set(justgo_credentials) if isinstance(justgo_credentials, list) else set()
        required_justgo = set(self.justgo_credentials_required)
        
        return required_justgo.issubset(justgo_creds)
    
    def get_missing_credentials(self, user_credentials, justgo_credentials=None):
        """Get list of missing credentials"""
        missing = []
        
        # Check regular credentials
        if self.required_credentials:
            user_creds = set(user_credentials) if isinstance(user_credentials, list) else set()
            required_creds = set(self.required_credentials)
            missing.extend(list(required_creds - user_creds))
        
        # Check JustGo credentials
        if self.justgo_credentials_required and justgo_credentials:
            justgo_creds = set(justgo_credentials) if isinstance(justgo_credentials, list) else set()
            required_justgo = set(self.justgo_credentials_required)
            missing.extend([f"JustGo: {cred}" for cred in (required_justgo - justgo_creds)])
        
        return missing
    
    # Status management methods
    def change_status(self, new_status, changed_by=None, notes=None):
        """Change role status with audit trail"""
        if self.status != new_status:
            old_status = self.status
            self.status = new_status
            self.status_changed_at = timezone.now()
            self.status_changed_by = changed_by
            
            if notes:
                self.notes = f"{self.notes}\n\n[{timezone.now()}] Status changed from {old_status} to {new_status}: {notes}".strip()
            
            self.save()
    
    def activate(self, activated_by=None):
        """Activate the role"""
        self.change_status(self.RoleStatus.ACTIVE, activated_by, "Role activated")
    
    def suspend(self, suspended_by=None, reason=None):
        """Suspend the role"""
        reason_text = f" - {reason}" if reason else ""
        self.change_status(self.RoleStatus.SUSPENDED, suspended_by, f"Role suspended{reason_text}")
    
    def cancel(self, cancelled_by=None, reason=None):
        """Cancel the role"""
        reason_text = f" - {reason}" if reason else ""
        self.change_status(self.RoleStatus.CANCELLED, cancelled_by, f"Role cancelled{reason_text}")
    
    def complete(self, completed_by=None):
        """Mark role as completed"""
        self.change_status(self.RoleStatus.COMPLETED, completed_by, "Role completed")
    
    # Configuration methods
    def get_configuration(self, key=None, default=None):
        """Get role configuration value"""
        if key is None:
            return self.role_configuration
        return self.role_configuration.get(key, default)
    
    def set_configuration(self, key, value):
        """Set role configuration value"""
        self.role_configuration[key] = value
        self.save(update_fields=['role_configuration'])
    
    def update_configuration(self, updates):
        """Update multiple configuration values"""
        self.role_configuration.update(updates)
        self.save(update_fields=['role_configuration'])
    
    # Assignment and volunteer methods
    def get_assigned_volunteers(self):
        """Get assigned volunteers (placeholder - will be implemented with Assignment model)"""
        # This will be implemented when Assignment model is created
        return []
    
    def get_volunteer_count(self):
        """Get current volunteer count"""
        return self.filled_positions
    
    def update_volunteer_count(self):
        """Update filled positions based on actual assignments"""
        # This will be implemented when Assignment model is created
        # For now, we'll keep the manual tracking
        pass
    
    # Utility methods
    def is_application_open(self):
        """Check if applications are still open"""
        if self.application_deadline:
            return timezone.now() <= self.application_deadline
        return self.status == self.RoleStatus.ACTIVE and not self.is_full()
    
    def get_days_until_deadline(self):
        """Get days until application deadline"""
        if not self.application_deadline:
            return None
        
        delta = self.application_deadline.date() - timezone.now().date()
        return delta.days if delta.days >= 0 else 0
    
    def clone_for_venue(self, target_venue, new_name=None, created_by=None):
        """Clone role for another venue"""
        clone = Role(
            event=target_venue.event,
            venue=target_venue,
            name=new_name or f"{self.name} ({target_venue.short_name or target_venue.name})",
            slug=f"{self.slug}-{target_venue.slug}",
            short_name=self.short_name,
            role_type=self.role_type,
            description=self.description,
            summary=self.summary,
            minimum_age=self.minimum_age,
            maximum_age=self.maximum_age,
            skill_level_required=self.skill_level_required,
            physical_requirements=self.physical_requirements.copy(),
            language_requirements=self.language_requirements.copy(),
            required_credentials=self.required_credentials.copy(),
            preferred_credentials=self.preferred_credentials.copy(),
            justgo_credentials_required=self.justgo_credentials_required.copy(),
            requires_garda_vetting=self.requires_garda_vetting,
            requires_child_protection=self.requires_child_protection,
            requires_security_clearance=self.requires_security_clearance,
            total_positions=self.total_positions,
            minimum_volunteers=self.minimum_volunteers,
            commitment_level=self.commitment_level,
            estimated_hours_per_day=self.estimated_hours_per_day,
            total_estimated_hours=self.total_estimated_hours,
            training_required=self.training_required,
            training_duration_hours=self.training_duration_hours,
            uniform_required=self.uniform_required,
            meal_provided=self.meal_provided,
            transport_provided=self.transport_provided,
            accommodation_provided=self.accommodation_provided,
            priority_level=self.priority_level,
            created_by=created_by,
        )
        
        # Copy JSON fields
        clone.schedule_requirements = self.schedule_requirements.copy()
        clone.availability_windows = self.availability_windows.copy()
        clone.training_materials = self.training_materials.copy()
        clone.uniform_details = self.uniform_details.copy()
        clone.equipment_provided = self.equipment_provided.copy()
        clone.equipment_required = self.equipment_required.copy()
        clone.benefits = self.benefits.copy()
        clone.role_configuration = self.role_configuration.copy()
        clone.selection_criteria = self.selection_criteria.copy()
        
        clone.save()
        return clone
    
    def get_absolute_url(self):
        """Get absolute URL for this role"""
        from django.urls import reverse
        return reverse('events:role-detail', kwargs={
            'event_slug': self.event.slug,
            'role_slug': self.slug
        })
    
    def to_dict(self):
        """Convert role to dictionary representation"""
        return {
            'id': str(self.id),
            'event_id': str(self.event.id),
            'venue_id': str(self.venue.id) if self.venue else None,
            'name': self.name,
            'slug': self.slug,
            'short_name': self.short_name,
            'role_type': self.role_type,
            'status': self.status,
            'description': self.description,
            'summary': self.summary,
            'requirements': {
                'minimum_age': self.minimum_age,
                'maximum_age': self.maximum_age,
                'skill_level': self.skill_level_required,
                'physical': self.physical_requirements,
                'language': self.language_requirements,
                'credentials': self.required_credentials,
                'preferred_credentials': self.preferred_credentials,
                'justgo_credentials': self.justgo_credentials_required,
                'garda_vetting': self.requires_garda_vetting,
                'child_protection': self.requires_child_protection,
                'security_clearance': self.requires_security_clearance,
            },
            'capacity': {
                'total_positions': self.total_positions,
                'filled_positions': self.filled_positions,
                'available_positions': self.get_available_positions(),
                'minimum_volunteers': self.minimum_volunteers,
                'capacity_percentage': self.get_capacity_percentage(),
                'is_full': self.is_full(),
                'is_understaffed': self.is_understaffed(),
            },
            'commitment': {
                'level': self.commitment_level,
                'hours_per_day': float(self.estimated_hours_per_day) if self.estimated_hours_per_day else None,
                'total_hours': float(self.total_estimated_hours) if self.total_estimated_hours else None,
                'schedule_requirements': self.schedule_requirements,
                'availability_windows': self.availability_windows,
            },
            'training': {
                'required': self.training_required,
                'duration_hours': float(self.training_duration_hours) if self.training_duration_hours else None,
                'materials': self.training_materials,
            },
            'benefits': {
                'uniform_required': self.uniform_required,
                'uniform_details': self.uniform_details,
                'equipment_provided': self.equipment_provided,
                'equipment_required': self.equipment_required,
                'meal_provided': self.meal_provided,
                'transport_provided': self.transport_provided,
                'accommodation_provided': self.accommodation_provided,
                'benefits': self.benefits,
            },
            'application': {
                'deadline': self.application_deadline.isoformat() if self.application_deadline else None,
                'is_open': self.is_application_open(),
                'days_until_deadline': self.get_days_until_deadline(),
                'selection_criteria': self.selection_criteria,
                'application_process': self.application_process,
            },
            'contact': {
                'supervisor': str(self.role_supervisor.id) if self.role_supervisor else None,
                'contact_person': self.contact_person,
                'contact_email': self.contact_email,
                'contact_phone': self.contact_phone,
            },
            'status_info': {
                'priority_level': self.priority_level,
                'is_featured': self.is_featured,
                'is_urgent': self.is_urgent,
                'is_public': self.is_public,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Assignment(models.Model):
    """
    Assignment model for managing volunteer assignments to roles.
    Provides comprehensive status tracking, admin override support,
    and detailed assignment management with audit trails.
    """
    
    class AssignmentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Review')
        APPROVED = 'APPROVED', _('Approved')
        CONFIRMED = 'CONFIRMED', _('Confirmed by Volunteer')
        ACTIVE = 'ACTIVE', _('Active/Ongoing')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        REJECTED = 'REJECTED', _('Rejected')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn by Volunteer')
        NO_SHOW = 'NO_SHOW', _('No Show')
        SUSPENDED = 'SUSPENDED', _('Suspended')
    
    class AssignmentType(models.TextChoices):
        STANDARD = 'STANDARD', _('Standard Assignment')
        EMERGENCY = 'EMERGENCY', _('Emergency Assignment')
        REPLACEMENT = 'REPLACEMENT', _('Replacement Assignment')
        BACKUP = 'BACKUP', _('Backup Assignment')
        ADMIN_OVERRIDE = 'ADMIN_OVERRIDE', _('Admin Override Assignment')
    
    class PriorityLevel(models.TextChoices):
        LOW = 'LOW', _('Low Priority')
        NORMAL = 'NORMAL', _('Normal Priority')
        HIGH = 'HIGH', _('High Priority')
        URGENT = 'URGENT', _('Urgent')
        CRITICAL = 'CRITICAL', _('Critical')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Assignment relationships
    volunteer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text=_('Volunteer assigned to this role')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text=_('Role being assigned')
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text=_('Event this assignment belongs to')
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name='assignments',
        null=True,
        blank=True,
        help_text=_('Venue for this assignment (if applicable)')
    )
    
    # Assignment details
    assignment_type = models.CharField(
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.STANDARD,
        help_text=_('Type of assignment')
    )
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
        help_text=_('Current assignment status')
    )
    priority_level = models.CharField(
        max_length=10,
        choices=PriorityLevel.choices,
        default=PriorityLevel.NORMAL,
        help_text=_('Assignment priority level')
    )
    
    # Scheduling information
    assigned_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the assignment was created')
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_('Assignment start date')
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_('Assignment end date')
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_('Assignment start time')
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_('Assignment end time')
    )
    
    # Assignment configuration
    assignment_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Assignment-specific configuration and settings')
    )
    special_instructions = models.TextField(
        blank=True,
        help_text=_('Special instructions for this assignment')
    )
    equipment_assigned = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Equipment assigned to volunteer')
    )
    uniform_assigned = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Uniform details assigned to volunteer')
    )
    
    # Status tracking and workflow
    application_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer applied for this role')
    )
    review_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When assignment was reviewed')
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When assignment was approved')
    )
    confirmation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer confirmed assignment')
    )
    completion_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When assignment was completed')
    )
    
    # Admin override support
    is_admin_override = models.BooleanField(
        default=False,
        help_text=_('Whether this assignment was created via admin override')
    )
    admin_override_reason = models.TextField(
        blank=True,
        help_text=_('Reason for admin override (required if is_admin_override=True)')
    )
    admin_override_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_override_assignments',
        help_text=_('Admin user who created the override')
    )
    admin_override_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When admin override was applied')
    )
    
    # Requirement overrides
    age_requirement_override = models.BooleanField(
        default=False,
        help_text=_('Override age requirements')
    )
    credential_requirement_override = models.BooleanField(
        default=False,
        help_text=_('Override credential requirements')
    )
    capacity_override = models.BooleanField(
        default=False,
        help_text=_('Override role capacity limits')
    )
    override_justification = models.TextField(
        blank=True,
        help_text=_('Justification for requirement overrides')
    )
    
    # Performance and feedback
    performance_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Performance rating (1-5 stars)')
    )
    feedback_from_volunteer = models.TextField(
        blank=True,
        help_text=_('Feedback from volunteer about the assignment')
    )
    feedback_from_supervisor = models.TextField(
        blank=True,
        help_text=_('Feedback from supervisor about volunteer performance')
    )
    
    # Attendance tracking
    check_in_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer checked in')
    )
    check_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When volunteer checked out')
    )
    actual_hours_worked = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_('Actual hours worked')
    )
    attendance_notes = models.TextField(
        blank=True,
        help_text=_('Notes about attendance or performance')
    )
    
    # Communication and notifications
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Volunteer notification preferences for this assignment')
    )
    last_notification_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When last notification was sent')
    )
    reminder_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of reminders sent')
    )
    
    # Assignment management
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments',
        help_text=_('User who created this assignment')
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_assignments',
        help_text=_('User who reviewed this assignment')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_assignments',
        help_text=_('User who approved this assignment')
    )
    
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
        related_name='status_changed_assignments',
        help_text=_('User who last changed the status')
    )
    status_change_reason = models.TextField(
        blank=True,
        help_text=_('Reason for status change')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about this assignment')
    )
    external_references = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('External system references and IDs')
    )
    
    class Meta:
        verbose_name = _('assignment')
        verbose_name_plural = _('assignments')
        ordering = ['-created_at', 'event', 'role', 'volunteer']
        unique_together = [['volunteer', 'role']]  # One assignment per volunteer per role
        indexes = [
            models.Index(fields=['volunteer']),
            models.Index(fields=['role']),
            models.Index(fields=['event']),
            models.Index(fields=['venue']),
            models.Index(fields=['status']),
            models.Index(fields=['assignment_type']),
            models.Index(fields=['priority_level']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_admin_override']),
            models.Index(fields=['assigned_date']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_date__lte=models.F('end_date')),
                name='assignment_start_date_before_end_date'
            ),
            models.CheckConstraint(
                check=models.Q(start_time__lte=models.F('end_time')),
                name='assignment_start_time_before_end_time'
            ),
            models.CheckConstraint(
                check=models.Q(
                    is_admin_override=False
                ) | models.Q(
                    is_admin_override=True,
                    admin_override_reason__isnull=False
                ),
                name='assignment_admin_override_requires_reason'
            ),
        ]
    
    def __str__(self):
        return f"{self.volunteer.get_full_name()} → {self.role.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Enhanced save method with validation and auto-population"""
        # Auto-populate event and venue from role
        if not self.event_id:
            self.event = self.role.event
        if not self.venue_id and self.role.venue:
            self.venue = self.role.venue
        
        # Set default configuration
        if not self.assignment_configuration:
            self.assignment_configuration = self._get_default_assignment_configuration()
        
        # Set default notification preferences
        if not self.notification_preferences:
            self.notification_preferences = self._get_default_notification_preferences()
        
        # Validate admin override requirements
        if self.is_admin_override and not self.admin_override_reason:
            raise ValidationError(_('Admin override reason is required when is_admin_override is True'))
        
        # Set admin override date if not set
        if self.is_admin_override and not self.admin_override_date:
            self.admin_override_date = timezone.now()
        
        # Update status dates based on status
        self._update_status_dates()
        
        super().save(*args, **kwargs)
        
        # Update role filled positions
        self._update_role_capacity()
    
    def _get_default_assignment_configuration(self):
        """Get default assignment configuration"""
        return {
            'auto_reminders': True,
            'reminder_days_before': [7, 3, 1],
            'require_check_in': True,
            'require_check_out': True,
            'allow_early_check_in': 30,  # minutes
            'allow_late_check_out': 30,  # minutes
            'track_location': False,
            'require_supervisor_approval': False,
            'custom_fields': {},
        }
    
    def _get_default_notification_preferences(self):
        """Get default notification preferences"""
        return {
            'email_notifications': True,
            'sms_notifications': False,
            'push_notifications': True,
            'reminder_notifications': True,
            'status_change_notifications': True,
            'assignment_updates': True,
            'schedule_changes': True,
        }
    
    def _update_status_dates(self):
        """Update status-related dates based on current status"""
        now = timezone.now()
        
        if self.status == self.AssignmentStatus.APPROVED and not self.approval_date:
            self.approval_date = now
        elif self.status == self.AssignmentStatus.CONFIRMED and not self.confirmation_date:
            self.confirmation_date = now
        elif self.status == self.AssignmentStatus.COMPLETED and not self.completion_date:
            self.completion_date = now
    
    def _update_role_capacity(self):
        """Update role filled positions based on active assignments"""
        if self.role_id:
            active_count = Assignment.objects.filter(
                role=self.role,
                status__in=[
                    self.AssignmentStatus.APPROVED,
                    self.AssignmentStatus.CONFIRMED,
                    self.AssignmentStatus.ACTIVE,
                ]
            ).count()
            
            if self.role.filled_positions != active_count:
                Role.objects.filter(id=self.role.id).update(filled_positions=active_count)
    
    # Status checking methods
    def is_active(self):
        """Check if assignment is currently active"""
        return self.status in [
            self.AssignmentStatus.APPROVED,
            self.AssignmentStatus.CONFIRMED,
            self.AssignmentStatus.ACTIVE,
        ]
    
    def is_pending(self):
        """Check if assignment is pending review"""
        return self.status == self.AssignmentStatus.PENDING
    
    def is_completed(self):
        """Check if assignment is completed"""
        return self.status == self.AssignmentStatus.COMPLETED
    
    def is_cancelled(self):
        """Check if assignment is cancelled or withdrawn"""
        return self.status in [
            self.AssignmentStatus.CANCELLED,
            self.AssignmentStatus.REJECTED,
            self.AssignmentStatus.WITHDRAWN,
        ]
    
    def can_be_modified(self):
        """Check if assignment can still be modified"""
        return self.status in [
            self.AssignmentStatus.PENDING,
            self.AssignmentStatus.APPROVED,
            self.AssignmentStatus.CONFIRMED,
        ]
    
    def can_be_cancelled(self):
        """Check if assignment can be cancelled"""
        return self.status not in [
            self.AssignmentStatus.COMPLETED,
            self.AssignmentStatus.CANCELLED,
            self.AssignmentStatus.REJECTED,
            self.AssignmentStatus.WITHDRAWN,
        ]
    
    # Status change methods
    def approve(self, approved_by=None, notes=None):
        """Approve the assignment"""
        self.change_status(
            self.AssignmentStatus.APPROVED,
            approved_by,
            notes or "Assignment approved"
        )
        self.approved_by = approved_by
        self.approval_date = timezone.now()
        self.save()
    
    def confirm(self, notes=None):
        """Confirm assignment (by volunteer)"""
        self.change_status(
            self.AssignmentStatus.CONFIRMED,
            self.volunteer,
            notes or "Assignment confirmed by volunteer"
        )
        self.confirmation_date = timezone.now()
        self.save()
    
    def activate(self, activated_by=None, notes=None):
        """Activate the assignment"""
        self.change_status(
            self.AssignmentStatus.ACTIVE,
            activated_by,
            notes or "Assignment activated"
        )
        self.save()
    
    def complete(self, completed_by=None, notes=None, performance_rating=None):
        """Complete the assignment"""
        self.change_status(
            self.AssignmentStatus.COMPLETED,
            completed_by,
            notes or "Assignment completed"
        )
        self.completion_date = timezone.now()
        if performance_rating:
            self.performance_rating = performance_rating
        self.save()
    
    def cancel(self, cancelled_by=None, reason=None):
        """Cancel the assignment"""
        reason_text = f" - {reason}" if reason else ""
        self.change_status(
            self.AssignmentStatus.CANCELLED,
            cancelled_by,
            f"Assignment cancelled{reason_text}"
        )
        self.save()
    
    def reject(self, rejected_by=None, reason=None):
        """Reject the assignment"""
        reason_text = f" - {reason}" if reason else ""
        self.change_status(
            self.AssignmentStatus.REJECTED,
            rejected_by,
            f"Assignment rejected{reason_text}"
        )
        self.save()
    
    def withdraw(self, reason=None):
        """Withdraw assignment (by volunteer)"""
        reason_text = f" - {reason}" if reason else ""
        self.change_status(
            self.AssignmentStatus.WITHDRAWN,
            self.volunteer,
            f"Assignment withdrawn by volunteer{reason_text}"
        )
        self.save()
    
    def mark_no_show(self, marked_by=None, notes=None):
        """Mark volunteer as no-show"""
        self.change_status(
            self.AssignmentStatus.NO_SHOW,
            marked_by,
            notes or "Volunteer marked as no-show"
        )
        self.save()
    
    def suspend(self, suspended_by=None, reason=None):
        """Suspend the assignment"""
        reason_text = f" - {reason}" if reason else ""
        self.change_status(
            self.AssignmentStatus.SUSPENDED,
            suspended_by,
            f"Assignment suspended{reason_text}"
        )
        self.save()
    
    def change_status(self, new_status, changed_by=None, reason=None):
        """Change assignment status with audit trail"""
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.status_changed_by = changed_by
        self.status_change_reason = reason or f"Status changed from {old_status} to {new_status}"
    
    # Admin override methods
    def apply_admin_override(self, admin_user, reason, override_types=None):
        """Apply admin override to assignment"""
        if not admin_user.is_staff:
            raise ValidationError(_('Only staff users can apply admin overrides'))
        
        self.is_admin_override = True
        self.admin_override_reason = reason
        self.admin_override_by = admin_user
        self.admin_override_date = timezone.now()
        
        # Apply specific overrides
        if override_types:
            if 'age' in override_types:
                self.age_requirement_override = True
            if 'credentials' in override_types:
                self.credential_requirement_override = True
            if 'capacity' in override_types:
                self.capacity_override = True
        
        self.override_justification = reason
        self.save()
    
    def remove_admin_override(self, admin_user, reason):
        """Remove admin override from assignment"""
        if not admin_user.is_staff:
            raise ValidationError(_('Only staff users can remove admin overrides'))
        
        self.is_admin_override = False
        self.admin_override_reason = ""
        self.admin_override_by = None
        self.admin_override_date = None
        self.age_requirement_override = False
        self.credential_requirement_override = False
        self.capacity_override = False
        self.override_justification = ""
        
        # Add note about override removal
        self.notes += f"\n[{timezone.now()}] Admin override removed by {admin_user.get_full_name()}: {reason}"
        self.save()
    
    # Attendance methods
    def check_in(self, check_in_time=None, location=None):
        """Check in volunteer for assignment"""
        self.check_in_time = check_in_time or timezone.now()
        if location:
            config = self.assignment_configuration.copy()
            config['check_in_location'] = location
            self.assignment_configuration = config
        
        # Auto-activate if approved/confirmed
        if self.status in [self.AssignmentStatus.APPROVED, self.AssignmentStatus.CONFIRMED]:
            self.activate(notes="Auto-activated on check-in")
        
        self.save()
    
    def check_out(self, check_out_time=None, location=None):
        """Check out volunteer from assignment"""
        self.check_out_time = check_out_time or timezone.now()
        if location:
            config = self.assignment_configuration.copy()
            config['check_out_location'] = location
            self.assignment_configuration = config
        
        # Calculate actual hours worked
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            self.actual_hours_worked = duration.total_seconds() / 3600
        
        self.save()
    
    # Validation methods
    def validate_assignment(self):
        """Validate assignment against role requirements"""
        errors = []
        
        # Check age requirements (unless overridden)
        if not self.age_requirement_override:
            volunteer_age = self.volunteer.get_age() if hasattr(self.volunteer, 'get_age') else None
            if volunteer_age and not self.role.check_age_requirement(volunteer_age):
                errors.append(f"Volunteer age ({volunteer_age}) does not meet role requirements")
        
        # Check credential requirements (unless overridden)
        if not self.credential_requirement_override:
            # This would check against volunteer's credentials
            # Implementation depends on volunteer profile structure
            pass
        
        # Check capacity (unless overridden)
        if not self.capacity_override:
            if not self.role.can_accept_volunteers():
                errors.append("Role is at capacity")
        
        return errors
    
    # Utility methods
    def get_duration(self):
        """Get assignment duration in days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return None
    
    def get_time_commitment(self):
        """Get time commitment details"""
        duration_days = self.get_duration()
        if duration_days and self.role.estimated_hours_per_day:
            total_hours = duration_days * float(self.role.estimated_hours_per_day)
            return {
                'duration_days': duration_days,
                'hours_per_day': float(self.role.estimated_hours_per_day),
                'total_estimated_hours': total_hours,
                'actual_hours_worked': float(self.actual_hours_worked) if self.actual_hours_worked else None,
            }
        return None
    
    def get_schedule_info(self):
        """Get schedule information"""
        return {
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'duration_days': self.get_duration(),
            'time_commitment': self.get_time_commitment(),
        }
    
    def get_status_history(self):
        """Get status change history (placeholder - would need separate model)"""
        # This would return status change history
        # For now, return basic info
        return {
            'current_status': self.status,
            'status_changed_at': self.status_changed_at.isoformat() if self.status_changed_at else None,
            'status_changed_by': self.status_changed_by.get_full_name() if self.status_changed_by else None,
            'status_change_reason': self.status_change_reason,
        }
    
    def clone_for_role(self, target_role, created_by=None):
        """Clone assignment for another role"""
        clone = Assignment(
            volunteer=self.volunteer,
            role=target_role,
            event=target_role.event,
            venue=target_role.venue,
            assignment_type=self.assignment_type,
            priority_level=self.priority_level,
            start_date=self.start_date,
            end_date=self.end_date,
            start_time=self.start_time,
            end_time=self.end_time,
            special_instructions=self.special_instructions,
            assigned_by=created_by,
        )
        
        # Copy JSON fields
        clone.assignment_configuration = self.assignment_configuration.copy()
        clone.equipment_assigned = self.equipment_assigned.copy()
        clone.uniform_assigned = self.uniform_assigned.copy()
        clone.notification_preferences = self.notification_preferences.copy()
        
        clone.save()
        return clone
    
    def get_absolute_url(self):
        """Get absolute URL for this assignment"""
        from django.urls import reverse
        return reverse('events:assignment-detail', kwargs={
            'assignment_id': str(self.id)
        })
    
    def to_dict(self):
        """Convert assignment to dictionary representation"""
        return {
            'id': str(self.id),
            'volunteer': {
                'id': str(self.volunteer.id),
                'name': self.volunteer.get_full_name(),
                'email': self.volunteer.email,
            },
            'role': {
                'id': str(self.role.id),
                'name': self.role.name,
                'slug': self.role.slug,
            },
            'event': {
                'id': str(self.event.id),
                'name': self.event.name,
                'slug': self.event.slug,
            },
            'venue': {
                'id': str(self.venue.id),
                'name': self.venue.name,
                'slug': self.venue.slug,
            } if self.venue else None,
            'assignment_details': {
                'type': self.assignment_type,
                'status': self.status,
                'priority_level': self.priority_level,
                'is_admin_override': self.is_admin_override,
                'admin_override_reason': self.admin_override_reason,
            },
            'schedule': self.get_schedule_info(),
            'status_info': self.get_status_history(),
            'dates': {
                'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
                'application_date': self.application_date.isoformat() if self.application_date else None,
                'approval_date': self.approval_date.isoformat() if self.approval_date else None,
                'confirmation_date': self.confirmation_date.isoformat() if self.confirmation_date else None,
                'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            },
            'attendance': {
                'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
                'check_out_time': self.check_out_time.isoformat() if self.check_out_time else None,
                'actual_hours_worked': float(self.actual_hours_worked) if self.actual_hours_worked else None,
                'attendance_notes': self.attendance_notes,
            },
            'feedback': {
                'performance_rating': self.performance_rating,
                'feedback_from_volunteer': self.feedback_from_volunteer,
                'feedback_from_supervisor': self.feedback_from_supervisor,
            },
            'overrides': {
                'age_requirement_override': self.age_requirement_override,
                'credential_requirement_override': self.credential_requirement_override,
                'capacity_override': self.capacity_override,
                'override_justification': self.override_justification,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
