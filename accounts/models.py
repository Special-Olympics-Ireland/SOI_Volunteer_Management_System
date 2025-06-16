from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

class User(AbstractUser):
    """
    Custom User model supporting multiple user types for ISG 2026 Volunteer Management System.
    Extends Django's AbstractUser to support volunteers, staff, and various management roles.
    """
    
    class UserType(models.TextChoices):
        VOLUNTEER = 'VOLUNTEER', _('Volunteer')
        STAFF = 'STAFF', _('Staff')
        VMT = 'VMT', _('Volunteer Management Team')
        CVT = 'CVT', _('Corporate Volunteer Team')
        GOC = 'GOC', _('Games Organizing Committee')
        ADMIN = 'ADMIN', _('Administrator')

    class VolunteerType(models.TextChoices):
        """Sub-categories for volunteers based on their background"""
        GENERAL = 'GENERAL', _('General Volunteer')
        EXISTING_SOI = 'EXISTING_SOI', _('Existing SOI Volunteer')
        CORPORATE = 'CORPORATE', _('Corporate Volunteer')
        COMMUNITY = 'COMMUNITY', _('Community Volunteer')
        THIRD_PARTY = 'THIRD_PARTY', _('3rd Party Volunteer')
        ATHLETE = 'ATHLETE', _('Athlete Volunteer')

    class MembershipType(models.TextChoices):
        """JustGo membership types"""
        VOLUNTEER = 'VOLUNTEER', _('Volunteer')
        EVENT_ONLY = 'EVENT_ONLY', _('Event Only Volunteer')
        AUXILIARY = 'AUXILIARY', _('Auxiliary Member')
        NONE = 'NONE', _('No Membership')

    # Core user identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.VOLUNTEER,
        help_text=_('Primary user type determining access level')
    )
    volunteer_type = models.CharField(
        max_length=20,
        choices=VolunteerType.choices,
        blank=True,
        null=True,
        help_text=_('Specific volunteer category (only for volunteers)')
    )

    # Extended profile information
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text=_('Primary contact phone number')
    )
    mobile_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text=_('Mobile phone number')
    )
    date_of_birth = models.DateField(
        null=True, 
        blank=True,
        help_text=_('Date of birth (required for volunteers)')
    )
    
    # Emergency contact information
    emergency_contact_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_('Emergency contact full name')
    )
    emergency_contact_relationship = models.CharField(
        max_length=50, 
        blank=True,
        help_text=_('Relationship to emergency contact')
    )
    emergency_phone = models.CharField(
        max_length=20, 
        blank=True,
        help_text=_('Emergency contact phone number')
    )
    
    # Address information
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Ireland')
    
    # Staff and management specific fields
    department = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_('Department (for staff and management users)')
    )
    position = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_('Job title or position')
    )
    employee_id = models.CharField(
        max_length=50, 
        blank=True,
        unique=True,
        null=True,
        help_text=_('Employee ID for staff members')
    )
    
    # JustGo integration fields
    justgo_member_id = models.CharField(
        max_length=100, 
        blank=True,
        unique=True,
        null=True,
        help_text=_('JustGo member ID for integration')
    )
    justgo_membership_type = models.CharField(
        max_length=20,
        choices=MembershipType.choices,
        default=MembershipType.NONE,
        help_text=_('JustGo membership type')
    )
    justgo_sync_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', _('Sync Pending')),
            ('SYNCED', _('Synced')),
            ('ERROR', _('Sync Error')),
            ('NOT_REQUIRED', _('Sync Not Required')),
        ],
        default='NOT_REQUIRED',
        help_text=_('JustGo synchronization status')
    )
    justgo_last_sync = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_('Last successful JustGo sync timestamp')
    )
    
    # Profile completion and verification
    profile_complete = models.BooleanField(
        default=False,
        help_text=_('Whether user has completed their profile')
    )
    email_verified = models.BooleanField(
        default=False,
        help_text=_('Whether email address has been verified')
    )
    phone_verified = models.BooleanField(
        default=False,
        help_text=_('Whether phone number has been verified')
    )
    
    # Preferences and settings
    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ('en', _('English')),
            ('ga', _('Irish')),
        ],
        default='en',
        help_text=_('Preferred language for communications')
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text=_('Receive email notifications')
    )
    sms_notifications = models.BooleanField(
        default=False,
        help_text=_('Receive SMS notifications')
    )
    
    # GDPR and consent management
    gdpr_consent = models.BooleanField(
        default=False,
        help_text=_('GDPR data processing consent')
    )
    gdpr_consent_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_('Date GDPR consent was given')
    )
    marketing_consent = models.BooleanField(
        default=False,
        help_text=_('Consent to receive marketing communications')
    )
    
    # Account status and management
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Whether user account has been approved by admin')
    )
    approval_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_('Date account was approved')
    )
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        help_text=_('Admin user who approved this account')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_('Last recorded user activity')
    )
    
    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about this user (admin only)')
    )
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['volunteer_type']),
            models.Index(fields=['justgo_member_id']),
            models.Index(fields=['email_verified', 'is_approved']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        if self.get_full_name():
            return f"{self.get_full_name()} ({self.get_user_type_display()})"
        return f"{self.username} ({self.get_user_type_display()})"
    
    def save(self, *args, **kwargs):
        """Custom save method with validation and auto-updates"""
        # Auto-approve admin and staff users
        if self.user_type in [self.UserType.ADMIN, self.UserType.STAFF] and not self.is_approved:
            self.is_approved = True
            self.approval_date = timezone.now()
        
        # Validate volunteer type
        if self.user_type == self.UserType.VOLUNTEER:
            if not self.volunteer_type:
                self.volunteer_type = self.VolunteerType.GENERAL
        elif self.volunteer_type:
            # Clear volunteer_type if not a volunteer
            self.volunteer_type = None
        
        # Update profile completion status
        self.profile_complete = self._check_profile_complete()
        
        # Update last activity if user is being saved due to activity
        if hasattr(self, '_update_activity') and self._update_activity:
            self.last_activity = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _check_profile_complete(self):
        """Check if user profile is complete based on user type"""
        required_fields = ['first_name', 'last_name', 'email']
        
        if self.user_type == self.UserType.VOLUNTEER:
            required_fields.extend([
                'phone_number', 'date_of_birth', 'address_line_1', 
                'city', 'county', 'postal_code'
            ])
            
            # Additional requirements for certain volunteer types
            if self.volunteer_type in [self.VolunteerType.CORPORATE, self.VolunteerType.THIRD_PARTY]:
                required_fields.extend(['emergency_contact_name', 'emergency_phone'])
        
        elif self.user_type in [self.UserType.STAFF, self.UserType.VMT, self.UserType.CVT, self.UserType.GOC]:
            required_fields.extend(['department', 'position'])
        
        # Check if all required fields are filled
        for field in required_fields:
            if not getattr(self, field, None):
                return False
        
        return True
    
    # User type checking methods
    def is_volunteer(self):
        """Check if user is a volunteer"""
        return self.user_type == self.UserType.VOLUNTEER
    
    def is_staff_member(self):
        """Check if user is a staff member"""
        return self.user_type == self.UserType.STAFF
    
    def is_vmt(self):
        """Check if user is Volunteer Management Team"""
        return self.user_type == self.UserType.VMT
    
    def is_cvt(self):
        """Check if user is Corporate Volunteer Team"""
        return self.user_type == self.UserType.CVT
    
    def is_goc(self):
        """Check if user is Games Organizing Committee"""
        return self.user_type == self.UserType.GOC
    
    def is_admin(self):
        """Check if user is an administrator"""
        return self.user_type == self.UserType.ADMIN
    
    def is_management(self):
        """Check if user has management privileges (VMT, CVT, GOC, Admin)"""
        return self.user_type in [
            self.UserType.VMT, 
            self.UserType.CVT, 
            self.UserType.GOC, 
            self.UserType.ADMIN
        ]
    
    def can_manage_volunteers(self):
        """Check if user can manage volunteers"""
        return self.user_type in [
            self.UserType.VMT, 
            self.UserType.GOC, 
            self.UserType.ADMIN
        ]
    
    def can_manage_events(self):
        """Check if user can manage events"""
        return self.user_type in [
            self.UserType.STAFF,
            self.UserType.GOC, 
            self.UserType.ADMIN
        ]
    
    # JustGo integration methods
    def needs_justgo_sync(self):
        """Check if user needs JustGo synchronization"""
        return (
            self.is_volunteer() and 
            self.justgo_sync_status in ['PENDING', 'ERROR'] and
            self.email_verified
        )
    
    def has_justgo_profile(self):
        """Check if user has a JustGo profile"""
        return bool(self.justgo_member_id)
    
    def get_full_address(self):
        """Get formatted full address"""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.county,
            self.postal_code,
            self.country
        ]
        return ', '.join(filter(None, address_parts))
    
    def get_age(self):
        """Calculate user's age"""
        if not self.date_of_birth:
            return None
        
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        
        # Adjust if birthday hasn't occurred this year
        if today < self.date_of_birth.replace(year=today.year):
            age -= 1
            
        return age
    
    def is_eligible_volunteer(self):
        """Check if user meets minimum volunteer requirements"""
        if not self.is_volunteer():
            return False
        
        # Check minimum age (15 years)
        age = self.get_age()
        if age is None or age < 15:
            return False
        
        # Check required consents
        if not self.gdpr_consent:
            return False
        
        # Check profile completion
        if not self.profile_complete:
            return False
        
        return True
    
    def update_activity(self):
        """Update last activity timestamp"""
        self._update_activity = True
        self.save(update_fields=['last_activity'])
    
    def approve_account(self, approved_by_user):
        """Approve user account"""
        self.is_approved = True
        self.approval_date = timezone.now()
        self.approved_by = approved_by_user
        self.save(update_fields=['is_approved', 'approval_date', 'approved_by'])
    
    def revoke_approval(self):
        """Revoke user account approval"""
        self.is_approved = False
        self.approval_date = None
        self.approved_by = None
        self.save(update_fields=['is_approved', 'approval_date', 'approved_by'])
