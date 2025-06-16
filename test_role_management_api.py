#!/usr/bin/env python
"""
Test script for Role Management API endpoints.
Tests all CRUD operations, capacity tracking, and custom actions.

Usage:
    python test_role_management_api.py
"""

import os
import sys
import django
import json
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.contrib.auth import get_user_model
from events.models import Event, Venue, Role
from django.test import Client

User = get_user_model()

class RoleManagementAPITester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        
        # Create test data
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create test data for role management testing"""
        print("Setting up test data...")
        
        # Create test user with unique email and username
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_email = f'test-role-api-{timestamp}@example.com'
        test_username = f'test-role-api-{timestamp}'
        
        self.test_user, created = User.objects.get_or_create(
            email=test_email,
            defaults={
                'username': test_username,
                'first_name': 'Test',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            self.test_user.set_password('testpass123')
            self.test_user.save()
        
        # Create test event
        event_slug = f'test-event-role-api-{timestamp}'
        self.test_event, created = Event.objects.get_or_create(
            slug=event_slug,
            defaults={
                'name': 'Test Event for Role API',
                'start_date': datetime.now().date(),
                'end_date': (datetime.now() + timedelta(days=7)).date(),
                'host_city': 'Dublin',
                'volunteer_target': 100,
                'created_by': self.test_user
            }
        )
        
        # Create test venue
        venue_slug = f'test-venue-role-api-{timestamp}'
        self.test_venue, created = Venue.objects.get_or_create(
            event=self.test_event,
            slug=venue_slug,
            defaults={
                'name': 'Test Venue for Role API',
                'address_line_1': '123 Test Street',
                'city': 'Dublin',
                'total_capacity': 1000,
                'volunteer_capacity': 50,
                'created_by': self.test_user
            }
        )
        
        # Login for authenticated requests
        self.client.login(email=test_email, password='testpass123')
        
        print("✓ Test data setup complete")
    
    def log_test(self, test_name, success, details=None):
        """Log test results"""
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def test_role_list_api(self):
        """Test role list endpoint"""
        try:
            response = self.client.get('/events/api/roles/')
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Retrieved {len(data)} roles"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("Role List API", success, details)
            return response.json() if success else None
            
        except Exception as e:
            self.log_test("Role List API", False, str(e))
            return None
    
    def test_role_create_api(self):
        """Test role creation endpoint"""
        try:
            role_data = {
                'event': str(self.test_event.id),
                'venue': str(self.test_venue.id),
                'name': 'Test Swimming Official',
                'slug': 'test-swimming-official',
                'role_type': 'SPORT_OFFICIAL',
                'description': 'Official for swimming events',
                'summary': 'Swimming competition official',
                'minimum_age': 18,
                'total_positions': 5,
                'minimum_volunteers': 2,
                'skill_level_required': 'INTERMEDIATE',
                'commitment_level': 'DAILY',
                'estimated_hours_per_day': 8.0,
                'training_required': True,
                'requires_garda_vetting': True,
                'is_public': True,
                'priority_level': 3
            }
            
            response = self.client.post(
                '/events/api/roles/',
                data=json.dumps(role_data),
                content_type='application/json'
            )
            
            success = response.status_code == 201
            
            if success:
                data = response.json()
                self.test_role_id = data['id']
                details = f"Created role: {data['name']} (ID: {self.test_role_id})"
            else:
                details = f"Status: {response.status_code}, Response: {response.content.decode()}"
            
            self.log_test("Role Create API", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test("Role Create API", False, str(e))
            return None
    
    def test_role_detail_api(self):
        """Test role detail endpoint"""
        if not hasattr(self, 'test_role_id'):
            self.log_test("Role Detail API", False, "No test role ID available")
            return None
        
        try:
            response = self.client.get(f'/events/api/roles/{self.test_role_id}/')
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Retrieved role: {data['name']}"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("Role Detail API", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test("Role Detail API", False, str(e))
            return None
    
    def test_role_capacity_api(self):
        """Test role capacity tracking endpoint"""
        if not hasattr(self, 'test_role_id'):
            self.log_test("Role Capacity API", False, "No test role ID available")
            return None
        
        try:
            response = self.client.get(f'/events/api/roles/{self.test_role_id}/capacity/')
            success = response.status_code == 200
            
            if success:
                data = response.json()
                capacity_info = data.get('capacity_info', {})
                details = f"Capacity: {capacity_info.get('filled_positions', 0)}/{capacity_info.get('total_positions', 0)}"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("Role Capacity API", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test("Role Capacity API", False, str(e))
            return None
    
    def run_all_tests(self):
        """Run all role management API tests"""
        print("=" * 60)
        print("ROLE MANAGEMENT API TEST SUITE")
        print("=" * 60)
        
        # Test sequence
        self.test_role_list_api()
        self.test_role_create_api()
        self.test_role_detail_api()
        self.test_role_capacity_api()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        return passed_tests == total_tests

def main():
    """Main test execution"""
    tester = RoleManagementAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All role management API tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == '__main__':
    main() 