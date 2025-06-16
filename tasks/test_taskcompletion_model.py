"""
Comprehensive tests for TaskCompletion model functionality.
Tests cover status management, verification workflow, time tracking, data management, and validation.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from accounts.models import User
from events.models import Event, Venue, Role, Assignment
from tasks.models import Task, TaskCompletion


class TaskCompletionModelTest(TestCase):
    """Test TaskCompletion model functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.volunteer_user = User.objects.create_user(
            username='volunteer_user',
            email='volunteer@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Volunteer',
            user_type=User.UserType.VOLUNTEER
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Staff',
            user_type=User.UserType.STAFF
        )
        
        # Create test event
        self.event = Event.objects.create(
            name='Test Event 2026',
            slug='test-event-2026',
            start_date=timezone.now().date() + timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=35),
            created_by=self.staff_user
        )
        
        # Create test venue
        self.venue = Venue.objects.create(
            event=self.event,
            name='Test Venue',
            slug='test-venue',
            address_line_1='123 Test Street',
            city='Test City',
            created_by=self.staff_user
        )
        
        # Create test role
        self.role = Role.objects.create(
            event=self.event,
            venue=self.venue,
            name='Test Role',
            description='Test role description',
            role_type=Role.RoleType.GENERAL_VOLUNTEER,
            total_positions=10,
            created_by=self.staff_user
        )
        
        # Create test assignment
        self.assignment = Assignment.objects.create(
            volunteer=self.volunteer_user,
            role=self.role,
            event=self.event,
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=32),
            assigned_by=self.staff_user
        )
        
        # Create test task
        self.task = Task.objects.create(
            role=self.role,
            event=self.event,
            venue=self.venue,
            title='Test Task',
            description='Test task description',
            task_type=Task.TaskType.CHECKBOX,
            created_by=self.staff_user
        )
    
    def test_taskcompletion_creation_basic(self):
        """Test basic task completion creation"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            assignment=self.assignment,
            completion_data={'completed': True}
        )
        
        self.assertEqual(completion.task, self.task)
        self.assertEqual(completion.volunteer, self.volunteer_user)
        self.assertEqual(completion.assignment, self.assignment)
        self.assertEqual(completion.status, TaskCompletion.CompletionStatus.PENDING)
        self.assertEqual(completion.completion_type, TaskCompletion.CompletionType.CHECKBOX)
        self.assertFalse(completion.requires_verification)
        self.assertEqual(completion.revision_count, 0)
    
    def test_taskcompletion_creation_all_types(self):
        """Test creating completions for all task types"""
        task_types = [
            (Task.TaskType.CHECKBOX, TaskCompletion.CompletionType.CHECKBOX, {'completed': True}),
            (Task.TaskType.PHOTO, TaskCompletion.CompletionType.PHOTO_UPLOAD, {'photos': ['photo1.jpg']}),
            (Task.TaskType.TEXT, TaskCompletion.CompletionType.TEXT_SUBMISSION, {'text': 'Test submission'}),
            (Task.TaskType.CUSTOM, TaskCompletion.CompletionType.CUSTOM_FIELDS, {'field1': 'value1'}),
        ]
        
        for task_type, expected_completion_type, completion_data in task_types:
            with self.subTest(task_type=task_type):
                task = Task.objects.create(
                    role=self.role,
                    event=self.event,
                    title=f'Test {task_type} Task',
                    description='Test description',
                    task_type=task_type,
                    created_by=self.staff_user
                )
                
                completion = TaskCompletion.objects.create(
                    task=task,
                    volunteer=self.volunteer_user,
                    completion_data=completion_data
                )
                
                self.assertEqual(completion.completion_type, expected_completion_type)
                self.assertEqual(completion.completion_data, completion_data)
    
    def test_taskcompletion_string_representation(self):
        """Test task completion string representation"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        expected = f"{self.volunteer_user.get_full_name()} - {self.task.title} (Pending Submission)"
        self.assertEqual(str(completion), expected)
    
    def test_taskcompletion_status_management(self):
        """Test task completion status management methods"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Test submit
        self.assertTrue(completion.is_pending())
        completion.submit(submitted_by=self.volunteer_user)
        self.assertTrue(completion.is_submitted())
        self.assertIsNotNone(completion.submitted_at)
        
        # Test approve
        completion.approve(approved_by=self.staff_user, notes='Good work')
        self.assertTrue(completion.is_approved())
        self.assertIsNotNone(completion.completed_at)
        self.assertEqual(completion.verification_notes, 'Good work')
        
        # Test verify
        completion.verify(verified_by=self.staff_user, quality_score=5, notes='Excellent')
        self.assertTrue(completion.is_verified())
        self.assertEqual(completion.verified_by, self.staff_user)
        self.assertIsNotNone(completion.verified_at)
        self.assertEqual(completion.quality_score, 5)
    
    def test_taskcompletion_rejection_workflow(self):
        """Test task completion rejection workflow"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Submit and reject
        completion.submit(submitted_by=self.volunteer_user)
        completion.reject(rejected_by=self.staff_user, reason='Insufficient evidence')
        
        self.assertTrue(completion.is_rejected())
        self.assertEqual(completion.status_change_reason, 'Insufficient evidence')
        self.assertEqual(completion.status_changed_by, self.staff_user)
    
    def test_taskcompletion_revision_workflow(self):
        """Test task completion revision workflow"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Submit and request revision
        completion.submit(submitted_by=self.volunteer_user)
        completion.request_revision(requested_by=self.staff_user, notes='Please add more details')
        
        self.assertTrue(completion.needs_revision())
        self.assertEqual(completion.revision_count, 1)
        self.assertEqual(completion.revision_notes, 'Please add more details')
        
        # Test create revision
        revision = completion.create_revision(revised_by=self.volunteer_user)
        self.assertEqual(revision.previous_completion, completion)
        self.assertEqual(revision.revision_count, 2)
        self.assertEqual(revision.task, completion.task)
        self.assertEqual(revision.volunteer, completion.volunteer)
    
    def test_taskcompletion_time_tracking(self):
        """Test task completion time tracking"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Test start work
        completion.start_work()
        self.assertIsNotNone(completion.time_started)
        
        # Test calculate time spent
        completion.completed_at = timezone.now() + timedelta(minutes=30)
        time_spent = completion.calculate_time_spent()
        self.assertIsNotNone(time_spent)
        self.assertGreaterEqual(time_spent, 29)  # Allow for small timing differences
        self.assertLessEqual(time_spent, 31)
        
        # Test time display
        completion.time_spent_minutes = 90
        self.assertEqual(completion.get_time_spent_display(), '1h 30m')
        
        completion.time_spent_minutes = 60
        self.assertEqual(completion.get_time_spent_display(), '1h')
        
        completion.time_spent_minutes = 30
        self.assertEqual(completion.get_time_spent_display(), '30m')
    
    def test_taskcompletion_data_management(self):
        """Test task completion data management methods"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True, 'notes': 'Initial notes'}
        )
        
        # Test get completion data
        self.assertTrue(completion.get_completion_data('completed'))
        self.assertEqual(completion.get_completion_data('notes'), 'Initial notes')
        self.assertIsNone(completion.get_completion_data('nonexistent'))
        self.assertEqual(completion.get_completion_data('nonexistent', 'default'), 'default')
        
        # Test set completion data
        completion.set_completion_data('quality', 'excellent')
        self.assertEqual(completion.get_completion_data('quality'), 'excellent')
        
        # Test update completion data
        completion.update_completion_data({
            'notes': 'Updated notes',
            'additional_info': 'Extra information'
        })
        self.assertEqual(completion.get_completion_data('notes'), 'Updated notes')
        self.assertEqual(completion.get_completion_data('additional_info'), 'Extra information')
    
    def test_taskcompletion_photo_management(self):
        """Test task completion photo management"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'photos': ['photo1.jpg', 'photo2.jpg']}
        )
        
        # Test accessing photos from completion_data
        photos = completion.get_completion_data('photos', [])
        self.assertEqual(photos, ['photo1.jpg', 'photo2.jpg'])
        
        # Test add photo using the actual add_photo method
        completion.add_photo('photo3.jpg', 'Test photo 3')
        self.assertEqual(len(completion.photos), 1)
        self.assertEqual(completion.photos[0]['url'], 'photo3.jpg')
        self.assertEqual(completion.photos[0]['description'], 'Test photo 3')
    
    def test_taskcompletion_attachment_management(self):
        """Test task completion attachment management"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'attachments': ['doc1.pdf']}
        )
        
        # Test accessing attachments from completion_data
        attachments = completion.get_completion_data('attachments', [])
        self.assertEqual(attachments, ['doc1.pdf'])
        
        # Test add attachment using the actual add_attachment method
        completion.add_attachment('doc2.pdf', 'document2.pdf', 'application/pdf')
        self.assertEqual(len(completion.attachments), 1)
        self.assertEqual(completion.attachments[0]['url'], 'doc2.pdf')
        self.assertEqual(completion.attachments[0]['filename'], 'document2.pdf')
        self.assertEqual(completion.attachments[0]['file_type'], 'application/pdf')
    
    def test_taskcompletion_verification_requirements(self):
        """Test task completion verification requirements"""
        # Create task requiring verification
        verification_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Verification Required Task',
            description='Task requiring verification',
            task_type=Task.TaskType.PHOTO,
            requires_verification=True,
            created_by=self.staff_user
        )
        
        completion = TaskCompletion.objects.create(
            task=verification_task,
            volunteer=self.volunteer_user,
            completion_data={'photos': ['evidence.jpg']}
        )
        
        self.assertTrue(completion.requires_verification)
        self.assertFalse(completion.is_verified())
        
        # First submit the completion
        completion.submit(submitted_by=self.volunteer_user)
        self.assertTrue(completion.is_submitted())
        
        # Then approve the completion
        completion.approve(approved_by=self.staff_user)
        self.assertTrue(completion.is_approved())
        
        # Then verify completion
        completion.verify(verified_by=self.staff_user, quality_score=4)
        self.assertTrue(completion.is_verified())
        self.assertEqual(completion.quality_score, 4)
    
    def test_taskcompletion_validation(self):
        """Test task completion validation"""
        # Test invalid quality score
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        with self.assertRaises(ValidationError):
            completion.quality_score = 6  # Invalid score (max is 5)
            completion.full_clean()
        
        with self.assertRaises(ValidationError):
            completion.quality_score = 0  # Invalid score (min is 1)
            completion.full_clean()
        
        # Test valid quality scores
        for score in [1, 2, 3, 4, 5]:
            completion.quality_score = score
            completion.full_clean()  # Should not raise
        
        # Test time spent validation
        with self.assertRaises(ValidationError):
            completion.time_spent_minutes = -1  # Invalid negative time
            completion.full_clean()
        
        # Test valid time spent
        completion.time_spent_minutes = 30
        completion.full_clean()  # Should not raise
    
    def test_taskcompletion_status_checking_methods(self):
        """Test task completion status checking methods"""
        completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Test initial status
        self.assertTrue(completion.is_pending())
        self.assertFalse(completion.is_submitted())
        self.assertFalse(completion.is_approved())
        self.assertFalse(completion.is_rejected())
        self.assertFalse(completion.needs_revision())
        self.assertFalse(completion.is_verified())
        
        # Test submitted status
        completion.status = TaskCompletion.CompletionStatus.SUBMITTED
        completion.save()
        self.assertFalse(completion.is_pending())
        self.assertTrue(completion.is_submitted())
        
        # Test approved status
        completion.status = TaskCompletion.CompletionStatus.APPROVED
        completion.save()
        self.assertTrue(completion.is_approved())
        
        # Test rejected status
        completion.status = TaskCompletion.CompletionStatus.REJECTED
        completion.save()
        self.assertTrue(completion.is_rejected())
        
        # Test needs revision status
        completion.status = TaskCompletion.CompletionStatus.REVISION_REQUIRED
        completion.save()
        self.assertTrue(completion.needs_revision())
        
        # Test verified status
        completion.status = TaskCompletion.CompletionStatus.VERIFIED
        completion.save()
        self.assertTrue(completion.is_verified())
    
    def test_taskcompletion_unique_constraint(self):
        """Test task completion unique constraint"""
        # Create first completion
        TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Try to create duplicate - should raise ValidationError
        with self.assertRaises(ValidationError):
            duplicate = TaskCompletion(
                task=self.task,
                volunteer=self.volunteer_user,
                completion_data={'completed': False}
            )
            duplicate.full_clean()
    
    def test_taskcompletion_to_dict(self):
        """Test task completion to_dict method"""
        # Create a task that requires verification
        verification_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Verification Task',
            description='Task requiring verification',
            task_type=Task.TaskType.PHOTO,
            requires_verification=True,
            created_by=self.staff_user
        )
        
        completion = TaskCompletion.objects.create(
            task=verification_task,
            volunteer=self.volunteer_user,
            assignment=self.assignment,
            completion_data={'completed': True, 'notes': 'Test notes'},
            quality_score=4,
            time_spent_minutes=45
        )
        
        result = completion.to_dict()
        
        # Check required fields that actually exist in the to_dict method
        self.assertEqual(result['id'], str(completion.id))
        self.assertEqual(result['task_id'], str(verification_task.id))
        self.assertEqual(result['task_title'], verification_task.title)
        self.assertEqual(result['volunteer_name'], self.volunteer_user.get_full_name())
        self.assertEqual(result['status'], completion.status)
        self.assertEqual(result['completion_type'], completion.completion_type)
        self.assertEqual(result['quality_score'], 4)
        self.assertEqual(result['time_spent'], '45m')
        self.assertEqual(result['revision_count'], 0)
        self.assertTrue(result['requires_verification'])
        self.assertFalse(result['is_complete'])
    
    def test_taskcompletion_task_counter_integration(self):
        """Test task completion integration with task counters"""
        # Create multiple completions for the same task
        volunteers = []
        for i in range(3):
            volunteer = User.objects.create_user(
                username=f'volunteer{i}',
                email=f'volunteer{i}@test.com',
                password='testpass123',
                first_name=f'Volunteer{i}',
                last_name='Test',
                user_type=User.UserType.VOLUNTEER
            )
            volunteers.append(volunteer)
            
            # Create assignment for each volunteer
            assignment = Assignment.objects.create(
                volunteer=volunteer,
                role=self.role,
                event=self.event,
                venue=self.venue,
                assigned_by=self.staff_user
            )
            
            # Create completion
            TaskCompletion.objects.create(
                task=self.task,
                volunteer=volunteer,
                assignment=assignment,
                completion_data={'completed': True}
            )
        
        # Check task completion counts
        total_completions = TaskCompletion.objects.filter(task=self.task).count()
        self.assertEqual(total_completions, 3)
        
        # Check status-specific counts
        pending_count = TaskCompletion.objects.filter(
            task=self.task,
            status=TaskCompletion.CompletionStatus.PENDING
        ).count()
        self.assertEqual(pending_count, 3)
    
    def test_taskcompletion_prerequisite_integration(self):
        """Test task completion integration with task prerequisites"""
        # Create prerequisite task
        prerequisite_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Prerequisite Task',
            description='Must be completed first',
            task_type=Task.TaskType.CHECKBOX,
            created_by=self.staff_user
        )
        
        # Create dependent task
        dependent_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='Dependent Task',
            description='Depends on prerequisite',
            task_type=Task.TaskType.CHECKBOX,
            created_by=self.staff_user
        )
        dependent_task.prerequisite_tasks.add(prerequisite_task)
        
        # Complete prerequisite task
        prerequisite_completion = TaskCompletion.objects.create(
            task=prerequisite_task,
            volunteer=self.volunteer_user,
            assignment=self.assignment,
            completion_data={'completed': True}
        )
        prerequisite_completion.approve(approved_by=self.staff_user)
        
        # Now complete dependent task
        dependent_completion = TaskCompletion.objects.create(
            task=dependent_task,
            volunteer=self.volunteer_user,
            assignment=self.assignment,
            completion_data={'completed': True}
        )
        
        # Both completions should exist
        self.assertTrue(TaskCompletion.objects.filter(task=prerequisite_task).exists())
        self.assertTrue(TaskCompletion.objects.filter(task=dependent_task).exists())
    
    def test_taskcompletion_edge_cases(self):
        """Test task completion edge cases"""
        # Test completion without assignment
        completion_no_assignment = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        self.assertIsNone(completion_no_assignment.assignment)
        
        # Test completion with minimal data
        minimal_completion = TaskCompletion.objects.create(
            task=self.task,
            volunteer=self.volunteer_user,
            completion_data={}
        )
        self.assertEqual(minimal_completion.completion_data, {})
        
        # Test string representation with long task title
        long_title_task = Task.objects.create(
            role=self.role,
            event=self.event,
            title='A' * 100,  # Very long title
            description='Long title task',
            task_type=Task.TaskType.CHECKBOX,
            created_by=self.staff_user
        )
        
        long_title_completion = TaskCompletion.objects.create(
            task=long_title_task,
            volunteer=self.volunteer_user,
            completion_data={'completed': True}
        )
        
        # Should not raise exception
        str_repr = str(long_title_completion)
        self.assertIsInstance(str_repr, str)
    
    def test_taskcompletion_ordering(self):
        """Test task completion ordering"""
        # Create multiple completions at different times
        completions = []
        for i in range(3):
            completion = TaskCompletion.objects.create(
                task=self.task,
                volunteer=self.volunteer_user,
                completion_data={'completed': True, 'order': i}
            )
            completions.append(completion)
            
            # Simulate time passing
            if i > 0:
                completion.created_at = timezone.now() + timedelta(minutes=i)
                completion.save()
        
        # Test default ordering (most recent first)
        ordered_completions = list(TaskCompletion.objects.filter(task=self.task))
        
        # Should be ordered by creation time (newest first)
        for i in range(len(ordered_completions) - 1):
            self.assertGreaterEqual(
                ordered_completions[i].created_at,
                ordered_completions[i + 1].created_at
            ) 