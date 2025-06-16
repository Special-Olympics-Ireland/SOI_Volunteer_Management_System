#!/usr/bin/env python
"""
Comprehensive test script for SOI Hub audit logging system.

This script tests:
- AdminAuditService functionality
- Audit logging for critical operations
- Admin interface audit integration
- Security event detection
- Report generation capabilities
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from common.models import AuditLog, AdminOverride
from common.audit_service import AdminAuditService
from volunteers.models import VolunteerProfile

User = get_user_model()


class AuditLoggingTester:
    """Comprehensive audit logging test suite."""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.test_user = None
        self.test_admin = None
        self.test_volunteer = None
        self.test_override = None
        
    def run_all_tests(self):
        """Run all audit logging tests."""
        print("🔍 Starting Comprehensive Audit Logging Tests")
        print("=" * 60)
        
        try:
            self.setup_test_data()
            self.test_audit_service_basic_operations()
            self.test_critical_operation_logging()
            self.test_bulk_operation_logging()
            self.test_data_export_logging()
            self.test_admin_override_logging()
            self.test_security_operation_logging()
            self.test_audit_summary_generation()
            self.test_security_alerts()
            self.test_audit_log_queries()
            self.cleanup_test_data()
            
            print("\n✅ All audit logging tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def setup_test_data(self):
        """Set up test data for audit logging tests."""
        print("\n📋 Setting up test data...")
        
        # Create or get test users
        self.test_user, created = User.objects.get_or_create(
            username='audit_test_user',
            defaults={
                'email': 'audit_test@example.com',
                'first_name': 'Audit',
                'last_name': 'Tester'
            }
        )
        if created:
            self.test_user.set_password('testpass123')
            self.test_user.save()
        
        self.test_admin, created = User.objects.get_or_create(
            username='audit_admin',
            defaults={
                'email': 'audit_admin@example.com',
                'first_name': 'Admin',
                'last_name': 'Tester',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            self.test_admin.set_password('adminpass123')
            self.test_admin.save()
        
        # Create or get test volunteer profile
        self.test_volunteer, created = VolunteerProfile.objects.get_or_create(
            user=self.test_user,
            defaults={
                'emergency_contact_name': 'Emergency Contact',
                'emergency_contact_phone': '+61412345678',
                'emergency_contact_relationship': 'Parent',
                'experience_level': 'BEGINNER',
                'availability_level': 'FLEXIBLE'
            }
        )
        
        print(f"✅ Created test users: {self.test_user.username}, {self.test_admin.username}")
        print(f"✅ Created test volunteer profile: {self.test_volunteer.id}")
    
    def test_audit_service_basic_operations(self):
        """Test basic AdminAuditService operations."""
        print("\n🔧 Testing AdminAuditService basic operations...")
        
        request = self.factory.post('/admin/test/')
        request.user = self.test_admin
        
        # Test user management operation logging
        AdminAuditService.log_user_management_operation(
            operation='user_create',
            user=self.test_admin,
            target_user=self.test_user,
            request=request,
            details={'test_operation': True}
        )
        
        # Test volunteer management operation logging
        AdminAuditService.log_volunteer_management_operation(
            operation='volunteer_create',
            user=self.test_admin,
            volunteer_profile=self.test_volunteer,
            request=request,
            details={'test_operation': True}
        )
        
        # Test system management operation logging
        AdminAuditService.log_system_management_operation(
            operation='system_test',
            user=self.test_admin,
            request=request,
            details={'test_operation': True}
        )
        
        # Verify audit logs were created
        recent_logs = AuditLog.objects.filter(
            user=self.test_admin,
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        )
        
        assert recent_logs.count() >= 3, f"Expected at least 3 audit logs, got {recent_logs.count()}"
        
        print("✅ Basic audit service operations logged successfully")
        
        # Display created logs
        for log in recent_logs:
            print(f"   📝 {log.action_type}: {log.action_description}")
    
    def test_critical_operation_logging(self):
        """Test critical operation logging."""
        print("\n🚨 Testing critical operation logging...")
        
        request = self.factory.post('/admin/critical/')
        request.user = self.test_admin
        
        # Test emergency access logging
        AdminAuditService.log_emergency_access(
            user=self.test_admin,
            access_type='emergency_override',
            justification='Testing emergency access logging',
            request=request,
            details={'emergency_test': True}
        )
        
        # Test permission change logging
        AdminAuditService.log_permission_change(
            user=self.test_admin,
            target_user=self.test_user,
            permission_change='grant_admin',
            permissions=['admin_access', 'staff_access'],
            request=request,
            details={'permission_test': True}
        )
        
        # Test system configuration change
        AdminAuditService.log_system_configuration_change(
            user=self.test_admin,
            config_key='test_config',
            old_value='old_value',
            new_value='new_value',
            request=request,
            details={'config_test': True}
        )
        
        # Verify critical operations were logged
        critical_logs = AuditLog.objects.filter(
            user=self.test_admin,
            metadata__critical_operation=True,
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        )
        
        assert critical_logs.count() >= 3, f"Expected at least 3 critical logs, got {critical_logs.count()}"
        
        print("✅ Critical operations logged successfully")
        
        # Display critical logs
        for log in critical_logs:
            print(f"   🚨 {log.action_type}: {log.action_description}")
    
    def test_bulk_operation_logging(self):
        """Test bulk operation logging."""
        print("\n📦 Testing bulk operation logging...")
        
        request = self.factory.post('/admin/bulk/')
        request.user = self.test_admin
        
        # Test bulk operation logging
        AdminAuditService.log_bulk_operation(
            operation='bulk_update_volunteers',
            user=self.test_admin,
            model_class=VolunteerProfile,
            affected_count=25,
            criteria={'status': 'active'},
            request=request,
            details={'bulk_test': True}
        )
        
        # Verify bulk operation was logged
        bulk_logs = AuditLog.objects.filter(
            user=self.test_admin,
            metadata__bulk_operation=True,
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        )
        
        assert bulk_logs.count() >= 1, f"Expected at least 1 bulk log, got {bulk_logs.count()}"
        
        bulk_log = bulk_logs.first()
        assert bulk_log.metadata['affected_count'] == 25
        assert bulk_log.metadata['model_name'] == 'VolunteerProfile'
        
        print("✅ Bulk operation logged successfully")
        print(f"   📦 {bulk_log.action_description}")
    
    def test_data_export_logging(self):
        """Test data export logging."""
        print("\n📤 Testing data export logging...")
        
        request = self.factory.get('/admin/export/')
        request.user = self.test_admin
        
        # Test data export logging
        AdminAuditService.log_data_export(
            user=self.test_admin,
            export_type='volunteer_data',
            model_class=VolunteerProfile,
            record_count=150,
            export_format='csv',
            request=request,
            details={'export_test': True}
        )
        
        # Verify export was logged
        export_logs = AuditLog.objects.filter(
            user=self.test_admin,
            metadata__data_export=True,
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        )
        
        assert export_logs.count() >= 1, f"Expected at least 1 export log, got {export_logs.count()}"
        
        export_log = export_logs.first()
        assert export_log.metadata['record_count'] == 150
        assert export_log.metadata['export_format'] == 'csv'
        
        print("✅ Data export logged successfully")
        print(f"   📤 {export_log.action_description}")
    
    def test_admin_override_logging(self):
        """Test admin override logging."""
        print("\n⚠️ Testing admin override logging...")
        
        request = self.factory.post('/admin/override/')
        request.user = self.test_admin
        
        # Create test admin override
        content_type = ContentType.objects.get_for_model(VolunteerProfile)
        self.test_override = AdminOverride.objects.create(
            override_type='AGE_REQUIREMENT',
            title='Test Age Override',
            description='Testing admin override logging',
            justification='Test justification for audit logging',
            content_type=content_type,
            object_id=str(self.test_volunteer.id),
            requested_by=self.test_admin,
            risk_level='MEDIUM',
            impact_level='LOW'
        )
        
        # Test admin override logging
        AdminAuditService.log_admin_override(
            user=self.test_admin,
            override_type='age_requirement_override',
            target_object=self.test_volunteer,
            justification='Testing admin override audit logging',
            original_value=15,
            new_value=14,
            request=request,
            details={'override_test': True}
        )
        
        # Verify override was logged
        override_logs = AuditLog.objects.filter(
            user=self.test_admin,
            metadata__admin_override=True,
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        )
        
        assert override_logs.count() >= 1, f"Expected at least 1 override log, got {override_logs.count()}"
        
        override_log = override_logs.first()
        assert override_log.metadata['override_type'] == 'age_requirement_override'
        assert override_log.metadata['original_value'] == 15
        assert override_log.metadata['new_value'] == 14
        
        print("✅ Admin override logged successfully")
        print(f"   ⚠️ {override_log.action_description}")
    
    def test_security_operation_logging(self):
        """Test security operation logging."""
        print("\n🔒 Testing security operation logging...")
        
        request = self.factory.post('/admin/security/')
        request.user = self.test_admin
        
        # Test security operation logging
        AdminAuditService.log_security_operation(
            operation='security_audit',
            user=self.test_admin,
            request=request,
            details={'security_test': True}
        )
        
        # Verify security operation was logged
        security_logs = AuditLog.objects.filter(
            user=self.test_admin,
            metadata__category='SECURITY_OPERATIONS',
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        )
        
        assert security_logs.count() >= 1, f"Expected at least 1 security log, got {security_logs.count()}"
        
        security_log = security_logs.first()
        assert security_log.metadata['category'] == 'SECURITY_OPERATIONS'
        
        print("✅ Security operation logged successfully")
        print(f"   🔒 {security_log.action_description}")
    
    def test_audit_summary_generation(self):
        """Test audit summary generation."""
        print("\n📊 Testing audit summary generation...")
        
        # Generate audit summary
        summary = AdminAuditService.get_audit_summary(days=1)
        
        # Verify summary structure
        required_keys = [
            'period_days', 'start_date', 'end_date', 'total_operations',
            'operations_by_type', 'operations_by_user', 'critical_operations',
            'security_events', 'failed_operations', 'top_users',
            'recent_critical_operations'
        ]
        
        for key in required_keys:
            assert key in summary, f"Missing key in summary: {key}"
        
        print("✅ Audit summary generated successfully")
        print(f"   📊 Total operations: {summary['total_operations']}")
        print(f"   📊 Critical operations: {summary['critical_operations']}")
        print(f"   📊 Security events: {summary['security_events']}")
        
        # Display top users
        if summary['top_users']:
            print("   👥 Top users:")
            for username, count in summary['top_users'][:3]:
                print(f"      - {username}: {count} operations")
    
    def test_security_alerts(self):
        """Test security alerts generation."""
        print("\n🚨 Testing security alerts generation...")
        
        # Generate security alerts
        alerts = AdminAuditService.get_security_alerts(hours=1)
        
        # Verify alerts structure
        if alerts:
            alert = alerts[0]
            required_keys = [
                'timestamp', 'user', 'action', 'description',
                'ip_address', 'severity', 'metadata'
            ]
            
            for key in required_keys:
                assert key in alert, f"Missing key in alert: {key}"
            
            print("✅ Security alerts generated successfully")
            print(f"   🚨 Total alerts: {len(alerts)}")
            
            # Display alerts by severity
            high_alerts = [a for a in alerts if a['severity'] == 'HIGH']
            medium_alerts = [a for a in alerts if a['severity'] == 'MEDIUM']
            low_alerts = [a for a in alerts if a['severity'] == 'LOW']
            
            print(f"   🚨 High severity: {len(high_alerts)}")
            print(f"   ⚠️ Medium severity: {len(medium_alerts)}")
            print(f"   ℹ️ Low severity: {len(low_alerts)}")
        else:
            print("✅ No security alerts found (expected for test environment)")
    
    def test_audit_log_queries(self):
        """Test audit log query functionality."""
        print("\n🔍 Testing audit log queries...")
        
        # Test various query patterns
        total_logs = AuditLog.objects.count()
        recent_logs = AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        admin_logs = AuditLog.objects.filter(user=self.test_admin).count()
        critical_logs = AuditLog.objects.filter(
            metadata__critical_operation=True
        ).count()
        
        bulk_logs = AuditLog.objects.filter(
            metadata__bulk_operation=True
        ).count()
        
        print("✅ Audit log queries executed successfully")
        print(f"   📊 Total logs: {total_logs}")
        print(f"   📊 Recent logs (1h): {recent_logs}")
        print(f"   📊 Admin logs: {admin_logs}")
        print(f"   📊 Critical logs: {critical_logs}")
        print(f"   📊 Bulk operation logs: {bulk_logs}")
        
        # Test performance of complex queries
        start_time = datetime.now()
        
        complex_query = AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).select_related('user', 'content_type').prefetch_related().order_by('-timestamp')[:100]
        
        list(complex_query)  # Force evaluation
        
        query_time = (datetime.now() - start_time).total_seconds()
        print(f"   ⚡ Complex query performance: {query_time:.3f}s")
        
        assert query_time < 1.0, f"Query too slow: {query_time:.3f}s"
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test audit logs
        test_logs = AuditLog.objects.filter(
            user__in=[self.test_user, self.test_admin],
            timestamp__gte=timezone.now() - timedelta(hours=1)
        )
        deleted_logs = test_logs.count()
        test_logs.delete()
        
        # Delete test objects
        if self.test_override:
            self.test_override.delete()
        
        if self.test_volunteer:
            self.test_volunteer.delete()
        
        if self.test_user:
            self.test_user.delete()
        
        if self.test_admin:
            self.test_admin.delete()
        
        print(f"✅ Cleaned up {deleted_logs} test audit logs")
        print("✅ Cleaned up test users and objects")


def main():
    """Run the audit logging test suite."""
    print("🔍 SOI Hub Audit Logging Test Suite")
    print("=" * 60)
    
    tester = AuditLoggingTester()
    tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("🎉 Audit logging test suite completed!")


if __name__ == '__main__':
    main() 