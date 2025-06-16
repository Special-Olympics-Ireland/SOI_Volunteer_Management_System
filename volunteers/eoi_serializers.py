"""
EOI API Serializers for ISG 2026 Volunteer Management System

This module provides REST API serializers for the Expression of Interest (EOI) system,
enabling external integrations and API access to volunteer registration data.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date
import uuid

from .eoi_models import (
    EOISubmission,
    EOIProfileInformation,
    EOIRecruitmentPreferences,
    EOIGamesInformation,
    CorporateVolunteerGroup
)

User = get_user_model()


class EOIProfileInformationSerializer(serializers.ModelSerializer):
    """
    Serializer for EOI Profile Information
    """
    confirm_email = serializers.EmailField(write_only=True, required=True)
    age = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = EOIProfileInformation
        fields = [
            'id', 'first_name', 'last_name', 'preferred_name', 'date_of_birth', 'age', 'gender',
            'email', 'confirm_email', 'phone_number', 'alternative_phone',
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship', 'emergency_contact_email',
            'education_level', 'employment_status', 'occupation',
            'languages_spoken', 'nationality',
            'medical_conditions', 'mobility_requirements',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'age']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'date_of_birth': {'required': True},
            'email': {'required': True},
            'phone_number': {'required': True},
            'address_line_1': {'required': True},
            'city': {'required': True},
            'state_province': {'required': True},
            'postal_code': {'required': True},
            'country': {'required': True},
            'emergency_contact_name': {'required': True},
            'emergency_contact_phone': {'required': True},
            'emergency_contact_relationship': {'required': True},
        }
    
    def get_age(self, obj):
        """Calculate age from date of birth"""
        if obj.date_of_birth:
            today = date.today()
            return today.year - obj.date_of_birth.year - (
                (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        return None
    
    def validate_date_of_birth(self, value):
        """Validate minimum age requirement (15 years)"""
        if value:
            today = date.today()
            age = today.year - value.year - (
                (today.month, today.day) < (value.month, value.day)
            )
            if age < 15:
                raise serializers.ValidationError(_('Volunteers must be at least 15 years old.'))
        return value
    
    def validate(self, data):
        """Validate email confirmation"""
        email = data.get('email')
        confirm_email = data.get('confirm_email')
        
        if email and confirm_email and email != confirm_email:
            raise serializers.ValidationError({
                'confirm_email': _('Email addresses do not match.')
            })
        
        return data


class EOIRecruitmentPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for EOI Recruitment Preferences
    """
    
    class Meta:
        model = EOIRecruitmentPreferences
        fields = [
            'id', 'volunteer_experience_level', 'previous_events', 'special_skills',
            'motivation', 'volunteer_goals',
            'preferred_sports', 'preferred_venues', 'preferred_roles', 'role_restrictions',
            'availability_level', 'preferred_time_slots', 'max_hours_per_day',
            'can_lift_heavy_items', 'can_stand_long_periods', 'can_work_outdoors', 'can_work_with_crowds',
            'has_own_transport', 'transport_method',
            'preferred_communication_method',
            'training_interests', 'leadership_interest',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'volunteer_experience_level': {'required': True},
            'motivation': {'required': True},
            'availability_level': {'required': True},
            'max_hours_per_day': {'required': True, 'min_value': 1, 'max_value': 24},
        }
    
    def validate_motivation(self, value):
        """Validate motivation field"""
        if value and len(value.strip()) < 50:
            raise serializers.ValidationError(
                _('Please provide a more detailed explanation (at least 50 characters).')
            )
        return value


class EOIGamesInformationSerializer(serializers.ModelSerializer):
    """
    Serializer for EOI Games Information
    """
    volunteer_photo_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = EOIGamesInformation
        fields = [
            'id', 'volunteer_photo', 'volunteer_photo_url', 'photo_consent',
            't_shirt_size', 'requires_uniform', 'uniform_collection_preference',
            'dietary_requirements', 'has_food_allergies', 'food_allergy_details',
            'available_dates', 'unavailable_dates', 'preferred_shifts',
            'requires_accommodation', 'accommodation_preferences',
            'social_media_consent', 'testimonial_consent',
            'is_part_of_group', 'group_name', 'group_leader_name', 'group_leader_contact',
            'additional_information', 'how_did_you_hear',
            'terms_accepted', 'privacy_policy_accepted', 'code_of_conduct_accepted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'volunteer_photo_url']
        extra_kwargs = {
            't_shirt_size': {'required': True},
            'photo_consent': {'required': True},
            'terms_accepted': {'required': True},
            'privacy_policy_accepted': {'required': True},
            'code_of_conduct_accepted': {'required': True},
        }
    
    def get_volunteer_photo_url(self, obj):
        """Get the full URL for the volunteer photo"""
        if obj.volunteer_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.volunteer_photo.url)
            return obj.volunteer_photo.url
        return None
    
    def validate(self, data):
        """Validate form dependencies"""
        # Validate food allergy details
        has_food_allergies = data.get('has_food_allergies')
        food_allergy_details = data.get('food_allergy_details')
        
        if has_food_allergies and not food_allergy_details:
            raise serializers.ValidationError({
                'food_allergy_details': _('Please provide details of your food allergies.')
            })
        
        # Validate accommodation preferences
        requires_accommodation = data.get('requires_accommodation')
        accommodation_preferences = data.get('accommodation_preferences')
        
        if requires_accommodation and not accommodation_preferences:
            raise serializers.ValidationError({
                'accommodation_preferences': _('Please provide your accommodation preferences.')
            })
        
        # Validate required consents
        required_consents = ['terms_accepted', 'privacy_policy_accepted', 'code_of_conduct_accepted']
        for consent_field in required_consents:
            if not data.get(consent_field):
                raise serializers.ValidationError({
                    consent_field: _('You must accept this to proceed.')
                })
        
        return data


class CorporateVolunteerGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Corporate Volunteer Groups
    """
    volunteer_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CorporateVolunteerGroup
        fields = [
            'id', 'name', 'description', 'website',
            'primary_contact_name', 'primary_contact_email', 'primary_contact_phone',
            'address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country',
            'expected_volunteer_count', 'volunteer_count', 'industry_sector',
            'preferred_volunteer_roles', 'preferred_venues', 'group_requirements',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'volunteer_count', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': True},
            'primary_contact_name': {'required': True},
            'primary_contact_email': {'required': True},
            'primary_contact_phone': {'required': True},
            'address_line_1': {'required': True},
            'city': {'required': True},
            'state_province': {'required': True},
            'postal_code': {'required': True},
            'country': {'required': True},
            'expected_volunteer_count': {'required': True, 'min_value': 1},
        }
    
    def get_volunteer_count(self, obj):
        """Get the actual number of volunteers registered for this group"""
        return EOIGamesInformation.objects.filter(
            group_name=obj.name,
            eoi_submission__status__in=['SUBMITTED', 'UNDER_REVIEW', 'APPROVED']
        ).count()


class EOISubmissionSerializer(serializers.ModelSerializer):
    """
    Main serializer for EOI Submissions
    """
    profile_information = EOIProfileInformationSerializer(read_only=True)
    recruitment_preferences = EOIRecruitmentPreferencesSerializer(read_only=True)
    games_information = EOIGamesInformationSerializer(read_only=True)
    user_email = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    volunteer_type_display = serializers.CharField(source='get_volunteer_type_display', read_only=True)
    
    class Meta:
        model = EOISubmission
        fields = [
            'id', 'user', 'user_email', 'session_key',
            'volunteer_type', 'volunteer_type_display',
            'status', 'status_display',
            'completion_percentage',
            'profile_section_complete', 'recruitment_section_complete', 'games_section_complete',
            'profile_information', 'recruitment_preferences', 'games_information',
            'submitted_at', 'reviewed_at', 'review_notes',
            'confirmation_email_sent', 'confirmation_email_sent_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'completion_percentage', 'status_display', 'volunteer_type_display',
            'profile_section_complete', 'recruitment_section_complete', 'games_section_complete',
            'submitted_at', 'reviewed_at', 'confirmation_email_sent', 'confirmation_email_sent_at',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'volunteer_type': {'required': True},
        }
    
    def get_user_email(self, obj):
        """Get user email from profile information or user model"""
        if obj.profile_information and obj.profile_information.email:
            return obj.profile_information.email
        elif obj.user and obj.user.email:
            return obj.user.email
        return None


class EOISubmissionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new EOI submissions
    """
    profile_information = EOIProfileInformationSerializer(required=True)
    recruitment_preferences = EOIRecruitmentPreferencesSerializer(required=True)
    games_information = EOIGamesInformationSerializer(required=True)
    
    class Meta:
        model = EOISubmission
        fields = [
            'volunteer_type',
            'profile_information',
            'recruitment_preferences',
            'games_information'
        ]
        extra_kwargs = {
            'volunteer_type': {'required': True},
        }
    
    def create(self, validated_data):
        """Create EOI submission with all related data"""
        profile_data = validated_data.pop('profile_information')
        recruitment_data = validated_data.pop('recruitment_preferences')
        games_data = validated_data.pop('games_information')
        
        # Remove confirm_email from profile_data as it's not a model field
        profile_data.pop('confirm_email', None)
        
        # Create the main submission
        eoi_submission = EOISubmission.objects.create(**validated_data)
        
        # Create related objects
        profile_info = EOIProfileInformation.objects.create(
            eoi_submission=eoi_submission,
            **profile_data
        )
        
        recruitment_prefs = EOIRecruitmentPreferences.objects.create(
            eoi_submission=eoi_submission,
            **recruitment_data
        )
        
        games_info = EOIGamesInformation.objects.create(
            eoi_submission=eoi_submission,
            **games_data
        )
        
        # Update completion status
        eoi_submission.profile_section_complete = True
        eoi_submission.recruitment_section_complete = True
        eoi_submission.games_section_complete = True
        eoi_submission.status = EOISubmission.SubmissionStatus.SUBMITTED
        eoi_submission.save()
        
        return eoi_submission


class EOISubmissionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating EOI submissions (staff only)
    """
    
    class Meta:
        model = EOISubmission
        fields = [
            'status',
            'review_notes'
        ]
        extra_kwargs = {
            'status': {'required': False},
            'review_notes': {'required': False},
        }
    
    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.instance
        if instance:
            current_status = instance.status
            
            # Define allowed status transitions
            allowed_transitions = {
                'DRAFT': ['SUBMITTED', 'CANCELLED'],
                'SUBMITTED': ['UNDER_REVIEW', 'CANCELLED'],
                'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'PENDING_INFO'],
                'PENDING_INFO': ['UNDER_REVIEW', 'REJECTED'],
                'APPROVED': ['CONFIRMED', 'REJECTED'],
                'REJECTED': ['UNDER_REVIEW'],  # Allow re-review
                'CONFIRMED': [],  # Final state
                'CANCELLED': ['DRAFT'],  # Allow restart
                'WITHDRAWN': []  # Final state
            }
            
            if value not in allowed_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f'Cannot transition from {current_status} to {value}'
                )
        
        return value


class EOISubmissionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing EOI submissions
    """
    user_email = serializers.SerializerMethodField(read_only=True)
    volunteer_name = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    volunteer_type_display = serializers.CharField(source='get_volunteer_type_display', read_only=True)
    
    class Meta:
        model = EOISubmission
        fields = [
            'id', 'user_email', 'volunteer_name',
            'volunteer_type', 'volunteer_type_display',
            'status', 'status_display',
            'completion_percentage',
            'submitted_at', 'created_at'
        ]
    
    def get_user_email(self, obj):
        """Get user email"""
        if obj.profile_information and obj.profile_information.email:
            return obj.profile_information.email
        elif obj.user and obj.user.email:
            return obj.user.email
        return None
    
    def get_volunteer_name(self, obj):
        """Get volunteer name"""
        if obj.profile_information:
            name = f"{obj.profile_information.first_name} {obj.profile_information.last_name}"
            if obj.profile_information.preferred_name:
                name = f"{obj.profile_information.preferred_name} ({name})"
            return name
        return None


class EOIStatsSerializer(serializers.Serializer):
    """
    Serializer for EOI statistics
    """
    total_submissions = serializers.IntegerField()
    by_status = serializers.DictField()
    by_volunteer_type = serializers.DictField()
    completion_rate = serializers.FloatField()
    recent_submissions = serializers.IntegerField()
    pending_review = serializers.IntegerField()
    approved_count = serializers.IntegerField() 