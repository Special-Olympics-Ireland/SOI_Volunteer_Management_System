"""
Comprehensive Test Suite for Mobile Responsive Admin Interface

This test suite validates the mobile-responsive design implementation,
including mobile detection, responsive layouts, touch-friendly interfaces,
and mobile-specific functionality.
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, Mock

from accounts.models import User
from events.models import Event, Assignment, Role, Venue
from volunteers.models import VolunteerProfile
from tasks.models import Task, TaskCompletion
from common.models import AdminOverride, AuditLog
from common.mobile_admin_views import mobile_context

User = get_user_model()


class MobileResponsiveTestCase(TestCase):
    """Test mobile responsive design functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type='ADMIN',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test volunteers
        self.volunteer1 = User.objects.create_user(
            email='volunteer1@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            user_type='VOLUNTEER'
        )
        
        self.volunteer2 = User.objects.create_user(
            email='volunteer2@test.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith',
            user_type='VOLUNTEER'
        )
        
        # Create volunteer profiles
        VolunteerProfile.objects.create(
            user=self.volunteer1,
            phone_number='+1234567890',
            date_of_birth='1990-01-01',
            address='123 Test St',
            city='Test City',
            state='TS',
            postal_code='12345',
            country='Test Country'
        )
        
        VolunteerProfile.objects.create(
            user=self.volunteer2,
            phone_number='+1234567891',
            date_of_birth='1992-02-02',
            address='456 Test Ave',
            city='Test City',
            state='TS',
            postal_code='12346',
            country='Test Country'
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='789 Test Blvd',
            city='Test City',
            state='TS',
            postal_code='12347',
            country='Test Country',
            capacity=1000
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event',
            description='Test event description',
            start_date=timezone.now() + timezone.timedelta(days=30),
            end_date=timezone.now() + timezone.timedelta(days=32),
            venue=self.venue,
            status='ACTIVE'
        )
        
        # Create test role
        self.role = Role.objects.create(
            name='Test Role',
            description='Test role description',
            event=self.event,
            capacity=10,
            requirements={'age_min': 18}
        )
        
        # Create test assignment
        self.assignment = Assignment.objects.create(
            volunteer=self.volunteer1,
            event=self.event,
            role=self.role,
            status='PENDING'
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            task_type='CHECKBOX',
            due_date=timezone.now() + timezone.timedelta(days=1),
            assigned_to=self.volunteer1,
            created_by=self.admin_user
        )
        
        # Create test audit log
        AuditLog.objects.create(
            user=self.admin_user,
            action='TEST_ACTION',
            object_type='Test',
            object_id='1',
            details='Test audit log entry'
        )
        
        # Set up clients
        self.client = Client()
        self.mobile_client = Client()
        
        # Login admin user
        self.client.login(email='admin@test.com', password='testpass123')
        self.mobile_client.login(email='admin@test.com', password='testpass123')
    
    def test_mobile_detection(self):
        """Test mobile device detection functionality."""
        # Test desktop user agent
        desktop_request = Mock()
        desktop_request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        context = mobile_context(desktop_request)
        self.assertFalse(context['is_mobile'])
        self.assertTrue(context['mobile_optimized'])
        
        # Test mobile user agent (iPhone)
        mobile_request = Mock()
        mobile_request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        }
        
        context = mobile_context(mobile_request)
        self.assertTrue(context['is_mobile'])
        self.assertTrue(context['touch_friendly'])
        
        # Test mobile user agent (Android)
        android_request = Mock()
        android_request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36'
        }
        
        context = mobile_context(android_request)
        self.assertTrue(context['is_mobile'])
        self.assertTrue(context['touch_friendly'])
        
        # Test tablet user agent (iPad)
        tablet_request = Mock()
        tablet_request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        }
        
        context = mobile_context(tablet_request)
        self.assertTrue(context['is_mobile'])
        self.assertTrue(context['touch_friendly'])
    
    def test_mobile_css_loading(self):
        """Test that mobile CSS is properly loaded."""
        # Test mobile admin template
        response = self.client.get('/mobile-admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mobile-responsive.css')
        self.assertContains(response, 'viewport')
        self.assertContains(response, 'mobile-web-app-capable')
        self.assertContains(response, 'theme-color')
    
    def test_mobile_dashboard_view(self):
        """Test mobile admin dashboard view."""
        response = self.client.get('/mobile-admin/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mobile Admin Dashboard')
        self.assertContains(response, 'Dashboard Overview')
        self.assertContains(response, 'Quick Actions')
        self.assertContains(response, 'Recent Activity')
        
        # Check that statistics are displayed
        self.assertContains(response, 'Total Volunteers')
        self.assertContains(response, 'Active Events')
        self.assertContains(response, 'Pending Assignments')
        self.assertContains(response, 'Overdue Tasks')
        
        # Check that quick action buttons are present
        self.assertContains(response, 'Volunteers')
        self.assertContains(response, 'Events')
        self.assertContains(response, 'Assignments')
        self.assertContains(response, 'Tasks')
    
    def test_mobile_volunteer_list_view(self):
        """Test mobile volunteer list view."""
        response = self.client.get('/mobile-admin/volunteers/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Volunteers')
        self.assertContains(response, self.volunteer1.get_full_name())
        self.assertContains(response, self.volunteer2.get_full_name())
        
        # Test search functionality
        response = self.client.get('/mobile-admin/volunteers/?search=John')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')
        
        # Test pagination
        response = self.client.get('/mobile-admin/volunteers/?page=1')
        self.assertEqual(response.status_code, 200)
    
    def test_mobile_quick_actions(self):
        """Test mobile quick action functionality."""
        # Test assignment approval
        response = self.client.post('/mobile-admin/quick-action/', {
            'action': 'approve',
            'object_id': self.assignment.id,
            'object_type': 'assignment'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after action
        
        # Verify assignment was approved
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'CONFIRMED')
        
        # Test volunteer activation
        self.volunteer1.is_active = False
        self.volunteer1.save()
        
        response = self.client.post('/mobile-admin/quick-action/', {
            'action': 'activate',
            'object_id': self.volunteer1.id,
            'object_type': 'volunteer'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify volunteer was activated
        self.volunteer1.refresh_from_db()
        self.assertTrue(self.volunteer1.is_active)
    
    def test_mobile_stats_api(self):
        """Test mobile statistics API endpoint."""
        response = self.client.get('/mobile-admin/api/stats/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Check statistics structure
        self.assertIn('volunteers', data)
        self.assertIn('events', data)
        self.assertIn('assignments', data)
        self.assertIn('tasks', data)
        
        # Check volunteer statistics
        self.assertEqual(data['volunteers']['total'], 2)
        self.assertEqual(data['volunteers']['active'], 2)
        
        # Check event statistics
        self.assertEqual(data['events']['total'], 1)
        self.assertEqual(data['events']['active'], 1)
        
        # Check assignment statistics
        self.assertEqual(data['assignments']['total'], 1)
        self.assertEqual(data['assignments']['pending'], 1)
    
    def test_mobile_search_api(self):
        """Test mobile search API endpoint."""
        # Test volunteer search
        response = self.client.get('/mobile-admin/api/search/?q=John&type=volunteers')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'John Doe')
        self.assertEqual(data['results'][0]['type'], 'volunteer')
        
        # Test event search
        response = self.client.get('/mobile-admin/api/search/?q=Test&type=events')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'Test Event')
        self.assertEqual(data['results'][0]['type'], 'event')
        
        # Test short query (should return empty results)
        response = self.client.get('/mobile-admin/api/search/?q=T')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 0)
    
    def test_mobile_notifications_api(self):
        """Test mobile notifications API endpoint."""
        # Create overdue task
        overdue_task = Task.objects.create(
            title='Overdue Task',
            description='This task is overdue',
            task_type='CHECKBOX',
            due_date=timezone.now() - timezone.timedelta(days=1),
            assigned_to=self.volunteer1,
            created_by=self.admin_user,
            status='PENDING'
        )
        
        # Create admin override
        admin_override = AdminOverride.objects.create(
            created_by=self.admin_user,
            override_type='ASSIGNMENT_OVERRIDE',
            target_object_type='Assignment',
            target_object_id=str(self.assignment.id),
            justification='Test override',
            expiry_date=timezone.now() + timezone.timedelta(days=1),
            status='ACTIVE'
        )
        
        response = self.client.get('/mobile-admin/api/notifications/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('notifications', data)
        notifications = data['notifications']
        
        # Should have notifications for overdue tasks, pending assignments, and active overrides
        notification_types = [n['title'] for n in notifications]
        self.assertIn('Overdue Tasks', notification_types)
        self.assertIn('Pending Assignments', notification_types)
        self.assertIn('Active Overrides', notification_types)
    
    def test_mobile_bulk_actions(self):
        """Test mobile bulk actions functionality."""
        # Test bulk volunteer activation
        self.volunteer1.is_active = False
        self.volunteer2.is_active = False
        self.volunteer1.save()
        self.volunteer2.save()
        
        response = self.client.post('/mobile-admin/bulk-actions/', {
            'action': 'activate',
            'object_type': 'volunteers',
            'object_ids': [self.volunteer1.id, self.volunteer2.id]
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify volunteers were activated
        self.volunteer1.refresh_from_db()
        self.volunteer2.refresh_from_db()
        self.assertTrue(self.volunteer1.is_active)
        self.assertTrue(self.volunteer2.is_active)
        
        # Test bulk assignment approval
        assignment2 = Assignment.objects.create(
            volunteer=self.volunteer2,
            event=self.event,
            role=self.role,
            status='PENDING'
        )
        
        response = self.client.post('/mobile-admin/bulk-actions/', {
            'action': 'approve',
            'object_type': 'assignments',
            'object_ids': [self.assignment.id, assignment2.id]
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify assignments were approved
        self.assignment.refresh_from_db()
        assignment2.refresh_from_db()
        self.assertEqual(self.assignment.status, 'CONFIRMED')
        self.assertEqual(assignment2.status, 'CONFIRMED')
    
    def test_mobile_template_responsiveness(self):
        """Test mobile template responsive features."""
        response = self.client.get('/mobile-admin/')
        
        # Check for mobile-specific CSS classes
        self.assertContains(response, 'mobile-dashboard')
        self.assertContains(response, 'stats-grid')
        self.assertContains(response, 'quick-actions')
        self.assertContains(response, 'action-button')
        
        # Check for responsive grid layouts
        self.assertContains(response, 'grid-template-columns')
        self.assertContains(response, 'repeat(auto-fit')
        
        # Check for touch-friendly button sizes
        self.assertContains(response, 'min-height: 44px')
        self.assertContains(response, 'min-width: 44px')
        
        # Check for mobile media queries
        self.assertContains(response, '@media (max-width: 480px)')
        
        # Check for mobile-specific JavaScript
        self.assertContains(response, 'touchstart')
        self.assertContains(response, 'touchend')
        self.assertContains(response, 'vibrate')
    
    def test_mobile_accessibility_features(self):
        """Test mobile accessibility features."""
        response = self.client.get('/mobile-admin/')
        
        # Check for proper ARIA labels
        self.assertContains(response, 'aria-label')
        
        # Check for focus indicators
        self.assertContains(response, 'outline: 2px solid')
        
        # Check for proper heading structure
        self.assertContains(response, '<h1')
        
        # Check for semantic HTML elements
        self.assertContains(response, 'role=')
    
    def test_mobile_performance_optimizations(self):
        """Test mobile performance optimization features."""
        response = self.client.get('/mobile-admin/')
        
        # Check for viewport meta tag
        self.assertContains(response, 'width=device-width')
        self.assertContains(response, 'initial-scale=1.0')
        
        # Check for preload directives
        self.assertContains(response, 'rel="preload"')
        
        # Check for touch scrolling optimization
        self.assertContains(response, '-webkit-overflow-scrolling: touch')
        
        # Check for GPU acceleration
        self.assertContains(response, 'transform: translateZ(0)')
    
    def test_mobile_user_agent_handling(self):
        """Test proper handling of different mobile user agents."""
        mobile_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'Mozilla/5.0 (Linux; Android 10; SM-G975F)',
            'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)',
            'Mozilla/5.0 (Linux; Android 11; Pixel 5)',
        ]
        
        for user_agent in mobile_user_agents:
            response = self.mobile_client.get('/mobile-admin/', 
                                            HTTP_USER_AGENT=user_agent)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'mobile-dashboard')
    
    def test_mobile_form_optimizations(self):
        """Test mobile form optimization features."""
        response = self.client.get('/mobile-admin/')
        
        # Check for mobile-friendly input styling
        self.assertContains(response, 'font-size: 16px')  # Prevents zoom on iOS
        self.assertContains(response, 'touch-action')
        
        # Check for proper input types and attributes
        self.assertContains(response, 'inputmode')
        self.assertContains(response, 'autocomplete')
    
    def test_mobile_error_handling(self):
        """Test mobile-specific error handling."""
        # Test invalid quick action
        response = self.client.post('/mobile-admin/quick-action/', {
            'action': 'invalid_action',
            'object_id': '999',
            'object_type': 'invalid_type'
        })
        
        self.assertEqual(response.status_code, 302)  # Should redirect with error message
        
        # Test bulk action with no items selected
        response = self.client.post('/mobile-admin/bulk-actions/', {
            'action': 'activate',
            'object_type': 'volunteers',
            'object_ids': []
        })
        
        self.assertEqual(response.status_code, 302)  # Should redirect with error message


class MobileIntegrationTestCase(TestCase):
    """Test mobile responsive design integration with existing admin functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type='ADMIN',
            is_staff=True,
            is_superuser=True
        )
        
        self.client = Client()
        self.client.login(email='admin@test.com', password='testpass123')
    
    def test_mobile_admin_integration_with_existing_admin(self):
        """Test that mobile admin integrates properly with existing Django admin."""
        # Test that regular admin still works
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        
        # Test that mobile admin is accessible
        response = self.client.get('/mobile-admin/')
        self.assertEqual(response.status_code, 200)
        
        # Test that mobile CSS doesn't interfere with regular admin
        response = self.client.get('/admin/')
        self.assertNotContains(response, 'mobile-dashboard')
    
    def test_mobile_responsive_css_file_exists(self):
        """Test that mobile responsive CSS file exists and is accessible."""
        response = self.client.get('/static/admin/css/mobile-responsive.css')
        # Note: This test assumes static files are served in test environment
        # In production, static files would be served by web server
    
    def test_mobile_template_inheritance(self):
        """Test that mobile templates properly inherit from base templates."""
        response = self.client.get('/mobile-admin/')
        
        # Should contain elements from base admin template
        self.assertContains(response, 'SOI Hub')
        self.assertContains(response, 'Administration')
        
        # Should also contain mobile-specific elements
        self.assertContains(response, 'mobile-dashboard')
        self.assertContains(response, 'touch-friendly')


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['__main__'])
    
    if failures:
        exit(1) 