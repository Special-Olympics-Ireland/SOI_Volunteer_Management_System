"""
Comprehensive Test Suite for Task Management System.

This test suite covers all aspects of the task management system including:
- Task creation and management
- Task assignment workflows
- Progress tracking and completion
- Template management
- Analytics and reporting
- Admin interface functionality
"""

import json
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.admin.sites import AdminSite
from unittest.mock import patch, MagicMock

from tasks.models import Task, TaskCompletion, TaskTemplate, TaskDependency
from tasks.task_management_service import TaskManagementService
from tasks.admin import TaskAdmin, TaskCompletionAdmin, TaskTemplateAdmin
from events.models import Event, Venue, Role, Assignment
from volunteers.models import VolunteerProfile
from common.audit_service import AdminAuditService

User = get_user_model()


class TaskManagementTester:
    """
    Comprehensive test class for task management system functionality.
    """
    
    def __init__(self, test_case):
        self.test_case = test_case
        self.client = Client()
        self.setup_test_data()
    
    def setup_test_data(self):
        """Set up test data for task management tests."""
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            first_name='Admin',
            last_name='User'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            user_type='STAFF',
            first_name='Staff',
            last_name='User'
        )
        
        self.volunteer_user = User.objects.create_user(
            username='volunteer',
            email='volunteer@test.com',
            password='testpass123',
            user_type='VOLUNTEER',
            first_name='Test',
            last_name='Volunteer'
        )
        
        # Create volunteer profile
        self.volunteer_profile = VolunteerProfile.objects.create(
            user=self.volunteer_user,
            status='ACTIVE',
            phone_number='+61400000000',
            date_of_birth='1990-01-01',
            emergency_contact_name='Emergency Contact',
            emergency_contact_phone='+61400000001'
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            state='NSW',
            postcode='2000',
            capacity=1000
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event',
            description='Test event description',
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=32),
            venue=self.venue,
            status='ACTIVE'
        )
        
        # Create test role
        self.role = Role.objects.create(
            name='Test Role',
            description='Test role description',
            event=self.event,
            capacity=10,
            requirements={'skills': ['communication'], 'experience': 'beginner'}
        )
        
        # Create assignment
        self.assignment = Assignment.objects.create(
            volunteer=self.volunteer_profile,
            role=self.role,
            event=self.event,
            status='CONFIRMED'
        )
        
        # Create test task template
        self.task_template = TaskTemplate.objects.create(
            name='Test Template',
            description='Test template description',
            task_type='CHECKBOX',
            category='GENERAL',
            default_priority='MEDIUM',
            estimated_duration=30,
            instructions_template='Complete this test task',
            created_by=self.admin_user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            task_type='CHECKBOX',
            role=self.role,
            event=self.event,
            priority='MEDIUM',
            due_date=timezone.now() + timedelta(days=7),
            estimated_duration=30,
            instructions='Complete this test task',
            is_mandatory=True,
            points_value=10,
            created_by=self.admin_user
        )
    
    def test_task_creation_service(self):
        """Test task creation through service."""
        print("Testing task creation service...")
        
        task_data = {
            'title': 'Service Created Task',
            'description': 'Task created through service',
            'task_type': 'PHOTO',
            'priority': 'HIGH',
            'due_date': timezone.now() + timedelta(days=5),
            'estimated_duration': 45,
            'instructions': 'Take a photo for this task',
            'is_mandatory': False,
            'points_value': 15,
            'auto_assign': True
        }
        
        task = TaskManagementService.create_role_specific_task(
            self.role.id, task_data, self.admin_user
        )
        
        self.test_case.assertEqual(task.title, 'Service Created Task')
        self.test_case.assertEqual(task.task_type, 'PHOTO')
        self.test_case.assertEqual(task.priority, 'HIGH')
        self.test_case.assertEqual(task.role, self.role)
        self.test_case.assertEqual(task.created_by, self.admin_user)
        
        # Check auto-assignment
        completion = TaskCompletion.objects.filter(task=task, volunteer=self.volunteer_profile).first()
        self.test_case.assertIsNotNone(completion)
        self.test_case.assertEqual(completion.status, 'NOT_STARTED')
        
        print("✓ Task creation service test passed")
    
    def test_task_assignment_workflow(self):
        """Test task assignment workflow."""
        print("Testing task assignment workflow...")
        
        # Test individual assignment
        completion = TaskManagementService.assign_task_to_volunteer(
            self.task.id, self.volunteer_profile.id, self.admin_user
        )
        
        self.test_case.assertEqual(completion.task, self.task)
        self.test_case.assertEqual(completion.volunteer, self.volunteer_profile)
        self.test_case.assertEqual(completion.assigned_by, self.admin_user)
        self.test_case.assertEqual(completion.status, 'NOT_STARTED')
        
        # Test duplicate assignment prevention
        with self.test_case.assertRaises(ValidationError):
            TaskManagementService.assign_task_to_volunteer(
                self.task.id, self.volunteer_profile.id, self.admin_user
            )
        
        print("✓ Task assignment workflow test passed")
    
    def test_bulk_task_assignment(self):
        """Test bulk task assignment functionality."""
        print("Testing bulk task assignment...")
        
        # Create additional volunteers and tasks
        volunteer2 = VolunteerProfile.objects.create(
            user=User.objects.create_user(
                username='volunteer2',
                email='volunteer2@test.com',
                password='testpass123',
                user_type='VOLUNTEER'
            ),
            status='ACTIVE',
            phone_number='+61400000002',
            date_of_birth='1991-01-01',
            emergency_contact_name='Emergency Contact 2',
            emergency_contact_phone='+61400000003'
        )
        
        Assignment.objects.create(
            volunteer=volunteer2,
            role=self.role,
            event=self.event,
            status='CONFIRMED'
        )
        
        task2 = Task.objects.create(
            title='Bulk Test Task 2',
            description='Second task for bulk testing',
            task_type='TEXT',
            role=self.role,
            event=self.event,
            priority='LOW',
            created_by=self.admin_user
        )
        
        # Test bulk assignment
        results = TaskManagementService.bulk_assign_tasks(
            [self.task.id, task2.id],
            [self.volunteer_profile.id, volunteer2.id],
            self.admin_user
        )
        
        self.test_case.assertEqual(results['total_attempted'], 4)  # 2 tasks × 2 volunteers
        self.test_case.assertEqual(results['total_successful'], 4)
        self.test_case.assertEqual(results['total_failed'], 0)
        
        # Verify assignments were created
        completions = TaskCompletion.objects.filter(
            task__in=[self.task, task2],
            volunteer__in=[self.volunteer_profile, volunteer2]
        )
        self.test_case.assertEqual(completions.count(), 4)
        
        print("✓ Bulk task assignment test passed")
    
    def test_task_progress_tracking(self):
        """Test task progress tracking and status updates."""
        print("Testing task progress tracking...")
        
        # Create task completion
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='NOT_STARTED'
        )
        
        # Test progress update to IN_PROGRESS
        updated_completion = TaskManagementService.update_task_progress(
            completion.id,
            {
                'status': 'IN_PROGRESS',
                'progress_percentage': 50,
                'notes': 'Started working on task'
            },
            self.volunteer_user
        )
        
        self.test_case.assertEqual(updated_completion.status, 'IN_PROGRESS')
        self.test_case.assertEqual(updated_completion.progress_percentage, 50)
        self.test_case.assertIsNotNone(updated_completion.started_at)
        
        # Test completion
        completed_completion = TaskManagementService.update_task_progress(
            completion.id,
            {
                'status': 'COMPLETED',
                'completion_data': {'checkbox_completed': True},
                'time_spent': 1.5
            },
            self.volunteer_user
        )
        
        self.test_case.assertEqual(completed_completion.status, 'COMPLETED')
        self.test_case.assertEqual(completed_completion.progress_percentage, 100)
        self.test_case.assertIsNotNone(completed_completion.completed_at)
        self.test_case.assertEqual(completed_completion.time_spent, 1.5)
        
        print("✓ Task progress tracking test passed")
    
    def test_volunteer_task_retrieval(self):
        """Test volunteer task retrieval with filtering."""
        print("Testing volunteer task retrieval...")
        
        # Create multiple task completions
        TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='COMPLETED'
        )
        
        task2 = Task.objects.create(
            title='In Progress Task',
            description='Task in progress',
            task_type='PHOTO',
            role=self.role,
            event=self.event,
            priority='HIGH',
            created_by=self.admin_user
        )
        
        TaskCompletion.objects.create(
            task=task2,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='IN_PROGRESS'
        )
        
        # Test retrieval without filters
        volunteer_tasks = TaskManagementService.get_volunteer_tasks(self.volunteer_profile.id)
        
        self.test_case.assertEqual(volunteer_tasks['total_tasks'], 2)
        self.test_case.assertIn('COMPLETED', volunteer_tasks['tasks_by_status'])
        self.test_case.assertIn('IN_PROGRESS', volunteer_tasks['tasks_by_status'])
        
        # Test retrieval with status filter
        completed_tasks = TaskManagementService.get_volunteer_tasks(
            self.volunteer_profile.id,
            {'status': 'COMPLETED'}
        )
        
        self.test_case.assertEqual(completed_tasks['total_tasks'], 1)
        
        print("✓ Volunteer task retrieval test passed")
    
    def test_role_task_analysis(self):
        """Test role-specific task analysis."""
        print("Testing role task analysis...")
        
        # Create task completion
        TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='COMPLETED'
        )
        
        role_data = TaskManagementService.get_role_tasks(self.role.id, include_completions=True)
        
        self.test_case.assertEqual(role_data['role_id'], self.role.id)
        self.test_case.assertEqual(role_data['role_name'], self.role.name)
        self.test_case.assertGreater(role_data['total_tasks'], 0)
        self.test_case.assertIn('role_statistics', role_data)
        
        # Check task data includes completion stats
        for task_data in role_data['tasks']:
            self.test_case.assertIn('completion_stats', task_data)
        
        print("✓ Role task analysis test passed")
    
    def test_task_template_management(self):
        """Test task template creation and usage."""
        print("Testing task template management...")
        
        # Test template creation
        template_data = {
            'name': 'Service Template',
            'description': 'Template created through service',
            'task_type': 'CUSTOM',
            'category': 'TRAINING',
            'default_priority': 'HIGH',
            'estimated_duration': 60,
            'instructions_template': 'Follow these custom instructions',
            'required_skills': ['leadership', 'communication'],
            'is_mandatory_default': True,
            'points_value_default': 25
        }
        
        template = TaskManagementService.create_task_template(template_data, self.admin_user)
        
        self.test_case.assertEqual(template.name, 'Service Template')
        self.test_case.assertEqual(template.category, 'TRAINING')
        self.test_case.assertEqual(template.default_priority, 'HIGH')
        
        # Test task creation from template
        customizations = {
            'title': 'Task from Template',
            'due_date': timezone.now() + timedelta(days=10),
            'metadata': {'custom_field': 'custom_value'}
        }
        
        task_from_template = TaskManagementService.create_task_from_template(
            template.id, self.role.id, customizations, self.admin_user
        )
        
        self.test_case.assertEqual(task_from_template.title, 'Task from Template')
        self.test_case.assertEqual(task_from_template.task_type, 'CUSTOM')
        self.test_case.assertEqual(task_from_template.priority, 'HIGH')
        self.test_case.assertIn('created_from_template', task_from_template.metadata)
        
        print("✓ Task template management test passed")
    
    def test_task_analytics_generation(self):
        """Test task analytics and reporting."""
        print("Testing task analytics generation...")
        
        # Create various task completions for analytics
        TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='COMPLETED',
            time_spent=2.0
        )
        
        analytics = TaskManagementService.get_task_analytics()
        
        # Check overview section
        self.test_case.assertIn('overview', analytics)
        self.test_case.assertIn('total_tasks', analytics['overview'])
        self.test_case.assertIn('total_assignments', analytics['overview'])
        self.test_case.assertIn('completion_rate', analytics['overview'])
        
        # Check distribution section
        self.test_case.assertIn('task_distribution', analytics)
        self.test_case.assertIn('by_type', analytics['task_distribution'])
        self.test_case.assertIn('by_priority', analytics['task_distribution'])
        
        # Check performance metrics
        self.test_case.assertIn('performance_metrics', analytics)
        
        print("✓ Task analytics generation test passed")
    
    def test_task_dependencies(self):
        """Test task dependency management."""
        print("Testing task dependencies...")
        
        # Create prerequisite task
        prerequisite_task = Task.objects.create(
            title='Prerequisite Task',
            description='Must be completed first',
            task_type='CHECKBOX',
            role=self.role,
            event=self.event,
            priority='MEDIUM',
            created_by=self.admin_user
        )
        
        # Create dependent task
        dependent_task_data = {
            'title': 'Dependent Task',
            'description': 'Depends on prerequisite',
            'task_type': 'TEXT',
            'priority': 'HIGH',
            'dependencies': [prerequisite_task.id]
        }
        
        dependent_task = TaskManagementService.create_role_specific_task(
            self.role.id, dependent_task_data, self.admin_user
        )
        
        # Check dependency was created
        dependency = TaskDependency.objects.filter(
            task=dependent_task,
            depends_on=prerequisite_task
        ).first()
        
        self.test_case.assertIsNotNone(dependency)
        
        # Test prerequisite checking
        has_prerequisites = TaskManagementService._check_task_prerequisites(
            dependent_task, self.volunteer_profile
        )
        self.test_case.assertFalse(has_prerequisites)  # Prerequisite not completed
        
        # Complete prerequisite
        TaskCompletion.objects.create(
            task=prerequisite_task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='COMPLETED'
        )
        
        has_prerequisites = TaskManagementService._check_task_prerequisites(
            dependent_task, self.volunteer_profile
        )
        self.test_case.assertTrue(has_prerequisites)  # Prerequisite completed
        
        print("✓ Task dependencies test passed")
    
    def test_admin_interface_functionality(self):
        """Test admin interface functionality."""
        print("Testing admin interface functionality...")
        
        # Test TaskAdmin
        site = AdminSite()
        task_admin = TaskAdmin(Task, site)
        
        # Test custom display methods
        display_type = task_admin.get_task_type_display(self.task)
        self.test_case.assertIn('☑️', display_type)
        
        display_priority = task_admin.get_priority_display(self.task)
        self.test_case.assertIn('MEDIUM', display_priority)
        
        # Test completion stats display
        TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='COMPLETED'
        )
        
        completion_stats = task_admin.get_completion_stats(self.task)
        self.test_case.assertIn('100.0%', completion_stats)
        
        # Test TaskCompletionAdmin
        completion_admin = TaskCompletionAdmin(TaskCompletion, site)
        completion = TaskCompletion.objects.first()
        
        if completion:
            status_display = completion_admin.get_status_display(completion)
            self.test_case.assertIn(completion.status, status_display)
        
        print("✓ Admin interface functionality test passed")
    
    def test_task_validation_and_error_handling(self):
        """Test task validation and error handling."""
        print("Testing task validation and error handling...")
        
        # Test invalid task data
        invalid_task_data = {
            'title': '',  # Empty title should fail
            'description': 'Valid description',
            'task_type': 'INVALID_TYPE',  # Invalid type
            'priority': 'INVALID_PRIORITY'  # Invalid priority
        }
        
        with self.test_case.assertRaises(ValidationError):
            TaskManagementService.create_role_specific_task(
                self.role.id, invalid_task_data, self.admin_user
            )
        
        # Test assignment to non-existent volunteer
        with self.test_case.assertRaises(ValidationError):
            TaskManagementService.assign_task_to_volunteer(
                self.task.id, 99999, self.admin_user  # Non-existent volunteer ID
            )
        
        # Test progress update with invalid completion ID
        with self.test_case.assertRaises(ValidationError):
            TaskManagementService.update_task_progress(
                99999, {'status': 'COMPLETED'}, self.admin_user
            )
        
        print("✓ Task validation and error handling test passed")
    
    def test_task_completion_validation(self):
        """Test task completion validation based on task type."""
        print("Testing task completion validation...")
        
        # Create photo task
        photo_task = Task.objects.create(
            title='Photo Task',
            description='Take a photo',
            task_type='PHOTO',
            role=self.role,
            event=self.event,
            priority='MEDIUM',
            created_by=self.admin_user
        )
        
        completion = TaskCompletion.objects.create(
            task=photo_task,
            volunteer=self.volunteer_profile,
            assigned_by=self.admin_user,
            status='IN_PROGRESS'
        )
        
        # Test completion without photo should fail
        with self.test_case.assertRaises(ValidationError):
            TaskManagementService.update_task_progress(
                completion.id,
                {'status': 'COMPLETED'},
                self.volunteer_user
            )
        
        # Test completion with photo should succeed
        TaskManagementService.update_task_progress(
            completion.id,
            {
                'status': 'COMPLETED',
                'completion_data': {'photo_url': 'https://example.com/photo.jpg'}
            },
            self.volunteer_user
        )
        
        completion.refresh_from_db()
        self.test_case.assertEqual(completion.status, 'COMPLETED')
        
        print("✓ Task completion validation test passed")
    
    def test_performance_and_caching(self):
        """Test performance optimizations and caching."""
        print("Testing performance and caching...")
        
        # Create multiple tasks and completions for performance testing
        tasks = []
        for i in range(10):
            task = Task.objects.create(
                title=f'Performance Task {i}',
                description=f'Task {i} for performance testing',
                task_type='CHECKBOX',
                role=self.role,
                event=self.event,
                priority='MEDIUM',
                created_by=self.admin_user
            )
            tasks.append(task)
            
            TaskCompletion.objects.create(
                task=task,
                volunteer=self.volunteer_profile,
                assigned_by=self.admin_user,
                status='COMPLETED' if i % 2 == 0 else 'IN_PROGRESS'
            )
        
        # Test analytics performance
        start_time = timezone.now()
        analytics = TaskManagementService.get_task_analytics()
        end_time = timezone.now()
        
        execution_time = (end_time - start_time).total_seconds()
        self.test_case.assertLess(execution_time, 5.0)  # Should complete within 5 seconds
        
        # Verify analytics data
        self.test_case.assertGreaterEqual(analytics['overview']['total_tasks'], 10)
        
        print(f"✓ Performance test passed (execution time: {execution_time:.2f}s)")
    
    def run_all_tests(self):
        """Run all task management tests."""
        print("=" * 60)
        print("RUNNING COMPREHENSIVE TASK MANAGEMENT TESTS")
        print("=" * 60)
        
        test_methods = [
            self.test_task_creation_service,
            self.test_task_assignment_workflow,
            self.test_bulk_task_assignment,
            self.test_task_progress_tracking,
            self.test_volunteer_task_retrieval,
            self.test_role_task_analysis,
            self.test_task_template_management,
            self.test_task_analytics_generation,
            self.test_task_dependencies,
            self.test_admin_interface_functionality,
            self.test_task_validation_and_error_handling,
            self.test_task_completion_validation,
            self.test_performance_and_caching
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_method in test_methods:
            try:
                test_method()
                passed_tests += 1
            except Exception as e:
                print(f"✗ {test_method.__name__} FAILED: {str(e)}")
                failed_tests += 1
        
        print("=" * 60)
        print(f"TASK MANAGEMENT TEST RESULTS")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Total: {len(test_methods)}")
        print("=" * 60)
        
        return passed_tests, failed_tests


class TaskManagementTestCase(TestCase):
    """Django test case for task management system."""
    
    def test_comprehensive_task_management(self):
        """Run comprehensive task management tests."""
        tester = TaskManagementTester(self)
        passed, failed = tester.run_all_tests()
        
        # Assert that all tests passed
        self.assertEqual(failed, 0, f"{failed} tests failed")
        self.assertGreater(passed, 0, "No tests were run")


class TaskManagementIntegrationTestCase(TestCase):
    """Integration tests for task management system."""
    
    def setUp(self):
        """Set up test data."""
        self.tester = TaskManagementTester(self)
        self.client = Client()
    
    def test_admin_task_management_view(self):
        """Test admin task management dashboard view."""
        self.client.force_login(self.tester.admin_user)
        
        response = self.client.get('/admin/tasks/task/task-management/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task Management Dashboard')
    
    def test_task_assignment_view(self):
        """Test task assignment view."""
        self.client.force_login(self.tester.admin_user)
        
        response = self.client.get(f'/admin/tasks/task/{self.tester.task.id}/assign-volunteers/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assign Volunteers')
    
    def test_bulk_assignment_view(self):
        """Test bulk assignment view."""
        self.client.force_login(self.tester.admin_user)
        
        response = self.client.get('/admin/tasks/task/bulk-assign/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bulk Task Assignment')
    
    def test_analytics_view(self):
        """Test analytics view."""
        self.client.force_login(self.tester.admin_user)
        
        response = self.client.get('/admin/tasks/task/analytics/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task Analytics')
    
    @patch('tasks.task_management_service.AdminAuditService.log_system_management_operation')
    def test_audit_logging_integration(self, mock_audit):
        """Test audit logging integration."""
        # Create task through service
        task_data = {
            'title': 'Audit Test Task',
            'description': 'Task for audit testing',
            'task_type': 'CHECKBOX',
            'priority': 'MEDIUM'
        }
        
        TaskManagementService.create_role_specific_task(
            self.tester.role.id, task_data, self.tester.admin_user
        )
        
        # Verify audit logging was called
        mock_audit.assert_called()
        call_args = mock_audit.call_args
        self.assertEqual(call_args[1]['operation'], 'task_creation')
        self.assertEqual(call_args[1]['user'], self.tester.admin_user)


if __name__ == '__main__':
    # Run tests directly
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.admin',
                'tasks',
                'events',
                'volunteers',
                'common',
            ],
            SECRET_KEY='test-secret-key',
            USE_TZ=True,
        )
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['__main__']) 