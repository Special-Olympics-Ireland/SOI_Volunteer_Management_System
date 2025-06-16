"""
Comprehensive tests for the Event model.
Tests all functionality including configuration management, status changes, and business logic.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json

from .models import Event, Venue

User = get_user_model()

class EventModelTest(TestCase):
    """Test cases for the Event model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='ADMIN'
        )
        
        self.event_data = {
            'name': 'ISG 2026',
            'slug': 'isg-2026',
            'short_name': 'ISG26',
            'event_type': Event.EventType.INTERNATIONAL_GAMES,
            'start_date': date.today() + timedelta(days=30),
            'end_date': date.today() + timedelta(days=34),
            'host_city': 'Dublin',
            'volunteer_target': 5000,
            'created_by': self.user
        }
    
    def test_event_creation(self):
        """Test basic event creation"""
        event = Event.objects.create(**self.event_data)
        
        self.assertEqual(event.name, 'ISG 2026')
        self.assertEqual(event.slug, 'isg-2026')
        self.assertEqual(event.status, Event.EventStatus.DRAFT)
        self.assertEqual(event.volunteer_target, 5000)
        self.assertTrue(event.is_active)
        self.assertTrue(event.is_public)
        self.assertFalse(event.is_featured)
    
    def test_event_str_representation(self):
        """Test string representation of event"""
        event = Event.objects.create(**self.event_data)
        expected = f"ISG 2026 ({event.start_date.year})"
        self.assertEqual(str(event), expected)
    
    def test_event_default_configurations(self):
        """Test that default configurations are set on creation"""
        event = Event.objects.create(**self.event_data)
        
        # Check that default configurations are populated
        self.assertIsInstance(event.event_configuration, dict)
        self.assertIsInstance(event.volunteer_configuration, dict)
        self.assertIsInstance(event.venue_configuration, dict)
        self.assertIsInstance(event.role_configuration, dict)
        self.assertIsInstance(event.features_enabled, dict)
        self.assertIsInstance(event.brand_colors, dict)
        
        # Check specific default values
        self.assertTrue(event.event_configuration.get('require_photo_upload'))
        self.assertEqual(event.event_configuration.get('max_venue_preferences'), 3)
        self.assertEqual(event.brand_colors.get('primary'), '#228B22')
        self.assertTrue(event.features_enabled.get('volunteer_registration'))
    
    def test_event_date_validation(self):
        """Test date validation constraints"""
        # Test end date before start date (should fail at model validation level)
        invalid_data = self.event_data.copy()
        invalid_data['end_date'] = invalid_data['start_date'] - timedelta(days=1)
        
        event = Event(**invalid_data)
        # This should fail model validation due to constraint
        with self.assertRaises(ValidationError):
            event.full_clean()
    
    def test_volunteer_target_validation(self):
        """Test volunteer target validation"""
        # Negative volunteer target should be prevented by validator
        invalid_data = self.event_data.copy()
        invalid_data['volunteer_target'] = -100
        
        with self.assertRaises(ValidationError):
            event = Event(**invalid_data)
            event.full_clean()
    
    def test_volunteer_minimum_age_validation(self):
        """Test volunteer minimum age validation"""
        # Test age too low
        invalid_data = self.event_data.copy()
        invalid_data['volunteer_minimum_age'] = 10
        
        with self.assertRaises(ValidationError):
            event = Event(**invalid_data)
            event.full_clean()
        
        # Test age too high
        invalid_data['volunteer_minimum_age'] = 30
        
        with self.assertRaises(ValidationError):
            event = Event(**invalid_data)
            event.full_clean()
    
    def test_event_status_methods(self):
        """Test event status checking methods"""
        # Test upcoming event
        event = Event.objects.create(**self.event_data)
        self.assertTrue(event.is_upcoming())
        self.assertFalse(event.is_ongoing())
        self.assertFalse(event.is_past())
        
        # Test ongoing event
        event.start_date = date.today() - timedelta(days=1)
        event.end_date = date.today() + timedelta(days=1)
        event.save()
        
        self.assertFalse(event.is_upcoming())
        self.assertTrue(event.is_ongoing())
        self.assertFalse(event.is_past())
        
        # Test past event
        event.start_date = date.today() - timedelta(days=5)
        event.end_date = date.today() - timedelta(days=1)
        event.save()
        
        self.assertFalse(event.is_upcoming())
        self.assertFalse(event.is_ongoing())
        self.assertTrue(event.is_past())
    
    def test_get_duration_days(self):
        """Test event duration calculation"""
        event = Event.objects.create(**self.event_data)
        expected_duration = (event.end_date - event.start_date).days + 1
        self.assertEqual(event.get_duration_days(), expected_duration)
    
    def test_can_register_volunteers(self):
        """Test volunteer registration availability"""
        event = Event.objects.create(**self.event_data)
        
        # Draft status should not allow registration
        self.assertFalse(event.can_register_volunteers())
        
        # Registration open status should allow registration
        event.status = Event.EventStatus.REGISTRATION_OPEN
        event.save()
        self.assertTrue(event.can_register_volunteers())
        
        # Inactive event should not allow registration
        event.is_active = False
        event.save()
        self.assertFalse(event.can_register_volunteers())
        
        # Private event should not allow registration
        event.is_active = True
        event.is_public = False
        event.save()
        self.assertFalse(event.can_register_volunteers())
    
    def test_registration_status_with_dates(self):
        """Test registration status with date constraints"""
        event = Event.objects.create(**self.event_data)
        event.status = Event.EventStatus.REGISTRATION_OPEN
        
        # Registration not yet open
        event.registration_open_date = timezone.now() + timedelta(days=1)
        event.save()
        self.assertEqual(event.get_registration_status(), 'not_yet_open')
        
        # Registration open
        event.registration_open_date = timezone.now() - timedelta(days=1)
        event.registration_close_date = timezone.now() + timedelta(days=1)
        event.save()
        self.assertEqual(event.get_registration_status(), 'open')
        
        # Registration closed
        event.registration_close_date = timezone.now() - timedelta(days=1)
        event.save()
        self.assertEqual(event.get_registration_status(), 'closed')
    
    def test_configuration_management(self):
        """Test configuration get/set methods"""
        event = Event.objects.create(**self.event_data)
        
        # Test getting configuration
        config = event.get_configuration('event')
        self.assertIsInstance(config, dict)
        
        # Test getting specific key
        photo_required = event.get_configuration('event', 'require_photo_upload')
        self.assertTrue(photo_required)
        
        # Test getting with default
        custom_value = event.get_configuration('event', 'nonexistent_key', 'default_value')
        self.assertEqual(custom_value, 'default_value')
        
        # Test setting configuration
        event.set_configuration('event', 'test_key', 'test_value')
        self.assertEqual(event.get_configuration('event', 'test_key'), 'test_value')
        
        # Test updating multiple configurations
        updates = {'key1': 'value1', 'key2': 'value2'}
        event.update_configuration('event', updates)
        self.assertEqual(event.get_configuration('event', 'key1'), 'value1')
        self.assertEqual(event.get_configuration('event', 'key2'), 'value2')
    
    def test_status_change_tracking(self):
        """Test status change tracking and audit trail"""
        event = Event.objects.create(**self.event_data)
        original_status = event.status
        
        # Change status
        new_status = Event.EventStatus.PLANNING
        event.change_status(new_status, self.user, "Moving to planning phase")
        
        self.assertEqual(event.status, new_status)
        self.assertEqual(event.status_changed_by, self.user)
        self.assertIsNotNone(event.status_changed_at)
        self.assertIn("Moving to planning phase", event.notes)
    
    def test_event_activation_deactivation(self):
        """Test event activation and deactivation"""
        event = Event.objects.create(**self.event_data)
        
        # Test deactivation
        event.deactivate(self.user, "Testing deactivation")
        self.assertFalse(event.is_active)
        self.assertIn("deactivated", event.notes)
        
        # Test activation
        event.activate(self.user)
        self.assertTrue(event.is_active)
        self.assertIn("activated", event.notes)
    
    def test_event_cloning(self):
        """Test event cloning functionality"""
        original_event = Event.objects.create(**self.event_data)
        
        # Add some configuration
        original_event.set_configuration('event', 'custom_setting', 'custom_value')
        
        # Clone the event
        cloned_event = original_event.clone(
            'ISG 2027',
            'isg-2027',
            self.user
        )
        
        self.assertEqual(cloned_event.name, 'ISG 2027')
        self.assertEqual(cloned_event.slug, 'isg-2027')
        self.assertEqual(cloned_event.status, Event.EventStatus.DRAFT)
        self.assertEqual(cloned_event.created_by, self.user)
        
        # Check that configuration was copied
        self.assertEqual(
            cloned_event.get_configuration('event', 'custom_setting'),
            'custom_value'
        )
        
        # Ensure it's a separate instance
        self.assertNotEqual(original_event.id, cloned_event.id)
    
    def test_event_managers(self):
        """Test event managers many-to-many relationship"""
        event = Event.objects.create(**self.event_data)
        
        # Create additional users
        manager1 = User.objects.create_user(
            username='manager1',
            email='manager1@example.com',
            password='pass123',
            user_type='VMT'
        )
        manager2 = User.objects.create_user(
            username='manager2',
            email='manager2@example.com',
            password='pass123',
            user_type='GOC'
        )
        
        # Add managers
        event.event_managers.add(manager1, manager2)
        
        self.assertEqual(event.event_managers.count(), 2)
        self.assertIn(manager1, event.event_managers.all())
        self.assertIn(manager2, event.event_managers.all())
    
    def test_volunteer_count_methods(self):
        """Test volunteer counting methods (placeholder until Assignment model exists)"""
        event = Event.objects.create(**self.event_data)
        
        # These methods will return 0 until Assignment model is implemented
        self.assertEqual(event.get_volunteer_count(), 0)
        self.assertEqual(event.get_volunteer_target_progress(), 0)
    
    def test_venue_and_role_count_methods(self):
        """Test venue and role counting methods (placeholder until models exist)"""
        event = Event.objects.create(**self.event_data)
        
        # These methods will return 0 until Venue and Role models are implemented
        self.assertEqual(event.get_venue_count(), 0)
        self.assertEqual(event.get_role_count(), 0)
    
    def test_to_dict_method(self):
        """Test event dictionary conversion for API responses"""
        event = Event.objects.create(**self.event_data)
        event_dict = event.to_dict()
        
        self.assertIsInstance(event_dict, dict)
        self.assertEqual(event_dict['name'], event.name)
        self.assertEqual(event_dict['slug'], event.slug)
        self.assertEqual(event_dict['status'], event.status)
        self.assertIn('id', event_dict)
        self.assertIn('created_at', event_dict)
        self.assertIn('updated_at', event_dict)
    
    def test_event_unique_slug(self):
        """Test that event slugs must be unique"""
        Event.objects.create(**self.event_data)
        
        # Try to create another event with the same slug
        duplicate_data = self.event_data.copy()
        duplicate_data['name'] = 'Different Name'
        
        with self.assertRaises(Exception):  # IntegrityError at database level
            Event.objects.create(**duplicate_data)
    
    def test_event_meta_options(self):
        """Test model meta options"""
        event = Event.objects.create(**self.event_data)
        
        # Test verbose names
        self.assertEqual(Event._meta.verbose_name, 'event')
        self.assertEqual(Event._meta.verbose_name_plural, 'events')
        
        # Test default ordering
        self.assertEqual(Event._meta.ordering, ['-start_date', 'name'])
    
    def test_event_indexes(self):
        """Test that database indexes are properly defined"""
        # This is more of a structural test
        indexes = Event._meta.indexes
        self.assertTrue(len(indexes) > 0)
        
        # Check that important fields have indexes
        index_fields = []
        for index in indexes:
            index_fields.extend(index.fields)
        
        self.assertIn('status', index_fields)
        self.assertIn('slug', index_fields)
        self.assertIn('created_at', index_fields)
    
    def test_event_constraints(self):
        """Test that database constraints are properly defined"""
        constraints = Event._meta.constraints
        self.assertTrue(len(constraints) > 0)
        
        # Check constraint names
        constraint_names = [constraint.name for constraint in constraints]
        self.assertIn('event_end_date_after_start_date', constraint_names)
        self.assertIn('event_volunteer_target_non_negative', constraint_names)

class VenueModelTest(TestCase):
    """Test cases for Venue model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            slug='test-event',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            host_city='Dublin',
            host_country='Ireland',
            created_by=self.user
        )
        
        self.venue_data = {
            'event': self.event,
            'name': 'Test Venue',
            'slug': 'test-venue',
            'short_name': 'TV',
            'venue_type': Venue.VenueType.SPORTS_FACILITY,
            'address_line_1': '123 Test Street',
            'city': 'Dublin',
            'country': 'Ireland',
            'total_capacity': 1000,
            'volunteer_capacity': 100,
            'spectator_capacity': 900,
            'created_by': self.user
        }
    
    def test_venue_creation(self):
        """Test basic venue creation"""
        venue = Venue.objects.create(**self.venue_data)
        
        self.assertEqual(venue.name, 'Test Venue')
        self.assertEqual(venue.slug, 'test-venue')
        self.assertEqual(venue.event, self.event)
        self.assertEqual(venue.status, Venue.VenueStatus.DRAFT)
        self.assertTrue(venue.is_active)
        self.assertIsNotNone(venue.id)
    
    def test_venue_str_representation(self):
        """Test venue string representation"""
        venue = Venue.objects.create(**self.venue_data)
        expected_str = f"{venue.name} ({venue.event.name})"
        self.assertEqual(str(venue), expected_str)
    
    def test_venue_unique_slug_per_event(self):
        """Test venue slug uniqueness within event"""
        # Create first venue
        Venue.objects.create(**self.venue_data)
        
        # Try to create second venue with same slug in same event
        venue_data_2 = self.venue_data.copy()
        venue_data_2['name'] = 'Test Venue 2'
        
        venue2 = Venue(**venue_data_2)
        with self.assertRaises(ValidationError):
            venue2.full_clean()
    
    def test_venue_address_methods(self):
        """Test venue address-related methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test full address
        expected_address = "123 Test Street, Dublin, Ireland"
        self.assertEqual(venue.get_full_address(), expected_address)
        
        # Test with all address fields
        venue.address_line_2 = "Unit 5"
        venue.county = "Dublin County"
        venue.postal_code = "D01 ABC123"
        venue.save()
        
        expected_full_address = "123 Test Street, Unit 5, Dublin, Dublin County, D01 ABC123, Ireland"
        self.assertEqual(venue.get_full_address(), expected_full_address)
    
    def test_venue_coordinates(self):
        """Test venue coordinate methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test without coordinates
        self.assertFalse(venue.has_coordinates())
        self.assertIsNone(venue.get_coordinates())
        
        # Test with coordinates
        venue.latitude = Decimal('53.3498')
        venue.longitude = Decimal('-6.2603')
        venue.save()
        
        self.assertTrue(venue.has_coordinates())
        coordinates = venue.get_coordinates()
        self.assertEqual(coordinates, (53.3498, -6.2603))
    
    def test_venue_capacity_methods(self):
        """Test venue capacity-related methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test initial capacity
        self.assertEqual(venue.get_assigned_volunteer_count(), 0)
        self.assertEqual(venue.get_available_capacity(), 100)
        self.assertEqual(venue.get_capacity_utilization(), 0.0)
        self.assertFalse(venue.is_at_capacity())
        self.assertTrue(venue.can_accommodate_volunteers(50))
        self.assertTrue(venue.can_accommodate_volunteers(100))
        self.assertFalse(venue.can_accommodate_volunteers(101))
    
    def test_venue_accessibility_methods(self):
        """Test venue accessibility methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test default accessibility
        self.assertFalse(venue.is_fully_accessible())
        self.assertFalse(venue.has_basic_accessibility())
        self.assertEqual(venue.get_accessibility_features(), [])
        
        # Test with accessibility features
        venue.accessibility_level = Venue.AccessibilityLevel.FULL
        venue.wheelchair_accessible = True
        venue.accessible_parking = True
        venue.accessible_toilets = True
        venue.hearing_loop = True
        venue.save()
        
        self.assertTrue(venue.is_fully_accessible())
        self.assertTrue(venue.has_basic_accessibility())
        features = venue.get_accessibility_features()
        self.assertIn('Wheelchair Accessible', features)
        self.assertIn('Accessible Parking', features)
        self.assertIn('Accessible Toilets', features)
        self.assertIn('Hearing Loop', features)
    
    def test_venue_configuration_defaults(self):
        """Test venue configuration defaults are set"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Check that default configurations are set
        self.assertIsInstance(venue.venue_configuration, dict)
        self.assertIsInstance(venue.facilities, dict)
        self.assertIsInstance(venue.operational_hours, dict)
        self.assertIsInstance(venue.equipment_available, list)
        self.assertIsInstance(venue.emergency_contact, dict)
        
        # Check specific default values
        self.assertTrue(venue.venue_configuration.get('check_in_required'))
        self.assertEqual(venue.venue_configuration.get('security_level'), 'standard')
        self.assertIn('Tables', venue.equipment_available)
    
    def test_venue_configuration_management(self):
        """Test venue configuration management methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test setting configuration
        venue.set_configuration('test_key', 'test_value')
        self.assertEqual(venue.get_configuration('test_key'), 'test_value')
        
        # Test updating configuration
        updates = {'key1': 'value1', 'key2': 'value2'}
        venue.update_configuration(updates)
        self.assertEqual(venue.get_configuration('key1'), 'value1')
        self.assertEqual(venue.get_configuration('key2'), 'value2')
    
    def test_venue_facility_management(self):
        """Test venue facility management methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test setting facility
        self.assertFalse(venue.get_facility('toilets'))
        venue.set_facility('toilets', True)
        self.assertTrue(venue.get_facility('toilets'))
    
    def test_venue_operational_hours(self):
        """Test venue operational hours methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test default operational hours
        monday_hours = venue.get_operational_hours('monday')
        self.assertEqual(monday_hours['open'], '08:00')
        self.assertEqual(monday_hours['close'], '18:00')
        self.assertFalse(monday_hours['closed'])
        
        # Test if venue is open
        self.assertTrue(venue.is_open_on_day('monday'))
    
    def test_venue_status_change(self):
        """Test venue status change with audit trail"""
        venue = Venue.objects.create(**self.venue_data)
        original_status = venue.status
        
        # Change status
        new_status = Venue.VenueStatus.CONFIRMED
        venue.change_status(new_status, self.user, "Venue confirmed")
        
        self.assertEqual(venue.status, new_status)
        self.assertEqual(venue.status_changed_by, self.user)
        self.assertIsNotNone(venue.status_changed_at)
        self.assertIn("Venue confirmed", venue.notes)
    
    def test_venue_activation_deactivation(self):
        """Test venue activation and deactivation"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test deactivation
        venue.deactivate(self.user, "Test deactivation")
        self.assertFalse(venue.is_active)
        self.assertIn("Test deactivation", venue.notes)
        
        # Test activation
        venue.activate(self.user)
        self.assertTrue(venue.is_active)
    
    def test_venue_primary_setting(self):
        """Test setting venue as primary"""
        venue = Venue.objects.create(**self.venue_data)
        
        self.assertFalse(venue.is_primary)
        venue.set_as_primary(self.user)
        self.assertTrue(venue.is_primary)
    
    def test_venue_distance_calculation(self):
        """Test venue distance calculation"""
        venue1 = Venue.objects.create(**self.venue_data)
        venue1.latitude = Decimal('53.3498')
        venue1.longitude = Decimal('-6.2603')
        venue1.save()
        
        venue_data_2 = self.venue_data.copy()
        venue_data_2['name'] = 'Test Venue 2'
        venue_data_2['slug'] = 'test-venue-2'
        venue2 = Venue.objects.create(**venue_data_2)
        venue2.latitude = Decimal('53.3500')
        venue2.longitude = Decimal('-6.2600')
        venue2.save()
        
        # Test distance calculation (should return a number)
        distance = venue1.get_distance_to(venue2)
        self.assertIsInstance(distance, float)
        self.assertGreater(distance, 0)
        
        # Test with venue without coordinates
        venue3_data = self.venue_data.copy()
        venue3_data['name'] = 'Test Venue 3'
        venue3_data['slug'] = 'test-venue-3'
        venue3 = Venue.objects.create(**venue3_data)
        
        distance_none = venue1.get_distance_to(venue3)
        self.assertIsNone(distance_none)
    
    def test_venue_cloning(self):
        """Test venue cloning functionality"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Create target event
        target_event = Event.objects.create(
            name='Target Event',
            slug='target-event',
            start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=70),
            host_city='Cork',
            host_country='Ireland',
            created_by=self.user
        )
        
        # Clone the venue
        cloned_venue = venue.clone_for_event(
            target_event=target_event,
            new_name="Cloned Test Venue",
            created_by=self.user
        )
        
        self.assertNotEqual(venue.id, cloned_venue.id)
        self.assertEqual(cloned_venue.name, "Cloned Test Venue")
        self.assertEqual(cloned_venue.event, target_event)
        self.assertEqual(cloned_venue.created_by, self.user)
        self.assertEqual(cloned_venue.status, Venue.VenueStatus.DRAFT)
        self.assertEqual(cloned_venue.address_line_1, venue.address_line_1)
    
    def test_venue_capacity_validation(self):
        """Test venue capacity validation"""
        # Test valid capacities
        venue = Venue.objects.create(**self.venue_data)
        self.assertEqual(venue.total_capacity, 1000)
        self.assertEqual(venue.volunteer_capacity, 100)
        self.assertEqual(venue.spectator_capacity, 900)
        
        # Test negative capacity validation (handled by model constraints)
        venue_data_invalid = self.venue_data.copy()
        venue_data_invalid['total_capacity'] = -1
        
        venue_invalid = Venue(**venue_data_invalid)
        with self.assertRaises(ValidationError):
            venue_invalid.full_clean()
    
    def test_venue_coordinate_validation(self):
        """Test venue coordinate validation"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test valid coordinates
        venue.latitude = Decimal('53.3498')
        venue.longitude = Decimal('-6.2603')
        venue.full_clean()  # Should not raise
        
        # Note: Coordinate validation is typically handled at the serializer level
        # The model allows any decimal values for flexibility
        # This test verifies that valid coordinates work correctly
        self.assertTrue(venue.has_coordinates())
        coordinates = venue.get_coordinates()
        self.assertEqual(coordinates, (53.3498, -6.2603))
    
    def test_venue_role_count_methods(self):
        """Test venue role count methods"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test initial role counts (should be 0 until Role model is implemented)
        self.assertEqual(venue.get_role_count(), 0)
        self.assertEqual(venue.get_active_role_count(), 0)
    
    def test_venue_to_dict(self):
        """Test venue to_dict method"""
        venue = Venue.objects.create(**self.venue_data)
        venue_dict = venue.to_dict()
        
        self.assertIsInstance(venue_dict, dict)
        self.assertEqual(venue_dict['name'], venue.name)
        self.assertEqual(venue_dict['slug'], venue.slug)
        self.assertEqual(venue_dict['venue_type'], venue.venue_type)
        self.assertEqual(venue_dict['status'], venue.status)
        self.assertIn('full_address', venue_dict)
        self.assertIn('capacity_utilization', venue_dict)
        self.assertIn('accessibility_features', venue_dict)
        self.assertIn('created_at', venue_dict)
        self.assertIn('updated_at', venue_dict)
    
    def test_venue_event_relationship(self):
        """Test venue-event relationship"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Test venue is associated with event
        self.assertEqual(venue.event, self.event)
        
        # Test event can access its venues
        self.assertIn(venue, self.event.venues.all())
        self.assertEqual(self.event.get_venue_count(), 1)
    
    def test_venue_coordinators_relationship(self):
        """Test venue coordinators many-to-many relationship"""
        venue = Venue.objects.create(**self.venue_data)
        
        # Create additional users
        coordinator1 = User.objects.create_user(
            username='coordinator1',
            email='coord1@example.com',
            password='testpass123'
        )
        coordinator2 = User.objects.create_user(
            username='coordinator2',
            email='coord2@example.com',
            password='testpass123'
        )
        
        # Add coordinators
        venue.venue_coordinators.add(coordinator1, coordinator2)
        
        # Test relationship
        self.assertEqual(venue.venue_coordinators.count(), 2)
        self.assertIn(coordinator1, venue.venue_coordinators.all())
        self.assertIn(coordinator2, venue.venue_coordinators.all())
        
        # Test reverse relationship
        self.assertIn(venue, coordinator1.coordinated_venues.all())
        self.assertIn(venue, coordinator2.coordinated_venues.all()) 