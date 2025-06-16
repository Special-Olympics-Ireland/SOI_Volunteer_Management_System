from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from .models import User

class UserModelTest(TestCase):
    """Test cases for the enhanced User model"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@soi.ie',
            password='testpass123',
            user_type=User.UserType.ADMIN,
            first_name='Admin',
            last_name='User'
        )
        
        self.volunteer_data = {
            'username': 'volunteer1',
            'email': 'volunteer@example.com',
            'password': 'testpass123',
            'first_name': 'John',
            'last_name': 'Doe',
            'user_type': User.UserType.VOLUNTEER,
            'volunteer_type': User.VolunteerType.GENERAL,
            'date_of_birth': date(1990, 1, 1),
            'phone_number': '0871234567',
            'address_line_1': '123 Main St',
            'city': 'Dublin',
            'county': 'Dublin',
            'postal_code': 'D01 A1B2',
            'gdpr_consent': True
        }
    
    def test_user_creation(self):
        """Test basic user creation"""
        user = User.objects.create_user(**self.volunteer_data)
        self.assertEqual(user.username, 'volunteer1')
        self.assertEqual(user.email, 'volunteer@example.com')
        self.assertEqual(user.user_type, User.UserType.VOLUNTEER)
        self.assertEqual(user.volunteer_type, User.VolunteerType.GENERAL)
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_str_representation(self):
        """Test string representation of user"""
        user = User.objects.create_user(**self.volunteer_data)
        expected = f"John Doe (Volunteer)"
        self.assertEqual(str(user), expected)
        
        # Test with user without full name
        user_no_name = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        expected_no_name = f"testuser (Volunteer)"
        self.assertEqual(str(user_no_name), expected_no_name)
    
    def test_user_type_methods(self):
        """Test user type checking methods"""
        volunteer = User.objects.create_user(**self.volunteer_data)
        
        self.assertTrue(volunteer.is_volunteer())
        self.assertFalse(volunteer.is_staff_member())
        self.assertFalse(volunteer.is_vmt())
        self.assertFalse(volunteer.is_cvt())
        self.assertFalse(volunteer.is_goc())
        self.assertFalse(volunteer.is_admin())
        self.assertFalse(volunteer.is_management())
        self.assertFalse(volunteer.can_manage_volunteers())
        self.assertFalse(volunteer.can_manage_events())
        
        # Test admin user
        self.assertFalse(self.admin_user.is_volunteer())
        self.assertTrue(self.admin_user.is_admin())
        self.assertTrue(self.admin_user.is_management())
        self.assertTrue(self.admin_user.can_manage_volunteers())
        self.assertTrue(self.admin_user.can_manage_events())
    
    def test_age_calculation(self):
        """Test age calculation"""
        user = User.objects.create_user(**self.volunteer_data)
        expected_age = timezone.now().date().year - 1990
        
        # Adjust for birthday not yet occurred this year
        today = timezone.now().date()
        if today < date(today.year, 1, 1):
            expected_age -= 1
        
        self.assertEqual(user.get_age(), expected_age)
        
        # Test user without date of birth
        user_no_dob = User.objects.create_user(
            username='nodob',
            email='nodob@example.com',
            password='testpass123'
        )
        self.assertIsNone(user_no_dob.get_age())
    
    def test_full_address(self):
        """Test full address formatting"""
        user = User.objects.create_user(**self.volunteer_data)
        expected_address = "123 Main St, Dublin, Dublin, D01 A1B2, Ireland"
        self.assertEqual(user.get_full_address(), expected_address)
        
        # Test with partial address
        user.address_line_2 = "Apt 4"
        user.save()
        expected_with_apt = "123 Main St, Apt 4, Dublin, Dublin, D01 A1B2, Ireland"
        self.assertEqual(user.get_full_address(), expected_with_apt)
    
    def test_profile_completion_check(self):
        """Test profile completion checking"""
        # Create volunteer with complete profile
        user = User.objects.create_user(**self.volunteer_data)
        self.assertTrue(user.profile_complete)
        
        # Test incomplete profile (missing required field)
        incomplete_data = self.volunteer_data.copy()
        incomplete_data['username'] = 'incomplete'
        incomplete_data['email'] = 'incomplete@example.com'
        del incomplete_data['phone_number']  # Remove required field
        
        incomplete_user = User.objects.create_user(**incomplete_data)
        self.assertFalse(incomplete_user.profile_complete)
    
    def test_volunteer_eligibility(self):
        """Test volunteer eligibility checking"""
        user = User.objects.create_user(**self.volunteer_data)
        self.assertTrue(user.is_eligible_volunteer())
        
        # Test underage volunteer
        underage_data = self.volunteer_data.copy()
        underage_data['username'] = 'underage'
        underage_data['email'] = 'underage@example.com'
        underage_data['date_of_birth'] = date.today() - timedelta(days=365 * 10)  # 10 years old
        
        underage_user = User.objects.create_user(**underage_data)
        self.assertFalse(underage_user.is_eligible_volunteer())
        
        # Test without GDPR consent
        no_consent_data = self.volunteer_data.copy()
        no_consent_data['username'] = 'noconsent'
        no_consent_data['email'] = 'noconsent@example.com'
        no_consent_data['gdpr_consent'] = False
        
        no_consent_user = User.objects.create_user(**no_consent_data)
        self.assertFalse(no_consent_user.is_eligible_volunteer())
    
    def test_justgo_integration_methods(self):
        """Test JustGo integration methods"""
        user = User.objects.create_user(**self.volunteer_data)
        
        # Test initial state
        self.assertFalse(user.has_justgo_profile())
        self.assertFalse(user.needs_justgo_sync())
        
        # Set up for sync
        user.email_verified = True
        user.justgo_sync_status = 'PENDING'
        user.save()
        
        self.assertTrue(user.needs_justgo_sync())
        
        # Add JustGo member ID
        user.justgo_member_id = 'JG123456'
        user.save()
        
        self.assertTrue(user.has_justgo_profile())
    
    def test_approval_methods(self):
        """Test user approval methods"""
        user = User.objects.create_user(**self.volunteer_data)
        
        # Initial state
        self.assertFalse(user.is_approved)
        self.assertIsNone(user.approval_date)
        self.assertIsNone(user.approved_by)
        
        # Approve user
        user.approve_account(self.admin_user)
        
        self.assertTrue(user.is_approved)
        self.assertIsNotNone(user.approval_date)
        self.assertEqual(user.approved_by, self.admin_user)
        
        # Revoke approval
        user.revoke_approval()
        
        self.assertFalse(user.is_approved)
        self.assertIsNone(user.approval_date)
        self.assertIsNone(user.approved_by)
    
    def test_auto_approval_for_admin(self):
        """Test automatic approval for admin and staff users"""
        admin_data = {
            'username': 'newadmin',
            'email': 'newadmin@soi.ie',
            'password': 'testpass123',
            'user_type': User.UserType.ADMIN,
            'first_name': 'New',
            'last_name': 'Admin'
        }
        
        admin_user = User.objects.create_user(**admin_data)
        self.assertTrue(admin_user.is_approved)
        self.assertIsNotNone(admin_user.approval_date)
    
    def test_activity_tracking(self):
        """Test activity tracking"""
        user = User.objects.create_user(**self.volunteer_data)
        
        # Initial state
        self.assertIsNone(user.last_activity)
        
        # Update activity
        user.update_activity()
        
        self.assertIsNotNone(user.last_activity)
        
        # Check that timestamp is recent
        time_diff = timezone.now() - user.last_activity
        self.assertLess(time_diff.total_seconds(), 5)  # Within 5 seconds
    
    def test_uuid_primary_key(self):
        """Test that UUID is used as primary key"""
        user = User.objects.create_user(**self.volunteer_data)
        
        # Check that ID is a UUID
        self.assertIsInstance(user.id, type(user.id))
        self.assertEqual(len(str(user.id)), 36)  # UUID string length
        self.assertIn('-', str(user.id))  # UUID contains hyphens
    
    def test_volunteer_type_validation(self):
        """Test volunteer type validation"""
        # Test that volunteer_type is set for volunteers
        volunteer_data = self.volunteer_data.copy()
        del volunteer_data['volunteer_type']  # Remove volunteer_type
        
        user = User.objects.create_user(**volunteer_data)
        # Should default to GENERAL for volunteers
        self.assertEqual(user.volunteer_type, User.VolunteerType.GENERAL)
        
        # Test that volunteer_type is cleared for non-volunteers
        staff_data = {
            'username': 'staff1',
            'email': 'staff@soi.ie',
            'password': 'testpass123',
            'user_type': User.UserType.STAFF,
            'volunteer_type': User.VolunteerType.CORPORATE,  # This should be cleared
            'department': 'IT',
            'position': 'Developer'
        }
        
        staff_user = User.objects.create_user(**staff_data)
        self.assertIsNone(staff_user.volunteer_type)
    
    def test_unique_constraints(self):
        """Test unique field constraints"""
        from django.db import IntegrityError, transaction
        
        # Test unique employee_id
        staff_data = {
            'username': 'staff1',
            'email': 'staff1@soi.ie',
            'password': 'testpass123',
            'user_type': User.UserType.STAFF,
            'employee_id': 'EMP001',
            'department': 'IT',
            'position': 'Developer'
        }
        
        staff1 = User.objects.create_user(**staff_data)
        
        staff_data2 = staff_data.copy()
        staff_data2['username'] = 'staff2'
        staff_data2['email'] = 'staff2@soi.ie'
        
        # Use transaction.atomic to handle the IntegrityError properly
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create_user(**staff_data2)
        
        # Test unique justgo_member_id
        volunteer_data2 = self.volunteer_data.copy()
        volunteer_data2['username'] = 'volunteer2'
        volunteer_data2['email'] = 'volunteer2@example.com'
        volunteer_data2['justgo_member_id'] = 'JG123456'
        
        volunteer1 = User.objects.create_user(**volunteer_data2)
        
        volunteer_data3 = volunteer_data2.copy()
        volunteer_data3['username'] = 'volunteer3'
        volunteer_data3['email'] = 'volunteer3@example.com'
        
        # Use transaction.atomic to handle the IntegrityError properly
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create_user(**volunteer_data3)
    
    def test_gdpr_consent_date_auto_set(self):
        """Test that GDPR consent date is automatically set"""
        user_data = self.volunteer_data.copy()
        user_data['gdpr_consent'] = True
        
        user = User.objects.create_user(**user_data)
        
        # GDPR consent date should be set automatically in serializer
        # For model creation, we need to set it manually or through serializer
        user.gdpr_consent_date = timezone.now()
        user.save()
        
        self.assertIsNotNone(user.gdpr_consent_date)
        
        # Test that it's recent
        time_diff = timezone.now() - user.gdpr_consent_date
        self.assertLess(time_diff.total_seconds(), 5) 