"""
Comprehensive test suite for Admin Override API

Tests all CRUD operations, custom actions, permissions, filtering,
bulk operations, and integration scenarios.
"""

import json
import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from common.models import AdminOverride, AuditLog
from events.models import Event, Venue
from volunteers.models import VolunteerProfile

User = get_user_model()


class AdminOverrideAPITestCase(APITestCase):
    """Test case for Admin Override CRUD operations"""
    
    def setUp(self):
        """Set up test data"""
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.vmt_user = User.objects.create_user(
            username='vmt_user',
            email='vmt@test.com',
            password='testpass123',
            user_type='VMT',
            is_staff=True
        )
        
        self.cvt_user = User.objects.create_user(
            username='cvt_user',
            email='cvt@test.com',
            password='testpass123',
            user_type='CVT',
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.volunteer_user = User.objects.create_user(
            username='volunteer_user',
            email='volunteer@test.com',
            password='testpass123',
            user_type='VOLUNTEER'
        )
        
        # Create test objects for overrides
        self.test_venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            capacity=100
        )
        
        self.test_event = Event.objects.create(
            name='Test Event',
            venue=self.test_venue,
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=1)).date()
        )
        
        # Create test override
        self.test_override = AdminOverride.objects.create(
            title='Test Override',
            override_type='CAPACITY_LIMIT',
            description='Test override description',
            justification='Test justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='MEDIUM',
            impact_level='LOW'
        )
        
        self.client = APIClient()
    
    def test_list_overrides_admin(self):
        """Test listing overrides as admin user"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Override')
    
    def test_list_overrides_staff_filtered(self):
        """Test that staff users only see their own overrides"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('common:adminoverride-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Create override by different user
        AdminOverride.objects.create(
            title='Other Override',
            override_type='AGE_REQUIREMENT',
            description='Other description',
            justification='Other justification',
            content_type=ContentType.objects.get_for_model(self.test_event),
            object_id=str(self.test_event.id),
            requested_by=self.vmt_user,
            risk_level='LOW',
            impact_level='MINIMAL'
        )
        
        response = self.client.get(url)
        self.assertEqual(len(response.data['results']), 1)  # Still only sees own override
    
    def test_create_override_success(self):
        """Test creating a new override"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('common:adminoverride-list')
        
        data = {
            'title': 'New Override',
            'override_type': 'AGE_REQUIREMENT',
            'description': 'New override description',
            'justification': 'This is a detailed justification for the override',
            'content_type_id': ContentType.objects.get_for_model(self.test_event).id,
            'object_id': str(self.test_event.id),
            'risk_level': 'LOW',
            'impact_level': 'MINIMAL',
            'priority_level': 5
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Override')
        self.assertEqual(response.data['requested_by'], self.staff_user.id)
        
        # Verify override was created in database
        override = AdminOverride.objects.get(title='New Override')
        self.assertEqual(override.requested_by, self.staff_user)
    
    def test_create_override_validation_errors(self):
        """Test validation errors when creating override"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('common:adminoverride-list')
        
        # Test missing required fields
        data = {
            'title': 'Test',
            'override_type': 'AGE_REQUIREMENT'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test short justification
        data = {
            'title': 'Test Override',
            'override_type': 'AGE_REQUIREMENT',
            'description': 'Test description',
            'justification': 'Too short',
            'content_type_id': ContentType.objects.get_for_model(self.test_event).id,
            'object_id': str(self.test_event.id),
            'risk_level': 'LOW',
            'impact_level': 'MINIMAL'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('justification', response.data)
    
    def test_retrieve_override_detail(self):
        """Test retrieving override details"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-detail', kwargs={'pk': self.test_override.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Override')
        self.assertIn('requested_by_display', response.data)
        self.assertIn('target_object_display', response.data)
    
    def test_update_override_admin(self):
        """Test updating override as admin"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-detail', kwargs={'pk': self.test_override.id})
        
        data = {
            'title': 'Updated Override Title',
            'description': 'Updated description',
            'justification': 'Updated justification for the override'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Override Title')
        
        # Verify in database
        self.test_override.refresh_from_db()
        self.assertEqual(self.test_override.title, 'Updated Override Title')
    
    def test_delete_override_admin_only(self):
        """Test that only admin can delete overrides"""
        # Test as VMT user (should fail)
        self.client.force_authenticate(user=self.vmt_user)
        url = reverse('common:adminoverride-detail', kwargs={'pk': self.test_override.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test as admin user (should succeed)
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deletion
        self.assertFalse(AdminOverride.objects.filter(id=self.test_override.id).exists())
    
    def test_volunteer_access_denied(self):
        """Test that volunteers cannot access override API"""
        self.client.force_authenticate(user=self.volunteer_user)
        url = reverse('common:adminoverride-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminOverrideWorkflowTestCase(APITestCase):
    """Test case for Admin Override workflow actions"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.vmt_user = User.objects.create_user(
            username='vmt_user',
            email='vmt@test.com',
            password='testpass123',
            user_type='VMT',
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.test_venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            capacity=100
        )
        
        self.pending_override = AdminOverride.objects.create(
            title='Pending Override',
            override_type='CAPACITY_LIMIT',
            description='Test override description',
            justification='Test justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='MEDIUM',
            impact_level='LOW',
            status='PENDING'
        )
        
        self.client = APIClient()
    
    def test_approve_override_success(self):
        """Test approving an override"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-approve', kwargs={'pk': self.pending_override.id})
        
        data = {
            'action': 'approve',
            'notes': 'Approved for testing purposes'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['override']['status'], 'APPROVED')
        
        # Verify in database
        self.pending_override.refresh_from_db()
        self.assertEqual(self.pending_override.status, 'APPROVED')
        self.assertEqual(self.pending_override.approved_by, self.admin_user)
    
    def test_reject_override_success(self):
        """Test rejecting an override"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-reject', kwargs={'pk': self.pending_override.id})
        
        data = {
            'action': 'reject',
            'reason': 'Insufficient justification'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['override']['status'], 'REJECTED')
        
        # Verify in database
        self.pending_override.refresh_from_db()
        self.assertEqual(self.pending_override.status, 'REJECTED')
        self.assertEqual(self.pending_override.rejection_reason, 'Insufficient justification')
    
    def test_activate_approved_override(self):
        """Test activating an approved override"""
        # First approve the override
        self.pending_override.approve(self.admin_user, 'Test approval')
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-activate', kwargs={'pk': self.pending_override.id})
        
        data = {
            'action': 'activate',
            'notes': 'Activating override'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['override']['status'], 'ACTIVE')
        
        # Verify in database
        self.pending_override.refresh_from_db()
        self.assertEqual(self.pending_override.status, 'ACTIVE')
    
    def test_revoke_active_override(self):
        """Test revoking an active override"""
        # First approve and activate the override
        self.pending_override.approve(self.admin_user, 'Test approval')
        self.pending_override.activate(self.admin_user)
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-revoke', kwargs={'pk': self.pending_override.id})
        
        data = {
            'action': 'revoke',
            'reason': 'No longer needed'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['override']['status'], 'REVOKED')
        
        # Verify in database
        self.pending_override.refresh_from_db()
        self.assertEqual(self.pending_override.status, 'REVOKED')
    
    def test_complete_override(self):
        """Test completing an override"""
        # First approve and activate the override
        self.pending_override.approve(self.admin_user, 'Test approval')
        self.pending_override.activate(self.admin_user)
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-complete', kwargs={'pk': self.pending_override.id})
        
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['override']['status'], 'COMPLETED')
        
        # Verify in database
        self.pending_override.refresh_from_db()
        self.assertEqual(self.pending_override.status, 'COMPLETED')
    
    def test_vmt_approval_restrictions(self):
        """Test VMT approval restrictions for critical overrides"""
        # Create critical risk override
        critical_override = AdminOverride.objects.create(
            title='Critical Override',
            override_type='EMERGENCY_ACCESS',
            description='Critical override',
            justification='Critical justification for emergency override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='CRITICAL',
            impact_level='HIGH',
            is_emergency=True,
            status='PENDING'
        )
        
        self.client.force_authenticate(user=self.vmt_user)
        url = reverse('common:adminoverride-approve', kwargs={'pk': critical_override.id})
        
        data = {
            'action': 'approve',
            'notes': 'Attempting to approve critical override'
        }
        
        response = self.client.post(url, data, format='json')
        
        # VMT should not be able to approve critical overrides
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminOverrideBulkOperationsTestCase(APITestCase):
    """Test case for bulk operations on admin overrides"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.test_venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            capacity=100
        )
        
        # Create multiple test overrides
        self.overrides = []
        for i in range(3):
            override = AdminOverride.objects.create(
                title=f'Test Override {i+1}',
                override_type='CAPACITY_LIMIT',
                description=f'Test override description {i+1}',
                justification=f'Test justification for override {i+1}',
                content_type=ContentType.objects.get_for_model(self.test_venue),
                object_id=str(self.test_venue.id),
                requested_by=self.staff_user,
                risk_level='MEDIUM',
                impact_level='LOW',
                status='PENDING'
            )
            self.overrides.append(override)
        
        self.client = APIClient()
    
    def test_bulk_approve_overrides(self):
        """Test bulk approving multiple overrides"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-bulk-operations')
        
        data = {
            'override_ids': [str(override.id) for override in self.overrides],
            'action': 'approve',
            'notes': 'Bulk approval for testing'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successful'], 3)
        self.assertEqual(response.data['failed'], 0)
        
        # Verify all overrides were approved
        for override in self.overrides:
            override.refresh_from_db()
            self.assertEqual(override.status, 'APPROVED')
    
    def test_bulk_reject_overrides(self):
        """Test bulk rejecting multiple overrides"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-bulk-operations')
        
        data = {
            'override_ids': [str(override.id) for override in self.overrides[:2]],
            'action': 'reject',
            'reason': 'Bulk rejection for testing'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successful'], 2)
        
        # Verify overrides were rejected
        for override in self.overrides[:2]:
            override.refresh_from_db()
            self.assertEqual(override.status, 'REJECTED')
    
    def test_bulk_update_tags(self):
        """Test bulk updating tags"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-bulk-operations')
        
        data = {
            'override_ids': [str(override.id) for override in self.overrides],
            'action': 'update_tags',
            'tags': ['urgent', 'capacity', 'venue']
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successful'], 3)
        
        # Verify tags were updated
        for override in self.overrides:
            override.refresh_from_db()
            self.assertEqual(override.tags, ['urgent', 'capacity', 'venue'])
    
    def test_bulk_update_priority(self):
        """Test bulk updating priority levels"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('common:adminoverride-bulk-operations')
        
        data = {
            'override_ids': [str(override.id) for override in self.overrides],
            'action': 'update_priority',
            'priority_level': 2
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['successful'], 3)
        
        # Verify priority was updated
        for override in self.overrides:
            override.refresh_from_db()
            self.assertEqual(override.priority_level, 2)


class AdminOverrideFilteringTestCase(APITestCase):
    """Test case for filtering and searching admin overrides"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.test_venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            capacity=100
        )
        
        # Create overrides with different attributes
        self.high_risk_override = AdminOverride.objects.create(
            title='High Risk Override',
            override_type='SYSTEM_RULE',
            description='High risk override',
            justification='High risk justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='HIGH',
            impact_level='HIGH',
            status='PENDING',
            is_emergency=True,
            tags=['urgent', 'system']
        )
        
        self.low_risk_override = AdminOverride.objects.create(
            title='Low Risk Override',
            override_type='CAPACITY_LIMIT',
            description='Low risk override',
            justification='Low risk justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='LOW',
            impact_level='MINIMAL',
            status='APPROVED',
            tags=['capacity']
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_filter_by_risk_level(self):
        """Test filtering by risk level"""
        url = reverse('common:adminoverride-list')
        response = self.client.get(url, {'risk_level': 'HIGH'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'High Risk Override')
    
    def test_filter_by_status(self):
        """Test filtering by status"""
        url = reverse('common:adminoverride-list')
        response = self.client.get(url, {'status': 'APPROVED'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Low Risk Override')
    
    def test_filter_by_emergency(self):
        """Test filtering by emergency status"""
        url = reverse('common:adminoverride-list')
        response = self.client.get(url, {'is_emergency': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'High Risk Override')
    
    def test_search_by_title(self):
        """Test searching by title"""
        url = reverse('common:adminoverride-list')
        response = self.client.get(url, {'search': 'High Risk'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'High Risk Override')
    
    def test_ordering(self):
        """Test ordering results"""
        url = reverse('common:adminoverride-list')
        response = self.client.get(url, {'ordering': 'risk_level'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        # Should be ordered by risk level (HIGH comes before LOW alphabetically)
        self.assertEqual(response.data['results'][0]['risk_level'], 'HIGH')


class AdminOverrideStatisticsTestCase(APITestCase):
    """Test case for admin override statistics"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.test_venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            capacity=100
        )
        
        # Create overrides with different statuses
        AdminOverride.objects.create(
            title='Pending Override 1',
            override_type='CAPACITY_LIMIT',
            description='Pending override',
            justification='Pending justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='MEDIUM',
            impact_level='LOW',
            status='PENDING'
        )
        
        AdminOverride.objects.create(
            title='Approved Override 1',
            override_type='AGE_REQUIREMENT',
            description='Approved override',
            justification='Approved justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='LOW',
            impact_level='MINIMAL',
            status='APPROVED'
        )
        
        AdminOverride.objects.create(
            title='Emergency Override 1',
            override_type='EMERGENCY_ACCESS',
            description='Emergency override',
            justification='Emergency justification for critical override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='CRITICAL',
            impact_level='HIGH',
            status='ACTIVE',
            is_emergency=True
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_get_statistics(self):
        """Test getting override statistics"""
        url = reverse('common:adminoverride-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check basic counts
        self.assertEqual(response.data['total_overrides'], 3)
        self.assertEqual(response.data['pending_overrides'], 1)
        self.assertEqual(response.data['approved_overrides'], 1)
        self.assertEqual(response.data['active_overrides'], 1)
        self.assertEqual(response.data['emergency_overrides'], 1)
        self.assertEqual(response.data['high_risk_overrides'], 1)  # CRITICAL counts as high risk
        
        # Check breakdown by type
        self.assertIn('overrides_by_type', response.data)
        self.assertIn('overrides_by_status', response.data)
        self.assertIn('overrides_by_risk_level', response.data)
        
        # Check recent activity
        self.assertIn('recent_activity', response.data)
        self.assertEqual(len(response.data['recent_activity']), 3)


class AdminOverrideSpecialEndpointsTestCase(APITestCase):
    """Test case for special admin override endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            is_staff=True
        )
        
        self.test_venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            capacity=100
        )
        
        # Create overrides with different statuses
        self.pending_override = AdminOverride.objects.create(
            title='Pending Override',
            override_type='CAPACITY_LIMIT',
            description='Pending override',
            justification='Pending justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='MEDIUM',
            impact_level='LOW',
            status='PENDING'
        )
        
        self.active_override = AdminOverride.objects.create(
            title='Active Override',
            override_type='AGE_REQUIREMENT',
            description='Active override',
            justification='Active justification for override',
            content_type=ContentType.objects.get_for_model(self.test_venue),
            object_id=str(self.test_venue.id),
            requested_by=self.staff_user,
            risk_level='LOW',
            impact_level='MINIMAL',
            status='ACTIVE',
            effective_from=timezone.now() - timedelta(days=1),
            effective_until=timezone.now() + timedelta(days=7)
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_get_pending_overrides(self):
        """Test getting pending overrides"""
        url = reverse('common:adminoverride-pending')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Pending Override')
    
    def test_get_active_overrides(self):
        """Test getting active overrides"""
        url = reverse('common:adminoverride-active')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Active Override')
    
    def test_get_expiring_overrides(self):
        """Test getting expiring overrides"""
        url = reverse('common:adminoverride-expiring')
        response = self.client.get(url, {'days': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Active Override')
    
    def test_get_override_types(self):
        """Test getting available override types"""
        url = reverse('common:adminoverride-types')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('override_types', response.data)
        self.assertIsInstance(response.data['override_types'], list)
        self.assertTrue(len(response.data['override_types']) > 0)
        
        # Check structure of type data
        type_data = response.data['override_types'][0]
        self.assertIn('value', type_data)
        self.assertIn('label', type_data)


if __name__ == '__main__':
    import django
    import os
    import sys
    
    # Add the project directory to Python path
    sys.path.insert(0, '/home/itsupport/projects/soi-hub')
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
    django.setup()
    
    # Run tests
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests([
        'test_admin_override_api.AdminOverrideAPITestCase',
        'test_admin_override_api.AdminOverrideWorkflowTestCase',
        'test_admin_override_api.AdminOverrideBulkOperationsTestCase',
        'test_admin_override_api.AdminOverrideFilteringTestCase',
        'test_admin_override_api.AdminOverrideStatisticsTestCase',
        'test_admin_override_api.AdminOverrideSpecialEndpointsTestCase'
    ])
    
    if failures:
        sys.exit(1)
    else:
        print("All tests passed!") 