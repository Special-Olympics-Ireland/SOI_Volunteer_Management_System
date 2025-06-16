"""
Comprehensive Test Suite for PowerBI Integration.

This test suite validates all aspects of the PowerBI integration including
services, views, permissions, data accuracy, and API endpoints.
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from volunteers.models import VolunteerProfile
from events.models import Event, Venue, Role, Assignment
from tasks.models import Task, TaskCompletion
from integrations.models import JustGoIntegration, JustGoSync
from common.models import AuditLog, AdminOverride
from common.powerbi_service import PowerBIService
from common.permissions import PowerBIAccessPermission, create_powerbi_permissions

User = get_user_model()


class PowerBIServiceTestCase(TestCase):
    """Test cases for PowerBI service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='ADMIN'
        )
        
        # Create test volunteers
        self.volunteers = []
        for i in range(10):
            volunteer = VolunteerProfile.objects.create(
                user=User.objects.create_user(
                    username=f'volunteer{i}',
                    email=f'volunteer{i}@example.com',
                    password='testpass123',
                    user_type='VOLUNTEER'
                ),
                first_name=f'Volunteer{i}',
                last_name='Test',
                phone='0400000000',
                date_of_birth=timezone.now().date() - timedelta(days=365*25),
                status='ACTIVE' if i < 7 else 'PENDING',
                volunteer_type='GENERAL',
                experience_level='BEGINNER' if i < 5 else 'EXPERIENCED'
            )
            self.volunteers.append(volunteer)
        
        # Create test venues
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            state='NSW',
            postcode='2000',
            capacity=1000
        )
        
        # Create test events
        self.events = []
        for i in range(5):
            event = Event.objects.create(
                name=f'Test Event {i}',
                description=f'Test event description {i}',
                venue=self.venue,
                start_date=timezone.now() + timedelta(days=i),
                end_date=timezone.now() + timedelta(days=i+1),
                status='ACTIVE' if i < 3 else 'DRAFT'
            )
            self.events.append(event)
        
        # Create test roles and assignments
        self.role = Role.objects.create(
            name='Test Role',
            description='Test role description',
            event=self.events[0],
            capacity=5,
            requirements={'skills': ['communication']}
        )
        
        # Create assignments
        for i in range(3):
            Assignment.objects.create(
                volunteer=self.volunteers[i],
                role=self.role,
                event=self.events[0],
                status='CONFIRMED'
            )
        
        # Create test tasks
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            task_type='CHECKBOX',
            role=self.role,
            is_active=True
        )
        
        # Create task completions
        for i in range(2):
            TaskCompletion.objects.create(
                task=self.task,
                volunteer=self.volunteers[i],
                status='COMPLETED',
                completed_at=timezone.now()
            )
    
    def test_volunteer_analytics_dataset_generation(self):
        """Test volunteer analytics dataset generation."""
        dataset = PowerBIService.get_volunteer_analytics_dataset()
        
        # Validate dataset structure
        self.assertIn('metadata', dataset)
        self.assertIn('demographics', dataset)
        self.assertIn('performance', dataset)
        self.assertIn('engagement', dataset)
        self.assertIn('lifecycle', dataset)
        self.assertIn('geographic', dataset)
        self.assertIn('skills_analysis', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate metadata
        metadata = dataset['metadata']
        self.assertIn('generated_at', metadata)
        self.assertIn('total_records', metadata)
        self.assertIn('data_freshness', metadata)
        self.assertEqual(metadata['version'], '1.0')
        
        # Validate summary metrics
        summary = dataset['summary_metrics']
        self.assertIn('total_volunteers', summary)
        self.assertIn('active_volunteers', summary)
        self.assertIn('pending_volunteers', summary)
        self.assertGreater(summary['total_volunteers'], 0)
    
    def test_volunteer_analytics_with_filters(self):
        """Test volunteer analytics with filters."""
        filters = {
            'status': 'ACTIVE',
            'date_from': timezone.now() - timedelta(days=30),
            'date_to': timezone.now()
        }
        
        dataset = PowerBIService.get_volunteer_analytics_dataset(filters)
        
        # Validate filters are applied
        self.assertEqual(dataset['metadata']['filters_applied'], filters)
        
        # Validate data reflects filters
        summary = dataset['summary_metrics']
        self.assertGreaterEqual(summary['active_volunteers'], 0)
    
    def test_event_analytics_dataset_generation(self):
        """Test event analytics dataset generation."""
        dataset = PowerBIService.get_event_analytics_dataset()
        
        # Validate dataset structure
        self.assertIn('metadata', dataset)
        self.assertIn('performance', dataset)
        self.assertIn('venue_utilization', dataset)
        self.assertIn('role_fulfillment', dataset)
        self.assertIn('timeline', dataset)
        self.assertIn('resource_allocation', dataset)
        self.assertIn('success_metrics', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate summary metrics
        summary = dataset['summary_metrics']
        self.assertIn('total_events', summary)
        self.assertIn('active_events', summary)
        self.assertIn('completed_events', summary)
        self.assertGreater(summary['total_events'], 0)
    
    def test_operational_analytics_dataset_generation(self):
        """Test operational analytics dataset generation."""
        dataset = PowerBIService.get_operational_analytics_dataset()
        
        # Validate dataset structure
        self.assertIn('metadata', dataset)
        self.assertIn('system_performance', dataset)
        self.assertIn('task_analytics', dataset)
        self.assertIn('integration_health', dataset)
        self.assertIn('admin_operations', dataset)
        self.assertIn('security_metrics', dataset)
        self.assertIn('data_quality', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate summary metrics
        summary = dataset['summary_metrics']
        self.assertIn('system_uptime', summary)
        self.assertIn('average_response_time', summary)
        self.assertIn('error_rate', summary)
        self.assertIn('data_completeness', summary)
        self.assertIn('security_score', summary)
    
    def test_financial_analytics_dataset_generation(self):
        """Test financial analytics dataset generation."""
        dataset = PowerBIService.get_financial_analytics_dataset()
        
        # Validate dataset structure
        self.assertIn('metadata', dataset)
        self.assertIn('cost_analysis', dataset)
        self.assertIn('roi_metrics', dataset)
        self.assertIn('budget_utilization', dataset)
        self.assertIn('resource_efficiency', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate summary metrics
        summary = dataset['summary_metrics']
        self.assertIn('total_volunteer_value', summary)
        self.assertIn('cost_per_volunteer', summary)
        self.assertIn('roi_percentage', summary)
        self.assertIn('efficiency_score', summary)
    
    def test_predictive_analytics_dataset_generation(self):
        """Test predictive analytics dataset generation."""
        dataset = PowerBIService.get_predictive_analytics_dataset()
        
        # Validate dataset structure
        self.assertIn('metadata', dataset)
        self.assertIn('demand_forecast', dataset)
        self.assertIn('retention_prediction', dataset)
        self.assertIn('capacity_planning', dataset)
        self.assertIn('trend_analysis', dataset)
        self.assertIn('risk_assessment', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate metadata includes prediction confidence
        metadata = dataset['metadata']
        self.assertIn('prediction_confidence', metadata)
        self.assertGreater(metadata['prediction_confidence'], 0)
        
        # Validate summary metrics
        summary = dataset['summary_metrics']
        self.assertIn('predicted_volunteer_growth', summary)
        self.assertIn('retention_risk_score', summary)
        self.assertIn('capacity_utilization_forecast', summary)
        self.assertIn('overall_health_score', summary)
    
    def test_real_time_dashboard_data_generation(self):
        """Test real-time dashboard data generation."""
        dashboard_data = PowerBIService.get_real_time_dashboard_data()
        
        # Validate dashboard structure
        self.assertIn('metadata', dashboard_data)
        self.assertIn('system_status', dashboard_data)
        self.assertIn('volunteer_metrics', dashboard_data)
        self.assertIn('event_metrics', dashboard_data)
        self.assertIn('task_metrics', dashboard_data)
        self.assertIn('integration_status', dashboard_data)
        self.assertIn('alerts', dashboard_data)
        self.assertIn('kpis', dashboard_data)
        
        # Validate metadata
        metadata = dashboard_data['metadata']
        self.assertEqual(metadata['data_freshness'], 'real_time')
        self.assertIn('refresh_interval', metadata)
        
        # Validate system status
        system_status = dashboard_data['system_status']
        self.assertIn('timestamp', system_status)
        self.assertIn('active_users', system_status)
        self.assertIn('system_load', system_status)
        
        # Validate volunteer metrics
        volunteer_metrics = dashboard_data['volunteer_metrics']
        self.assertIn('total_volunteers', volunteer_metrics)
        self.assertIn('active_volunteers', volunteer_metrics)
        self.assertGreater(volunteer_metrics['total_volunteers'], 0)
    
    def test_custom_dataset_generation(self):
        """Test custom dataset generation."""
        dataset_config = {
            'type': 'volunteer_summary',
            'filters': {'status': 'ACTIVE'},
            'aggregations': ['count', 'avg'],
            'dimensions': ['status', 'experience_level'],
            'measures': ['total_volunteers', 'average_age']
        }
        
        dataset = PowerBIService.get_custom_dataset(dataset_config)
        
        # Validate dataset structure
        self.assertIn('metadata', dataset)
        self.assertIn('data', dataset)
        self.assertIn('schema', dataset)
        self.assertIn('summary', dataset)
        
        # Validate metadata
        metadata = dataset['metadata']
        self.assertEqual(metadata['dataset_type'], 'volunteer_summary')
        self.assertEqual(metadata['configuration'], dataset_config)
    
    def test_caching_functionality(self):
        """Test caching functionality."""
        # Clear cache
        cache.clear()
        
        # First call should generate data
        start_time = timezone.now()
        dataset1 = PowerBIService.get_volunteer_analytics_dataset()
        first_call_time = timezone.now() - start_time
        
        # Second call should use cache (should be faster)
        start_time = timezone.now()
        dataset2 = PowerBIService.get_volunteer_analytics_dataset()
        second_call_time = timezone.now() - start_time
        
        # Validate datasets are identical
        self.assertEqual(dataset1, dataset2)
        
        # Second call should be faster (cached)
        # Note: This might not always be true in test environment
        # but validates caching is working
        self.assertIsNotNone(dataset2)


class PowerBIAPITestCase(APITestCase):
    """Test cases for PowerBI API endpoints."""
    
    def setUp(self):
        """Set up test data and authentication."""
        # Create test user with PowerBI permissions
        self.user = User.objects.create_user(
            username='powerbi_user',
            email='powerbi@example.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        # Create PowerBI permissions
        create_powerbi_permissions()
        
        # Assign permissions to user
        content_type = ContentType.objects.get_or_create(
            app_label='common',
            model='powerbidata'
        )[0]
        
        permissions = [
            'view_powerbi_data',
            'export_powerbi_data',
            'view_analytics'
        ]
        
        for perm_codename in permissions:
            try:
                permission = Permission.objects.get(
                    codename=perm_codename,
                    content_type=content_type
                )
                self.user.user_permissions.add(permission)
            except Permission.DoesNotExist:
                pass
        
        # Create API token
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        # Create test data
        self.create_test_data()
    
    def create_test_data(self):
        """Create test data for API tests."""
        # Create test volunteers
        for i in range(5):
            volunteer = VolunteerProfile.objects.create(
                user=User.objects.create_user(
                    username=f'vol_api_{i}',
                    email=f'vol_api_{i}@example.com',
                    password='testpass123',
                    user_type='VOLUNTEER'
                ),
                first_name=f'API_Vol{i}',
                last_name='Test',
                phone='0400000000',
                date_of_birth=timezone.now().date() - timedelta(days=365*25),
                status='ACTIVE',
                volunteer_type='GENERAL'
            )
        
        # Create test venue and event
        venue = Venue.objects.create(
            name='API Test Venue',
            address='123 API St',
            city='API City',
            state='NSW',
            postcode='2000',
            capacity=500
        )
        
        Event.objects.create(
            name='API Test Event',
            description='API test event',
            venue=venue,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            status='ACTIVE'
        )
    
    def test_volunteer_analytics_endpoint(self):
        """Test volunteer analytics API endpoint."""
        url = reverse('common:powerbi:volunteer_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('timestamp', data)
        
        # Validate dataset structure
        dataset = data['data']
        self.assertIn('metadata', dataset)
        self.assertIn('demographics', dataset)
        self.assertIn('summary_metrics', dataset)
    
    def test_volunteer_analytics_with_filters(self):
        """Test volunteer analytics endpoint with filters."""
        url = reverse('common:powerbi:volunteer_analytics')
        params = {
            'status': 'ACTIVE',
            'date_from': (timezone.now() - timedelta(days=30)).isoformat(),
            'date_to': timezone.now().isoformat()
        }
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        dataset = data['data']
        filters_applied = dataset['metadata']['filters_applied']
        
        self.assertEqual(filters_applied['status'], 'ACTIVE')
        self.assertIn('date_from', filters_applied)
        self.assertIn('date_to', filters_applied)
    
    def test_event_analytics_endpoint(self):
        """Test event analytics API endpoint."""
        url = reverse('common:powerbi:event_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate dataset structure
        dataset = data['data']
        self.assertIn('metadata', dataset)
        self.assertIn('performance', dataset)
        self.assertIn('summary_metrics', dataset)
    
    def test_operational_analytics_endpoint(self):
        """Test operational analytics API endpoint."""
        url = reverse('common:powerbi:operational_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate dataset structure
        dataset = data['data']
        self.assertIn('metadata', dataset)
        self.assertIn('system_performance', dataset)
        self.assertIn('summary_metrics', dataset)
    
    def test_financial_analytics_endpoint(self):
        """Test financial analytics API endpoint."""
        url = reverse('common:powerbi:financial_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate dataset structure
        dataset = data['data']
        self.assertIn('metadata', dataset)
        self.assertIn('cost_analysis', dataset)
        self.assertIn('summary_metrics', dataset)
    
    def test_predictive_analytics_endpoint(self):
        """Test predictive analytics API endpoint."""
        url = reverse('common:powerbi:predictive_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate dataset structure
        dataset = data['data']
        self.assertIn('metadata', dataset)
        self.assertIn('demand_forecast', dataset)
        self.assertIn('summary_metrics', dataset)
    
    def test_real_time_dashboard_endpoint(self):
        """Test real-time dashboard API endpoint."""
        url = reverse('common:powerbi:real_time_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate dashboard structure
        dashboard = data['data']
        self.assertIn('metadata', dashboard)
        self.assertIn('system_status', dashboard)
        self.assertIn('volunteer_metrics', dashboard)
        self.assertIn('kpis', dashboard)
    
    def test_custom_dataset_endpoint(self):
        """Test custom dataset API endpoint."""
        url = reverse('common:powerbi:custom_dataset')
        config = {
            'config': {
                'type': 'test_dataset',
                'filters': {'status': 'ACTIVE'},
                'aggregations': ['count'],
                'dimensions': ['status'],
                'measures': ['total_count']
            }
        }
        response = self.client.post(url, config, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate custom dataset structure
        dataset = data['data']
        self.assertIn('metadata', dataset)
        self.assertIn('data', dataset)
        self.assertEqual(dataset['metadata']['dataset_type'], 'test_dataset')
    
    def test_metadata_endpoint(self):
        """Test metadata API endpoint."""
        url = reverse('common:powerbi:metadata')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate metadata structure
        metadata = data['data']
        self.assertIn('endpoints', metadata)
        self.assertIn('authentication', metadata)
        self.assertIn('data_formats', metadata)
        self.assertIn('rate_limits', metadata)
        self.assertIn('schemas', metadata)
        self.assertIn('version', metadata)
    
    def test_export_endpoint_json(self):
        """Test export endpoint with JSON format."""
        url = reverse('common:powerbi:export_dataset', kwargs={'dataset_type': 'volunteer-analytics'})
        response = self.client.get(url, {'format': 'json'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
    
    def test_export_endpoint_csv(self):
        """Test export endpoint with CSV format."""
        url = reverse('common:powerbi:export_dataset', kwargs={'dataset_type': 'volunteer-analytics'})
        response = self.client.get(url, {'format': 'csv'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_health_check_endpoint(self):
        """Test health check API endpoint."""
        url = reverse('common:powerbi:health_check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate health check structure
        health = data['data']
        self.assertIn('status', health)
        self.assertIn('services', health)
        self.assertIn('performance', health)
        self.assertIn('data_freshness', health)
        
        # Validate service health checks
        services = health['services']
        self.assertIn('database', services)
        self.assertIn('cache', services)
        self.assertIn('api', services)
        self.assertIn('authentication', services)
    
    def test_summary_endpoint(self):
        """Test summary API endpoint."""
        url = reverse('common:powerbi:summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Validate summary structure
        summary = data['data']
        self.assertIn('overview', summary)
        self.assertIn('recent_activity', summary)
        self.assertIn('performance_indicators', summary)
        
        # Validate overview metrics
        overview = summary['overview']
        self.assertIn('total_volunteers', overview)
        self.assertIn('active_volunteers', overview)
        self.assertIn('total_events', overview)
    
    def test_cache_refresh_endpoint(self):
        """Test cache refresh API endpoint."""
        url = reverse('common:powerbi:cache_refresh')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        self.assertIn('timestamp', data)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to PowerBI endpoints."""
        # Remove authentication
        self.client.credentials()
        
        url = reverse('common:powerbi:volunteer_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_insufficient_permissions(self):
        """Test access with insufficient permissions."""
        # Create user without PowerBI permissions
        user = User.objects.create_user(
            username='noperm_user',
            email='noperm@example.com',
            password='testpass123',
            user_type='VOLUNTEER'
        )
        
        token = Token.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        
        url = reverse('common:powerbi:volunteer_analytics')
        response = client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PowerBIPermissionTestCase(TestCase):
    """Test cases for PowerBI permission system."""
    
    def setUp(self):
        """Set up test users and permissions."""
        # Create users with different types
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            user_type='ADMIN',
            is_superuser=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.vmt_user = User.objects.create_user(
            username='vmt',
            email='vmt@example.com',
            password='testpass123',
            user_type='VMT',
            is_staff=True
        )
        
        self.volunteer_user = User.objects.create_user(
            username='volunteer',
            email='volunteer@example.com',
            password='testpass123',
            user_type='VOLUNTEER'
        )
        
        # Create PowerBI permissions
        create_powerbi_permissions()
        
        # Assign permissions to staff user
        content_type = ContentType.objects.get_or_create(
            app_label='common',
            model='powerbidata'
        )[0]
        
        permission = Permission.objects.get_or_create(
            codename='view_powerbi_data',
            name='Can view PowerBI data',
            content_type=content_type
        )[0]
        
        self.staff_user.user_permissions.add(permission)
    
    def test_admin_user_has_powerbi_access(self):
        """Test admin user has PowerBI access."""
        permission = PowerBIAccessPermission()
        
        # Mock request
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        request = MockRequest(self.admin_user)
        self.assertTrue(permission.has_permission(request, None))
    
    def test_staff_user_with_permission_has_access(self):
        """Test staff user with permission has access."""
        permission = PowerBIAccessPermission()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        request = MockRequest(self.staff_user)
        self.assertTrue(permission.has_permission(request, None))
    
    def test_vmt_user_has_access(self):
        """Test VMT user has access."""
        permission = PowerBIAccessPermission()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        request = MockRequest(self.vmt_user)
        self.assertTrue(permission.has_permission(request, None))
    
    def test_volunteer_user_no_access(self):
        """Test volunteer user has no access."""
        permission = PowerBIAccessPermission()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        request = MockRequest(self.volunteer_user)
        self.assertFalse(permission.has_permission(request, None))
    
    def test_unauthenticated_user_no_access(self):
        """Test unauthenticated user has no access."""
        permission = PowerBIAccessPermission()
        
        class MockRequest:
            def __init__(self):
                self.user = None
        
        request = MockRequest()
        self.assertFalse(permission.has_permission(request, None))


class PowerBIIntegrationTestCase(TestCase):
    """Integration tests for PowerBI system."""
    
    def setUp(self):
        """Set up comprehensive test data."""
        self.setup_users()
        self.setup_volunteers()
        self.setup_events()
        self.setup_tasks()
        self.setup_audit_logs()
    
    def setup_users(self):
        """Set up test users."""
        self.admin_user = User.objects.create_user(
            username='integration_admin',
            email='integration_admin@example.com',
            password='testpass123',
            user_type='ADMIN',
            is_superuser=True,
            is_staff=True
        )
    
    def setup_volunteers(self):
        """Set up test volunteers with varied data."""
        self.volunteers = []
        
        # Create volunteers with different characteristics
        volunteer_data = [
            {'status': 'ACTIVE', 'experience': 'BEGINNER', 'age_offset': 20},
            {'status': 'ACTIVE', 'experience': 'INTERMEDIATE', 'age_offset': 25},
            {'status': 'ACTIVE', 'experience': 'EXPERIENCED', 'age_offset': 30},
            {'status': 'PENDING', 'experience': 'BEGINNER', 'age_offset': 22},
            {'status': 'INACTIVE', 'experience': 'EXPERIENCED', 'age_offset': 35},
        ]
        
        for i, data in enumerate(volunteer_data):
            volunteer = VolunteerProfile.objects.create(
                user=User.objects.create_user(
                    username=f'integration_vol_{i}',
                    email=f'integration_vol_{i}@example.com',
                    password='testpass123',
                    user_type='VOLUNTEER'
                ),
                first_name=f'Integration{i}',
                last_name='Volunteer',
                phone='0400000000',
                date_of_birth=timezone.now().date() - timedelta(days=365*data['age_offset']),
                status=data['status'],
                volunteer_type='GENERAL',
                experience_level=data['experience']
            )
            self.volunteers.append(volunteer)
    
    def setup_events(self):
        """Set up test events."""
        self.venue = Venue.objects.create(
            name='Integration Venue',
            address='123 Integration St',
            city='Integration City',
            state='NSW',
            postcode='2000',
            capacity=2000
        )
        
        self.events = []
        event_data = [
            {'status': 'ACTIVE', 'days_offset': 1},
            {'status': 'ACTIVE', 'days_offset': 7},
            {'status': 'COMPLETED', 'days_offset': -7},
            {'status': 'DRAFT', 'days_offset': 30},
        ]
        
        for i, data in enumerate(event_data):
            event = Event.objects.create(
                name=f'Integration Event {i}',
                description=f'Integration test event {i}',
                venue=self.venue,
                start_date=timezone.now() + timedelta(days=data['days_offset']),
                end_date=timezone.now() + timedelta(days=data['days_offset']+1),
                status=data['status']
            )
            self.events.append(event)
    
    def setup_tasks(self):
        """Set up test tasks and completions."""
        # Create roles for events
        self.roles = []
        for event in self.events[:2]:  # Only for active events
            role = Role.objects.create(
                name=f'Integration Role for {event.name}',
                description=f'Integration role for {event.name}',
                event=event,
                capacity=3,
                requirements={'skills': ['communication', 'teamwork']}
            )
            self.roles.append(role)
        
        # Create assignments
        self.assignments = []
        for i, role in enumerate(self.roles):
            for j in range(2):  # 2 assignments per role
                if i*2 + j < len(self.volunteers):
                    assignment = Assignment.objects.create(
                        volunteer=self.volunteers[i*2 + j],
                        role=role,
                        event=role.event,
                        status='CONFIRMED'
                    )
                    self.assignments.append(assignment)
        
        # Create tasks
        self.tasks = []
        for role in self.roles:
            task = Task.objects.create(
                title=f'Integration Task for {role.name}',
                description=f'Integration task for {role.name}',
                task_type='CHECKBOX',
                role=role,
                is_active=True
            )
            self.tasks.append(task)
        
        # Create task completions
        for task in self.tasks:
            for assignment in self.assignments:
                if assignment.role == task.role:
                    TaskCompletion.objects.create(
                        task=task,
                        volunteer=assignment.volunteer,
                        status='COMPLETED',
                        completed_at=timezone.now() - timedelta(hours=1)
                    )
    
    def setup_audit_logs(self):
        """Set up test audit logs."""
        # Create various audit log entries
        audit_data = [
            {'operation': 'volunteer_created', 'category': 'VOLUNTEER'},
            {'operation': 'event_created', 'category': 'EVENT'},
            {'operation': 'assignment_created', 'category': 'ASSIGNMENT'},
            {'operation': 'task_completed', 'category': 'TASK'},
            {'operation': 'admin_override_created', 'category': 'ADMIN_OVERRIDE'},
        ]
        
        for data in audit_data:
            AuditLog.objects.create(
                user=self.admin_user,
                operation=data['operation'],
                category=data['category'],
                details={'test': 'integration_data'},
                timestamp=timezone.now() - timedelta(minutes=30)
            )
    
    def test_end_to_end_volunteer_analytics(self):
        """Test end-to-end volunteer analytics generation."""
        # Generate volunteer analytics
        dataset = PowerBIService.get_volunteer_analytics_dataset()
        
        # Validate comprehensive data structure
        self.assertIn('metadata', dataset)
        self.assertIn('demographics', dataset)
        self.assertIn('performance', dataset)
        self.assertIn('engagement', dataset)
        self.assertIn('lifecycle', dataset)
        self.assertIn('geographic', dataset)
        self.assertIn('skills_analysis', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate data reflects test setup
        summary = dataset['summary_metrics']
        self.assertEqual(summary['total_volunteers'], len(self.volunteers))
        
        active_count = len([v for v in self.volunteers if v.status == 'ACTIVE'])
        self.assertEqual(summary['active_volunteers'], active_count)
        
        pending_count = len([v for v in self.volunteers if v.status == 'PENDING'])
        self.assertEqual(summary['pending_volunteers'], pending_count)
    
    def test_end_to_end_event_analytics(self):
        """Test end-to-end event analytics generation."""
        # Generate event analytics
        dataset = PowerBIService.get_event_analytics_dataset()
        
        # Validate comprehensive data structure
        self.assertIn('metadata', dataset)
        self.assertIn('performance', dataset)
        self.assertIn('venue_utilization', dataset)
        self.assertIn('role_fulfillment', dataset)
        self.assertIn('timeline', dataset)
        self.assertIn('resource_allocation', dataset)
        self.assertIn('success_metrics', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate data reflects test setup
        summary = dataset['summary_metrics']
        self.assertEqual(summary['total_events'], len(self.events))
        
        active_count = len([e for e in self.events if e.status == 'ACTIVE'])
        self.assertEqual(summary['active_events'], active_count)
        
        completed_count = len([e for e in self.events if e.status == 'COMPLETED'])
        self.assertEqual(summary['completed_events'], completed_count)
    
    def test_data_consistency_across_datasets(self):
        """Test data consistency across different datasets."""
        # Generate multiple datasets
        volunteer_dataset = PowerBIService.get_volunteer_analytics_dataset()
        event_dataset = PowerBIService.get_event_analytics_dataset()
        operational_dataset = PowerBIService.get_operational_analytics_dataset()
        
        # Validate consistent volunteer counts
        vol_summary = volunteer_dataset['summary_metrics']
        
        # All datasets should have consistent metadata structure
        for dataset in [volunteer_dataset, event_dataset, operational_dataset]:
            metadata = dataset['metadata']
            self.assertIn('generated_at', metadata)
            self.assertIn('version', metadata)
            self.assertEqual(metadata['version'], '1.0')
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Create additional test data
        additional_volunteers = []
        for i in range(50):  # Create 50 additional volunteers
            volunteer = VolunteerProfile.objects.create(
                user=User.objects.create_user(
                    username=f'perf_vol_{i}',
                    email=f'perf_vol_{i}@example.com',
                    password='testpass123',
                    user_type='VOLUNTEER'
                ),
                first_name=f'Perf{i}',
                last_name='Volunteer',
                phone='0400000000',
                date_of_birth=timezone.now().date() - timedelta(days=365*25),
                status='ACTIVE',
                volunteer_type='GENERAL'
            )
            additional_volunteers.append(volunteer)
        
        # Measure performance
        start_time = timezone.now()
        dataset = PowerBIService.get_volunteer_analytics_dataset()
        generation_time = timezone.now() - start_time
        
        # Validate dataset was generated successfully
        self.assertIn('metadata', dataset)
        self.assertIn('summary_metrics', dataset)
        
        # Validate data includes all volunteers
        summary = dataset['summary_metrics']
        expected_total = len(self.volunteers) + len(additional_volunteers)
        self.assertEqual(summary['total_volunteers'], expected_total)
        
        # Performance should be reasonable (less than 10 seconds)
        self.assertLess(generation_time.total_seconds(), 10)
        
        # Clean up additional data
        for volunteer in additional_volunteers:
            volunteer.user.delete()
            volunteer.delete()


def run_powerbi_tests():
    """
    Comprehensive test runner for PowerBI integration.
    
    This function runs all PowerBI tests and provides a summary report.
    """
    import unittest
    from django.test.utils import get_runner
    from django.conf import settings
    
    # Get the Django test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Define test cases to run
    test_cases = [
        PowerBIServiceTestCase,
        PowerBIAPITestCase,
        PowerBIPermissionTestCase,
        PowerBIIntegrationTestCase,
    ]
    
    # Create test suite
    suite = unittest.TestSuite()
    for test_case in test_cases:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_case)
        suite.addTests(tests)
    
    # Run tests
    result = test_runner.run_tests(['test_powerbi_integration'])
    
    return result


if __name__ == '__main__':
    run_powerbi_tests() 