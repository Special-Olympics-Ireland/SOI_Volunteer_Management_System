#!/usr/bin/env python3
"""
Comprehensive tests for the Role model
"""

import os
import sys
import django
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add the project directory to Python path
sys.path.append('/home/itsupport/projects/soi-hub')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.test_settings')
django.setup()

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from events.models import Event, Venue, Role

User = get_user_model()


class RoleModelTest(TestCase):
    """Test cases for the Role model"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            date_of_birth=date(1990, 1, 1)
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event 2026',
            slug='test-event-2026',
            short_name='TE26',
            event_type=Event.EventType.INTERNATIONAL_GAMES,
            start_date=date(2026, 6, 15),
            end_date=date(2026, 6, 25),
            host_city='Dublin',
            volunteer_target=1000,
            created_by=self.user
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            event=self.event,
            name='Test Stadium',
            slug='test-stadium',
            venue_type=Venue.VenueType.STADIUM,
            address_line_1='123 Test Street',
            city='Dublin',
            country='Ireland',
            total_capacity=50000,
            volunteer_capacity=200,
            created_by=self.user
        )
    
    def test_role_creation(self):
        """Test basic role creation"""
        role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Swimming Official',
            slug='swimming-official',
            role_type=Role.RoleType.SPORT_OFFICIAL,
            description='Official for swimming competitions',
            total_positions=5,
            minimum_volunteers=3,
            created_by=self.user
        )
        
        self.assertEqual(role.name, 'Swimming Official')
        self.assertEqual(role.event, self.event)
        self.assertEqual(role.venue, self.venue)
        self.assertEqual(role.role_type, Role.RoleType.SPORT_OFFICIAL)
        self.assertEqual(role.status, Role.RoleStatus.DRAFT)
        self.assertEqual(role.total_positions, 5)
        self.assertEqual(role.filled_positions, 0)
        self.assertEqual(role.minimum_volunteers, 3)
        self.assertTrue(role.id)  # UUID should be generated
    
    def test_role_str_representation(self):
        """Test string representation of role"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            created_by=self.user
        )
        
        expected = f"Test Role ({self.event.short_name})"
        self.assertEqual(str(role), expected)
    
    def test_role_default_values(self):
        """Test default values are set correctly"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            created_by=self.user
        )
        
        # Test default values
        self.assertEqual(role.role_type, Role.RoleType.GENERAL_VOLUNTEER)
        self.assertEqual(role.status, Role.RoleStatus.DRAFT)
        self.assertEqual(role.skill_level_required, Role.SkillLevel.ANY)
        self.assertEqual(role.commitment_level, Role.CommitmentLevel.FLEXIBLE)
        self.assertEqual(role.minimum_age, 15)
        self.assertEqual(role.total_positions, 1)
        self.assertEqual(role.filled_positions, 0)
        self.assertEqual(role.minimum_volunteers, 1)
        self.assertEqual(role.priority_level, 5)
        self.assertFalse(role.training_required)
        self.assertFalse(role.uniform_required)
        self.assertFalse(role.requires_garda_vetting)
        self.assertFalse(role.requires_child_protection)
        self.assertFalse(role.requires_security_clearance)
        self.assertTrue(role.is_public)
        self.assertFalse(role.is_featured)
        self.assertFalse(role.is_urgent)
    
    def test_role_configuration_defaults(self):
        """Test that default configurations are set"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            created_by=self.user
        )
        
        # Check default role configuration
        expected_config = {
            'auto_assign': False,
            'requires_approval': True,
            'allow_waitlist': True,
            'send_notifications': True,
            'track_attendance': True,
            'allow_substitutions': True,
            'require_confirmation': True,
        }
        self.assertEqual(role.role_configuration, expected_config)
        
        # Check default physical requirements
        self.assertEqual(role.physical_requirements, ['basic_mobility'])
        
        # Check default schedule requirements
        expected_schedule = {
            'flexible_hours': True,
            'weekend_availability': False,
            'early_morning': False,
            'late_evening': False,
            'split_shifts': False,
            'consecutive_days': False,
        }
        self.assertEqual(role.schedule_requirements, expected_schedule)
    
    def test_role_type_specific_physical_requirements(self):
        """Test that physical requirements are set based on role type"""
        # Test sport official
        role = Role.objects.create(
            event=self.event,
            name='Swimming Official',
            slug='swimming-official',
            role_type=Role.RoleType.SPORT_OFFICIAL,
            description='Test description',
            created_by=self.user
        )
        self.assertEqual(role.physical_requirements, ['standing', 'walking', 'good_vision'])
        
        # Test setup crew
        role2 = Role.objects.create(
            event=self.event,
            name='Setup Crew',
            slug='setup-crew',
            role_type=Role.RoleType.SETUP_CREW,
            description='Test description',
            created_by=self.user
        )
        self.assertEqual(role2.physical_requirements, ['lifting', 'carrying', 'physical_stamina'])
    
    def test_uniform_details_default(self):
        """Test that uniform details are set when uniform is required"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            uniform_required=True,
            created_by=self.user
        )
        
        expected_uniform = {
            'items': ['polo_shirt', 'id_badge'],
            'colors': ['green', 'white'],
            'sizes_available': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
            'provided_by': 'event_organizer',
            'return_required': True,
        }
        self.assertEqual(role.uniform_details, expected_uniform)
    
    def test_summary_auto_generation(self):
        """Test that summary is auto-generated from description"""
        long_description = "This is a very long description that should be truncated when used as a summary. " * 10
        
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description=long_description,
            created_by=self.user
        )
        
        # Summary should be truncated to 500 chars with "..."
        self.assertTrue(role.summary.endswith('...'))
        self.assertEqual(len(role.summary), 500)
        
        # Test short description
        short_description = "Short description"
        role2 = Role.objects.create(
            event=self.event,
            name='Test Role 2',
            slug='test-role-2',
            description=short_description,
            created_by=self.user
        )
        self.assertEqual(role2.summary, short_description)
    
    def test_capacity_methods(self):
        """Test capacity-related methods"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            status=Role.RoleStatus.ACTIVE,
            total_positions=10,
            filled_positions=3,
            minimum_volunteers=5,
            created_by=self.user
        )
        
        # Test capacity methods
        self.assertEqual(role.get_available_positions(), 7)
        self.assertEqual(role.get_capacity_percentage(), 30.0)
        self.assertFalse(role.is_full())
        self.assertTrue(role.is_understaffed())
        self.assertTrue(role.can_accept_volunteers(5))
        self.assertFalse(role.can_accept_volunteers(8))
        
        # Test when full
        role.filled_positions = 10
        role.save()
        self.assertEqual(role.get_available_positions(), 0)
        self.assertEqual(role.get_capacity_percentage(), 100.0)
        self.assertTrue(role.is_full())
        self.assertFalse(role.can_accept_volunteers(1))
    
    def test_age_requirement_checking(self):
        """Test age requirement validation"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            minimum_age=18,
            maximum_age=65,
            created_by=self.user
        )
        
        # Test age checking
        self.assertFalse(role.check_age_requirement(17))  # Too young
        self.assertTrue(role.check_age_requirement(18))   # Minimum age
        self.assertTrue(role.check_age_requirement(30))   # Within range
        self.assertTrue(role.check_age_requirement(65))   # Maximum age
        self.assertFalse(role.check_age_requirement(66))  # Too old
        
        # Test without maximum age
        role.maximum_age = None
        role.save()
        self.assertTrue(role.check_age_requirement(80))   # No upper limit
    
    def test_credential_checking(self):
        """Test credential requirement validation"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            required_credentials=['first_aid', 'cpr'],
            justgo_credentials_required=['swimming_coach', 'lifeguard'],
            created_by=self.user
        )
        
        # Test credential checking
        user_creds = ['first_aid', 'cpr', 'extra_cert']
        self.assertTrue(role.check_credential_requirements(user_creds))
        
        user_creds_insufficient = ['first_aid']
        self.assertFalse(role.check_credential_requirements(user_creds_insufficient))
        
        # Test JustGo credentials
        justgo_creds = ['swimming_coach', 'lifeguard', 'extra']
        self.assertTrue(role.check_justgo_requirements(justgo_creds))
        
        justgo_creds_insufficient = ['swimming_coach']
        self.assertFalse(role.check_justgo_requirements(justgo_creds_insufficient))
        
        # Test missing credentials
        missing = role.get_missing_credentials(['first_aid'], ['swimming_coach'])
        self.assertIn('cpr', missing)
        self.assertIn('JustGo: lifeguard', missing)
    
    def test_status_management(self):
        """Test role status management methods"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            created_by=self.user
        )
        
        # Test activation
        role.activate(activated_by=self.user)
        self.assertEqual(role.status, Role.RoleStatus.ACTIVE)
        self.assertIsNotNone(role.status_changed_at)
        self.assertEqual(role.status_changed_by, self.user)
        
        # Test suspension
        role.suspend(suspended_by=self.user, reason="Test suspension")
        self.assertEqual(role.status, Role.RoleStatus.SUSPENDED)
        self.assertIn("Test suspension", role.notes)
        
        # Test cancellation
        role.cancel(cancelled_by=self.user, reason="Test cancellation")
        self.assertEqual(role.status, Role.RoleStatus.CANCELLED)
        
        # Test completion
        role.complete(completed_by=self.user)
        self.assertEqual(role.status, Role.RoleStatus.COMPLETED)
    
    def test_automatic_status_change_on_capacity(self):
        """Test that status changes automatically when capacity is reached"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            status=Role.RoleStatus.ACTIVE,
            total_positions=2,
            filled_positions=1,
            created_by=self.user
        )
        
        # Fill to capacity
        role.filled_positions = 2
        role.save()
        self.assertEqual(role.status, Role.RoleStatus.FULL)
        
        # Reduce capacity
        role.filled_positions = 1
        role.save()
        self.assertEqual(role.status, Role.RoleStatus.ACTIVE)
    
    def test_application_deadline_methods(self):
        """Test application deadline related methods"""
        future_deadline = timezone.now() + timedelta(days=7)
        past_deadline = timezone.now() - timedelta(days=1)
        
        # Test with future deadline
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            status=Role.RoleStatus.ACTIVE,
            application_deadline=future_deadline,
            created_by=self.user
        )
        
        self.assertTrue(role.is_application_open())
        self.assertEqual(role.get_days_until_deadline(), 7)
        
        # Test with past deadline
        role.application_deadline = past_deadline
        role.save()
        self.assertFalse(role.is_application_open())
        self.assertEqual(role.get_days_until_deadline(), 0)
        
        # Test without deadline
        role.application_deadline = None
        role.save()
        self.assertTrue(role.is_application_open())
        self.assertIsNone(role.get_days_until_deadline())
    
    def test_configuration_methods(self):
        """Test configuration management methods"""
        role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test description',
            created_by=self.user
        )
        
        # Test getting configuration
        self.assertTrue(role.get_configuration('requires_approval'))
        self.assertFalse(role.get_configuration('auto_assign'))
        self.assertIsNone(role.get_configuration('nonexistent'))
        self.assertEqual(role.get_configuration('nonexistent', 'default'), 'default')
        
        # Test setting configuration
        role.set_configuration('custom_setting', True)
        self.assertTrue(role.get_configuration('custom_setting'))
        
        # Test updating configuration
        updates = {
            'auto_assign': True,
            'new_setting': 'test_value'
        }
        role.update_configuration(updates)
        self.assertTrue(role.get_configuration('auto_assign'))
        self.assertEqual(role.get_configuration('new_setting'), 'test_value')
    
    def test_role_cloning(self):
        """Test role cloning functionality"""
        # Create another venue
        venue2 = Venue.objects.create(
            event=self.event,
            name='Test Arena',
            slug='test-arena',
            venue_type=Venue.VenueType.ARENA,
            address_line_1='456 Test Avenue',
            city='Dublin',
            country='Ireland',
            total_capacity=20000,
            volunteer_capacity=100,
            created_by=self.user
        )
        
        # Create original role
        original_role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Original Role',
            slug='original-role',
            description='Original description',
            role_type=Role.RoleType.SPORT_OFFICIAL,
            total_positions=5,
            required_credentials=['first_aid'],
            training_required=True,
            created_by=self.user
        )
        
        # Clone the role
        cloned_role = original_role.clone_for_venue(venue2, created_by=self.user)
        
        # Verify clone
        self.assertEqual(cloned_role.event, venue2.event)
        self.assertEqual(cloned_role.venue, venue2)
        self.assertEqual(cloned_role.role_type, original_role.role_type)
        self.assertEqual(cloned_role.description, original_role.description)
        self.assertEqual(cloned_role.total_positions, original_role.total_positions)
        self.assertEqual(cloned_role.required_credentials, original_role.required_credentials)
        self.assertEqual(cloned_role.training_required, original_role.training_required)
        self.assertNotEqual(cloned_role.id, original_role.id)
        self.assertNotEqual(cloned_role.slug, original_role.slug)
    
    def test_role_to_dict(self):
        """Test role dictionary conversion"""
        role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Test Role',
            slug='test-role',
            description='Test description',
            role_type=Role.RoleType.SPORT_OFFICIAL,
            total_positions=5,
            filled_positions=2,
            minimum_volunteers=3,
            estimated_hours_per_day=Decimal('8.0'),
            created_by=self.user
        )
        
        role_dict = role.to_dict()
        
        # Test basic fields
        self.assertEqual(role_dict['name'], 'Test Role')
        self.assertEqual(role_dict['role_type'], Role.RoleType.SPORT_OFFICIAL)
        self.assertEqual(role_dict['event_id'], str(self.event.id))
        self.assertEqual(role_dict['venue_id'], str(self.venue.id))
        
        # Test capacity info
        capacity = role_dict['capacity']
        self.assertEqual(capacity['total_positions'], 5)
        self.assertEqual(capacity['filled_positions'], 2)
        self.assertEqual(capacity['available_positions'], 3)
        self.assertEqual(capacity['capacity_percentage'], 40.0)
        self.assertFalse(capacity['is_full'])
        self.assertTrue(capacity['is_understaffed'])
        
        # Test commitment info
        commitment = role_dict['commitment']
        self.assertEqual(commitment['hours_per_day'], 8.0)
    
    def test_database_constraints(self):
        """Test database constraints"""
        # Test that filled_positions cannot exceed total_positions
        with self.assertRaises(Exception):  # This should raise a database constraint error
            Role.objects.create(
                event=self.event,
                name='Invalid Role',
                slug='invalid-role',
                description='Test description',
                total_positions=5,
                filled_positions=10,  # More than total
                created_by=self.user
            )
        
        # Test that minimum_volunteers cannot exceed total_positions
        with self.assertRaises(Exception):
            Role.objects.create(
                event=self.event,
                name='Invalid Role 2',
                slug='invalid-role-2',
                description='Test description',
                total_positions=5,
                minimum_volunteers=10,  # More than total
                created_by=self.user
            )


def run_tests():
    """Run all role model tests"""
    import unittest
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(RoleModelTest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Role Model Tests Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*60}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 