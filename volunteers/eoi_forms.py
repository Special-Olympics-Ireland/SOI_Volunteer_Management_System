"""
Expression of Interest (EOI) Forms for ISG 2026 Volunteer Management System

This module contains forms for the three-part EOI form structure:
1. Profile Information Form (personal details, contact, demographics)
2. Recruitment Preferences Form (venue preferences, sports, skills, roles)
3. Games Information Form (photo upload, t-shirt, dietary, availability)
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from .eoi_models import (
    EOISubmission, 
    EOIProfileInformation, 
    EOIRecruitmentPreferences, 
    EOIGamesInformation,
    CorporateVolunteerGroup
)
from .eoi_file_handlers import FileUploadValidator
from common.file_utils import validate_image_file

User = get_user_model()


class EOISubmissionForm(forms.ModelForm):
    """
    Initial form for starting an EOI submission
    """
    
    class Meta:
        model = EOISubmission
        fields = ['volunteer_type']
        widgets = {
            'volunteer_type': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'required': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['volunteer_type'].label = _('What type of volunteer are you?')
        self.fields['volunteer_type'].help_text = _(
            'Please select the category that best describes your volunteer application'
        )
        
        # Add descriptions for each volunteer type
        volunteer_type_descriptions = {
            'NEW_VOLUNTEER': _('First time volunteering at a major sporting event'),
            'RETURNING_VOLUNTEER': _('Previously volunteered at sporting events or with our organization'),
            'CORPORATE_VOLUNTEER': _('Volunteering as part of a corporate or organizational group'),
            'STUDENT_VOLUNTEER': _('Currently enrolled as a student'),
            'FAMILY_VOLUNTEER': _('Volunteering with family members'),
            'SPECIALIST_VOLUNTEER': _('Professional with specialized skills (medical, technical, etc.)')
        }
        
        # Update choices with descriptions
        choices_with_descriptions = []
        for value, label in self.fields['volunteer_type'].choices:
            if value:  # Skip empty choice
                description = volunteer_type_descriptions.get(value, '')
                choices_with_descriptions.append((value, f"{label} - {description}"))
        
        self.fields['volunteer_type'].choices = [('', _('Please select...'))] + choices_with_descriptions


class EOIProfileInformationForm(forms.ModelForm):
    """
    Profile Information section form (Part 1 of 3)
    """
    
    # Additional fields for better UX
    confirm_email = forms.EmailField(
        label=_('Confirm Email Address'),
        help_text=_('Please re-enter your email address to confirm')
    )
    
    # JustGo integration field for returning volunteers
    check_justgo_membership = forms.BooleanField(
        required=False,
        label=_('Check JustGo Membership'),
        help_text=_('Check this box if you have previously volunteered with us or have a JustGo membership. We will automatically fill in your details if found.'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'check_justgo_membership'
        })
    )
    
    class Meta:
        model = EOIProfileInformation
        fields = [
            'first_name', 'last_name', 'preferred_name', 'date_of_birth', 'gender',
            'email', 'phone_number', 'alternative_phone',
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship', 'emergency_contact_email',
            'education_level', 'employment_status', 'occupation',
            'languages_spoken', 'nationality',
            'medical_conditions', 'mobility_requirements'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your first name'),
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your last name'),
                'required': True
            }),
            'preferred_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter preferred name (optional)')
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your email address'),
                'required': True
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., +353 1 234 5678'),
                'required': True
            }),
            'alternative_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Alternative phone number (optional)')
            }),
            'address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Street address'),
                'required': True
            }),
            'address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Apartment, suite, etc. (optional)')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City'),
                'required': True
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('State/Province/County'),
                'required': True
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Postal/ZIP code'),
                'required': True
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'Ireland'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Full name of emergency contact'),
                'required': True
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Emergency contact phone number'),
                'required': True
            }),
            'emergency_contact_relationship': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., spouse, parent, friend'),
                'required': True
            }),
            'emergency_contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Emergency contact email (optional)')
            }),
            'education_level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Current job title or field of study')
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nationality (optional)')
            }),
            'medical_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Please list any medical conditions, allergies, or medications we should be aware of')
            }),
            'mobility_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Any mobility assistance or accessibility requirements')
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up languages spoken as a dynamic field
        self.fields['languages_spoken'] = forms.CharField(
            label=_('Languages Spoken'),
            required=False,
            help_text=_('List languages you speak and your proficiency level (e.g., English - Native, Irish - Conversational)'),
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('e.g., English - Native, Irish - Conversational, Spanish - Basic')
            })
        )
        
        # Add confirm email field
        self.fields['confirm_email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Confirm your email address'),
            'required': True
        })
        
        # Reorder fields for better UX
        field_order = [
            'check_justgo_membership',
            'first_name', 'last_name', 'preferred_name', 'date_of_birth', 'gender',
            'email', 'confirm_email', 'phone_number', 'alternative_phone',
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship', 'emergency_contact_email',
            'education_level', 'employment_status', 'occupation', 'nationality',
            'languages_spoken', 'medical_conditions', 'mobility_requirements'
        ]
        
        # Reorder fields
        for field_name in reversed(field_order):
            if field_name in self.fields:
                self.fields.move_to_end(field_name, last=False)
    
    def clean_date_of_birth(self):
        """Validate minimum age requirement (15 years)"""
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            today = date.today()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
            if age < 15:
                raise ValidationError(_('Volunteers must be at least 15 years old.'))
        return date_of_birth
    
    def clean(self):
        """Validate email confirmation"""
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        
        if email and confirm_email and email != confirm_email:
            raise ValidationError({
                'confirm_email': _('Email addresses do not match.')
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save with languages processing"""
        instance = super().save(commit=False)
        
        # Process languages_spoken field
        languages_text = self.cleaned_data.get('languages_spoken', '')
        if languages_text:
            # Simple parsing of languages (can be enhanced later)
            languages_list = [lang.strip() for lang in languages_text.split(',') if lang.strip()]
            instance.languages_spoken = languages_list
        else:
            instance.languages_spoken = []
        
        if commit:
            instance.save()
        return instance


class EOIRecruitmentPreferencesForm(forms.ModelForm):
    """
    Recruitment Preferences section form (Part 2 of 3)
    """
    
    class Meta:
        model = EOIRecruitmentPreferences
        fields = [
            'volunteer_experience_level', 'previous_events', 'special_skills',
            'motivation', 'volunteer_goals',
            'preferred_sports', 'preferred_venues', 'preferred_roles', 'role_restrictions',
            'availability_level', 'preferred_time_slots', 'max_hours_per_day',
            'can_lift_heavy_items', 'can_stand_long_periods', 'can_work_outdoors', 'can_work_with_crowds',
            'has_own_transport', 'transport_method',
            'preferred_communication_method',
            'training_interests', 'leadership_interest'
        ]
        
        widgets = {
            'volunteer_experience_level': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'previous_events': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List any previous events you have volunteered at')
            }),
            'special_skills': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List any special skills, qualifications, or certifications')
            }),
            'motivation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Tell us why you want to volunteer for ISG 2026'),
                'required': True
            }),
            'volunteer_goals': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('What do you hope to achieve through volunteering?')
            }),
            'availability_level': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'max_hours_per_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 24,
                'value': 8
            }),
            'can_lift_heavy_items': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_stand_long_periods': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_work_outdoors': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_work_with_crowds': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'has_own_transport': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'transport_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'preferred_communication_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'leadership_interest': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up dynamic choice fields
        self._setup_sports_field()
        self._setup_venues_field()
        self._setup_roles_field()
        self._setup_time_slots_field()
        self._setup_training_interests_field()
        
        # Add help text
        self.fields['motivation'].help_text = _(
            'This helps us understand your interest and match you with suitable roles'
        )
        self.fields['max_hours_per_day'].help_text = _(
            'Maximum number of hours you are willing to volunteer per day'
        )
    
    def _setup_sports_field(self):
        """Set up preferred sports as multiple choice field"""
        SPORTS_CHOICES = [
            ('athletics', _('Athletics')),
            ('swimming', _('Swimming')),
            ('cycling', _('Cycling')),
            ('gymnastics', _('Gymnastics')),
            ('basketball', _('Basketball')),
            ('football', _('Football')),
            ('rugby', _('Rugby')),
            ('hockey', _('Hockey')),
            ('tennis', _('Tennis')),
            ('badminton', _('Badminton')),
            ('boxing', _('Boxing')),
            ('weightlifting', _('Weightlifting')),
            ('rowing', _('Rowing')),
            ('sailing', _('Sailing')),
            ('equestrian', _('Equestrian')),
            ('golf', _('Golf')),
            ('archery', _('Archery')),
            ('shooting', _('Shooting')),
            ('triathlon', _('Triathlon')),
            ('other', _('Other Sports'))
        ]
        
        self.fields['preferred_sports'] = forms.MultipleChoiceField(
            choices=SPORTS_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Sports'),
            help_text=_('Select the sports you are most interested in supporting')
        )
    
    def _setup_venues_field(self):
        """Set up preferred venues as multiple choice field"""
        VENUE_CHOICES = [
            ('main_stadium', _('Main Stadium')),
            ('aquatic_center', _('Aquatic Center')),
            ('indoor_arena', _('Indoor Arena')),
            ('outdoor_venues', _('Outdoor Venues')),
            ('training_facilities', _('Training Facilities')),
            ('athlete_village', _('Athlete Village')),
            ('media_center', _('Media Center')),
            ('transport_hubs', _('Transport Hubs')),
            ('city_center', _('City Center Locations')),
            ('accommodation', _('Accommodation Venues')),
            ('no_preference', _('No Preference'))
        ]
        
        self.fields['preferred_venues'] = forms.MultipleChoiceField(
            choices=VENUE_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Venues'),
            help_text=_('Select the types of venues you would prefer to work at')
        )
    
    def _setup_roles_field(self):
        """Set up preferred roles as multiple choice field"""
        ROLE_CHOICES = [
            ('spectator_services', _('Spectator Services')),
            ('athlete_services', _('Athlete Services')),
            ('media_operations', _('Media Operations')),
            ('transport', _('Transport')),
            ('security', _('Security')),
            ('medical', _('Medical Support')),
            ('technology', _('Technology Support')),
            ('ceremonies', _('Opening/Closing Ceremonies')),
            ('hospitality', _('Hospitality')),
            ('accreditation', _('Accreditation')),
            ('results', _('Results & Timing')),
            ('venue_operations', _('Venue Operations')),
            ('logistics', _('Logistics')),
            ('administration', _('Administration')),
            ('language_services', _('Language Services')),
            ('no_preference', _('No Preference'))
        ]
        
        self.fields['preferred_roles'] = forms.MultipleChoiceField(
            choices=ROLE_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Volunteer Roles'),
            help_text=_('Select the roles you are most interested in')
        )
    
    def _setup_time_slots_field(self):
        """Set up preferred time slots as multiple choice field"""
        TIME_SLOT_CHOICES = [
            ('early_morning', _('Early Morning (5:00-9:00 AM)')),
            ('morning', _('Morning (9:00 AM-1:00 PM)')),
            ('afternoon', _('Afternoon (1:00-5:00 PM)')),
            ('evening', _('Evening (5:00-9:00 PM)')),
            ('late_evening', _('Late Evening (9:00 PM-1:00 AM)')),
            ('overnight', _('Overnight (1:00-5:00 AM)')),
            ('flexible', _('Flexible - Any Time'))
        ]
        
        self.fields['preferred_time_slots'] = forms.MultipleChoiceField(
            choices=TIME_SLOT_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Time Slots'),
            help_text=_('Select the time slots you prefer to work')
        )
    
    def _setup_training_interests_field(self):
        """Set up training interests as multiple choice field"""
        TRAINING_CHOICES = [
            ('customer_service', _('Customer Service')),
            ('first_aid', _('First Aid')),
            ('language_skills', _('Language Skills')),
            ('technology', _('Technology Training')),
            ('leadership', _('Leadership Skills')),
            ('sport_specific', _('Sport-Specific Knowledge')),
            ('cultural_awareness', _('Cultural Awareness')),
            ('disability_awareness', _('Disability Awareness')),
            ('media_training', _('Media Training')),
            ('conflict_resolution', _('Conflict Resolution'))
        ]
        
        self.fields['training_interests'] = forms.MultipleChoiceField(
            choices=TRAINING_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Training Interests'),
            help_text=_('Select areas where you would like to receive training')
        )
    
    def clean_motivation(self):
        """Validate motivation field"""
        motivation = self.cleaned_data.get('motivation')
        if motivation and len(motivation.strip()) < 50:
            raise ValidationError(_('Please provide a more detailed explanation (at least 50 characters).'))
        return motivation
    
    def save(self, commit=True):
        """Save with proper JSON field handling"""
        instance = super().save(commit=False)
        
        # Convert multiple choice fields to JSON lists
        for field_name in ['preferred_sports', 'preferred_venues', 'preferred_roles', 'preferred_time_slots', 'training_interests']:
            if field_name in self.cleaned_data:
                setattr(instance, field_name, list(self.cleaned_data[field_name]))
        
        # Handle role restrictions (if any were specified in the form)
        if hasattr(self, 'cleaned_data') and 'role_restrictions' in self.cleaned_data:
            instance.role_restrictions = self.cleaned_data['role_restrictions'] or []
        
        if commit:
            instance.save()
        return instance


class EOIGamesInformationForm(forms.ModelForm):
    """
    Games Information section form (Part 3 of 3)
    """
    
    # Corporate group selection field
    corporate_group = forms.ModelChoiceField(
        queryset=CorporateVolunteerGroup.objects.filter(status='ACTIVE'),
        required=False,
        empty_label=_('Select your organization (if applicable)'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Corporate/Organization Group'),
        help_text=_('If you are volunteering as part of a corporate or organizational group, please select it here')
    )
    
    class Meta:
        model = EOIGamesInformation
        fields = [
            'volunteer_photo', 'photo_consent',
            't_shirt_size', 'requires_uniform', 'uniform_collection_preference',
            'dietary_requirements', 'has_food_allergies', 'food_allergy_details',
            'available_dates', 'unavailable_dates', 'preferred_shifts',
            'requires_accommodation', 'accommodation_preferences',
            'social_media_consent', 'testimonial_consent',
            'is_part_of_group', 'group_name', 'group_leader_name', 'group_leader_contact',
            'additional_information', 'how_did_you_hear',
            'terms_accepted', 'privacy_policy_accepted', 'code_of_conduct_accepted'
        ]
        
        widgets = {
            'volunteer_photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png'
            }),
            'photo_consent': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'required': True
            }),
            't_shirt_size': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'requires_uniform': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'uniform_collection_preference': forms.Select(attrs={
                'class': 'form-select'
            }),
            'dietary_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Please describe any dietary requirements, preferences, or restrictions')
            }),
            'has_food_allergies': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'food_allergy_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Please provide details of your food allergies or intolerances')
            }),
            'requires_accommodation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'accommodation_preferences': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Please describe your accommodation preferences or requirements')
            }),
            'social_media_consent': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'testimonial_consent': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_part_of_group': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'group_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Name of your group or organization')
            }),
            'group_leader_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Name of group leader or coordinator')
            }),
            'group_leader_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Contact information for group leader')
            }),
            'additional_information': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Any additional information you would like to share with us')
            }),
            'how_did_you_hear': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., website, social media, friend, advertisement')
            }),
            'terms_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'required': True
            }),
            'privacy_policy_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'required': True
            }),
            'code_of_conduct_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'required': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up dynamic date fields
        self._setup_availability_fields()
        self._setup_shift_preferences_field()
        
        # Add JavaScript-dependent field behavior
        self.fields['food_allergy_details'].required = False
        self.fields['group_name'].required = False
        self.fields['group_leader_name'].required = False
        self.fields['group_leader_contact'].required = False
        self.fields['accommodation_preferences'].required = False
        
        # Add help text for photo upload
        self.fields['volunteer_photo'].help_text = _(
            'Please upload a recent photo for your volunteer ID badge. '
            'Accepted formats: JPG, JPEG, PNG. Maximum file size: 5MB.'
        )
        
        # Add labels for consent fields
        self.fields['photo_consent'].label = _(
            'I consent to my photo being used for volunteer identification and promotional materials'
        )
        self.fields['social_media_consent'].label = _(
            'I consent to appear in social media posts and marketing materials'
        )
        self.fields['testimonial_consent'].label = _(
            'I consent to provide testimonials and quotes about my volunteer experience'
        )
        self.fields['terms_accepted'].label = _(
            'I accept the terms and conditions for volunteering'
        )
        self.fields['privacy_policy_accepted'].label = _(
            'I accept the privacy policy'
        )
        self.fields['code_of_conduct_accepted'].label = _(
            'I accept the volunteer code of conduct'
        )
    
    def _setup_availability_fields(self):
        """Set up availability date fields"""
        # These would typically be handled by JavaScript date pickers
        # For now, we'll use text areas with instructions
        self.fields['available_dates'] = forms.CharField(
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List the dates you are available during the Games (e.g., June 15-20, June 25)')
            }),
            required=False,
            label=_('Available Dates'),
            help_text=_('Please specify the dates you are available to volunteer during the Games')
        )
        
        self.fields['unavailable_dates'] = forms.CharField(
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('List any dates you are NOT available (e.g., June 22, June 28)')
            }),
            required=False,
            label=_('Unavailable Dates'),
            help_text=_('Please specify any dates you are NOT available during the Games')
        )
    
    def _setup_shift_preferences_field(self):
        """Set up shift preferences as multiple choice field"""
        SHIFT_CHOICES = [
            ('early_morning', _('Early Morning (5:00-9:00 AM)')),
            ('morning', _('Morning (9:00 AM-1:00 PM)')),
            ('afternoon', _('Afternoon (1:00-5:00 PM)')),
            ('evening', _('Evening (5:00-9:00 PM)')),
            ('late_evening', _('Late Evening (9:00 PM-1:00 AM)')),
            ('overnight', _('Overnight (1:00-5:00 AM)'))
        ]
        
        self.fields['preferred_shifts'] = forms.MultipleChoiceField(
            choices=SHIFT_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Shift Times'),
            help_text=_('Select your preferred shift times during the Games')
        )
    
    def clean_volunteer_photo(self):
        """Validate uploaded photo using enhanced file handler"""
        photo = self.cleaned_data.get('volunteer_photo')
        if photo:
            # Use the enhanced file upload validator
            FileUploadValidator.validate_volunteer_photo(photo)
        return photo
    
    def clean(self):
        """Validate form dependencies"""
        cleaned_data = super().clean()
        
        # Validate food allergy details
        has_food_allergies = cleaned_data.get('has_food_allergies')
        food_allergy_details = cleaned_data.get('food_allergy_details')
        
        if has_food_allergies and not food_allergy_details:
            raise ValidationError({
                'food_allergy_details': _('Please provide details of your food allergies.')
            })
        
        # Validate group information
        is_part_of_group = cleaned_data.get('is_part_of_group')
        group_name = cleaned_data.get('group_name')
        corporate_group = cleaned_data.get('corporate_group')
        
        if is_part_of_group and not group_name and not corporate_group:
            raise ValidationError({
                'group_name': _('Please provide the name of your group or select from the corporate groups list.')
            })
        
        # Validate accommodation preferences
        requires_accommodation = cleaned_data.get('requires_accommodation')
        accommodation_preferences = cleaned_data.get('accommodation_preferences')
        
        if requires_accommodation and not accommodation_preferences:
            raise ValidationError({
                'accommodation_preferences': _('Please provide your accommodation preferences.')
            })
        
        # Validate required consents
        required_consents = ['terms_accepted', 'privacy_policy_accepted', 'code_of_conduct_accepted']
        for consent_field in required_consents:
            if not cleaned_data.get(consent_field):
                field_label = self.fields[consent_field].label
                raise ValidationError({
                    consent_field: _('You must accept this to proceed.')
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save with proper JSON field handling"""
        instance = super().save(commit=False)
        
        # Handle corporate group selection
        corporate_group = self.cleaned_data.get('corporate_group')
        if corporate_group:
            instance.is_part_of_group = True
            instance.group_name = corporate_group.name
            instance.group_leader_name = corporate_group.primary_contact_name
            instance.group_leader_contact = corporate_group.primary_contact_email
        
        # Convert date fields to JSON lists (simple parsing for now)
        available_dates_text = self.cleaned_data.get('available_dates', '')
        if available_dates_text:
            # Simple parsing - can be enhanced with proper date parsing
            instance.available_dates = [date.strip() for date in available_dates_text.split(',') if date.strip()]
        
        unavailable_dates_text = self.cleaned_data.get('unavailable_dates', '')
        if unavailable_dates_text:
            instance.unavailable_dates = [date.strip() for date in unavailable_dates_text.split(',') if date.strip()]
        
        # Convert preferred shifts to JSON list
        if 'preferred_shifts' in self.cleaned_data:
            instance.preferred_shifts = list(self.cleaned_data['preferred_shifts'])
        
        if commit:
            instance.save()
        return instance


class CorporateVolunteerGroupForm(forms.ModelForm):
    """
    Form for corporate groups to register for volunteer opportunities
    """
    
    class Meta:
        model = CorporateVolunteerGroup
        fields = [
            'name', 'description', 'website',
            'primary_contact_name', 'primary_contact_email', 'primary_contact_phone',
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            'expected_volunteer_count', 'industry_sector',
            'preferred_volunteer_roles', 'preferred_venues', 'group_requirements'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Organization or company name'),
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Brief description of your organization')
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://www.example.com')
            }),
            'primary_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Full name of primary contact person'),
                'required': True
            }),
            'primary_contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Primary contact email address'),
                'required': True
            }),
            'primary_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Primary contact phone number'),
                'required': True
            }),
            'address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Street address'),
                'required': True
            }),
            'address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Suite, floor, etc. (optional)')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City'),
                'required': True
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('State/Province/County'),
                'required': True
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Postal/ZIP code'),
                'required': True
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'Ireland'
            }),
            'expected_volunteer_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': _('Expected number of volunteers')
            }),
            'industry_sector': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Technology, Healthcare, Finance')
            }),
            'group_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Any special requirements or requests for your group')
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up multiple choice fields for preferences
        self._setup_roles_field()
        self._setup_venues_field()
    
    def _setup_roles_field(self):
        """Set up preferred roles field"""
        ROLE_CHOICES = [
            ('spectator_services', _('Spectator Services')),
            ('athlete_services', _('Athlete Services')),
            ('media_operations', _('Media Operations')),
            ('transport', _('Transport')),
            ('hospitality', _('Hospitality')),
            ('venue_operations', _('Venue Operations')),
            ('administration', _('Administration')),
            ('technology', _('Technology Support')),
            ('logistics', _('Logistics'))
        ]
        
        self.fields['preferred_volunteer_roles'] = forms.MultipleChoiceField(
            choices=ROLE_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Volunteer Roles for Group'),
            help_text=_('Select the roles your group members would prefer')
        )
    
    def _setup_venues_field(self):
        """Set up preferred venues field"""
        VENUE_CHOICES = [
            ('main_stadium', _('Main Stadium')),
            ('aquatic_center', _('Aquatic Center')),
            ('indoor_arena', _('Indoor Arena')),
            ('outdoor_venues', _('Outdoor Venues')),
            ('athlete_village', _('Athlete Village')),
            ('media_center', _('Media Center')),
            ('city_center', _('City Center Locations')),
            ('no_preference', _('No Preference'))
        ]
        
        self.fields['preferred_venues'] = forms.MultipleChoiceField(
            choices=VENUE_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('Preferred Venues for Group'),
            help_text=_('Select the types of venues your group would prefer')
        )
    
    def save(self, commit=True):
        """Save with proper JSON field handling"""
        instance = super().save(commit=False)
        
        # Convert multiple choice fields to JSON lists
        if 'preferred_volunteer_roles' in self.cleaned_data:
            instance.preferred_volunteer_roles = list(self.cleaned_data['preferred_volunteer_roles'])
        
        if 'preferred_venues' in self.cleaned_data:
            instance.preferred_venues = list(self.cleaned_data['preferred_venues'])
        
        if commit:
            instance.save()
        return instance 