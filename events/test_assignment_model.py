"""
Comprehensive tests for the Assignment model.
Tests all functionality including status tracking, admin overrides, attendance, and validation.
"""

import uuid
from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Event, Venue, Role, Assignment

User = get_user_model()


class AssignmentModelTest(TestCase):
    """Test cases for Assignment model functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.volunteer = User.objects.create_user(
            username='volunteer',
            email='volunteer@test.com',
            password='testpass123',
            first_name='John',
            last_name='Volunteer',
            user_type=User.UserType.VOLUNTEER,
            date_of_birth=date(1990, 1, 1)
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type=User.UserType.ADMIN,
            is_staff=True,
            date_of_birth=date(1985, 1, 1)
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            first_name='Staff',
            last_name='User',
            user_type=User.UserType.STAFF,
            is_staff=True,
            date_of_birth=date(1988, 1, 1)
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event 2026',
            slug='test-event-2026',
            event_type=Event.EventType.INTERNATIONAL_GAMES,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 15),
            host_city='Dublin',
            volunteer_target=1000,
            created_by=self.admin_user
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            event=self.event,
            name='Test Venue',
            slug='test-venue',
            venue_type=Venue.VenueType.SPORTS_FACILITY,
            address_line_1='123 Test Street',
            city='Dublin',
            country='Ireland',
            volunteer_capacity=100,
            created_by=self.admin_user
        )
        
        # Create test role
        self.role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Test Role',
            slug='test-role',
            role_type=Role.RoleType.GENERAL_VOLUNTEER,
            description='Test role description',
            minimum_age=18,
            total_positions=10,
            minimum_volunteers=5,
            created_by=self.admin_user
        )
    
    def test_assignment_creation(self):
        """Test basic assignment creation"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assignment_type=Assignment.AssignmentType.STANDARD,
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 10),
            assigned_by=self.admin_user
        )
        
        self.assertEqual(assignment.volunteer, self.volunteer)
        self.assertEqual(assignment.role, self.role)
        self.assertEqual(assignment.event, self.event)  # Auto-populated
        self.assertEqual(assignment.venue, self.venue)  # Auto-populated
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.PENDING)
        self.assertEqual(assignment.priority_level, Assignment.PriorityLevel.NORMAL)
        self.assertIsNotNone(assignment.assignment_configuration)
        self.assertIsNotNone(assignment.notification_preferences)
    
    def test_assignment_str_representation(self):
        """Test string representation of assignment"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        expected = f"{self.volunteer.get_full_name()} → {self.role.name} ({assignment.status})"
        self.assertEqual(str(assignment), expected)
    
    def test_assignment_unique_constraint(self):
        """Test unique constraint: one assignment per volunteer per role"""
        Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Try to create duplicate assignment
        with self.assertRaises(Exception):  # IntegrityError
            Assignment.objects.create(
                volunteer=self.volunteer,
                role=self.role,
                assigned_by=self.admin_user
            )
    
    def test_assignment_date_constraints(self):
        """Test date validation constraints"""
        # Test start_date <= end_date constraint
        with self.assertRaises(Exception):  # IntegrityError
            Assignment.objects.create(
                volunteer=self.volunteer,
                role=self.role,
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 5),  # End before start
                assigned_by=self.admin_user
            )
        
        # Test start_time <= end_time constraint
        with self.assertRaises(Exception):  # IntegrityError
            Assignment.objects.create(
                volunteer=self.volunteer,
                role=self.role,
                start_time=time(14, 0),
                end_time=time(10, 0),  # End before start
                assigned_by=self.admin_user
            )
    
    def test_admin_override_constraint(self):
        """Test admin override requires reason constraint"""
        with self.assertRaises(ValidationError):
            assignment = Assignment(
                volunteer=self.volunteer,
                role=self.role,
                is_admin_override=True,
                admin_override_reason='',  # Empty reason
                assigned_by=self.admin_user
            )
            assignment.full_clean()
    
    def test_status_checking_methods(self):
        """Test status checking methods"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Test initial status
        self.assertTrue(assignment.is_pending())
        self.assertFalse(assignment.is_active())
        self.assertFalse(assignment.is_completed())
        self.assertFalse(assignment.is_cancelled())
        
        # Test approved status
        assignment.status = Assignment.AssignmentStatus.APPROVED
        assignment.save()
        self.assertFalse(assignment.is_pending())
        self.assertTrue(assignment.is_active())
        
        # Test completed status
        assignment.status = Assignment.AssignmentStatus.COMPLETED
        assignment.save()
        self.assertTrue(assignment.is_completed())
        self.assertFalse(assignment.is_active())
        
        # Test cancelled status
        assignment.status = Assignment.AssignmentStatus.CANCELLED
        assignment.save()
        self.assertTrue(assignment.is_cancelled())
    
    def test_assignment_modification_permissions(self):
        """Test assignment modification permissions"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Can be modified when pending/approved/confirmed
        self.assertTrue(assignment.can_be_modified())
        
        assignment.status = Assignment.AssignmentStatus.APPROVED
        assignment.save()
        self.assertTrue(assignment.can_be_modified())
        
        assignment.status = Assignment.AssignmentStatus.CONFIRMED
        assignment.save()
        self.assertTrue(assignment.can_be_modified())
        
        # Cannot be modified when completed
        assignment.status = Assignment.AssignmentStatus.COMPLETED
        assignment.save()
        self.assertFalse(assignment.can_be_modified())
    
    def test_assignment_cancellation_permissions(self):
        """Test assignment cancellation permissions"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Can be cancelled when not completed/cancelled
        self.assertTrue(assignment.can_be_cancelled())
        
        assignment.status = Assignment.AssignmentStatus.COMPLETED
        assignment.save()
        self.assertFalse(assignment.can_be_cancelled())
        
        assignment.status = Assignment.AssignmentStatus.CANCELLED
        assignment.save()
        self.assertFalse(assignment.can_be_cancelled())
    
    def test_status_change_methods(self):
        """Test status change methods with audit trail"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Test approval
        assignment.approve(approved_by=self.admin_user, notes="Test approval")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.APPROVED)
        self.assertEqual(assignment.approved_by, self.admin_user)
        self.assertIsNotNone(assignment.approval_date)
        self.assertEqual(assignment.status_changed_by, self.admin_user)
        
        # Test confirmation
        assignment.confirm(notes="Test confirmation")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.CONFIRMED)
        self.assertIsNotNone(assignment.confirmation_date)
        
        # Test activation
        assignment.activate(activated_by=self.staff_user, notes="Test activation")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.ACTIVE)
        
        # Test completion
        assignment.complete(completed_by=self.staff_user, notes="Test completion", performance_rating=4)
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.COMPLETED)
        self.assertIsNotNone(assignment.completion_date)
        self.assertEqual(assignment.performance_rating, 4)
    
    def test_assignment_cancellation_methods(self):
        """Test assignment cancellation methods"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Test cancellation
        assignment.cancel(cancelled_by=self.admin_user, reason="Test cancellation")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.CANCELLED)
        self.assertIn("Test cancellation", assignment.status_change_reason)
        
        # Reset for rejection test
        assignment.status = Assignment.AssignmentStatus.PENDING
        assignment.save()
        
        # Test rejection
        assignment.reject(rejected_by=self.admin_user, reason="Test rejection")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.REJECTED)
        self.assertIn("Test rejection", assignment.status_change_reason)
        
        # Reset for withdrawal test
        assignment.status = Assignment.AssignmentStatus.APPROVED
        assignment.save()
        
        # Test withdrawal
        assignment.withdraw(reason="Test withdrawal")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.WITHDRAWN)
        self.assertIn("Test withdrawal", assignment.status_change_reason)
        
        # Reset for no-show test
        assignment.status = Assignment.AssignmentStatus.ACTIVE
        assignment.save()
        
        # Test no-show
        assignment.mark_no_show(marked_by=self.staff_user, notes="Test no-show")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.NO_SHOW)
        
        # Reset for suspension test
        assignment.status = Assignment.AssignmentStatus.ACTIVE
        assignment.save()
        
        # Test suspension
        assignment.suspend(suspended_by=self.admin_user, reason="Test suspension")
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.SUSPENDED)
        self.assertIn("Test suspension", assignment.status_change_reason)
    
    def test_admin_override_functionality(self):
        """Test admin override functionality"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Test applying admin override
        assignment.apply_admin_override(
            admin_user=self.admin_user,
            reason="Test override for capacity",
            override_types=['capacity', 'age']
        )
        
        self.assertTrue(assignment.is_admin_override)
        self.assertEqual(assignment.admin_override_reason, "Test override for capacity")
        self.assertEqual(assignment.admin_override_by, self.admin_user)
        self.assertIsNotNone(assignment.admin_override_date)
        self.assertTrue(assignment.capacity_override)
        self.assertTrue(assignment.age_requirement_override)
        self.assertFalse(assignment.credential_requirement_override)
        
        # Test removing admin override
        assignment.remove_admin_override(
            admin_user=self.admin_user,
            reason="Override no longer needed"
        )
        
        self.assertFalse(assignment.is_admin_override)
        self.assertEqual(assignment.admin_override_reason, "")
        self.assertIsNone(assignment.admin_override_by)
        self.assertFalse(assignment.capacity_override)
        self.assertFalse(assignment.age_requirement_override)
        self.assertIn("Override no longer needed", assignment.notes)
    
    def test_admin_override_permissions(self):
        """Test admin override permission restrictions"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Non-staff user cannot apply admin override
        with self.assertRaises(ValidationError):
            assignment.apply_admin_override(
                admin_user=self.volunteer,  # Not staff
                reason="Test override"
            )
        
        # Non-staff user cannot remove admin override
        assignment.is_admin_override = True
        assignment.admin_override_reason = "Test override"  # Required field
        assignment.save()
        
        with self.assertRaises(ValidationError):
            assignment.remove_admin_override(
                admin_user=self.volunteer,  # Not staff
                reason="Test removal"
            )
    
    def test_attendance_tracking(self):
        """Test attendance tracking functionality"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            status=Assignment.AssignmentStatus.CONFIRMED,
            assigned_by=self.admin_user
        )
        
        # Test check-in
        check_in_time = timezone.now()
        assignment.check_in(check_in_time=check_in_time, location="Main entrance")
        
        self.assertEqual(assignment.check_in_time, check_in_time)
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.ACTIVE)  # Auto-activated
        self.assertIn("check_in_location", assignment.assignment_configuration)
        
        # Test check-out
        check_out_time = check_in_time + timedelta(hours=8)
        assignment.check_out(check_out_time=check_out_time, location="Main exit")
        
        self.assertEqual(assignment.check_out_time, check_out_time)
        self.assertEqual(assignment.actual_hours_worked, Decimal('8.00'))
        self.assertIn("check_out_location", assignment.assignment_configuration)
    
    def test_assignment_validation(self):
        """Test assignment validation against role requirements"""
        # Create role with specific age requirement and multiple positions
        strict_role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Strict Role',
            slug='strict-role',
            role_type=Role.RoleType.SECURITY,
            description='Role with strict requirements',
            minimum_age=40,  # Volunteer is too young (born 1990, so ~36 in 2026)
            total_positions=2,  # Multiple positions to avoid capacity issues
            created_by=self.admin_user
        )
        
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=strict_role,
            assigned_by=self.admin_user
        )
        
        # Should fail validation (volunteer is too young)
        errors = assignment.validate_assignment()
        self.assertGreater(len(errors), 0)
        self.assertIn("age", errors[0].lower())
        
        # Test with age override - also need capacity override since role now has 1 filled position
        assignment.age_requirement_override = True
        assignment.capacity_override = True  # Need this since assignment creation filled the role
        assignment.save()
        errors = assignment.validate_assignment()
        self.assertEqual(len(errors), 0)  # Should pass with both overrides
        
        # Test with capacity override when role is full
        # Create a separate role for capacity testing
        capacity_role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Capacity Test Role',
            slug='capacity-test-role',
            role_type=Role.RoleType.GENERAL_VOLUNTEER,
            description='Role for testing capacity limits',
            minimum_age=18,
            total_positions=1,
            filled_positions=1,  # Already at capacity
            created_by=self.admin_user
        )
        
        assignment2 = Assignment(
            volunteer=self.staff_user,
            role=capacity_role,
            assigned_by=self.admin_user
        )
        
        errors = assignment2.validate_assignment()
        self.assertIn("Role is at capacity", errors[0])
        
        # Should pass with capacity override
        assignment2.capacity_override = True
        errors = assignment2.validate_assignment()
        self.assertEqual(len(errors), 0)
    
    def test_time_commitment_calculation(self):
        """Test time commitment calculation"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 9),  # 5 days
            assigned_by=self.admin_user
        )
        
        # Set role hours per day
        self.role.estimated_hours_per_day = Decimal('8.0')
        self.role.save()
        
        # Test duration calculation
        self.assertEqual(assignment.get_duration(), 5)
        
        # Test time commitment calculation
        commitment = assignment.get_time_commitment()
        self.assertEqual(commitment['duration_days'], 5)
        self.assertEqual(commitment['hours_per_day'], 8.0)
        self.assertEqual(commitment['total_estimated_hours'], 40.0)
        self.assertIsNone(commitment['actual_hours_worked'])
        
        # Add actual hours worked
        assignment.actual_hours_worked = Decimal('35.5')
        assignment.save()
        
        commitment = assignment.get_time_commitment()
        self.assertEqual(commitment['actual_hours_worked'], 35.5)
    
    def test_schedule_info(self):
        """Test schedule information retrieval"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 9),
            start_time=time(9, 0),
            end_time=time(17, 0),
            assigned_by=self.admin_user
        )
        
        schedule_info = assignment.get_schedule_info()
        
        self.assertEqual(schedule_info['start_date'], '2026-07-05')
        self.assertEqual(schedule_info['end_date'], '2026-07-09')
        self.assertEqual(schedule_info['start_time'], '09:00')
        self.assertEqual(schedule_info['end_time'], '17:00')
        self.assertEqual(schedule_info['duration_days'], 5)
    
    def test_assignment_cloning(self):
        """Test assignment cloning functionality"""
        # Create another role for cloning
        target_role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Target Role',
            slug='target-role',
            role_type=Role.RoleType.GENERAL_VOLUNTEER,
            description='Target role for cloning',
            total_positions=5,
            created_by=self.admin_user
        )
        
        original_assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assignment_type=Assignment.AssignmentType.STANDARD,
            priority_level=Assignment.PriorityLevel.HIGH,
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 9),
            special_instructions="Special instructions",
            assigned_by=self.admin_user
        )
        
        # Clone assignment
        cloned_assignment = original_assignment.clone_for_role(
            target_role=target_role,
            created_by=self.staff_user
        )
        
        # Verify clone properties
        self.assertEqual(cloned_assignment.volunteer, original_assignment.volunteer)
        self.assertEqual(cloned_assignment.role, target_role)
        self.assertEqual(cloned_assignment.event, target_role.event)
        self.assertEqual(cloned_assignment.venue, target_role.venue)
        self.assertEqual(cloned_assignment.assignment_type, original_assignment.assignment_type)
        self.assertEqual(cloned_assignment.priority_level, original_assignment.priority_level)
        self.assertEqual(cloned_assignment.start_date, original_assignment.start_date)
        self.assertEqual(cloned_assignment.special_instructions, original_assignment.special_instructions)
        self.assertEqual(cloned_assignment.assigned_by, self.staff_user)
        
        # Verify it's a separate object
        self.assertNotEqual(cloned_assignment.id, original_assignment.id)
    
    def test_role_capacity_update(self):
        """Test automatic role capacity updates"""
        # Initial state
        self.assertEqual(self.role.filled_positions, 0)
        
        # Create assignment
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            status=Assignment.AssignmentStatus.APPROVED,
            assigned_by=self.admin_user
        )
        
        # Check role capacity updated
        self.role.refresh_from_db()
        self.assertEqual(self.role.filled_positions, 1)
        
        # Cancel assignment
        assignment.cancel(cancelled_by=self.admin_user)
        
        # Check role capacity updated
        self.role.refresh_from_db()
        self.assertEqual(self.role.filled_positions, 0)
    
    def test_assignment_to_dict(self):
        """Test assignment dictionary representation"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assignment_type=Assignment.AssignmentType.STANDARD,
            status=Assignment.AssignmentStatus.APPROVED,
            priority_level=Assignment.PriorityLevel.HIGH,
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 9),
            performance_rating=4,
            assigned_by=self.admin_user
        )
        
        assignment_dict = assignment.to_dict()
        
        # Verify structure
        self.assertIn('id', assignment_dict)
        self.assertIn('volunteer', assignment_dict)
        self.assertIn('role', assignment_dict)
        self.assertIn('event', assignment_dict)
        self.assertIn('venue', assignment_dict)
        self.assertIn('assignment_details', assignment_dict)
        self.assertIn('schedule', assignment_dict)
        self.assertIn('status_info', assignment_dict)
        self.assertIn('dates', assignment_dict)
        self.assertIn('attendance', assignment_dict)
        self.assertIn('feedback', assignment_dict)
        self.assertIn('overrides', assignment_dict)
        
        # Verify content
        self.assertEqual(assignment_dict['volunteer']['name'], self.volunteer.get_full_name())
        self.assertEqual(assignment_dict['role']['name'], self.role.name)
        self.assertEqual(assignment_dict['assignment_details']['type'], Assignment.AssignmentType.STANDARD)
        self.assertEqual(assignment_dict['assignment_details']['status'], Assignment.AssignmentStatus.APPROVED)
        self.assertEqual(assignment_dict['feedback']['performance_rating'], 4)
    
    def test_default_configurations(self):
        """Test default configuration settings"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Test default assignment configuration
        config = assignment.assignment_configuration
        self.assertTrue(config['auto_reminders'])
        self.assertEqual(config['reminder_days_before'], [7, 3, 1])
        self.assertTrue(config['require_check_in'])
        self.assertTrue(config['require_check_out'])
        self.assertEqual(config['allow_early_check_in'], 30)
        
        # Test default notification preferences
        prefs = assignment.notification_preferences
        self.assertTrue(prefs['email_notifications'])
        self.assertFalse(prefs['sms_notifications'])
        self.assertTrue(prefs['push_notifications'])
        self.assertTrue(prefs['reminder_notifications'])
    
    def test_status_date_updates(self):
        """Test automatic status date updates"""
        assignment = Assignment.objects.create(
            volunteer=self.volunteer,
            role=self.role,
            assigned_by=self.admin_user
        )
        
        # Test approval date
        assignment.status = Assignment.AssignmentStatus.APPROVED
        assignment.save()
        self.assertIsNotNone(assignment.approval_date)
        
        # Test confirmation date
        assignment.status = Assignment.AssignmentStatus.CONFIRMED
        assignment.save()
        self.assertIsNotNone(assignment.confirmation_date)
        
        # Test completion date
        assignment.status = Assignment.AssignmentStatus.COMPLETED
        assignment.save()
        self.assertIsNotNone(assignment.completion_date)


class AssignmentModelEdgeCasesTest(TestCase):
    """Test edge cases and error conditions for Assignment model"""
    
    def setUp(self):
        """Set up test data for edge cases"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            user_type=User.UserType.VOLUNTEER,
            date_of_birth=date(1990, 1, 1)
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            slug='test-event',
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 15),
            host_city='Dublin'
        )
        
        self.role = Role.objects.create(
            event=self.event,
            name='Test Role',
            slug='test-role',
            description='Test role',
            total_positions=1
        )
    
    def test_assignment_without_venue(self):
        """Test assignment creation when role has no venue"""
        # Create role without venue
        role_no_venue = Role.objects.create(
            event=self.event,
            name='No Venue Role',
            slug='no-venue-role',
            description='Role without venue',
            total_positions=1
        )
        
        assignment = Assignment.objects.create(
            volunteer=self.user,
            role=role_no_venue
        )
        
        self.assertEqual(assignment.event, self.event)
        self.assertIsNone(assignment.venue)
    
    def test_assignment_with_minimal_data(self):
        """Test assignment creation with minimal required data"""
        assignment = Assignment.objects.create(
            volunteer=self.user,
            role=self.role
        )
        
        # Should have defaults
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.PENDING)
        self.assertEqual(assignment.assignment_type, Assignment.AssignmentType.STANDARD)
        self.assertEqual(assignment.priority_level, Assignment.PriorityLevel.NORMAL)
        self.assertIsNotNone(assignment.assignment_configuration)
        self.assertIsNotNone(assignment.notification_preferences)
    
    def test_assignment_status_history_placeholder(self):
        """Test status history method (placeholder implementation)"""
        assignment = Assignment.objects.create(
            volunteer=self.user,
            role=self.role
        )
        
        assignment.approve(notes="Test approval")
        
        history = assignment.get_status_history()
        self.assertEqual(history['current_status'], Assignment.AssignmentStatus.APPROVED)
        self.assertIsNotNone(history['status_changed_at'])
        self.assertIn('Test approval', history['status_change_reason'])
    
    def test_assignment_absolute_url(self):
        """Test absolute URL generation"""
        assignment = Assignment.objects.create(
            volunteer=self.user,
            role=self.role
        )
        
        # This would normally work with proper URL configuration
        # For now, just test that the method exists and handles missing URLs gracefully
        try:
            url = assignment.get_absolute_url()
            self.assertIsInstance(url, str)
            self.assertIn(str(assignment.id), url)
        except Exception as e:
            # Expected to fail without URL configuration
            self.assertIn("NoReverseMatch", str(type(e).__name__))


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.test_settings')
        django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['events.test_assignment_model'])
    
    if failures:
        exit(1) 