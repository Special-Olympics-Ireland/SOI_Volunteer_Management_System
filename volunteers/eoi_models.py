"""
Expression of Interest (EOI) Models for ISG 2026 Volunteer Management System

This module contains models for managing the three-part EOI form structure:
1. Profile Information (personal details, contact, demographics)
2. Recruitment Preferences (venue preferences, sports, skills, roles)
3. Games Information (photo upload, t-shirt, dietary, availability)
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from common.file_utils import validate_image_file

User = get_user_model()


class EOISubmission(models.Model):
    """
    Main EOI submission model that tracks the overall application process
    """
    
    class SubmissionStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft - In Progress')
        PROFILE_COMPLETE = 'PROFILE_COMPLETE', _('Profile Section Complete')
        RECRUITMENT_COMPLETE = 'RECRUITMENT_COMPLETE', _('Recruitment Section Complete')
        GAMES_COMPLETE = 'GAMES_COMPLETE', _('Games Section Complete')
        SUBMITTED = 'SUBMITTED', _('Submitted for Review')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')
    
    class VolunteerType(models.TextChoices):
        NEW_VOLUNTEER = 'NEW_VOLUNTEER', _('New Volunteer')
        RETURNING_VOLUNTEER = 'RETURNING_VOLUNTEER', _('Returning Volunteer')
        CORPORATE_VOLUNTEER = 'CORPORATE_VOLUNTEER', _('Corporate Volunteer')
        STUDENT_VOLUNTEER = 'STUDENT_VOLUNTEER', _('Student Volunteer')
        FAMILY_VOLUNTEER = 'FAMILY_VOLUNTEER', _('Family Volunteer')
        SPECIALIST_VOLUNTEER = 'SPECIALIST_VOLUNTEER', _('Specialist/Professional Volunteer')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User relationship (optional for anonymous submissions)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='eoi_submissions',
        help_text=_('Associated user account (if registered)')
    )
    
    # Submission tracking
    status = models.CharField(
        max_length=25,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.DRAFT,
        help_text=_('Current submission status')
    )
    volunteer_type = models.CharField(
        max_length=25,
        choices=VolunteerType.choices,
        help_text=_('Type of volunteer application')
    )
    
    # Form completion tracking
    profile_section_complete = models.BooleanField(
        default=False,
        help_text=_('Profile information section completed')
    )
    recruitment_section_complete = models.BooleanField(
        default=False,
        help_text=_('Recruitment preferences section completed')
    )
    games_section_complete = models.BooleanField(
        default=False,
        help_text=_('Games information section completed')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the EOI was submitted')
    )
    
    # Review tracking
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the EOI was reviewed')
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_eoi_submissions',
        help_text=_('Staff member who reviewed the EOI')
    )
    review_notes = models.TextField(
        blank=True,
        help_text=_('Internal review notes')
    )
    
    # Communication tracking
    confirmation_email_sent = models.BooleanField(
        default=False,
        help_text=_('Confirmation email sent to applicant')
    )
    confirmation_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When confirmation email was sent')
    )
    
    # Session tracking for anonymous users
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text=_('Session key for anonymous submissions')
    )
    
    # Progress tracking
    completion_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Overall completion percentage')
    )
    
    class Meta:
        verbose_name = _('EOI submission')
        verbose_name_plural = _('EOI submissions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['volunteer_type', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['session_key']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['reviewed_by', 'reviewed_at']),
        ]
    
    def __str__(self):
        if self.user:
            return f"EOI: {self.user.get_full_name()} ({self.get_status_display()})"
        return f"EOI: Anonymous ({self.get_status_display()}) - {self.created_at.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        """Update completion percentage and status based on section completion"""
        # Calculate completion percentage
        completed_sections = sum([
            self.profile_section_complete,
            self.recruitment_section_complete,
            self.games_section_complete
        ])
        self.completion_percentage = (completed_sections / 3) * 100
        
        # Update status based on completion
        if self.status == self.SubmissionStatus.DRAFT:
            if self.profile_section_complete and not self.recruitment_section_complete:
                self.status = self.SubmissionStatus.PROFILE_COMPLETE
            elif self.recruitment_section_complete and not self.games_section_complete:
                self.status = self.SubmissionStatus.RECRUITMENT_COMPLETE
            elif self.games_section_complete and self.completion_percentage == 100:
                self.status = self.SubmissionStatus.GAMES_COMPLETE
        
        super().save(*args, **kwargs)
    
    def submit(self):
        """Submit the EOI for review"""
        if self.completion_percentage < 100:
            raise ValidationError(_('All sections must be completed before submission'))
        
        self.status = self.SubmissionStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save()
    
    def is_complete(self):
        """Check if all sections are complete"""
        return all([
            self.profile_section_complete,
            self.recruitment_section_complete,
            self.games_section_complete
        ])
    
    def get_next_section(self):
        """Get the next section to complete"""
        if not self.profile_section_complete:
            return 'profile'
        elif not self.recruitment_section_complete:
            return 'recruitment'
        elif not self.games_section_complete:
            return 'games'
        return None


class EOIProfileInformation(models.Model):
    """
    Profile Information section of the EOI form
    Contains personal details, contact information, and demographics
    """
    
    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        NON_BINARY = 'NON_BINARY', _('Non-binary')
        PREFER_NOT_TO_SAY = 'PREFER_NOT_TO_SAY', _('Prefer not to say')
        OTHER = 'OTHER', _('Other')
    
    class EducationLevel(models.TextChoices):
        PRIMARY = 'PRIMARY', _('Primary School')
        SECONDARY = 'SECONDARY', _('Secondary School')
        CERTIFICATE = 'CERTIFICATE', _('Certificate/Diploma')
        UNDERGRADUATE = 'UNDERGRADUATE', _('Undergraduate Degree')
        POSTGRADUATE = 'POSTGRADUATE', _('Postgraduate Degree')
        DOCTORATE = 'DOCTORATE', _('Doctorate')
        OTHER = 'OTHER', _('Other')
    
    class EmploymentStatus(models.TextChoices):
        EMPLOYED_FULL_TIME = 'EMPLOYED_FULL_TIME', _('Employed Full-time')
        EMPLOYED_PART_TIME = 'EMPLOYED_PART_TIME', _('Employed Part-time')
        SELF_EMPLOYED = 'SELF_EMPLOYED', _('Self-employed')
        UNEMPLOYED = 'UNEMPLOYED', _('Unemployed')
        STUDENT = 'STUDENT', _('Student')
        RETIRED = 'RETIRED', _('Retired')
        HOMEMAKER = 'HOMEMAKER', _('Homemaker')
        OTHER = 'OTHER', _('Other')
    
    # Link to main EOI submission
    eoi_submission = models.OneToOneField(
        EOISubmission,
        on_delete=models.CASCADE,
        related_name='profile_information',
        help_text=_('Associated EOI submission')
    )
    
    # Personal Information
    first_name = models.CharField(
        max_length=100,
        help_text=_('First name')
    )
    last_name = models.CharField(
        max_length=100,
        help_text=_('Last name')
    )
    preferred_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Preferred name for communications and name tags')
    )
    date_of_birth = models.DateField(
        help_text=_('Date of birth (must be at least 15 years old)')
    )
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
        help_text=_('Gender identity')
    )
    
    # Contact Information
    email = models.EmailField(
        help_text=_('Primary email address')
    )
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.')
        )],
        help_text=_('Primary phone number')
    )
    alternative_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.')
        )],
        help_text=_('Alternative phone number')
    )
    
    # Address Information
    address_line_1 = models.CharField(
        max_length=255,
        help_text=_('Street address line 1')
    )
    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Street address line 2 (optional)')
    )
    city = models.CharField(
        max_length=100,
        help_text=_('City')
    )
    state_province = models.CharField(
        max_length=100,
        help_text=_('State or Province')
    )
    postal_code = models.CharField(
        max_length=20,
        help_text=_('Postal/ZIP code')
    )
    country = models.CharField(
        max_length=100,
        default='Ireland',
        help_text=_('Country')
    )
    
    # Emergency Contact
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
        help_text=_('Relationship to emergency contact')
    )
    emergency_contact_email = models.EmailField(
        blank=True,
        help_text=_('Emergency contact email (optional)')
    )
    
    # Demographics (optional)
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        blank=True,
        help_text=_('Highest level of education completed')
    )
    employment_status = models.CharField(
        max_length=25,
        choices=EmploymentStatus.choices,
        blank=True,
        help_text=_('Current employment status')
    )
    occupation = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Current occupation or field of study')
    )
    
    # Additional Information
    languages_spoken = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Languages spoken and proficiency levels')
    )
    nationality = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Nationality')
    )
    
    # Medical and Accessibility
    medical_conditions = models.TextField(
        blank=True,
        help_text=_('Any medical conditions or allergies we should be aware of')
    )
    mobility_requirements = models.TextField(
        blank=True,
        help_text=_('Any mobility assistance or accessibility requirements')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('EOI profile information')
        verbose_name_plural = _('EOI profile information')
    
    def __str__(self):
        return f"Profile: {self.first_name} {self.last_name}"
    
    def clean(self):
        """Validate profile information"""
        super().clean()
        
        # Validate minimum age (15 years)
        if self.date_of_birth:
            today = date.today()
            age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
            if age < 15:
                raise ValidationError({
                    'date_of_birth': _('Volunteers must be at least 15 years old.')
                })
    
    def get_age(self):
        """Calculate current age"""
        if not self.date_of_birth:
            return None
        
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def get_full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_display_name(self):
        """Get display name (preferred name if available, otherwise full name)"""
        return self.preferred_name or self.get_full_name()


class EOIRecruitmentPreferences(models.Model):
    """
    Recruitment Preferences section of the EOI form
    Contains venue preferences, sports interests, skills, and role preferences
    """
    
    class ExperienceLevel(models.TextChoices):
        NONE = 'NONE', _('No Experience')
        BEGINNER = 'BEGINNER', _('Beginner (1-2 events)')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermediate (3-5 events)')
        EXPERIENCED = 'EXPERIENCED', _('Experienced (6-10 events)')
        EXPERT = 'EXPERT', _('Expert (10+ events)')
        PROFESSIONAL = 'PROFESSIONAL', _('Professional/Staff')
    
    class AvailabilityLevel(models.TextChoices):
        FULL_TIME = 'FULL_TIME', _('Full Time (All Days)')
        PART_TIME = 'PART_TIME', _('Part Time (Some Days)')
        WEEKENDS_ONLY = 'WEEKENDS_ONLY', _('Weekends Only')
        SPECIFIC_DAYS = 'SPECIFIC_DAYS', _('Specific Days Only')
        FLEXIBLE = 'FLEXIBLE', _('Flexible')
        LIMITED = 'LIMITED', _('Limited Availability')
    
    # Link to main EOI submission
    eoi_submission = models.OneToOneField(
        EOISubmission,
        on_delete=models.CASCADE,
        related_name='recruitment_preferences',
        help_text=_('Associated EOI submission')
    )
    
    # Experience and Background
    volunteer_experience_level = models.CharField(
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
    
    # Motivation and Goals
    motivation = models.TextField(
        help_text=_('Why do you want to volunteer for ISG 2026?')
    )
    volunteer_goals = models.TextField(
        blank=True,
        help_text=_('What do you hope to achieve through volunteering?')
    )
    
    # Preferences
    preferred_sports = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Sports you are interested in supporting')
    )
    preferred_venues = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred venues or venue types')
    )
    preferred_roles = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred volunteer roles')
    )
    role_restrictions = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Roles or activities you cannot or will not do')
    )
    
    # Availability
    availability_level = models.CharField(
        max_length=20,
        choices=AvailabilityLevel.choices,
        default=AvailabilityLevel.FLEXIBLE,
        help_text=_('General availability level')
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
    
    # Physical Capabilities
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
    
    # Transport and Logistics
    has_own_transport = models.BooleanField(
        default=False,
        help_text=_('Has own reliable transport to venues')
    )
    transport_method = models.CharField(
        max_length=30,
        choices=[
            ('OWN_CAR', _('Own Car')),
            ('PUBLIC_TRANSPORT', _('Public Transport')),
            ('CYCLING', _('Cycling')),
            ('WALKING', _('Walking')),
            ('CARPOOL', _('Carpool')),
            ('VOLUNTEER_TRANSPORT', _('Volunteer Transport')),
            ('OTHER', _('Other')),
        ],
        default='PUBLIC_TRANSPORT',
        help_text=_('Primary method of transport to venues')
    )
    
    # Communication Preferences
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
    
    # Training and Development
    training_interests = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Areas of training you are interested in')
    )
    leadership_interest = models.BooleanField(
        default=False,
        help_text=_('Interested in leadership or supervisory roles')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('EOI recruitment preferences')
        verbose_name_plural = _('EOI recruitment preferences')
    
    def __str__(self):
        return f"Recruitment Preferences: {self.eoi_submission}"


class EOIGamesInformation(models.Model):
    """
    Games Information section of the EOI form
    Contains photo upload, uniform details, dietary requirements, and specific availability
    """
    
    class TShirtSize(models.TextChoices):
        XS = 'XS', _('Extra Small')
        S = 'S', _('Small')
        M = 'M', _('Medium')
        L = 'L', _('Large')
        XL = 'XL', _('Extra Large')
        XXL = 'XXL', _('2X Large')
        XXXL = 'XXXL', _('3X Large')
    
    # Link to main EOI submission
    eoi_submission = models.OneToOneField(
        EOISubmission,
        on_delete=models.CASCADE,
        related_name='games_information',
        help_text=_('Associated EOI submission')
    )
    
    # Photo Upload
    volunteer_photo = models.ImageField(
        upload_to='volunteer_photos/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
            validate_image_file
        ],
        help_text=_('Recent photo for volunteer ID badge (JPG, JPEG, or PNG format)')
    )
    photo_consent = models.BooleanField(
        default=False,
        help_text=_('I consent to my photo being used for volunteer identification and promotional materials')
    )
    
    # Uniform and Equipment
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
    uniform_collection_preference = models.CharField(
        max_length=20,
        choices=[
            ('PICKUP', _('Pick up at volunteer center')),
            ('DELIVERY', _('Delivery to address')),
            ('EVENT_DAY', _('Collect on event day')),
        ],
        default='PICKUP',
        help_text=_('Preferred method for uniform collection')
    )
    
    # Dietary Requirements
    dietary_requirements = models.TextField(
        blank=True,
        help_text=_('Dietary requirements, allergies, or preferences')
    )
    has_food_allergies = models.BooleanField(
        default=False,
        help_text=_('Has food allergies or intolerances')
    )
    food_allergy_details = models.TextField(
        blank=True,
        help_text=_('Details of food allergies or intolerances')
    )
    
    # Specific Availability for Games
    available_dates = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Specific dates available for volunteering during the Games')
    )
    unavailable_dates = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Dates not available for volunteering during the Games')
    )
    preferred_shifts = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred shift times (early morning, morning, afternoon, evening, late night)')
    )
    
    # Accommodation (if applicable)
    requires_accommodation = models.BooleanField(
        default=False,
        help_text=_('Requires accommodation during the Games')
    )
    accommodation_preferences = models.TextField(
        blank=True,
        help_text=_('Accommodation preferences or requirements')
    )
    
    # Social Media and Marketing Consent
    social_media_consent = models.BooleanField(
        default=False,
        help_text=_('I consent to appear in social media posts and marketing materials')
    )
    testimonial_consent = models.BooleanField(
        default=False,
        help_text=_('I consent to provide testimonials and quotes about my volunteer experience')
    )
    
    # Corporate/Group Information (if applicable)
    is_part_of_group = models.BooleanField(
        default=False,
        help_text=_('Part of a corporate or organized group')
    )
    group_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Name of corporate group or organization')
    )
    group_leader_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Name of group leader or coordinator')
    )
    group_leader_contact = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Contact information for group leader')
    )
    
    # Additional Information
    additional_information = models.TextField(
        blank=True,
        help_text=_('Any additional information you would like to share')
    )
    how_did_you_hear = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('How did you hear about the volunteer opportunity?')
    )
    
    # Terms and Conditions
    terms_accepted = models.BooleanField(
        default=False,
        help_text=_('I accept the terms and conditions for volunteering')
    )
    privacy_policy_accepted = models.BooleanField(
        default=False,
        help_text=_('I accept the privacy policy')
    )
    code_of_conduct_accepted = models.BooleanField(
        default=False,
        help_text=_('I accept the volunteer code of conduct')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('EOI games information')
        verbose_name_plural = _('EOI games information')
    
    def __str__(self):
        return f"Games Information: {self.eoi_submission}"
    
    def clean(self):
        """Validate games information"""
        super().clean()
        
        # Validate that all required consents are given
        if not self.terms_accepted:
            raise ValidationError({
                'terms_accepted': _('You must accept the terms and conditions to proceed.')
            })
        
        if not self.privacy_policy_accepted:
            raise ValidationError({
                'privacy_policy_accepted': _('You must accept the privacy policy to proceed.')
            })
        
        if not self.code_of_conduct_accepted:
            raise ValidationError({
                'code_of_conduct_accepted': _('You must accept the volunteer code of conduct to proceed.')
            })
        
        # Validate food allergy details if allergies are indicated
        if self.has_food_allergies and not self.food_allergy_details.strip():
            raise ValidationError({
                'food_allergy_details': _('Please provide details of your food allergies.')
            })
        
        # Validate group information if part of group
        if self.is_part_of_group:
            if not self.group_name.strip():
                raise ValidationError({
                    'group_name': _('Please provide the name of your group or organization.')
                })


class CorporateVolunteerGroup(models.Model):
    """
    Model for managing corporate volunteer groups and their registrations
    """
    
    class GroupStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        INACTIVE = 'INACTIVE', _('Inactive')
        PENDING = 'PENDING', _('Pending Approval')
        SUSPENDED = 'SUSPENDED', _('Suspended')
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Group Information
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text=_('Corporate group or organization name')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Description of the organization')
    )
    website = models.URLField(
        blank=True,
        help_text=_('Organization website')
    )
    
    # Contact Information
    primary_contact_name = models.CharField(
        max_length=200,
        help_text=_('Primary contact person name')
    )
    primary_contact_email = models.EmailField(
        help_text=_('Primary contact email')
    )
    primary_contact_phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.')
        )],
        help_text=_('Primary contact phone number')
    )
    
    # Address Information
    address_line_1 = models.CharField(
        max_length=255,
        help_text=_('Street address line 1')
    )
    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Street address line 2 (optional)')
    )
    city = models.CharField(
        max_length=100,
        help_text=_('City')
    )
    state_province = models.CharField(
        max_length=100,
        help_text=_('State or Province')
    )
    postal_code = models.CharField(
        max_length=20,
        help_text=_('Postal/ZIP code')
    )
    country = models.CharField(
        max_length=100,
        default='Ireland',
        help_text=_('Country')
    )
    
    # Group Details
    status = models.CharField(
        max_length=15,
        choices=GroupStatus.choices,
        default=GroupStatus.PENDING,
        help_text=_('Current group status')
    )
    expected_volunteer_count = models.PositiveIntegerField(
        help_text=_('Expected number of volunteers from this group')
    )
    industry_sector = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Industry sector or type of organization')
    )
    
    # Preferences
    preferred_volunteer_roles = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred volunteer roles for group members')
    )
    preferred_venues = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Preferred venues for group volunteering')
    )
    group_requirements = models.TextField(
        blank=True,
        help_text=_('Special requirements or requests for the group')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the group was approved')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_corporate_groups',
        help_text=_('Staff member who approved the group')
    )
    
    class Meta:
        verbose_name = _('corporate volunteer group')
        verbose_name_plural = _('corporate volunteer groups')
        ordering = ['name']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['name']),
            models.Index(fields=['primary_contact_email']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.expected_volunteer_count} volunteers)"
    
    def get_volunteer_count(self):
        """Get actual number of volunteers registered from this group"""
        return EOIGamesInformation.objects.filter(
            group_name=self.name,
            is_part_of_group=True
        ).count()
    
    def approve(self, approved_by):
        """Approve the corporate group"""
        self.status = self.GroupStatus.ACTIVE
        self.approved_at = timezone.now()
        self.approved_by = approved_by
        self.save()
    
    def suspend(self, reason=''):
        """Suspend the corporate group"""
        self.status = self.GroupStatus.SUSPENDED
        self.save()
        # Could add reason tracking here if needed 