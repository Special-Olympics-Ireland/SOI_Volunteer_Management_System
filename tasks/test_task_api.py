from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from tasks.models import Task, TaskCompletion
from events.models import Event, Venue, Role, Assignment
from volunteers.models import VolunteerProfile

User = get_user_model()


class TaskManagementAPITest(TestCase):
    """Test suite for Task Management API"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='test_task_admin',
            email='test_task_admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type='ADMIN',
            is_staff=True,
            is_superuser=True
        )
        
        self.staff_user = User.objects.create_user(
            username='test_task_staff',
            email='test_task_staff@test.com',
            password='testpass123',
            first_name='Staff',
            last_name='User',
            user_type='VMT',
            is_staff=True
        )
        
        self.volunteer_user = User.objects.create_user(
            username='test_task_volunteer',
            email='test_task_volunteer@test.com',
            password='testpass123',
            first_name='Volunteer',
            last_name='User',
            user_type='VOLUNTEER'
        )
        
        # Create volunteer profile
        self.volunteer_profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            status='ACTIVE'
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            state='TS',
            postal_code='12345',
            capacity=100,
            venue_type='INDOOR'
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event',
            description='Test event for API testing',
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=32),
            venue=self.venue,
            status='PLANNING'
        )
        
        # Create test role
        self.role = Role.objects.create(
            name='Test Role',
            description='Test role for API testing',
            event=self.event,
            total_positions=10,
            filled_positions=0,
            requirements={'age_min': 18}
        )
        
        # Create assignment for volunteer
        self.assignment = Assignment.objects.create(
            volunteer=self.volunteer_user,
            role=self.role,
            status='APPROVED',
            assigned_by=self.staff_user
        )
        
        # Create test tasks
        self.task1 = Task.objects.create(
            title='Test Task 1',
            description='First test task',
            task_type='CHECKBOX',
            category='TRAINING',
            priority='HIGH',
            is_mandatory=True,
            requires_verification=True,
            due_date=timezone.now() + timedelta(days=7),
            estimated_duration_minutes=60,
            role=self.role,
            event=self.event,
            created_by=self.staff_user
        )
        
        self.task2 = Task.objects.create(
            title='Test Task 2',
            description='Second test task',
            task_type='PHOTO',
            category='PREPARATION',
            priority='MEDIUM',
            is_mandatory=False,
            requires_verification=False,
            due_date=timezone.now() + timedelta(days=14),
            estimated_duration_minutes=30,
            role=self.role,
            event=self.event,
            created_by=self.staff_user
        )
        
        # Create test task completion
        self.completion1 = TaskCompletion.objects.create(
            task=self.task1,
            volunteer=self.volunteer_user,
            assignment=self.assignment,
            completion_type='CHECKBOX',
            status='PENDING'
        )
    
    def test_task_list_api(self):
        """Test task list API endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('tasks:task-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_task_detail_api(self):
        """Test task detail API endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('tasks:task-detail', kwargs={'pk': self.task1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Task 1')
    
    def test_task_create_api(self):
        """Test task creation API endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('tasks:task-list')
        
        data = {
            'title': 'New Test Task',
            'description': 'New task for testing',
            'task_type': 'TEXT',
            'category': 'TRAINING',
            'priority': 'MEDIUM',
            'is_mandatory': False,
            'requires_verification': False,
            'due_date': (timezone.now() + timedelta(days=10)).isoformat(),
            'estimated_duration_minutes': 45,
            'role': self.role.pk,
            'event': self.event.pk
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Test Task')
    
    def test_task_completion_list_api(self):
        """Test task completion list API endpoint"""
        self.client.force_authenticate(user=self.volunteer_user)
        url = reverse('tasks:taskcompletion-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_task_completion_workflow(self):
        """Test task completion workflow actions"""
        self.client.force_authenticate(user=self.volunteer_user)
        
        # Test submit action
        url = reverse('tasks:taskcompletion-submit', kwargs={'pk': self.completion1.pk})
        data = {'completion_data': {'checkbox_value': True}}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.completion1.refresh_from_db()
        self.assertEqual(self.completion1.status, 'SUBMITTED')
    
    def test_task_stats_api(self):
        """Test task statistics API endpoint"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('tasks:task-stats', kwargs={'pk': self.task1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('completion_stats', response.data)
    
    def test_permission_based_access(self):
        """Test permission-based access control"""
        # Test volunteer access to task list (should be limited)
        self.client.force_authenticate(user=self.volunteer_user)
        url = reverse('tasks:task-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test volunteer cannot create tasks
        data = {
            'title': 'Unauthorized Task',
            'description': 'Should not be created',
            'task_type': 'TEXT',
            'category': 'TRAINING',
            'priority': 'LOW',
            'role': self.role.pk,
            'event': self.event.pk
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_task_filtering(self):
        """Test task filtering capabilities"""
        self.client.force_authenticate(user=self.staff_user)
        
        # Test filter by role
        url = reverse('tasks:task-by-role', kwargs={'role_id': self.role.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Test filter by event
        url = reverse('tasks:task-by-event', kwargs={'event_id': self.event.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_task_completion_verification(self):
        """Test task completion verification process"""
        # Submit completion first
        self.completion1.status = 'SUBMITTED'
        self.completion1.completion_data = {'checkbox_value': True}
        self.completion1.save()
        
        # Test verification by staff
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('tasks:taskcompletion-verify', kwargs={'pk': self.completion1.pk})
        data = {'verification_notes': 'Verified successfully'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.completion1.refresh_from_db()
        self.assertEqual(self.completion1.status, 'VERIFIED') 