"""
Unit Tests for EOI Models - ISG 2026 Volunteer Management System

This module contains comprehensive tests for all EOI models including:
- EOISubmission model with status workflow and validation
- EOIProfileInformation model with age calculation and validation
- EOIRecruitmentPreferences model with preference validation
- EOIGamesInformation model with file handling and consent validation
- CorporateVolunteerGroup model with group management
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from unittest.mock import patch, MagicMock

from .eoi_models import (
    EOISubmission,
    EOIProfileInformation,
    EOIRecruitmentPreferences,
    EOIGamesInformation,
    CorporateVolunteerGroup
)

User = get_user_model()


class EOISubmissionModelTest(TestCase):
    """Test cases for EOISubmission model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_eoi_submission_creation(self):
        """Test basic EOI submission creation"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        self.assertEqual(submission.volunteer_type, 'NEW_VOLUNTEER')
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.status, EOISubmission.SubmissionStatus.DRAFT)
        self.assertFalse(submission.profile_section_complete)
        self.assertFalse(submission.recruitment_section_complete)
        self.assertFalse(submission.games_section_complete)
        self.assertFalse(submission.email_confirmed)
        self.assertIsNone(submission.submitted_at)
        self.assertIsInstance(submission.id, uuid.UUID)
    
    def test_eoi_submission_anonymous_creation(self):
        """Test EOI submission creation for anonymous users"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            session_key='test_session_123'
        )
        
        self.assertIsNone(submission.user)
        self.assertEqual(submission.session_key, 'test_session_123')
        self.assertEqual(submission.status, EOISubmission.SubmissionStatus.DRAFT)
    
    def test_volunteer_type_choices(self):
        """Test all volunteer type choices are valid"""
        valid_types = [choice[0] for choice in EOISubmission.VolunteerType.choices]
        
        for volunteer_type in valid_types:
            submission = EOISubmission.objects.create(
                volunteer_type=volunteer_type,
                user=self.user
            )
            self.assertEqual(submission.volunteer_type, volunteer_type)
    
    def test_status_workflow(self):
        """Test status workflow transitions"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        # Test draft to submitted
        submission.status = EOISubmission.SubmissionStatus.SUBMITTED
        submission.submitted_at = datetime.now()
        submission.save()
        
        self.assertEqual(submission.status, EOISubmission.SubmissionStatus.SUBMITTED)
        self.assertIsNotNone(submission.submitted_at)
    
    def test_completion_percentage(self):
        """Test completion percentage calculation"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        # Initially 0%
        self.assertEqual(submission.completion_percentage, 0)
        
        # Complete profile section
        submission.profile_section_complete = True
        submission.save()
        self.assertAlmostEqual(submission.completion_percentage, 33.33, places=1)
        
        # Complete recruitment section
        submission.recruitment_section_complete = True
        submission.save()
        self.assertAlmostEqual(submission.completion_percentage, 66.67, places=1)
        
        # Complete games section
        submission.games_section_complete = True
        submission.save()
        self.assertEqual(submission.completion_percentage, 100)
    
    def test_is_complete_method(self):
        """Test is_complete method"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        self.assertFalse(submission.is_complete())
        
        # Complete all sections
        submission.profile_section_complete = True
        submission.recruitment_section_complete = True
        submission.games_section_complete = True
        submission.save()
        
        self.assertTrue(submission.is_complete())
    
    def test_get_next_section_method(self):
        """Test get_next_section method"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        # Initially should return profile
        self.assertEqual(submission.get_next_section(), 'profile')
        
        # Complete profile
        submission.profile_section_complete = True
        submission.save()
        self.assertEqual(submission.get_next_section(), 'recruitment')
        
        # Complete recruitment
        submission.recruitment_section_complete = True
        submission.save()
        self.assertEqual(submission.get_next_section(), 'games')
        
        # Complete games
        submission.games_section_complete = True
        submission.save()
        self.assertIsNone(submission.get_next_section())
    
    def test_submit_method(self):
        """Test submit method"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user,
            profile_section_complete=True,
            recruitment_section_complete=True,
            games_section_complete=True
        )
        
        # Should be able to submit when complete
        submission.submit()
        
        self.assertEqual(submission.status, EOISubmission.SubmissionStatus.SUBMITTED)
        self.assertIsNotNone(submission.submitted_at)
    
    def test_submit_method_incomplete(self):
        """Test submit method with incomplete submission"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        # Should raise ValidationError when incomplete
        with self.assertRaises(ValidationError):
            submission.submit()
    
    def test_str_method(self):
        """Test string representation"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
        
        expected = f"EOI Submission - {self.user.get_full_name()} (NEW_VOLUNTEER)"
        self.assertEqual(str(submission), expected)
    
    def test_str_method_anonymous(self):
        """Test string representation for anonymous users"""
        submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            session_key='test_session'
        )
        
        expected = f"EOI Submission - Anonymous (NEW_VOLUNTEER)"
        self.assertEqual(str(submission), expected)


class EOIProfileInformationModelTest(TestCase):
    """Test cases for EOIProfileInformation model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser2',
            email='test@example.com',
            password='testpass123'
        )
        self.eoi_submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
    
    def test_profile_creation(self):
        """Test basic profile information creation"""
        profile = EOIProfileInformation.objects.create(
            eoi_submission=self.eoi_submission,
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            date_of_birth=date(1990, 1, 1),
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Spouse'
        )
        
        self.assertEqual(profile.first_name, 'John')
        self.assertEqual(profile.last_name, 'Doe')
        self.assertEqual(profile.email, 'john.doe@example.com')
        self.assertEqual(profile.eoi_submission, self.eoi_submission)
    
    def test_age_calculation(self):
        """Test age calculation property"""
        # Test with known date
        birth_date = date(1990, 6, 15)
        profile = EOIProfileInformation.objects.create(
            eoi_submission=self.eoi_submission,
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            date_of_birth=birth_date,
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Spouse'
        )
        
        # Calculate expected age
        today = date.today()
        expected_age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            expected_age -= 1
        
        self.assertEqual(profile.age, expected_age)
    
    def test_minimum_age_validation(self):
        """Test minimum age validation (15 years)"""
        # Create profile with age under 15
        too_young_date = date.today() - timedelta(days=14*365)  # 14 years old
        
        profile = EOIProfileInformation(
            eoi_submission=self.eoi_submission,
            first_name='Young',
            last_name='Person',
            email='young@example.com',
            date_of_birth=too_young_date,
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Parent',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Parent'
        )
        
        with self.assertRaises(ValidationError):
            profile.full_clean()
    
    def test_valid_age_validation(self):
        """Test valid age validation (15+ years)"""
        # Create profile with valid age
        valid_date = date.today() - timedelta(days=16*365)  # 16 years old
        
        profile = EOIProfileInformation(
            eoi_submission=self.eoi_submission,
            first_name='Valid',
            last_name='Person',
            email='valid@example.com',
            date_of_birth=valid_date,
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Parent',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Parent'
        )
        
        # Should not raise ValidationError
        profile.full_clean()
        profile.save()
        self.assertIsNotNone(profile.id)
    
    def test_email_validation(self):
        """Test email format validation"""
        profile = EOIProfileInformation(
            eoi_submission=self.eoi_submission,
            first_name='John',
            last_name='Doe',
            email='invalid-email',  # Invalid email format
            date_of_birth=date(1990, 1, 1),
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Spouse'
        )
        
        with self.assertRaises(ValidationError):
            profile.full_clean()
    
    def test_languages_spoken_field(self):
        """Test languages_spoken JSON field"""
        profile = EOIProfileInformation.objects.create(
            eoi_submission=self.eoi_submission,
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            date_of_birth=date(1990, 1, 1),
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Spouse',
            languages_spoken=['English', 'Irish', 'Spanish']
        )
        
        self.assertEqual(profile.languages_spoken, ['English', 'Irish', 'Spanish'])
        self.assertIsInstance(profile.languages_spoken, list)
    
    def test_str_method(self):
        """Test string representation"""
        profile = EOIProfileInformation.objects.create(
            eoi_submission=self.eoi_submission,
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            date_of_birth=date(1990, 1, 1),
            phone_number='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+353 1 234 5679',
            emergency_contact_relationship='Spouse'
        )
        
        expected = "John Doe - john.doe@example.com"
        self.assertEqual(str(profile), expected)


class EOIRecruitmentPreferencesModelTest(TestCase):
    """Test cases for EOIRecruitmentPreferences model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser3',
            email='test@example.com',
            password='testpass123'
        )
        self.eoi_submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
    
    def test_recruitment_preferences_creation(self):
        """Test basic recruitment preferences creation"""
        preferences = EOIRecruitmentPreferences.objects.create(
            eoi_submission=self.eoi_submission,
            volunteer_experience_level='BEGINNER',
            motivation='I want to help make the games successful and contribute to the community',
            preferred_sports=['football', 'basketball'],
            preferred_venues=['main_stadium', 'aquatic_center'],
            preferred_roles=['spectator_services', 'athlete_services'],
            availability_level='FULL_TIME',
            max_hours_per_day=8,
            can_lift_heavy_items=True,
            can_stand_long_periods=True,
            can_work_outdoors=True,
            can_work_with_crowds=True,
            has_own_transport=True,
            transport_method='car'
        )
        
        self.assertEqual(preferences.volunteer_experience_level, 'BEGINNER')
        self.assertEqual(preferences.motivation, 'I want to help make the games successful and contribute to the community')
        self.assertEqual(preferences.preferred_sports, ['football', 'basketball'])
        self.assertEqual(preferences.max_hours_per_day, 8)
        self.assertTrue(preferences.can_lift_heavy_items)
    
    def test_motivation_length_validation(self):
        """Test motivation minimum length validation"""
        # Test with short motivation (less than 50 characters)
        preferences = EOIRecruitmentPreferences(
            eoi_submission=self.eoi_submission,
            volunteer_experience_level='BEGINNER',
            motivation='Short',  # Too short
            availability_level='FULL_TIME'
        )
        
        with self.assertRaises(ValidationError):
            preferences.full_clean()
    
    def test_motivation_valid_length(self):
        """Test motivation with valid length"""
        # Test with valid motivation (50+ characters)
        long_motivation = 'I am very excited to volunteer for the ISG 2026 games because I believe in the power of sport to bring people together.'
        
        preferences = EOIRecruitmentPreferences(
            eoi_submission=self.eoi_submission,
            volunteer_experience_level='BEGINNER',
            motivation=long_motivation,
            availability_level='FULL_TIME'
        )
        
        # Should not raise ValidationError
        preferences.full_clean()
        preferences.save()
        self.assertIsNotNone(preferences.id)
    
    def test_max_hours_validation(self):
        """Test max hours per day validation"""
        # Test with invalid hours (negative)
        preferences = EOIRecruitmentPreferences(
            eoi_submission=self.eoi_submission,
            volunteer_experience_level='BEGINNER',
            motivation='I want to help make the games successful and contribute to the community',
            availability_level='FULL_TIME',
            max_hours_per_day=-1  # Invalid
        )
        
        with self.assertRaises(ValidationError):
            preferences.full_clean()
        
        # Test with invalid hours (too high)
        preferences.max_hours_per_day = 25  # Invalid
        with self.assertRaises(ValidationError):
            preferences.full_clean()
    
    def test_json_fields(self):
        """Test JSON fields for preferences"""
        preferences = EOIRecruitmentPreferences.objects.create(
            eoi_submission=self.eoi_submission,
            volunteer_experience_level='INTERMEDIATE',
            motivation='I want to help make the games successful and contribute to the community',
            preferred_sports=['football', 'basketball', 'swimming'],
            preferred_venues=['main_stadium', 'aquatic_center', 'training_ground'],
            preferred_roles=['spectator_services', 'athlete_services', 'media_operations'],
            special_skills=['first_aid', 'languages', 'photography'],
            training_interests=['leadership', 'technical_skills', 'customer_service'],
            availability_level='PART_TIME'
        )
        
        self.assertIsInstance(preferences.preferred_sports, list)
        self.assertIsInstance(preferences.preferred_venues, list)
        self.assertIsInstance(preferences.preferred_roles, list)
        self.assertIsInstance(preferences.special_skills, list)
        self.assertIsInstance(preferences.training_interests, list)
        
        self.assertEqual(len(preferences.preferred_sports), 3)
        self.assertIn('football', preferences.preferred_sports)
    
    def test_str_method(self):
        """Test string representation"""
        preferences = EOIRecruitmentPreferences.objects.create(
            eoi_submission=self.eoi_submission,
            volunteer_experience_level='BEGINNER',
            motivation='I want to help make the games successful and contribute to the community',
            availability_level='FULL_TIME'
        )
        
        expected = f"Recruitment Preferences - {self.eoi_submission}"
        self.assertEqual(str(preferences), expected)


class EOIGamesInformationModelTest(TestCase):
    """Test cases for EOIGamesInformation model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser4',
            email='test@example.com',
            password='testpass123'
        )
        self.eoi_submission = EOISubmission.objects.create(
            volunteer_type='NEW_VOLUNTEER',
            user=self.user
        )
    
    def test_games_information_creation(self):
        """Test basic games information creation"""
        games_info = EOIGamesInformation.objects.create(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            dietary_requirements='Vegetarian',
            has_food_allergies=True,
            food_allergy_details='Nuts, shellfish',
            requires_accommodation=False,
            preferred_shifts=['morning', 'afternoon'],
            photo_consent=True,
            social_media_consent=True,
            testimonial_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True,
            how_did_you_hear='Social media'
        )
        
        self.assertEqual(games_info.t_shirt_size, 'LARGE')
        self.assertEqual(games_info.dietary_requirements, 'Vegetarian')
        self.assertTrue(games_info.has_food_allergies)
        self.assertEqual(games_info.food_allergy_details, 'Nuts, shellfish')
        self.assertEqual(games_info.preferred_shifts, ['morning', 'afternoon'])
    
    def test_required_consents_validation(self):
        """Test required consent validations"""
        # Test without required consents
        games_info = EOIGamesInformation(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            photo_consent=False,  # Required
            terms_accepted=False,  # Required
            privacy_policy_accepted=False,  # Required
            code_of_conduct_accepted=False  # Required
        )
        
        with self.assertRaises(ValidationError):
            games_info.full_clean()
    
    def test_valid_consents(self):
        """Test with all required consents"""
        games_info = EOIGamesInformation(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        # Should not raise ValidationError
        games_info.full_clean()
        games_info.save()
        self.assertIsNotNone(games_info.id)
    
    def test_food_allergy_validation(self):
        """Test food allergy details validation"""
        # Test with food allergies but no details
        games_info = EOIGamesInformation(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            has_food_allergies=True,
            food_allergy_details='',  # Should be required when has_food_allergies=True
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        with self.assertRaises(ValidationError):
            games_info.full_clean()
    
    def test_accommodation_validation(self):
        """Test accommodation preferences validation"""
        # Test with accommodation required but no preferences
        games_info = EOIGamesInformation(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            requires_accommodation=True,
            accommodation_preferences='',  # Should be required when requires_accommodation=True
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        with self.assertRaises(ValidationError):
            games_info.full_clean()
    
    def test_group_information_validation(self):
        """Test group information validation"""
        # Test with group membership but no group name
        games_info = EOIGamesInformation(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            is_part_of_group=True,
            group_name='',  # Should be required when is_part_of_group=True
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        with self.assertRaises(ValidationError):
            games_info.full_clean()
    
    def test_photo_url_property(self):
        """Test photo_url property"""
        games_info = EOIGamesInformation.objects.create(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            volunteer_photo='volunteers/photos/test_photo.jpg',
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        expected_url = '/media/volunteers/photos/test_photo.jpg'
        self.assertEqual(games_info.photo_url, expected_url)
    
    def test_photo_url_property_no_photo(self):
        """Test photo_url property when no photo"""
        games_info = EOIGamesInformation.objects.create(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        self.assertIsNone(games_info.photo_url)
    
    def test_json_fields(self):
        """Test JSON fields"""
        games_info = EOIGamesInformation.objects.create(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            preferred_shifts=['morning', 'evening'],
            available_dates=['2026-06-15', '2026-06-16', '2026-06-17'],
            unavailable_dates=['2026-06-20'],
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        self.assertIsInstance(games_info.preferred_shifts, list)
        self.assertIsInstance(games_info.available_dates, list)
        self.assertIsInstance(games_info.unavailable_dates, list)
        
        self.assertEqual(len(games_info.preferred_shifts), 2)
        self.assertIn('morning', games_info.preferred_shifts)
    
    def test_str_method(self):
        """Test string representation"""
        games_info = EOIGamesInformation.objects.create(
            eoi_submission=self.eoi_submission,
            t_shirt_size='LARGE',
            photo_consent=True,
            terms_accepted=True,
            privacy_policy_accepted=True,
            code_of_conduct_accepted=True
        )
        
        expected = f"Games Information - {self.eoi_submission}"
        self.assertEqual(str(games_info), expected)


class CorporateVolunteerGroupModelTest(TestCase):
    """Test cases for CorporateVolunteerGroup model"""
    
    def test_corporate_group_creation(self):
        """Test basic corporate group creation"""
        group = CorporateVolunteerGroup.objects.create(
            name='Tech Corp Volunteers',
            description='Technology company volunteer group',
            primary_contact_name='John Manager',
            primary_contact_email='john.manager@techcorp.com',
            primary_contact_phone='+353 1 234 5678',
            address_line_1='123 Business Park',
            city='Dublin',
            state_province='Dublin',
            postal_code='D02 XY12',
            country='Ireland',
            expected_volunteer_count=25,
            industry_sector='Technology'
        )
        
        self.assertEqual(group.name, 'Tech Corp Volunteers')
        self.assertEqual(group.primary_contact_name, 'John Manager')
        self.assertEqual(group.expected_volunteer_count, 25)
        self.assertEqual(group.status, CorporateVolunteerGroup.GroupStatus.PENDING)
        self.assertIsInstance(group.id, uuid.UUID)
    
    def test_email_validation(self):
        """Test email format validation"""
        group = CorporateVolunteerGroup(
            name='Test Corp',
            primary_contact_name='Test Contact',
            primary_contact_email='invalid-email',  # Invalid format
            primary_contact_phone='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            expected_volunteer_count=10
        )
        
        with self.assertRaises(ValidationError):
            group.full_clean()
    
    def test_volunteer_count_validation(self):
        """Test volunteer count validation"""
        # Test with negative count
        group = CorporateVolunteerGroup(
            name='Test Corp',
            primary_contact_name='Test Contact',
            primary_contact_email='test@example.com',
            primary_contact_phone='+353 1 234 5678',
            address_line_1='123 Test Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            expected_volunteer_count=-5  # Invalid
        )
        
        with self.assertRaises(ValidationError):
            group.full_clean()
        
        # Test with zero count
        group.expected_volunteer_count = 0  # Invalid
        with self.assertRaises(ValidationError):
            group.full_clean()
    
    def test_json_fields(self):
        """Test JSON fields for preferences"""
        group = CorporateVolunteerGroup.objects.create(
            name='Multi Corp',
            primary_contact_name='Contact Person',
            primary_contact_email='contact@multicorp.com',
            primary_contact_phone='+353 1 234 5678',
            address_line_1='456 Corporate Ave',
            city='Cork',
            state_province='Cork',
            postal_code='T12 ABC3',
            country='Ireland',
            expected_volunteer_count=50,
            preferred_volunteer_roles=['spectator_services', 'hospitality', 'logistics'],
            preferred_venues=['main_stadium', 'convention_center']
        )
        
        self.assertIsInstance(group.preferred_volunteer_roles, list)
        self.assertIsInstance(group.preferred_venues, list)
        self.assertEqual(len(group.preferred_volunteer_roles), 3)
        self.assertIn('spectator_services', group.preferred_volunteer_roles)
    
    def test_status_choices(self):
        """Test all status choices are valid"""
        valid_statuses = [choice[0] for choice in CorporateVolunteerGroup.GroupStatus.choices]
        
        for status in valid_statuses:
            group = CorporateVolunteerGroup.objects.create(
                name=f'Test Corp {status}',
                primary_contact_name='Test Contact',
                primary_contact_email=f'test{status}@example.com',
                primary_contact_phone='+353 1 234 5678',
                address_line_1='123 Test Street',
                city='Dublin',
                state_province='Dublin',
                postal_code='D01 ABC1',
                country='Ireland',
                expected_volunteer_count=10,
                status=status
            )
            self.assertEqual(group.status, status)
    
    def test_str_method(self):
        """Test string representation"""
        group = CorporateVolunteerGroup.objects.create(
            name='Example Corp Volunteers',
            primary_contact_name='Contact Person',
            primary_contact_email='contact@example.com',
            primary_contact_phone='+353 1 234 5678',
            address_line_1='789 Example Street',
            city='Galway',
            state_province='Galway',
            postal_code='H91 ABC4',
            country='Ireland',
            expected_volunteer_count=15
        )
        
        expected = "Example Corp Volunteers (15 volunteers)"
        self.assertEqual(str(group), expected)
    
    def test_unique_name_constraint(self):
        """Test unique name constraint"""
        # Create first group
        CorporateVolunteerGroup.objects.create(
            name='Unique Corp',
            primary_contact_name='Contact 1',
            primary_contact_email='contact1@unique.com',
            primary_contact_phone='+353 1 234 5678',
            address_line_1='123 Unique Street',
            city='Dublin',
            state_province='Dublin',
            postal_code='D01 ABC1',
            country='Ireland',
            expected_volunteer_count=10
        )
        
        # Try to create second group with same name
        with self.assertRaises(IntegrityError):
            CorporateVolunteerGroup.objects.create(
                name='Unique Corp',  # Duplicate name
                primary_contact_name='Contact 2',
                primary_contact_email='contact2@unique.com',
                primary_contact_phone='+353 1 234 5679',
                address_line_1='456 Different Street',
                city='Cork',
                state_province='Cork',
                postal_code='T12 XYZ2',
                country='Ireland',
                expected_volunteer_count=20
            ) 