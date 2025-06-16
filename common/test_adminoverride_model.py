from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

from accounts.models import User
from events.models import Event, Venue, Role
from common.models import AdminOverride


class AdminOverrideModelTest(TestCase):
    """Test cases for AdminOverride model"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type=User.UserType.ADMIN
        )
        
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@test.com',
            password='testpass123',
            first_name='Staff',
            last_name='User',
            user_type=User.UserType.STAFF
        )
        
        self.volunteer_user = User.objects.create_user(
            username='volunteer_user',
            email='volunteer@test.com',
            password='testpass123',
            first_name='Volunteer',
            last_name='User',
            user_type=User.UserType.VOLUNTEER
        )
        
        # Create test event for target object
        self.event = Event.objects.create(
            name='Test Event',
            slug='test-event',
            short_name='TE2024',
            description='Test event description',
            event_type=Event.EventType.INTERNATIONAL_GAMES,
            status=Event.EventStatus.PLANNING,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=35),
            created_by=self.admin_user
        )
        
        # Get content type for event
        self.event_content_type = ContentType.objects.get_for_model(Event)
    
    def test_adminoverride_creation_basic(self):
        """Test basic admin override creation"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.AGE_REQUIREMENT,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Age Requirement Override',
            description='Override minimum age requirement for special case',
            justification='Volunteer has extensive experience despite being under minimum age',
            requested_by=self.staff_user
        )
        
        self.assertEqual(override.override_type, AdminOverride.OverrideType.AGE_REQUIREMENT)
        self.assertEqual(override.status, AdminOverride.OverrideStatus.PENDING)
        self.assertEqual(override.target_object, self.event)
        self.assertEqual(override.title, 'Age Requirement Override')
        self.assertEqual(override.requested_by, self.staff_user)
        self.assertEqual(override.risk_level, AdminOverride.RiskLevel.MEDIUM)
        self.assertEqual(override.impact_level, AdminOverride.ImpactLevel.LOW)
        self.assertEqual(override.priority_level, 5)
        self.assertFalse(override.is_emergency)
        self.assertTrue(override.requires_monitoring)
        self.assertTrue(override.documentation_required)
        self.assertFalse(override.documentation_provided)
    
    def test_adminoverride_status_workflow(self):
        """Test admin override status workflow"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.CAPACITY_LIMIT,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Capacity Override',
            description='Increase venue capacity for special circumstances',
            justification='Additional safety measures implemented',
            requested_by=self.staff_user
        )
        
        # Test initial status
        self.assertTrue(override.is_pending())
        self.assertFalse(override.is_approved())
        self.assertFalse(override.is_active())
        self.assertFalse(override.is_effective())
        
        # Test approval
        override.approve(self.admin_user, 'Approved after safety review')
        self.assertTrue(override.is_approved())
        self.assertFalse(override.is_pending())
        self.assertEqual(override.approved_by, self.admin_user)
        self.assertEqual(override.approval_notes, 'Approved after safety review')
        self.assertIsNotNone(override.approved_at)
        self.assertIsNotNone(override.effective_from)
        
        # Test activation
        override.activate(self.admin_user)
        self.assertTrue(override.is_active())
        self.assertTrue(override.is_effective())
        self.assertIsNotNone(override.applied_at)
        
        # Test completion
        override.complete(self.admin_user)
        self.assertEqual(override.status, AdminOverride.OverrideStatus.COMPLETED)
        self.assertFalse(override.is_active())
    
    def test_adminoverride_rejection_workflow(self):
        """Test admin override rejection workflow"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.CREDENTIAL_REQUIREMENT,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Credential Override',
            description='Bypass credential requirement',
            justification='Emergency situation requires immediate action',
            requested_by=self.staff_user
        )
        
        # Test rejection
        override.reject(self.admin_user, 'Insufficient justification provided')
        self.assertEqual(override.status, AdminOverride.OverrideStatus.REJECTED)
        self.assertEqual(override.rejection_reason, 'Insufficient justification provided')
        self.assertIsNotNone(override.status_changed_at)
        self.assertEqual(override.status_changed_by, self.admin_user)
    
    def test_adminoverride_revocation(self):
        """Test admin override revocation"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.DEADLINE_EXTENSION,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Deadline Extension',
            description='Extend registration deadline',
            justification='Technical issues prevented timely registration',
            requested_by=self.staff_user
        )
        
        # Approve and activate
        override.approve(self.admin_user)
        override.activate(self.admin_user)
        
        # Test revocation
        override.revoke(self.admin_user, 'No longer needed due to system fix')
        self.assertTrue(override.is_revoked())
        self.assertEqual(override.status_change_reason, 'No longer needed due to system fix')
        self.assertIsNotNone(override.revoked_at)
    
    def test_adminoverride_validation(self):
        """Test admin override validation"""
        # Test effective date validation
        override = AdminOverride(
            override_type=AdminOverride.OverrideType.STATUS_CHANGE,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Status Change Override',
            description='Change event status',
            justification='Special circumstances require status change',
            requested_by=self.staff_user,
            effective_from=timezone.now() + timedelta(days=5),
            effective_until=timezone.now() + timedelta(days=2)  # Invalid: until before from
        )
        
        with self.assertRaises(ValidationError):
            override.clean()
    
    def test_adminoverride_high_risk_validation(self):
        """Test validation for high-risk overrides"""
        # Test high-risk override without justification
        override = AdminOverride(
            override_type=AdminOverride.OverrideType.SYSTEM_RULE,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='System Rule Override',
            description='Override critical system rule',
            justification='',  # Empty justification
            risk_level=AdminOverride.RiskLevel.HIGH,
            requested_by=self.staff_user
        )
        
        with self.assertRaises(ValidationError):
            override.clean()
        
        # Test with proper justification
        override.justification = 'Detailed justification for high-risk override with mitigation measures'
        override.clean()  # Should not raise exception
    
    def test_adminoverride_priority_validation(self):
        """Test priority level validation"""
        # Test invalid priority level - database constraint should prevent this
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            override = AdminOverride.objects.create(
                override_type=AdminOverride.OverrideType.OTHER,
                content_type=self.event_content_type,
                object_id=str(self.event.id),
                title='Test Override',
                description='Test description',
                justification='Test justification',
                priority_level=15,  # Invalid: > 10
                requested_by=self.staff_user
            )
    
    def test_adminoverride_emergency_handling(self):
        """Test emergency override handling"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.EMERGENCY_ACCESS,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Emergency Access Override',
            description='Emergency access required for critical situation',
            justification='System failure requires immediate administrative access',
            is_emergency=True,
            priority_level=1,
            requires_immediate_action=True,
            risk_level=AdminOverride.RiskLevel.CRITICAL,
            impact_level=AdminOverride.ImpactLevel.HIGH,
            requested_by=self.staff_user
        )
        
        self.assertTrue(override.is_emergency)
        self.assertTrue(override.requires_immediate_action)
        self.assertEqual(override.priority_level, 1)
        self.assertEqual(override.risk_level, AdminOverride.RiskLevel.CRITICAL)
        self.assertEqual(override.impact_level, AdminOverride.ImpactLevel.HIGH)
    
    def test_adminoverride_expiration(self):
        """Test override expiration functionality"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.VERIFICATION_BYPASS,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Verification Bypass',
            description='Temporary bypass of verification requirement',
            justification='Time-sensitive situation requires immediate action',
            effective_from=timezone.now() - timedelta(hours=1),
            effective_until=timezone.now() - timedelta(minutes=30),  # Already expired
            requested_by=self.staff_user
        )
        
        # Approve and activate
        override.approve(self.admin_user)
        override.activate(self.admin_user)
        
        # Test expiration detection
        self.assertTrue(override.is_expired())
        self.assertFalse(override.is_effective())
        self.assertIsNone(override.get_time_remaining())
    
    def test_adminoverride_duration_calculation(self):
        """Test override duration calculation"""
        start_time = timezone.now()
        end_time = start_time + timedelta(days=7)
        
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.ROLE_RESTRICTION,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Role Restriction Override',
            description='Temporary role restriction override',
            justification='Special circumstances require role flexibility',
            effective_from=start_time,
            effective_until=end_time,
            requested_by=self.staff_user
        )
        
        self.assertEqual(override.get_duration(), 7)
    
    def test_adminoverride_communication_log(self):
        """Test communication log functionality"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.DATA_MODIFICATION,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Data Modification Override',
            description='Override data validation rules',
            justification='Correction of historical data requires rule bypass',
            requested_by=self.staff_user
        )
        
        # Test adding communication log entry
        override.add_communication_log('Initial review completed', self.admin_user)
        
        self.assertEqual(len(override.communication_log), 1)
        self.assertEqual(override.communication_log[0]['message'], 'Initial review completed')
        self.assertEqual(override.communication_log[0]['user'], self.admin_user.get_full_name())
        self.assertEqual(override.communication_log[0]['user_id'], str(self.admin_user.id))
        
        # Test adding another entry
        override.add_communication_log('Additional documentation requested', self.staff_user)
        self.assertEqual(len(override.communication_log), 2)
    
    def test_adminoverride_monitoring_update(self):
        """Test monitoring update functionality"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.PREREQUISITE_SKIP,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Prerequisite Skip Override',
            description='Skip prerequisite requirements',
            justification='Equivalent experience demonstrated through alternative means',
            requires_monitoring=True,
            monitoring_frequency='DAILY',
            requested_by=self.staff_user
        )
        
        # Test monitoring update
        override.update_monitoring('Daily monitoring check completed - no issues found', self.admin_user)
        
        self.assertIsNotNone(override.last_monitored_at)
        self.assertEqual(override.monitoring_notes, 'Daily monitoring check completed - no issues found')
        self.assertEqual(len(override.communication_log), 1)
    
    def test_adminoverride_to_dict(self):
        """Test override dictionary conversion"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.ASSIGNMENT_RULE,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Assignment Rule Override',
            description='Override assignment validation rules',
            justification='Special assignment requirements for experienced volunteer',
            risk_level=AdminOverride.RiskLevel.LOW,
            impact_level=AdminOverride.ImpactLevel.MINIMAL,
            priority_level=3,
            is_emergency=False,
            requested_by=self.staff_user
        )
        
        override_dict = override.to_dict()
        
        self.assertEqual(override_dict['id'], str(override.id))
        self.assertEqual(override_dict['override_type'], AdminOverride.OverrideType.ASSIGNMENT_RULE)
        self.assertEqual(override_dict['override_type_display'], 'Assignment Rule Override')
        self.assertEqual(override_dict['status'], AdminOverride.OverrideStatus.PENDING)
        self.assertEqual(override_dict['status_display'], 'Pending Approval')
        self.assertEqual(override_dict['title'], 'Assignment Rule Override')
        self.assertEqual(override_dict['risk_level'], AdminOverride.RiskLevel.LOW)
        self.assertEqual(override_dict['impact_level'], AdminOverride.ImpactLevel.MINIMAL)
        self.assertEqual(override_dict['priority_level'], 3)
        self.assertFalse(override_dict['is_emergency'])
        self.assertEqual(override_dict['requested_by'], self.staff_user.get_full_name())
        self.assertIsNone(override_dict['approved_by'])
        self.assertFalse(override_dict['is_effective'])
    
    def test_adminoverride_string_representation(self):
        """Test string representation of override"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.CAPACITY_LIMIT,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Test Capacity Override',
            description='Test override description',
            justification='Test justification',
            requested_by=self.staff_user
        )
        
        expected_str = f"Capacity Limit Override - Test Capacity Override (Pending Approval)"
        self.assertEqual(str(override), expected_str)
    
    def test_adminoverride_save_auto_population(self):
        """Test automatic field population on save"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.STATUS_CHANGE,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Status Change Override',
            description='Change event status',
            justification='Administrative requirement for status change',
            requested_by=self.staff_user
        )
        
        # Approve the override
        override.status = AdminOverride.OverrideStatus.APPROVED
        override.save()
        
        # Check that effective_from was auto-populated
        self.assertIsNotNone(override.effective_from)
        
        # Activate the override
        override.status = AdminOverride.OverrideStatus.ACTIVE
        override.save()
        
        # Check that applied_at was auto-populated
        self.assertIsNotNone(override.applied_at)
    
    def test_adminoverride_complex_workflow(self):
        """Test complex override workflow with multiple status changes"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.SYSTEM_RULE,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Complex System Override',
            description='Complex override requiring multiple approvals',
            justification='Critical system modification required for event success',
            risk_level=AdminOverride.RiskLevel.HIGH,
            impact_level=AdminOverride.ImpactLevel.HIGH,
            priority_level=2,
            business_case='Business case for critical system modification',
            risk_assessment='Detailed risk assessment with mitigation strategies',
            impact_assessment='Comprehensive impact analysis on all stakeholders',
            compliance_notes='Compliance review completed with legal team',
            regulatory_impact='No regulatory impact identified',
            requires_monitoring=True,
            monitoring_frequency='HOURLY',
            requested_by=self.staff_user
        )
        
        # Add communication log entries
        override.add_communication_log('Initial request submitted', self.staff_user)
        override.add_communication_log('Risk assessment completed', self.admin_user)
        
        # Approve with detailed notes
        override.approve(self.admin_user, 'Approved after thorough risk assessment and stakeholder review')
        
        # Activate
        override.activate(self.admin_user)
        
        # Update monitoring
        override.update_monitoring('Hourly monitoring - system stable', self.admin_user)
        
        # Verify final state
        self.assertTrue(override.is_active())
        self.assertTrue(override.is_effective())
        self.assertEqual(len(override.communication_log), 3)  # 2 manual + 1 from monitoring
        self.assertIsNotNone(override.last_monitored_at)
        self.assertEqual(override.monitoring_frequency, 'HOURLY')
    
    def test_adminoverride_metadata_and_tags(self):
        """Test metadata and tags functionality"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.OTHER,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Tagged Override',
            description='Override with metadata and tags',
            justification='Testing metadata functionality',
            tags=['urgent', 'system-critical', 'temporary'],
            external_references={
                'ticket_id': 'TICKET-12345',
                'approval_id': 'APPROVAL-67890'
            },
            custom_fields={
                'department': 'IT Operations',
                'cost_center': 'CC-1001',
                'estimated_duration': '2 hours'
            },
            requested_by=self.staff_user
        )
        
        self.assertEqual(override.tags, ['urgent', 'system-critical', 'temporary'])
        self.assertEqual(override.external_references['ticket_id'], 'TICKET-12345')
        self.assertEqual(override.custom_fields['department'], 'IT Operations')
    
    def test_adminoverride_notification_tracking(self):
        """Test notification and stakeholder tracking"""
        override = AdminOverride.objects.create(
            override_type=AdminOverride.OverrideType.EMERGENCY_ACCESS,
            content_type=self.event_content_type,
            object_id=str(self.event.id),
            title='Emergency Access Override',
            description='Emergency access for critical incident',
            justification='Critical incident requires immediate system access',
            is_emergency=True,
            stakeholders_notified=[
                'security@example.com',
                'operations@example.com',
                'management@example.com'
            ],
            notification_sent=True,
            requested_by=self.staff_user
        )
        
        self.assertTrue(override.notification_sent)
        self.assertEqual(len(override.stakeholders_notified), 3)
        self.assertIn('security@example.com', override.stakeholders_notified) 