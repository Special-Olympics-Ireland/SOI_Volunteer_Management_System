import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from .models import Task
from events.models import Event, Venue, Role
from accounts.models import User

User = get_user_model()


class TaskModelTest(TestCase):
    """Comprehensive tests for Task model functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type=User.UserType.ADMIN
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event',
            slug='test-event',
            event_type=Event.EventType.INTERNATIONAL_GAMES,
            start_date=timezone.now().date() + timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=35),
            created_by=self.user
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            slug='test-venue',
            event=self.event,
            venue_type=Venue.VenueType.SPORTS_FACILITY,
            address_line_1='123 Test Street',
            city='Test City',
            county='Test County',
            postal_code='T12 3ST',
            created_by=self.user
        )
        
        # Create test role
        self.role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Test Role',
            slug='test-role',
            description='Test role description',
            role_type=Role.RoleType.VENUE_COORDINATOR,
            total_positions=10,
            created_by=self.user
        )
    
    def test_task_creation_basic(self):
        """Test basic task creation"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            venue=self.venue,
            title='Test Task',
            description='Test task description',
            task_type=Task.TaskType.CHECKBOX,
            created_by=self.user
        )
        
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.task_type, Task.TaskType.CHECKBOX)
        self.assertEqual(task.status, Task.TaskStatus.DRAFT)
        self.assertEqual(task.priority, Task.PriorityLevel.NORMAL)
        self.assertEqual(task.category, Task.TaskCategory.OTHER)
        self.assertIsInstance(task.id, uuid.UUID)
        self.assertTrue(task.task_configuration)  # Should have default config
    
    def test_task_creation_all_types(self):
        """Test creating tasks of all types"""
        task_types = [
            Task.TaskType.CHECKBOX,
            Task.TaskType.PHOTO,
            Task.TaskType.TEXT,
            Task.TaskType.CUSTOM
        ]
        
        for task_type in task_types:
            task = Task.objects.create(
                role=self.role,
                event=self.event,
                title=f'Test {task_type} Task',
                description=f'Test {task_type} description',
                task_type=task_type,
                created_by=self.user
            )
            
            self.assertEqual(task.task_type, task_type)
            self.assertTrue(task.task_configuration)
            
            # Check default configurations
            if task_type == Task.TaskType.CHECKBOX:
                self.assertIn('completion_text', task.task_configuration)
                self.assertIn('requires_confirmation', task.task_configuration)
            elif task_type == Task.TaskType.PHOTO:
                self.assertIn('max_photos', task.task_configuration)
                self.assertIn('allowed_formats', task.task_configuration)
            elif task_type == Task.TaskType.TEXT:
                self.assertIn('min_length', task.task_configuration)
                self.assertIn('max_length', task.task_configuration)
            elif task_type == Task.TaskType.CUSTOM:
                self.assertIn('fields', task.task_configuration)
    
    def test_task_string_representation(self):
        """Test task string representation"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            task_type=Task.TaskType.PHOTO,
            created_by=self.user
        )
        
        expected = f"Test Task (Photo Upload)"
        self.assertEqual(str(task), expected)
    
    def test_task_date_validation(self):
        """Test task date validation"""
        # Test valid dates
        start_date = timezone.now() + timedelta(days=1)
        due_date = timezone.now() + timedelta(days=5)
        
        task = Task(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            start_date=start_date,
            due_date=due_date,
            created_by=self.user
        )
        
        # Should not raise validation error
        task.clean()
        task.save()
        
        # Test invalid dates (start after due)
        task.start_date = timezone.now() + timedelta(days=10)
        task.due_date = timezone.now() + timedelta(days=5)
        
        with self.assertRaises(ValidationError):
            task.clean()
    
    def test_task_configuration_validation(self):
        """Test task configuration validation"""
        # Test photo task with invalid configuration
        task = Task(
            role=self.role,
            event=self.event,
            title='Photo Task',
            description='Test description',
            task_type=Task.TaskType.PHOTO,
            task_configuration={
                'min_photos': 5,
                'max_photos': 3  # Invalid: min > max
            },
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            task.clean()
        
        # Test text task with invalid configuration
        task = Task(
            role=self.role,
            event=self.event,
            title='Text Task',
            description='Test description',
            task_type=Task.TaskType.TEXT,
            task_configuration={
                'min_length': 1000,
                'max_length': 100  # Invalid: min > max
            },
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            task.clean()
    
    def test_task_status_management(self):
        """Test task status management methods"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            created_by=self.user
        )
        
        # Test activation
        self.assertEqual(task.status, Task.TaskStatus.DRAFT)
        task.activate(activated_by=self.user, reason='Testing activation')
        self.assertEqual(task.status, Task.TaskStatus.ACTIVE)
        self.assertEqual(task.status_changed_by, self.user)
        self.assertIsNotNone(task.status_changed_at)
        
        # Test suspension
        task.suspend(suspended_by=self.user, reason='Testing suspension')
        self.assertEqual(task.status, Task.TaskStatus.SUSPENDED)
        
        # Test completion
        task.complete(completed_by=self.user, reason='Testing completion')
        self.assertEqual(task.status, Task.TaskStatus.COMPLETED)
        
        # Test cancellation
        task.cancel(cancelled_by=self.user, reason='Testing cancellation')
        self.assertEqual(task.status, Task.TaskStatus.CANCELLED)
        
        # Test archiving
        task.archive(archived_by=self.user, reason='Testing archiving')
        self.assertEqual(task.status, Task.TaskStatus.ARCHIVED)
    
    def test_task_status_checking(self):
        """Test task status checking methods"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            created_by=self.user
        )
        
        # Test is_active
        self.assertFalse(task.is_active())
        task.activate()
        self.assertTrue(task.is_active())
        
        # Test is_available (active + no start date + no prerequisites)
        self.assertTrue(task.is_available())
        
        # Test with future start date
        task.start_date = timezone.now() + timedelta(days=1)
        task.due_date = timezone.now() + timedelta(days=2)  # Ensure due_date is after start_date
        task.save()
        self.assertFalse(task.is_available())
        
        # Test is_overdue - reset start_date to past and set due_date to past
        task.start_date = timezone.now() - timedelta(days=2)
        task.due_date = timezone.now() - timedelta(days=1)
        task.save()
        self.assertTrue(task.is_overdue())
        
        # Test is_due_soon
        task.due_date = timezone.now() + timedelta(days=2)
        task.save()
        self.assertTrue(task.is_due_soon(days=3))
        
        # Set due date further out to test false case
        task.due_date = timezone.now() + timedelta(days=5)
        task.save()
        self.assertFalse(task.is_due_soon(days=3))
    
    def test_task_prerequisites(self):
        """Test task prerequisite functionality"""
        # Create prerequisite task
        prereq_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Prerequisite Task',
            description='Must be completed first',
            created_by=self.user
        )
        
        # Create main task with prerequisite
        main_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Main Task',
            description='Requires prerequisite',
            created_by=self.user
        )
        main_task.prerequisite_tasks.add(prereq_task)
        
        # Test prerequisite checking
        self.assertFalse(main_task.are_prerequisites_met())
        
        # Activate prerequisite
        prereq_task.activate()
        self.assertTrue(main_task.are_prerequisites_met())
        
        # Test missing prerequisites
        missing = main_task.get_missing_prerequisites()
        self.assertEqual(len(missing), 0)  # All active now
    
    def test_task_circular_dependency_validation(self):
        """Test circular dependency validation"""
        task1 = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Task 1',
            description='First task',
            created_by=self.user
        )
        
        task2 = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Task 2',
            description='Second task',
            created_by=self.user
        )
        
        # Create valid dependency: task2 depends on task1
        task2.prerequisite_tasks.add(task1)
        task2.clean()  # Should not raise error
        
        # Try to create circular dependency: task1 depends on task2
        task1.prerequisite_tasks.add(task2)
        
        with self.assertRaises(ValidationError):
            task1.clean()
    
    def test_task_completion_tracking(self):
        """Test task completion tracking methods"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            created_by=self.user
        )
        
        # Test initial state
        self.assertEqual(task.total_completions, 0)
        self.assertEqual(task.verified_completions, 0)
        self.assertEqual(task.get_completion_rate(), 0)
        
        # Test increment completions
        task.increment_completions(verified=False)
        self.assertEqual(task.total_completions, 1)
        self.assertEqual(task.verified_completions, 0)
        
        task.increment_completions(verified=True)
        self.assertEqual(task.total_completions, 2)
        self.assertEqual(task.verified_completions, 1)
        self.assertEqual(task.get_completion_rate(), 50.0)
        
        # Test decrement completions
        task.decrement_completions(was_verified=True)
        self.assertEqual(task.total_completions, 1)
        self.assertEqual(task.verified_completions, 0)
    
    def test_task_configuration_methods(self):
        """Test task configuration management methods"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            task_type=Task.TaskType.PHOTO,
            created_by=self.user
        )
        
        # Test get_configuration
        max_photos = task.get_configuration('max_photos')
        self.assertEqual(max_photos, 3)  # Default value
        
        # Test set_configuration
        task.set_configuration('max_photos', 5)
        self.assertEqual(task.get_configuration('max_photos'), 5)
        
        # Test update_configuration
        task.update_configuration({
            'min_photos': 2,
            'max_file_size_mb': 10
        })
        self.assertEqual(task.get_configuration('min_photos'), 2)
        self.assertEqual(task.get_configuration('max_file_size_mb'), 10)
    
    def test_task_completion_data_validation(self):
        """Test completion data validation for different task types"""
        # Test checkbox task
        checkbox_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Checkbox Task',
            description='Test checkbox',
            task_type=Task.TaskType.CHECKBOX,
            created_by=self.user
        )
        
        # Valid completion
        errors = checkbox_task.validate_completion_data({'completed': True})
        self.assertEqual(len(errors), 0)
        
        # Invalid completion
        errors = checkbox_task.validate_completion_data({'completed': False})
        self.assertGreater(len(errors), 0)
        
        # Test photo task
        photo_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Photo Task',
            description='Test photo upload',
            task_type=Task.TaskType.PHOTO,
            created_by=self.user
        )
        
        # Valid completion (1-3 photos by default)
        errors = photo_task.validate_completion_data({'photos': ['photo1.jpg', 'photo2.jpg']})
        self.assertEqual(len(errors), 0)
        
        # Invalid completion (too many photos)
        errors = photo_task.validate_completion_data({'photos': ['1.jpg', '2.jpg', '3.jpg', '4.jpg']})
        self.assertGreater(len(errors), 0)
        
        # Test text task
        text_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Text Task',
            description='Test text submission',
            task_type=Task.TaskType.TEXT,
            created_by=self.user
        )
        
        # Valid completion (10-1000 chars by default)
        errors = text_task.validate_completion_data({'text': 'This is a valid text submission.'})
        self.assertEqual(len(errors), 0)
        
        # Invalid completion (too short)
        errors = text_task.validate_completion_data({'text': 'Short'})
        self.assertGreater(len(errors), 0)
    
    def test_task_clone_functionality(self):
        """Test task cloning functionality"""
        original_task = Task.objects.create(
            role=self.role,
            event=self.event,
            venue=self.venue,
            title='Original Task',
            description='Original description',
            task_type=Task.TaskType.PHOTO,
            category=Task.TaskCategory.TRAINING,
            priority=Task.PriorityLevel.HIGH,
            is_mandatory=True,
            created_by=self.user
        )
        
        # Create another role for cloning
        new_role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='New Role',
            slug='new-role',
            description='New role description',
            role_type=Role.RoleType.VENUE_COORDINATOR,
            total_positions=5,
            created_by=self.user
        )
        
        # Clone the task
        cloned_task = original_task.clone_for_role(new_role, created_by=self.user)
        
        # Verify cloned properties
        self.assertEqual(cloned_task.role, new_role)
        self.assertEqual(cloned_task.title, original_task.title)
        self.assertEqual(cloned_task.description, original_task.description)
        self.assertEqual(cloned_task.task_type, original_task.task_type)
        self.assertEqual(cloned_task.category, original_task.category)
        self.assertEqual(cloned_task.priority, original_task.priority)
        self.assertEqual(cloned_task.is_mandatory, original_task.is_mandatory)
        self.assertNotEqual(cloned_task.id, original_task.id)
    
    def test_task_utility_methods(self):
        """Test task utility methods"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Test Task',
            description='Test description',
            estimated_duration_minutes=90,
            due_date=timezone.now() + timedelta(days=5),
            created_by=self.user
        )
        
        # Test duration display
        duration = task.get_estimated_duration_display()
        self.assertEqual(duration, '1h 30m')
        
        # Test days until due
        days_until_due = task.get_days_until_due()
        self.assertEqual(days_until_due, 4)  # Should be 4 days (rounded down)
        
        # Test to_dict
        task_dict = task.to_dict()
        self.assertIn('id', task_dict)
        self.assertIn('title', task_dict)
        self.assertIn('task_type', task_dict)
        self.assertEqual(task_dict['title'], 'Test Task')
    
    def test_task_ordering(self):
        """Test task ordering"""
        # Create tasks with different priorities and display orders
        task1 = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Task 1',
            description='First task',
            display_order=2,
            priority=Task.PriorityLevel.LOW,
            created_by=self.user
        )
        
        task2 = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Task 2',
            description='Second task',
            display_order=1,
            priority=Task.PriorityLevel.HIGH,
            created_by=self.user
        )
        
        # Test ordering (display_order, priority, due_date, title)
        tasks = list(Task.objects.all())
        self.assertEqual(tasks[0], task2)  # Lower display_order comes first
        self.assertEqual(tasks[1], task1)
    
    def test_task_indexes_and_performance(self):
        """Test that database indexes are working (basic check)"""
        # Create multiple tasks for different scenarios
        for i in range(10):
            Task.objects.create(
                role=self.role,
                event=self.event,
                title=f'Task {i}',
                description=f'Description {i}',
                task_type=Task.TaskType.CHECKBOX if i % 2 == 0 else Task.TaskType.PHOTO,
                status=Task.TaskStatus.ACTIVE if i % 3 == 0 else Task.TaskStatus.DRAFT,
                created_by=self.user
            )
        
        # Test queries that should use indexes
        active_tasks = Task.objects.filter(status=Task.TaskStatus.ACTIVE)
        self.assertGreater(len(active_tasks), 0)
        
        role_tasks = Task.objects.filter(role=self.role)
        self.assertEqual(len(role_tasks), 10)
        
        checkbox_tasks = Task.objects.filter(task_type=Task.TaskType.CHECKBOX)
        self.assertGreater(len(checkbox_tasks), 0)
    
    def test_task_edge_cases(self):
        """Test edge cases and error conditions"""
        # Test task without venue (should be allowed)
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            venue=None,  # No venue
            title='No Venue Task',
            description='Task without venue',
            created_by=self.user
        )
        self.assertIsNone(task.venue)
        
        # Test task with minimal data
        minimal_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Minimal Task',
            description='Minimal description'
        )
        self.assertIsNotNone(minimal_task.id)
        self.assertEqual(minimal_task.status, Task.TaskStatus.DRAFT)
        
        # Test task configuration edge cases
        task_with_empty_config = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Empty Config Task',
            description='Task with empty config',
            task_configuration={}
        )
        # Should get default config on save
        self.assertTrue(task_with_empty_config.task_configuration)
    
    def test_task_foreign_key_relationships(self):
        """Test foreign key relationships and cascading"""
        task = Task.objects.create(
            role=self.role,
            event=self.event,
            venue=self.venue,
            title='Relationship Test Task',
            description='Testing relationships',
            created_by=self.user
        )
        
        # Test relationships exist
        self.assertEqual(task.role, self.role)
        self.assertEqual(task.event, self.event)
        self.assertEqual(task.venue, self.venue)
        self.assertEqual(task.created_by, self.user)
        
        # Test reverse relationships
        self.assertIn(task, self.role.tasks.all())
        self.assertIn(task, self.event.tasks.all())
        self.assertIn(task, self.venue.tasks.all())
        self.assertIn(task, self.user.created_tasks.all()) 