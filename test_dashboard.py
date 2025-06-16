#!/usr/bin/env python
"""
Comprehensive test script for SOI Hub Dashboard system.

This script tests:
- DashboardService functionality
- Dashboard views and templates
- API endpoints and data formats
- Real-time statistics and KPIs
- Performance and caching
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.urls import reverse

from common.dashboard_service import DashboardService
from common.models import AuditLog, AdminOverride
from volunteers.models import VolunteerProfile
from events.models import Event, Role, Assignment
from tasks.models import Task, TaskCompletion

User = get_user_model()


class DashboardTester:
    """Comprehensive dashboard test suite."""
    
    def __init__(self):
        self.client = Client()
        self.test_user = None
        self.test_admin = None
        
    def run_all_tests(self):
        """Run all dashboard tests."""
        print("🎯 Starting Comprehensive Dashboard Tests")
        print("=" * 60)
        
        try:
            self.setup_test_data()
            self.test_dashboard_service()
            self.test_dashboard_views()
            self.test_dashboard_api_endpoints()
            self.test_kpi_calculations()
            self.test_caching_performance()
            self.test_real_time_updates()
            self.cleanup_test_data()
            
            print("\n✅ All dashboard tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def setup_test_data(self):
        """Set up test data for dashboard tests."""
        print("\n📋 Setting up test data...")
        
        # Create test users
        self.test_user, created = User.objects.get_or_create(
            username='dashboard_test_user',
            defaults={
                'email': 'dashboard_test@example.com',
                'first_name': 'Dashboard',
                'last_name': 'Tester'
            }
        )
        
        self.test_admin, created = User.objects.get_or_create(
            username='dashboard_admin',
            defaults={
                'email': 'dashboard_admin@example.com',
                'first_name': 'Dashboard',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # Create test volunteer profiles
        for i in range(5):
            volunteer, created = VolunteerProfile.objects.get_or_create(
                user=self.test_user,
                defaults={
                    'emergency_contact_name': f'Emergency Contact {i}',
                    'emergency_contact_phone': f'+61412345{i:03d}',
                    'emergency_contact_relationship': 'Parent',
                    'experience_level': 'BEGINNER',
                    'availability_level': 'FLEXIBLE',
                    'status': 'ACTIVE' if i < 3 else 'PENDING'
                }
            )
            if created:
                break  # Only create one per user
        
        # Create test audit logs
        for i in range(10):
            AuditLog.objects.create(
                action_type='TEST_ACTION',
                action_description=f'Test action {i}',
                user=self.test_admin,
                ip_address='127.0.0.1',
                duration_ms=100 + i * 10,
                response_status=200 if i < 8 else 500,
                metadata={
                    'test_data': True,
                    'critical_operation': i < 3,
                    'category': 'SYSTEM_MANAGEMENT'
                }
            )
        
        print(f"✅ Created test data for dashboard testing")
    
    def test_dashboard_service(self):
        """Test DashboardService functionality."""
        print("\n🔧 Testing DashboardService...")
        
        # Test dashboard overview
        overview = DashboardService.get_dashboard_overview(user=self.test_admin)
        
        # Verify overview structure
        required_keys = [
            'timestamp', 'volunteer_metrics', 'event_metrics', 'assignment_metrics',
            'task_metrics', 'system_metrics', 'integration_metrics', 'performance_metrics',
            'recent_activity', 'alerts_and_notifications', 'trends', 'kpis'
        ]
        
        for key in required_keys:
            assert key in overview, f"Missing key in overview: {key}"
        
        print("✅ Dashboard overview structure validated")
        
        # Test individual metric methods
        volunteer_metrics = DashboardService.get_volunteer_metrics()
        assert 'total_volunteers' in volunteer_metrics
        assert 'status_distribution' in volunteer_metrics
        print("✅ Volunteer metrics working")
        
        system_metrics = DashboardService.get_system_metrics()
        assert 'total_users' in system_metrics
        assert 'system_health' in system_metrics
        print("✅ System metrics working")
        
        kpis = DashboardService.get_key_performance_indicators()
        assert len(kpis) > 0
        print("✅ KPI calculations working")
        
        # Test alerts and notifications
        alerts = DashboardService.get_alerts_and_notifications()
        assert 'alerts' in alerts
        assert 'total_alerts' in alerts
        print("✅ Alerts and notifications working")
        
        # Test recent activity
        activity = DashboardService.get_recent_activity(limit=5)
        assert len(activity) <= 5
        if activity:
            assert 'timestamp' in activity[0]
            assert 'action' in activity[0]
            assert 'user' in activity[0]
        print("✅ Recent activity working")
        
        print("✅ DashboardService tests completed successfully")
    
    def test_dashboard_views(self):
        """Test dashboard views and templates."""
        print("\n🌐 Testing dashboard views...")
        
        # Login as admin
        self.client.force_login(self.test_admin)
        
        # Test main dashboard view
        response = self.client.get('/admin/common/dashboard/')
        assert response.status_code == 200, f"Dashboard view failed: {response.status_code}"
        print("✅ Main dashboard view accessible")
        
        # Test volunteer dashboard
        response = self.client.get('/admin/common/dashboard/volunteers/')
        assert response.status_code == 200, f"Volunteer dashboard failed: {response.status_code}"
        print("✅ Volunteer dashboard view accessible")
        
        # Test event dashboard
        response = self.client.get('/admin/common/dashboard/events/')
        assert response.status_code == 200, f"Event dashboard failed: {response.status_code}"
        print("✅ Event dashboard view accessible")
        
        # Test system dashboard
        response = self.client.get('/admin/common/dashboard/system/')
        assert response.status_code == 200, f"System dashboard failed: {response.status_code}"
        print("✅ System dashboard view accessible")
        
        print("✅ Dashboard views tests completed successfully")
    
    def test_dashboard_api_endpoints(self):
        """Test dashboard API endpoints."""
        print("\n🔌 Testing dashboard API endpoints...")
        
        # Login as admin
        self.client.force_login(self.test_admin)
        
        # Test main API endpoint
        response = self.client.get('/admin/common/dashboard/api/')
        assert response.status_code == 200, f"Dashboard API failed: {response.status_code}"
        
        data = response.json()
        assert data['success'] == True
        assert 'data' in data
        assert 'timestamp' in data
        print("✅ Main dashboard API working")
        
        # Test metrics API endpoints
        metric_types = ['volunteers', 'events', 'assignments', 'tasks', 'system', 'integrations', 'performance', 'kpis']
        
        for metric_type in metric_types:
            response = self.client.get(f'/admin/common/dashboard/api/metrics/{metric_type}/')
            assert response.status_code == 200, f"Metrics API failed for {metric_type}: {response.status_code}"
            
            data = response.json()
            assert data['success'] == True
            assert data['metric_type'] == metric_type
            assert 'data' in data
        
        print("✅ Metrics API endpoints working")
        
        # Test alerts API
        response = self.client.get('/admin/common/dashboard/api/alerts/')
        assert response.status_code == 200, f"Alerts API failed: {response.status_code}"
        
        data = response.json()
        assert data['success'] == True
        assert 'data' in data
        print("✅ Alerts API working")
        
        # Test activity API
        response = self.client.get('/admin/common/dashboard/api/activity/?limit=10')
        assert response.status_code == 200, f"Activity API failed: {response.status_code}"
        
        data = response.json()
        assert data['success'] == True
        assert 'data' in data
        assert data['limit'] == 10
        print("✅ Activity API working")
        
        # Test trends API
        response = self.client.get('/admin/common/dashboard/api/trends/')
        assert response.status_code == 200, f"Trends API failed: {response.status_code}"
        
        data = response.json()
        assert data['success'] == True
        assert 'data' in data
        print("✅ Trends API working")
        
        print("✅ Dashboard API endpoints tests completed successfully")
    
    def test_kpi_calculations(self):
        """Test KPI calculation accuracy."""
        print("\n📊 Testing KPI calculations...")
        
        kpis = DashboardService.get_key_performance_indicators()
        
        # Test KPI structure
        for kpi_name, kpi_data in kpis.items():
            assert isinstance(kpi_data, dict), f"KPI {kpi_name} should be a dictionary"
            assert 'status' in kpi_data, f"KPI {kpi_name} missing status"
            assert 'target' in kpi_data, f"KPI {kpi_name} missing target"
            
            # Score can be None for no data
            if kpi_data['score'] is not None:
                assert isinstance(kpi_data['score'], (int, float)), f"KPI {kpi_name} score should be numeric"
        
        print("✅ KPI structure validation passed")
        
        # Test specific KPI calculations
        volunteer_satisfaction = kpis.get('volunteer_satisfaction')
        if volunteer_satisfaction:
            assert volunteer_satisfaction['target'] == 4.0
            print("✅ Volunteer satisfaction KPI configured correctly")
        
        system_uptime = kpis.get('system_uptime')
        if system_uptime:
            assert system_uptime['target'] == 99.9
            print("✅ System uptime KPI configured correctly")
        
        print("✅ KPI calculations tests completed successfully")
    
    def test_caching_performance(self):
        """Test dashboard caching and performance."""
        print("\n⚡ Testing caching and performance...")
        
        # Clear cache
        cache.clear()
        
        # First call (should cache)
        start_time = datetime.now()
        overview1 = DashboardService.get_dashboard_overview(user=self.test_admin)
        first_call_time = (datetime.now() - start_time).total_seconds()
        
        # Second call (should use cache)
        start_time = datetime.now()
        overview2 = DashboardService.get_dashboard_overview(user=self.test_admin)
        second_call_time = (datetime.now() - start_time).total_seconds()
        
        # Cache should make second call faster
        assert second_call_time < first_call_time, "Caching should improve performance"
        print(f"✅ Caching working: First call {first_call_time:.3f}s, Second call {second_call_time:.3f}s")
        
        # Test cache refresh
        response = self.client.get('/admin/common/dashboard/refresh-cache/')
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] == True
        print("✅ Cache refresh working")
        
        print("✅ Caching and performance tests completed successfully")
    
    def test_real_time_updates(self):
        """Test real-time update functionality."""
        print("\n🔄 Testing real-time updates...")
        
        # Get initial metrics
        initial_metrics = DashboardService.get_volunteer_metrics()
        initial_count = initial_metrics['total_volunteers']
        
        # Create new volunteer profile (simulate real-time change)
        new_user = User.objects.create_user(
            username='realtime_test_user',
            email='realtime@example.com'
        )
        
        VolunteerProfile.objects.create(
            user=new_user,
            emergency_contact_name='Real Time Contact',
            emergency_contact_phone='+61412999999',
            emergency_contact_relationship='Parent',
            experience_level='BEGINNER',
            availability_level='FLEXIBLE'
        )
        
        # Clear cache to force refresh
        cache.clear()
        
        # Get updated metrics
        updated_metrics = DashboardService.get_volunteer_metrics()
        updated_count = updated_metrics['total_volunteers']
        
        # Verify the change is reflected
        assert updated_count > initial_count, "Real-time updates should reflect new data"
        print(f"✅ Real-time updates working: {initial_count} -> {updated_count}")
        
        # Clean up
        new_user.delete()
        
        print("✅ Real-time updates tests completed successfully")
    
    def test_export_functionality(self):
        """Test dashboard export functionality."""
        print("\n📤 Testing export functionality...")
        
        # Login as admin
        self.client.force_login(self.test_admin)
        
        # Test JSON export
        response = self.client.get('/admin/common/dashboard/export/overview/?format=json')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        print("✅ JSON export working")
        
        # Test CSV export
        response = self.client.get('/admin/common/dashboard/export/volunteers/?format=csv')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        print("✅ CSV export working")
        
        # Test KPI export
        response = self.client.get('/admin/common/dashboard/export/kpis/?format=json')
        assert response.status_code == 200
        print("✅ KPI export working")
        
        print("✅ Export functionality tests completed successfully")
    
    def test_error_handling(self):
        """Test error handling in dashboard."""
        print("\n🚨 Testing error handling...")
        
        # Test invalid metric type
        response = self.client.get('/admin/common/dashboard/api/metrics/invalid_type/')
        assert response.status_code == 400
        
        data = response.json()
        assert data['success'] == False
        assert 'error' in data
        print("✅ Invalid metric type handled correctly")
        
        # Test invalid export type
        response = self.client.get('/admin/common/dashboard/export/invalid_type/')
        assert response.status_code == 400
        print("✅ Invalid export type handled correctly")
        
        # Test unauthorized access
        self.client.logout()
        response = self.client.get('/admin/common/dashboard/')
        assert response.status_code == 302  # Redirect to login
        print("✅ Unauthorized access handled correctly")
        
        print("✅ Error handling tests completed successfully")
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test audit logs
        AuditLog.objects.filter(
            action_type='TEST_ACTION',
            metadata__test_data=True
        ).delete()
        
        # Delete test users (cascade will handle profiles)
        User.objects.filter(
            username__in=['dashboard_test_user', 'dashboard_admin', 'realtime_test_user']
        ).delete()
        
        # Clear cache
        cache.clear()
        
        print("✅ Test data cleaned up")


def main():
    """Run the dashboard test suite."""
    print("🎯 SOI Hub Dashboard Test Suite")
    print("=" * 60)
    
    tester = DashboardTester()
    tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("🎉 Dashboard test suite completed!")


if __name__ == '__main__':
    main() 