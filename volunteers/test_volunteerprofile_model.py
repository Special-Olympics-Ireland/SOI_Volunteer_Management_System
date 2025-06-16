from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from accounts.models import User
from volunteers.models import VolunteerProfile


class VolunteerProfileModelTest(TestCase):
    """Test cases for VolunteerProfile model"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.volunteer_user = User.objects.create_user(
            username='volunteer_user',
            email='volunteer@test.com',
            password='testpass123',
            first_name='John',
            last_name='Volunteer',
            user_type=User.UserType.VOLUNTEER,
            date_of_birth=date(1990, 5, 15)
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            first_name='Staff',
            last_name='Member',
            user_type=User.UserType.STAFF
        )
        
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type=User.UserType.ADMIN
        )
    
    def test_volunteerprofile_creation_basic(self):
        """Test basic volunteer profile creation"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse'
        )
        
        self.assertEqual(profile.user, self.volunteer_user)
        self.assertEqual(profile.status, VolunteerProfile.VolunteerStatus.PENDING)
        self.assertEqual(profile.emergency_contact_name, 'Jane Doe')
        self.assertEqual(profile.emergency_contact_phone, '+1234567890')
        self.assertEqual(profile.emergency_contact_relationship, 'Spouse')
        self.assertEqual(profile.experience_level, VolunteerProfile.ExperienceLevel.NONE)
        self.assertEqual(profile.availability_level, VolunteerProfile.AvailabilityLevel.FLEXIBLE)
        self.assertEqual(profile.t_shirt_size, VolunteerProfile.TShirtSize.M)
        self.assertEqual(profile.transport_method, VolunteerProfile.TransportMethod.PUBLIC_TRANSPORT)
        self.assertEqual(profile.max_hours_per_day, 8)
        self.assertFalse(profile.has_own_transport)
        self.assertTrue(profile.can_lift_heavy_items)
        self.assertTrue(profile.can_stand_long_periods)
        self.assertTrue(profile.can_work_outdoors)
        self.assertTrue(profile.can_work_with_crowds)
        self.assertIsNotNone(profile.application_date)
    
    def test_volunteerprofile_status_workflow(self):
        """Test volunteer profile status workflow"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse'
        )
        
        # Test initial status
        self.assertTrue(profile.is_pending())
        self.assertFalse(profile.is_approved())
        self.assertFalse(profile.is_active())
        self.assertFalse(profile.is_available_for_assignment())
        
        # Test approval
        profile.approve(self.staff_user, 'Approved after review')
        self.assertTrue(profile.is_approved())
        self.assertFalse(profile.is_pending())
        self.assertTrue(profile.is_available_for_assignment())
        self.assertEqual(profile.reviewed_by, self.staff_user)
        self.assertEqual(profile.status_change_reason, 'Approved after review')
        self.assertIsNotNone(profile.approval_date)
        self.assertIsNotNone(profile.review_date)
        
        # Test activation
        profile.activate(self.staff_user)
        self.assertTrue(profile.is_active())
        self.assertTrue(profile.is_available_for_assignment())
        
        # Test suspension
        profile.suspend(self.admin_user, 'Suspended for investigation')
        self.assertEqual(profile.status, VolunteerProfile.VolunteerStatus.SUSPENDED)
        self.assertEqual(profile.status_change_reason, 'Suspended for investigation')
        self.assertFalse(profile.is_available_for_assignment())
    
    def test_volunteerprofile_rejection_workflow(self):
        """Test volunteer profile rejection workflow"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse'
        )
        
        # Test rejection
        profile.reject(self.staff_user, 'Does not meet minimum requirements')
        self.assertEqual(profile.status, VolunteerProfile.VolunteerStatus.REJECTED)
        self.assertEqual(profile.reviewed_by, self.staff_user)
        self.assertEqual(profile.status_change_reason, 'Does not meet minimum requirements')
        self.assertIsNotNone(profile.review_date)
        self.assertFalse(profile.is_available_for_assignment())
    
    def test_volunteerprofile_validation(self):
        """Test volunteer profile validation"""
        # Test missing emergency contact name
        profile = VolunteerProfile(
            user=self.volunteer_user,
            emergency_contact_name='',  # Empty name
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse'
        )
        
        with self.assertRaises(ValidationError):
            profile.clean()
        
        # Test corporate volunteer without group name
        profile = VolunteerProfile(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse',
            is_corporate_volunteer=True,
            corporate_group_name=''  # Empty group name
        )
        
        with self.assertRaises(ValidationError):
            profile.clean()
    
    def test_volunteerprofile_age_calculation(self):
        """Test age calculation"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse'
        )
        
        age = profile.get_age()
        expected_age = timezone.now().year - 1990
        # Account for birthday not yet passed this year
        if timezone.now().date() < date(timezone.now().year, 5, 15):
            expected_age -= 1
        
        self.assertEqual(age, expected_age)
    
    def test_volunteerprofile_background_check_methods(self):
        """Test background check related methods"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse',
            background_check_status='REQUIRED'
        )
        
        # Test requires background check
        self.assertTrue(profile.requires_background_check())
        self.assertFalse(profile.has_valid_background_check())
        
        # Test approved background check
        profile.background_check_status = 'APPROVED'
        profile.background_check_date = date.today()
        profile.background_check_expiry = date.today() + timedelta(days=365)
        profile.save()
        
        self.assertTrue(profile.has_valid_background_check())
    
    def test_volunteerprofile_training_management(self):
        """Test training completion management"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse'
        )
        
        # Test adding training completion
        profile.add_training_completion('First Aid Training')
        
        self.assertEqual(len(profile.training_completed), 1)
        self.assertEqual(profile.training_completed[0]['module'], 'First Aid Training')
        self.assertEqual(profile.training_completed[0]['status'], 'completed')
    
    def test_volunteerprofile_to_dict(self):
        """Test volunteer profile dictionary conversion"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse',
            status=VolunteerProfile.VolunteerStatus.APPROVED,
            experience_level=VolunteerProfile.ExperienceLevel.INTERMEDIATE,
            availability_level=VolunteerProfile.AvailabilityLevel.PART_TIME,
            preferred_roles=['Event Support'],
            preferred_venues=['Main Stadium'],
            is_corporate_volunteer=True,
            corporate_group_name='Tech Corp',
            has_own_transport=True,
            transport_method=VolunteerProfile.TransportMethod.OWN_CAR,
            background_check_status='APPROVED',
            reference_check_status='COMPLETED',
            performance_rating=Decimal('4.3')
        )
        
        profile_dict = profile.to_dict()
        
        self.assertEqual(profile_dict['id'], str(profile.id))
        self.assertEqual(profile_dict['user_id'], str(self.volunteer_user.id))
        self.assertEqual(profile_dict['user_name'], 'John Volunteer')
        self.assertEqual(profile_dict['user_email'], 'volunteer@test.com')
        self.assertEqual(profile_dict['status'], VolunteerProfile.VolunteerStatus.APPROVED)
        self.assertEqual(profile_dict['status_display'], 'Approved')
        self.assertEqual(profile_dict['experience_level'], VolunteerProfile.ExperienceLevel.INTERMEDIATE)
        self.assertEqual(profile_dict['experience_level_display'], 'Intermediate (3-5 events)')
        self.assertEqual(profile_dict['availability_level'], VolunteerProfile.AvailabilityLevel.PART_TIME)
        self.assertEqual(profile_dict['availability_level_display'], 'Part Time (Some Days)')
        self.assertEqual(profile_dict['preferred_roles'], ['Event Support'])
        self.assertEqual(profile_dict['preferred_venues'], ['Main Stadium'])
        self.assertTrue(profile_dict['is_corporate_volunteer'])
        self.assertEqual(profile_dict['corporate_group_name'], 'Tech Corp')
        self.assertTrue(profile_dict['has_own_transport'])
        self.assertEqual(profile_dict['transport_method'], 'Own Car')
        self.assertEqual(profile_dict['background_check_status'], 'APPROVED')
        self.assertEqual(profile_dict['reference_check_status'], 'COMPLETED')
        self.assertEqual(profile_dict['performance_rating'], 4.3)
        self.assertTrue(profile_dict['is_available_for_assignment'])
        self.assertTrue(profile_dict['has_valid_background_check'])
        self.assertIsNotNone(profile_dict['age'])
    
    def test_volunteerprofile_string_representation(self):
        """Test string representation of volunteer profile"""
        profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='+1234567890',
            emergency_contact_relationship='Spouse',
            status=VolunteerProfile.VolunteerStatus.APPROVED
        )
        
        expected_str = "John Volunteer - Approved"
        self.assertEqual(str(profile), expected_str)
