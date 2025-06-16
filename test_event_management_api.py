#!/usr/bin/env python
"""
Comprehensive test script for Event Management API endpoints.

Tests all CRUD operations, filtering, permissions, and custom actions
for Events and Venues management.

Usage:
    python manage.py shell < test_event_management_api.py
    # OR
    python test_event_management_api.py
"""

import os
import sys
import django
from datetime import date, datetime, timedelta
from decimal import Decimal
import json

# Setup Django
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
    django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from events.models import Event, Venue
from common.audit_service import AdminAuditService

User = get_user_model()

class EventManagementAPITest:
    """Comprehensive test suite for Event Management API"""
    
    def __init__(self):
        self.client = APIClient()
        self.admin_client = APIClient()
        self.public_client = APIClient()
        self.setup_test_data()
        
    def setup_test_data(self):
        """Create test users and initial data"""
        print("🔧 Setting up test data...")
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type='ADMIN',
            is_staff=True,
            is_superuser=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_test',
            email='staff@test.com',
            password='testpass123',
            first_name='Staff',
            last_name='User',
            user_type='STAFF',
            is_staff=True
        )
        
        self.volunteer_user = User.objects.create_user(
            username='volunteer_test',
            email='volunteer@test.com',
            password='testpass123',
            first_name='Volunteer',
            last_name='User',
            user_type='VOLUNTEER'
        )
        
        # Authenticate clients
        self.admin_client.force_authenticate(user=self.admin_user)
        self.client.force_authenticate(user=self.staff_user)
        # public_client remains unauthenticated
        
        # Create test event
        self.test_event = Event.objects.create(
            name='Test ISG 2026',
            slug='test-isg-2026',
            short_name='Test ISG',
            event_type='INTERNATIONAL_GAMES',
            status='PLANNING',
            description='Test event for API testing',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            host_city='Dublin',
            host_country='Ireland',
            volunteer_target=1000,
            created_by=self.admin_user,
            is_public=True,
            is_active=True
        )
        
        # Create test venue
        self.test_venue = Venue.objects.create(
            event=self.test_event,
            name='Test Stadium',
            slug='test-stadium',
            short_name='Stadium',
            venue_type='STADIUM',
            status='PLANNING',
            description='Test venue for API testing',
            address_line_1='123 Test Street',
            city='Dublin',
            country='Ireland',
            total_capacity=50000,
            volunteer_capacity=500,
            spectator_capacity=49500,
            created_by=self.admin_user,
            is_active=True
        )
        
        print("✅ Test data setup complete")
    
    def test_event_list_api(self):
        """Test Event List API endpoint"""
        print("\n📋 Testing Event List API...")
        
        # Test public access
        response = self.public_client.get('/events/api/events/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'results' in data, "Expected paginated response with 'results'"
        assert len(data['results']) >= 1, "Expected at least 1 event"
        
        # Test authenticated access
        response = self.admin_client.get('/events/api/events/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Test filtering
        response = self.admin_client.get('/events/api/events/?status=PLANNING')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        for event in data['results']:
            assert event['status'] == 'PLANNING', f"Expected PLANNING status, got {event['status']}"
        
        # Test search
        response = self.admin_client.get('/events/api/events/?search=Test')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data['results']) >= 1, "Expected search results"
        
        # Test ordering
        response = self.admin_client.get('/events/api/events/?ordering=name')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print("✅ Event List API tests passed")
    
    def test_event_detail_api(self):
        """Test Event Detail API endpoint"""
        print("\n📄 Testing Event Detail API...")
        
        # Test public access
        response = self.public_client.get(f'/events/api/events/{self.test_event.id}/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['id'] == str(self.test_event.id), "Event ID mismatch"
        assert data['name'] == self.test_event.name, "Event name mismatch"
        
        # Test authenticated access with more details
        response = self.admin_client.get(f'/events/api/events/{self.test_event.id}/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify comprehensive data
        expected_fields = [
            'id', 'name', 'slug', 'event_type', 'status', 'description',
            'start_date', 'end_date', 'host_city', 'volunteer_target',
            'volunteer_progress', 'registration_status', 'venue_count'
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print("✅ Event Detail API tests passed")
    
    def test_event_create_api(self):
        """Test Event Create API endpoint"""
        print("\n➕ Testing Event Create API...")
        
        # Test unauthorized access
        response = self.public_client.post('/events/api/events/', {})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Test authorized creation
        event_data = {
            'name': 'New Test Event',
            'slug': 'new-test-event',
            'short_name': 'New Event',
            'event_type': 'NATIONAL_GAMES',
            'description': 'A new test event',
            'start_date': (date.today() + timedelta(days=60)).isoformat(),
            'end_date': (date.today() + timedelta(days=67)).isoformat(),
            'host_city': 'Cork',
            'host_country': 'Ireland',
            'volunteer_target': 500,
            'is_public': True
        }
        
        response = self.admin_client.post('/events/api/events/', event_data, format='json')
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
        data = response.json()
        assert data['name'] == event_data['name'], "Event name mismatch"
        assert data['slug'] == event_data['slug'], "Event slug mismatch"
        
        # Verify event was created in database
        new_event = Event.objects.get(id=data['id'])
        assert new_event.name == event_data['name'], "Database event name mismatch"
        
        print("✅ Event Create API tests passed")
    
    def test_event_update_api(self):
        """Test Event Update API endpoint"""
        print("\n✏️ Testing Event Update API...")
        
        # Test unauthorized access
        response = self.public_client.put(f'/events/api/events/{self.test_event.id}/', {})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Test authorized update
        update_data = {
            'name': 'Updated Test Event',
            'description': 'Updated description',
            'volunteer_target': 1200
        }
        
        response = self.admin_client.patch(f'/events/api/events/{self.test_event.id}/', update_data, format='json')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
        data = response.json()
        assert data['name'] == update_data['name'], "Event name not updated"
        assert data['volunteer_target'] == update_data['volunteer_target'], "Volunteer target not updated"
        
        # Verify database update
        self.test_event.refresh_from_db()
        assert self.test_event.name == update_data['name'], "Database not updated"
        
        print("✅ Event Update API tests passed")
    
    def test_event_configuration_api(self):
        """Test Event Configuration API endpoint"""
        print("\n⚙️ Testing Event Configuration API...")
        
        # Test get configuration
        response = self.admin_client.get(f'/events/api/events/{self.test_event.id}/configuration/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        expected_config_fields = [
            'event_configuration', 'volunteer_configuration',
            'venue_configuration', 'role_configuration'
        ]
        for field in expected_config_fields:
            assert field in data, f"Missing configuration field: {field}"
        
        # Test update configuration
        config_data = {
            'event_configuration': {
                'registration_enabled': True,
                'max_volunteers_per_role': 10
            },
            'volunteer_configuration': {
                'minimum_age': 16,
                'background_check_required': True
            }
        }
        
        response = self.admin_client.patch(f'/events/api/events/{self.test_event.id}/configuration/', config_data, format='json')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
        data = response.json()
        assert data['event_configuration']['registration_enabled'] == True, "Configuration not updated"
        
        print("✅ Event Configuration API tests passed")
    
    def test_event_status_api(self):
        """Test Event Status API endpoint"""
        print("\n🔄 Testing Event Status API...")
        
        # Test get status
        response = self.admin_client.get(f'/events/api/events/{self.test_event.id}/status/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'status' in data, "Missing status field"
        assert 'available_statuses' in data, "Missing available_statuses field"
        
        # Test update status
        status_data = {
            'status': 'REGISTRATION_OPEN',
            'status_change_notes': 'Opening registration for testing'
        }
        
        response = self.admin_client.put(f'/events/api/events/{self.test_event.id}/status/', status_data, format='json')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
        data = response.json()
        assert data['status'] == 'REGISTRATION_OPEN', "Status not updated"
        
        # Verify database update
        self.test_event.refresh_from_db()
        assert self.test_event.status == 'REGISTRATION_OPEN', "Database status not updated"
        
        print("✅ Event Status API tests passed")
    
    def test_event_stats_api(self):
        """Test Event Statistics API endpoint"""
        print("\n📊 Testing Event Statistics API...")
        
        response = self.admin_client.get(f'/events/api/events/{self.test_event.id}/stats/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        expected_stats_fields = [
            'volunteer_stats', 'venue_stats', 'role_stats', 'registration_stats'
        ]
        for field in expected_stats_fields:
            assert field in data, f"Missing stats field: {field}"
        
        # Verify volunteer stats structure
        volunteer_stats = data['volunteer_stats']
        assert 'total_assigned' in volunteer_stats, "Missing total_assigned in volunteer_stats"
        assert 'target' in volunteer_stats, "Missing target in volunteer_stats"
        assert 'progress_percentage' in volunteer_stats, "Missing progress_percentage in volunteer_stats"
        
        print("✅ Event Statistics API tests passed")
    
    def test_event_custom_actions(self):
        """Test Event custom action endpoints"""
        print("\n🎯 Testing Event Custom Actions...")
        
        # Test venues action
        response = self.admin_client.get(f'/events/api/events/{self.test_event.id}/venues/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data) >= 1, "Expected at least 1 venue"
        
        # Test featured events
        response = self.public_client.get('/events/api/events/featured/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Test upcoming events
        response = self.public_client.get('/events/api/events/upcoming/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data) >= 1, "Expected at least 1 upcoming event"
        
        # Test active events
        response = self.public_client.get('/events/api/events/active/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print("✅ Event Custom Actions tests passed")
    
    def test_venue_list_api(self):
        """Test Venue List API endpoint"""
        print("\n🏟️ Testing Venue List API...")
        
        # Test public access
        response = self.public_client.get('/events/api/venues/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'results' in data, "Expected paginated response"
        assert len(data['results']) >= 1, "Expected at least 1 venue"
        
        # Test filtering by event
        response = self.admin_client.get(f'/events/api/venues/?event={self.test_event.id}')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        for venue in data['results']:
            assert venue['event'] == str(self.test_event.id), "Event filter not working"
        
        # Test search
        response = self.admin_client.get('/events/api/venues/?search=Stadium')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print("✅ Venue List API tests passed")
    
    def test_venue_detail_api(self):
        """Test Venue Detail API endpoint"""
        print("\n🏟️ Testing Venue Detail API...")
        
        response = self.public_client.get(f'/events/api/venues/{self.test_venue.id}/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['id'] == str(self.test_venue.id), "Venue ID mismatch"
        assert data['name'] == self.test_venue.name, "Venue name mismatch"
        
        # Verify comprehensive data
        expected_fields = [
            'id', 'name', 'venue_type', 'status', 'address_line_1',
            'city', 'total_capacity', 'volunteer_capacity', 'accessibility_level'
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print("✅ Venue Detail API tests passed")
    
    def test_venue_create_api(self):
        """Test Venue Create API endpoint"""
        print("\n➕ Testing Venue Create API...")
        
        # Test unauthorized access
        response = self.public_client.post('/events/api/venues/', {})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Test authorized creation
        venue_data = {
            'event': str(self.test_event.id),
            'name': 'New Test Venue',
            'slug': 'new-test-venue',
            'venue_type': 'GYMNASIUM',
            'address_line_1': '456 New Street',
            'city': 'Cork',
            'country': 'Ireland',
            'total_capacity': 2000,
            'volunteer_capacity': 50,
            'spectator_capacity': 1950,
            'is_active': True
        }
        
        response = self.admin_client.post('/events/api/venues/', venue_data, format='json')
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
        data = response.json()
        assert data['name'] == venue_data['name'], "Venue name mismatch"
        
        print("✅ Venue Create API tests passed")
    
    def test_venue_capacity_api(self):
        """Test Venue Capacity API endpoint"""
        print("\n📊 Testing Venue Capacity API...")
        
        response = self.public_client.get(f'/events/api/venues/{self.test_venue.id}/capacity/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        expected_capacity_fields = [
            'venue_id', 'venue_name', 'total_capacity', 'volunteer_capacity',
            'spectator_capacity', 'assigned_volunteers', 'available_capacity',
            'utilization_percentage', 'is_at_capacity'
        ]
        for field in expected_capacity_fields:
            assert field in data, f"Missing capacity field: {field}"
        
        assert data['total_capacity'] == self.test_venue.total_capacity, "Total capacity mismatch"
        assert data['volunteer_capacity'] == self.test_venue.volunteer_capacity, "Volunteer capacity mismatch"
        
        print("✅ Venue Capacity API tests passed")
    
    def test_venue_custom_actions(self):
        """Test Venue custom action endpoints"""
        print("\n🎯 Testing Venue Custom Actions...")
        
        # Test by_event action
        response = self.public_client.get(f'/events/api/venues/by_event/?event_id={self.test_event.id}')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data) >= 1, "Expected at least 1 venue for event"
        
        # Test accessible venues
        response = self.public_client.get('/events/api/venues/accessible/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print("✅ Venue Custom Actions tests passed")
    
    def test_bulk_operations_api(self):
        """Test Bulk Operations API endpoint"""
        print("\n📦 Testing Bulk Operations API...")
        
        # Create additional test event for bulk operations
        test_event_2 = Event.objects.create(
            name='Bulk Test Event',
            slug='bulk-test-event',
            event_type='LOCAL_EVENT',
            start_date=date.today() + timedelta(days=90),
            end_date=date.today() + timedelta(days=97),
            host_city='Galway',
            volunteer_target=200,
            created_by=self.admin_user,
            is_active=False
        )
        
        # Test bulk activation
        bulk_data = {
            'operation': 'activate',
            'event_ids': [str(test_event_2.id)],
            'data': {}
        }
        
        response = self.admin_client.post('/events/api/events/bulk/', bulk_data, format='json')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
        data = response.json()
        assert data['operation'] == 'activate', "Operation mismatch"
        assert data['processed'] == 1, "Processed count mismatch"
        
        # Verify activation
        test_event_2.refresh_from_db()
        assert test_event_2.is_active == True, "Event not activated"
        
        print("✅ Bulk Operations API tests passed")
    
    def test_permissions_and_security(self):
        """Test API permissions and security"""
        print("\n🔒 Testing Permissions and Security...")
        
        # Test volunteer user cannot create events
        volunteer_client = APIClient()
        volunteer_client.force_authenticate(user=self.volunteer_user)
        
        event_data = {
            'name': 'Unauthorized Event',
            'slug': 'unauthorized-event',
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=7)).isoformat()
        }
        
        response = volunteer_client.post('/events/api/events/', event_data, format='json')
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        # Test volunteer user cannot update events
        response = volunteer_client.patch(f'/events/api/events/{self.test_event.id}/', {'name': 'Hacked'}, format='json')
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        # Test volunteer user cannot delete events
        response = volunteer_client.delete(f'/events/api/events/{self.test_event.id}/')
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        # Test volunteer user can read public events
        response = volunteer_client.get('/events/api/events/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print("✅ Permissions and Security tests passed")
    
    def run_all_tests(self):
        """Run all test methods"""
        print("🚀 Starting Event Management API Tests")
        print("=" * 50)
        
        test_methods = [
            self.test_event_list_api,
            self.test_event_detail_api,
            self.test_event_create_api,
            self.test_event_update_api,
            self.test_event_configuration_api,
            self.test_event_status_api,
            self.test_event_stats_api,
            self.test_event_custom_actions,
            self.test_venue_list_api,
            self.test_venue_detail_api,
            self.test_venue_create_api,
            self.test_venue_capacity_api,
            self.test_venue_custom_actions,
            self.test_bulk_operations_api,
            self.test_permissions_and_security
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                test_method()
                passed += 1
            except Exception as e:
                print(f"❌ {test_method.__name__} FAILED: {str(e)}")
                failed += 1
        
        print("\n" + "=" * 50)
        print(f"🏁 Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All Event Management API tests passed!")
        else:
            print(f"⚠️ {failed} tests failed. Please review the errors above.")
        
        return failed == 0


def main():
    """Main function to run tests"""
    tester = EventManagementAPITest()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main()) 