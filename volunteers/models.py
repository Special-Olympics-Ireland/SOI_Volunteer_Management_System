from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class VolunteerProfile(models.Model):
    """
    VolunteerProfile model for storing Expression of Interest (EOI) data and volunteer preferences.
    Extends the base User model with volunteer-specific information and preferences.
    """
    
    class VolunteerStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Review')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        WAITLISTED = 'WAITLISTED', _('Waitlisted')
        ACTIVE = 'ACTIVE', _('Active Volunteer')
        INACTIVE = 'INACTIVE', _('Inactive')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')
    
    class AvailabilityLevel(models.TextChoices):
        FULL_TIME = 'FULL_TIME', _('Full Time (All Days)')
        PART_TIME = 'PART_TIME', _('Part Time (Some Days)')
        WEEKENDS_ONLY = 'WEEKENDS_ONLY', _('Weekends Only')
        SPECIFIC_DAYS = 'SPECIFIC_DAYS', _('Specific Days Only')
        FLEXIBLE = 'FLEXIBLE', _('Flexible')
        LIMITED = 'LIMITED', _('Limited Availability')
    
    class ExperienceLevel(models.TextChoices):
        NONE = 'NONE', _('No Experience')
        BEGINNER = 'BEGINNER', _('Beginner (1-2 events)')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermediate (3-5 events)')
        EXPERIENCED = 'EXPERIENCED', _('Experienced (6-10 events)')
        EXPERT = 'EXPERT', _('Expert (10+ events)')
        PROFESSIONAL = 'PROFESSIONAL', _('Professional/Staff')
    
    class TShirtSize(models.TextChoices):
        XS = 'XS', _('Extra Small')
        S = 'S', _('Small')
        M = 'M', _('Medium')
        L = 'L', _('Large')
        XL = 'XL', _('Extra Large')
        XXL = 'XXL', _('2X Large')
        XXXL = 'XXXL', _('3X Large')
    
    class TransportMethod(models.TextChoices):
        OWN_CAR = 'OWN_CAR', _('Own Car')
        PUBLIC_TRANSPORT = 'PUBLIC_TRANSPORT', _('Public Transport')
        CYCLING = 'CYCLING', _('Cycling')
        WALKING = 'WALKING', _('Walking')
        CARPOOL = 'CARPOOL', _('Carpool')
        VOLUNTEER_TRANSPORT = 'VOLUNTEER_TRANSPORT', _('Volunteer Transport')
        OTHER = 'OTHER', _('Other')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User relationship
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='volunteer_profile',
        help_text=_('Associated user account')
    )
    
    # EOI Status and tracking
    status = models.CharField(
        max_length=20,
        choices=VolunteerStatus.choices,
        default=VolunteerStatus.PENDING,
        help_text=_('Current volunteer status')
    )
    application_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the EOI was submitted')
    )
    review_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the application was reviewed')
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the application was approved')
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_volunteer_profiles',
        help_text=_('Staff member who reviewed the application')
    )
    
    # Personal preferences and information
    preferred_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Preferred name for communications and name tags')
    )
    emergency_contact_name = models.CharField(
        max_length=200,
        help_text=_('Emergency contact full name')
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.')
        )],
        help_text=_('Emergency contact phone number')
    )
    emergency_contact_relationship = models.CharField(
        max_length=100,
        help_text=_('Relationship to emergency contact (e.g., spouse, parent, friend)')
    )
    
    # Medical and dietary information
    medical_conditions = models.TextField(
        blank=True,
        help_text=_('Any medical conditions or allergies we should be aware of')
    )
    dietary_requirements = models.TextField(
        blank=True,
        help_text=_('Dietary requirements, allergies, or preferences')
    )
    mobility_requirements = models.TextField(
        blank=True,
        help_text=_('Any mobility assistance or accessibility requirements')
    )
    
    # Volunteer experience and skills
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.NONE,
        help_text=_('Overall volunteering experience level')
    )
    previous_events = models.TextField(
        blank=True,
        help_text=_('List of previous events volunteered at')
    )
    special_skills = models.TextField(
        blank=True,
        help_text=_('Special skills, qualifications, or certifications')
    )
    languages_spoken = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Languages spoken and proficiency levels')
    )
    
    # Availability and scheduling
    availability_level = models.CharField(
        max_length=20,
        choices=AvailabilityLevel.choices,
        default=AvailabilityLevel.FLEXIBLE,
        help_text=_('General availability level')
    )
    available_dates = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Specific dates available for volunteering')
    )
    unavailable_dates = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Dates not available for volunteering')
    )
    preferred_time_slots = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred time slots (morning, afternoon, evening, overnight)')
    )
    max_hours_per_day = models.PositiveIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        help_text=_('Maximum hours willing to volunteer per day')
    )
    
    # Role and venue preferences
    preferred_roles = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of preferred volunteer roles')
    )
    preferred_venues = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of preferred venues or venue types')
    )
    preferred_sports = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred sports to work with')
    )
    role_restrictions = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Roles or activities the volunteer cannot or will not do')
    )
    
    # Physical and practical considerations
    can_lift_heavy_items = models.BooleanField(
        default=True,
        help_text=_('Able to lift heavy items (over 20kg)')
    )
    can_stand_long_periods = models.BooleanField(
        default=True,
        help_text=_('Able to stand for long periods (4+ hours)')
    )
    can_work_outdoors = models.BooleanField(
        default=True,
        help_text=_('Comfortable working outdoors in various weather')
    )
    can_work_with_crowds = models.BooleanField(
        default=True,
        help_text=_('Comfortable working with large crowds')
    )
    has_own_transport = models.BooleanField(
        default=False,
        help_text=_('Has own reliable transport to venues')
    )
    transport_method = models.CharField(
        max_length=30,
        choices=TransportMethod.choices,
        default=TransportMethod.PUBLIC_TRANSPORT,
        help_text=_('Primary method of transport to venues')
    )
    
    # Uniform and equipment
    t_shirt_size = models.CharField(
        max_length=10,
        choices=TShirtSize.choices,
        default=TShirtSize.M,
        help_text=_('T-shirt size for volunteer uniform')
    )
    requires_uniform = models.BooleanField(
        default=True,
        help_text=_('Requires volunteer uniform')
    )
    has_own_equipment = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of own equipment available (radios, first aid kit, etc.)')
    )
    
    # Communication preferences
    preferred_communication_method = models.CharField(
        max_length=20,
        choices=[
            ('EMAIL', _('Email')),
            ('SMS', _('SMS/Text')),
            ('PHONE', _('Phone Call')),
            ('WHATSAPP', _('WhatsApp')),
            ('APP', _('Mobile App')),
        ],
        default='EMAIL',
        help_text=_('Preferred method of communication')
    )
    communication_frequency = models.CharField(
        max_length=20,
        choices=[
            ('DAILY', _('Daily Updates')),
            ('WEEKLY', _('Weekly Updates')),
            ('IMPORTANT_ONLY', _('Important Only')),
            ('MINIMAL', _('Minimal Communication')),
        ],
        default='WEEKLY',
        help_text=_('Preferred frequency of communications')
    )
    
    # Training and development
    training_completed = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of completed training modules')
    )
    training_required = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of required training modules')
    )
    training_preferences = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred training delivery methods and times')
    )
    
    # Background checks and verification
    background_check_status = models.CharField(
        max_length=20,
        choices=[
            ('NOT_REQUIRED', _('Not Required')),
            ('REQUIRED', _('Required')),
            ('SUBMITTED', _('Submitted')),
            ('IN_PROGRESS', _('In Progress')),
            ('APPROVED', _('Approved')),
            ('REJECTED', _('Rejected')),
            ('EXPIRED', _('Expired')),
        ],
        default='NOT_REQUIRED',
        help_text=_('Background check status')
    )
    background_check_date = models.DateField(
        null=True,
        blank=True,
        help_text=_('Date background check was completed')
    )
    background_check_expiry = models.DateField(
        null=True,
        blank=True,
        help_text=_('Date background check expires')
    )
    
    # References
    references = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of references with contact information')
    )
    reference_check_status = models.CharField(
        max_length=20,
        choices=[
            ('NOT_REQUIRED', _('Not Required')),
            ('REQUIRED', _('Required')),
            ('IN_PROGRESS', _('In Progress')),
            ('COMPLETED', _('Completed')),
            ('FAILED', _('Failed')),
        ],
        default='NOT_REQUIRED',
        help_text=_('Reference check status')
    )
    
    # Motivation and goals
    motivation = models.TextField(
        blank=True,
        help_text=_('Why do you want to volunteer for this event?')
    )
    volunteer_goals = models.TextField(
        blank=True,
        help_text=_('What do you hope to achieve through volunteering?')
    )
    previous_volunteer_feedback = models.TextField(
        blank=True,
        help_text=_('Feedback from previous volunteer experiences')
    )
    
    # Corporate and group volunteering
    is_corporate_volunteer = models.BooleanField(
        default=False,
        help_text=_('Part of a corporate volunteer group')
    )
    corporate_group_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Name of corporate group or organization')
    )
    group_leader_contact = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Contact information for group leader')
    )
    
    # Social media and marketing
    social_media_consent = models.BooleanField(
        default=False,
        help_text=_('Consent to appear in social media posts and marketing materials')
    )
    photo_consent = models.BooleanField(
        default=False,
        help_text=_('Consent for photos to be taken and used')
    )
    testimonial_consent = models.BooleanField(
        default=False,
        help_text=_('Consent to provide testimonials and quotes')
    )
    
    # Performance and feedback
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text=_('Overall performance rating (0-5 stars)')
    )
    feedback_summary = models.TextField(
        blank=True,
        help_text=_('Summary of feedback from supervisors and coordinators')
    )
    commendations = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of commendations and awards received')
    )
    
    # Administrative fields
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about the volunteer')
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Tags for categorization and search')
    )
    
    # Audit fields
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
        related_name='status_changed_volunteer_profiles',
        help_text=_('User who last changed the status')
    )
    status_change_reason = models.TextField(
        blank=True,
        help_text=_('Reason for status change')
    )
    
    class Meta:
        verbose_name = _('volunteer profile')
        verbose_name_plural = _('volunteer profiles')
        ordering = ['-application_date', 'user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['status', 'application_date']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['experience_level', 'status']),
            models.Index(fields=['availability_level', 'status']),
            models.Index(fields=['is_corporate_volunteer', 'status']),
            models.Index(fields=['background_check_status']),
            models.Index(fields=['reference_check_status']),
            models.Index(fields=['reviewed_by', 'review_date']),
            models.Index(fields=['application_date']),
            models.Index(fields=['approval_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_hours_per_day__gte=1, max_hours_per_day__lte=24),
                name='volunteerprofile_max_hours_per_day_range'
            ),
            models.CheckConstraint(
                check=models.Q(performance_rating__isnull=True) | 
                      models.Q(performance_rating__gte=0, performance_rating__lte=5),
                name='volunteerprofile_performance_rating_range'
            ),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method with status tracking"""
        # Track status changes
        if self.pk:
            try:
                old_instance = VolunteerProfile.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.status_changed_at = timezone.now()
                    # Note: status_changed_by should be set by the calling code
            except VolunteerProfile.DoesNotExist:
                pass
        
        # Set review date when status changes from PENDING
        if (self.status != self.VolunteerStatus.PENDING and 
            not self.review_date):
            self.review_date = timezone.now()
        
        # Set approval date when approved
        if (self.status == self.VolunteerStatus.APPROVED and 
            not self.approval_date):
            self.approval_date = timezone.now()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate volunteer profile data"""
        super().clean()
        
        # Validate emergency contact information
        if not self.emergency_contact_name.strip():
            raise ValidationError(_('Emergency contact name is required'))
        
        if not self.emergency_contact_phone.strip():
            raise ValidationError(_('Emergency contact phone is required'))
        
        # Validate corporate volunteer information
        if self.is_corporate_volunteer and not self.corporate_group_name.strip():
            raise ValidationError(_('Corporate group name is required for corporate volunteers'))
        
        # Validate background check dates
        if (self.background_check_date and self.background_check_expiry and
            self.background_check_date > self.background_check_expiry):
            raise ValidationError(_('Background check expiry date cannot be before completion date'))
    
    # Status management methods
    def approve(self, approved_by, notes=''):
        """Approve the volunteer application"""
        if self.status in [self.VolunteerStatus.PENDING, self.VolunteerStatus.UNDER_REVIEW]:
            self.status = self.VolunteerStatus.APPROVED
            self.reviewed_by = approved_by
            self.approval_date = timezone.now()
            self.status_changed_at = timezone.now()
            self.status_changed_by = approved_by
            if notes:
                self.status_change_reason = notes
            self.save(update_fields=[
                'status', 'reviewed_by', 'approval_date', 'status_changed_at',
                'status_changed_by', 'status_change_reason'
            ])
    
    def reject(self, rejected_by, reason):
        """Reject the volunteer application"""
        if self.status in [self.VolunteerStatus.PENDING, self.VolunteerStatus.UNDER_REVIEW]:
            self.status = self.VolunteerStatus.REJECTED
            self.reviewed_by = rejected_by
            self.review_date = timezone.now()
            self.status_changed_at = timezone.now()
            self.status_changed_by = rejected_by
            self.status_change_reason = reason
            self.save(update_fields=[
                'status', 'reviewed_by', 'review_date', 'status_changed_at',
                'status_changed_by', 'status_change_reason'
            ])
    
    def waitlist(self, waitlisted_by, reason=''):
        """Move volunteer to waitlist"""
        if self.status in [self.VolunteerStatus.PENDING, self.VolunteerStatus.UNDER_REVIEW]:
            self.status = self.VolunteerStatus.WAITLISTED
            self.reviewed_by = waitlisted_by
            self.review_date = timezone.now()
            self.status_changed_at = timezone.now()
            self.status_changed_by = waitlisted_by
            if reason:
                self.status_change_reason = reason
            self.save(update_fields=[
                'status', 'reviewed_by', 'review_date', 'status_changed_at',
                'status_changed_by', 'status_change_reason'
            ])
    
    def activate(self, activated_by):
        """Activate approved volunteer"""
        if self.status == self.VolunteerStatus.APPROVED:
            self.status = self.VolunteerStatus.ACTIVE
            self.status_changed_at = timezone.now()
            self.status_changed_by = activated_by
            self.save(update_fields=['status', 'status_changed_at', 'status_changed_by'])
    
    def suspend(self, suspended_by, reason):
        """Suspend volunteer"""
        if self.status == self.VolunteerStatus.ACTIVE:
            self.status = self.VolunteerStatus.SUSPENDED
            self.status_changed_at = timezone.now()
            self.status_changed_by = suspended_by
            self.status_change_reason = reason
            self.save(update_fields=[
                'status', 'status_changed_at', 'status_changed_by', 'status_change_reason'
            ])
    
    def withdraw(self, withdrawn_by=None, reason=''):
        """Withdraw volunteer application or participation"""
        self.status = self.VolunteerStatus.WITHDRAWN
        self.status_changed_at = timezone.now()
        if withdrawn_by:
            self.status_changed_by = withdrawn_by
        if reason:
            self.status_change_reason = reason
        self.save(update_fields=[
            'status', 'status_changed_at', 'status_changed_by', 'status_change_reason'
        ])
    
    # Status checking methods
    def is_pending(self):
        """Check if application is pending"""
        return self.status == self.VolunteerStatus.PENDING
    
    def is_approved(self):
        """Check if volunteer is approved"""
        return self.status == self.VolunteerStatus.APPROVED
    
    def is_active(self):
        """Check if volunteer is active"""
        return self.status == self.VolunteerStatus.ACTIVE
    
    def is_available_for_assignment(self):
        """Check if volunteer is available for role assignments"""
        return self.status in [
            self.VolunteerStatus.APPROVED,
            self.VolunteerStatus.ACTIVE
        ]
    
    def requires_background_check(self):
        """Check if volunteer requires background check"""
        return self.background_check_status in [
            'REQUIRED', 'SUBMITTED', 'IN_PROGRESS'
        ]
    
    def has_valid_background_check(self):
        """Check if volunteer has valid background check"""
        if self.background_check_status != 'APPROVED':
            return False
        
        if self.background_check_expiry:
            return timezone.now().date() <= self.background_check_expiry
        
        return True
    
    # Utility methods
    def get_age(self):
        """Get volunteer's age"""
        if self.user.date_of_birth:
            today = timezone.now().date()
            return today.year - self.user.date_of_birth.year - (
                (today.month, today.day) < 
                (self.user.date_of_birth.month, self.user.date_of_birth.day)
            )
        return None
    
    def get_experience_summary(self):
        """Get summary of volunteer experience"""
        return {
            'level': self.experience_level,
            'level_display': self.get_experience_level_display(),
            'previous_events': self.previous_events,
            'special_skills': self.special_skills,
            'languages': self.languages_spoken,
            'performance_rating': float(self.performance_rating) if self.performance_rating else None
        }
    
    def get_availability_summary(self):
        """Get summary of volunteer availability"""
        return {
            'level': self.availability_level,
            'level_display': self.get_availability_level_display(),
            'available_dates': self.available_dates,
            'unavailable_dates': self.unavailable_dates,
            'preferred_time_slots': self.preferred_time_slots,
            'max_hours_per_day': self.max_hours_per_day,
            'has_transport': self.has_own_transport,
            'transport_method': self.get_transport_method_display()
        }
    
    def get_preferences_summary(self):
        """Get summary of volunteer preferences"""
        return {
            'preferred_roles': self.preferred_roles,
            'preferred_venues': self.preferred_venues,
            'preferred_sports': self.preferred_sports,
            'role_restrictions': self.role_restrictions,
            'physical_capabilities': {
                'can_lift_heavy': self.can_lift_heavy_items,
                'can_stand_long': self.can_stand_long_periods,
                'can_work_outdoors': self.can_work_outdoors,
                'can_work_crowds': self.can_work_with_crowds
            }
        }
    
    def add_training_completion(self, training_module, completion_date=None):
        """Add completed training module"""
        if not self.training_completed:
            self.training_completed = []
        
        completion_entry = {
            'module': training_module,
            'completed_date': (completion_date or timezone.now()).isoformat(),
            'status': 'completed'
        }
        
        # Remove any existing entry for this module
        self.training_completed = [
            t for t in self.training_completed 
            if t.get('module') != training_module
        ]
        
        self.training_completed.append(completion_entry)
        self.save(update_fields=['training_completed'])
    
    def add_commendation(self, title, description, awarded_by, date=None):
        """Add commendation or award"""
        if not self.commendations:
            self.commendations = []
        
        commendation = {
            'title': title,
            'description': description,
            'awarded_by': awarded_by,
            'date': (date or timezone.now()).isoformat()
        }
        
        self.commendations.append(commendation)
        self.save(update_fields=['commendations'])
    
    def update_performance_rating(self, rating, feedback=''):
        """Update performance rating and feedback"""
        self.performance_rating = rating
        if feedback:
            if self.feedback_summary:
                self.feedback_summary += f"\n\n{timezone.now().date()}: {feedback}"
            else:
                self.feedback_summary = f"{timezone.now().date()}: {feedback}"
        
        self.save(update_fields=['performance_rating', 'feedback_summary'])
    
    def to_dict(self):
        """Convert volunteer profile to dictionary representation"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id),
            'user_name': self.user.get_full_name(),
            'user_email': self.user.email,
            'status': self.status,
            'status_display': self.get_status_display(),
            'application_date': self.application_date.isoformat() if self.application_date else None,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'experience_level': self.experience_level,
            'experience_level_display': self.get_experience_level_display(),
            'availability_level': self.availability_level,
            'availability_level_display': self.get_availability_level_display(),
            'preferred_roles': self.preferred_roles,
            'preferred_venues': self.preferred_venues,
            'is_corporate_volunteer': self.is_corporate_volunteer,
            'corporate_group_name': self.corporate_group_name,
            'has_own_transport': self.has_own_transport,
            'transport_method': self.get_transport_method_display(),
            'background_check_status': self.background_check_status,
            'reference_check_status': self.reference_check_status,
            'performance_rating': float(self.performance_rating) if self.performance_rating else None,
            'is_available_for_assignment': self.is_available_for_assignment(),
            'has_valid_background_check': self.has_valid_background_check(),
            'age': self.get_age(),
        }
    
    def get_absolute_url(self):
        """Get absolute URL for volunteer profile detail"""
        from django.urls import reverse
        return reverse('volunteers:profile-detail', kwargs={'pk': self.pk})
