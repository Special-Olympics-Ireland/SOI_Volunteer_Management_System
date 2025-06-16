import json
import os
import tempfile
from datetime import datetime, timedelta
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from reporting.models import Report, ReportTemplate, ReportSchedule, ReportMetrics, ReportShare
from reporting.services import generate_report
from volunteers.models import VolunteerProfile
from events.models import Event, Venue, Assignment
from tasks.models import Task, TaskCompletion

User = get_user_model()


class ReportAPITestCase(APITestCase):
    """Test case for Report API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.vmt_user = User.objects.create_user(
            email='vmt@test.com',
            password='testpass123',
            first_name='VMT',
            last_name='User',
            user_type='VMT'
        )
        
        self.volunteer_user = User.objects.create_user(
            email='volunteer@test.com',
            password='testpass123',
            first_name='Volunteer',
            last_name='User',
            user_type='VOLUNTEER'
        )
        
        # Create test reports
        self.report1 = Report.objects.create(
            name='Test Report 1',
            description='Test description',
            report_type='VOLUNTEER_SUMMARY',
            export_format='CSV',
            status='COMPLETED',
            created_by=self.admin_user,
            total_records=100,
            file_path='/tmp/test_report.csv',
            file_size=1024
        )
        
        self.report2 = Report.objects.create(
            name='Test Report 2',
            description='Another test report',
            report_type='EVENT_SUMMARY',
            export_format='EXCEL',
            status='GENERATING',
            progress_percentage=50,
            created_by=self.vmt_user
        )
        
        # Create test template
        self.template = ReportTemplate.objects.create(
            name='Test Template',
            description='Test template description',
            report_type='VOLUNTEER_SUMMARY',
            default_parameters={'status_filter': 'ACTIVE'},
            default_export_format='CSV',
            is_public=True,
            created_by=self.admin_user
        )
        
        self.client = APIClient()
    
    def test_report_list_admin(self):
        """Test report list endpoint for admin user"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Check response structure
        report_data = response.data['results'][0]
        expected_fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'status', 'status_display', 'export_format', 'created_by_name',
            'created_at', 'file_size_display', 'download_url'
        ]
        for field in expected_fields:
            self.assertIn(field, report_data)
    
    def test_report_list_volunteer(self):
        """Test report list endpoint for volunteer user (should see no reports)"""
        self.client.force_authenticate(user=self.volunteer_user)
        
        url = '/api/reporting/reports/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_report_create(self):
        """Test report creation"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/'
        data = {
            'name': 'New Test Report',
            'description': 'New test description',
            'report_type': 'VOLUNTEER_DETAILED',
            'export_format': 'PDF',
            'parameters': {'status_filter': 'ACTIVE'}
        }
        
        with patch('reporting.views.generate_report') as mock_generate:
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.count(), 3)
        
        # Check created report
        new_report = Report.objects.get(name='New Test Report')
        self.assertEqual(new_report.created_by, self.admin_user)
        self.assertEqual(new_report.status, 'PENDING')
        
        # Check that generation was started
        mock_generate.assert_called_once()
    
    def test_report_create_volunteer_forbidden(self):
        """Test that volunteers cannot create reports"""
        self.client.force_authenticate(user=self.volunteer_user)
        
        url = '/api/reporting/reports/'
        data = {
            'name': 'Forbidden Report',
            'report_type': 'VOLUNTEER_SUMMARY',
            'export_format': 'CSV'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_report_detail(self):
        """Test report detail endpoint"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/reports/{self.report1.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Report 1')
        self.assertEqual(response.data['status'], 'COMPLETED')
        
        # Check detailed fields
        detailed_fields = ['parameters', 'file_path', 'generation_time', 'metrics', 'shares']
        for field in detailed_fields:
            self.assertIn(field, response.data)
    
    def test_report_progress(self):
        """Test report progress endpoint"""
        self.client.force_authenticate(user=self.vmt_user)
        
        url = f'/api/reporting/reports/{self.report2.id}/progress/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['report_id'], str(self.report2.id))
        self.assertEqual(response.data['status'], 'GENERATING')
        self.assertEqual(response.data['progress_percentage'], 50)
    
    def test_report_regenerate(self):
        """Test report regeneration"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/reports/{self.report1.id}/regenerate/'
        
        with patch('reporting.views.generate_report') as mock_generate:
            response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that report was reset
        self.report1.refresh_from_db()
        self.assertEqual(self.report1.status, 'PENDING')
        self.assertEqual(self.report1.progress_percentage, 0)
        
        # Check that generation was started
        mock_generate.assert_called_once()
    
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_report_download(self, mock_open, mock_exists):
        """Test report download"""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_open.return_value = mock_file
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/reports/{self.report1.id}/download/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_exists.assert_called_once_with('/tmp/test_report.csv')
        mock_open.assert_called_once()
    
    def test_report_download_not_ready(self):
        """Test download of report that's not ready"""
        self.client.force_authenticate(user=self.vmt_user)
        
        url = f'/api/reporting/reports/{self.report2.id}/download/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not ready', response.data['error'])
    
    def test_report_share_creation(self):
        """Test creating a report share"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/reports/{self.report1.id}/share/'
        data = {
            'share_type': 'LINK',
            'can_download': True,
            'expires_at': (timezone.now() + timedelta(days=7)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReportShare.objects.count(), 1)
        
        share = ReportShare.objects.first()
        self.assertEqual(share.report, self.report1)
        self.assertEqual(share.created_by, self.admin_user)
    
    def test_report_metrics(self):
        """Test report metrics endpoint"""
        # Create metrics for report
        ReportMetrics.objects.create(
            report=self.report1,
            rows_processed=100,
            columns_included=10,
            data_completeness_percent=95.5,
            download_count=5
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/reports/{self.report1.id}/metrics/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rows_processed'], 100)
        self.assertEqual(response.data['columns_included'], 10)
        self.assertEqual(response.data['data_completeness_percent'], 95.5)
        self.assertEqual(response.data['download_count'], 5)
    
    def test_bulk_operations_delete(self):
        """Test bulk delete operation"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/bulk-operations/'
        data = {
            'report_ids': [str(self.report1.id), str(self.report2.id)],
            'action': 'delete'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Report.objects.count(), 0)
        self.assertIn('Deleted 2 reports', response.data['results'])
    
    def test_bulk_operations_regenerate(self):
        """Test bulk regenerate operation"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/bulk-operations/'
        data = {
            'report_ids': [str(self.report1.id)],
            'action': 'regenerate'
        }
        
        with patch('reporting.views.generate_report') as mock_generate:
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate.assert_called_once()
    
    def test_report_types(self):
        """Test report types endpoint"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/types/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        
        # Check structure of first report type
        report_type = response.data[0]
        expected_fields = [
            'report_type', 'display_name', 'description',
            'required_parameters', 'optional_parameters',
            'supported_formats', 'estimated_generation_time'
        ]
        for field in expected_fields:
            self.assertIn(field, report_type)
    
    def test_report_filtering(self):
        """Test report filtering"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Test filter by report type
        url = '/api/reporting/reports/'
        response = self.client.get(url, {'report_type': 'VOLUNTEER_SUMMARY'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['report_type'], 'VOLUNTEER_SUMMARY')
        
        # Test filter by status
        response = self.client.get(url, {'status': 'COMPLETED'})
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'COMPLETED')
    
    def test_report_search(self):
        """Test report search functionality"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/'
        response = self.client.get(url, {'search': 'Test Report 1'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Report 1')


class ReportTemplateAPITestCase(APITestCase):
    """Test case for Report Template API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.volunteer_user = User.objects.create_user(
            email='volunteer@test.com',
            password='testpass123',
            user_type='VOLUNTEER'
        )
        
        self.template = ReportTemplate.objects.create(
            name='Test Template',
            description='Test template',
            report_type='VOLUNTEER_SUMMARY',
            default_parameters={'status_filter': 'ACTIVE'},
            is_public=True,
            created_by=self.admin_user
        )
        
        self.client = APIClient()
    
    def test_template_list(self):
        """Test template list endpoint"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/templates/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Template')
    
    def test_template_create(self):
        """Test template creation"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/templates/'
        data = {
            'name': 'New Template',
            'description': 'New template description',
            'report_type': 'EVENT_SUMMARY',
            'default_parameters': {'venue_filter': 'all'},
            'default_export_format': 'EXCEL',
            'is_public': False
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReportTemplate.objects.count(), 2)
        
        new_template = ReportTemplate.objects.get(name='New Template')
        self.assertEqual(new_template.created_by, self.admin_user)
    
    def test_template_use(self):
        """Test using template to create report"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/templates/{self.template.id}/use/'
        data = {
            'name': 'Report from Template',
            'description': 'Generated from template',
            'parameters': {'additional_param': 'value'}
        }
        
        with patch('reporting.views.generate_report') as mock_generate:
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that template usage was incremented
        self.template.refresh_from_db()
        self.assertEqual(self.template.usage_count, 1)
        
        # Check created report
        report = Report.objects.get(name='Report from Template')
        self.assertEqual(report.report_type, self.template.report_type)
        self.assertIn('status_filter', report.parameters)
        self.assertIn('additional_param', report.parameters)


class AnalyticsAPITestCase(APITestCase):
    """Test case for Analytics API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.volunteer_user = User.objects.create_user(
            email='volunteer@test.com',
            password='testpass123',
            user_type='VOLUNTEER'
        )
        
        # Create test data for analytics
        VolunteerProfile.objects.create(
            user=self.volunteer_user,
            status='ACTIVE'
        )
        
        self.client = APIClient()
    
    def test_dashboard_admin(self):
        """Test dashboard endpoint for admin user"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/analytics/dashboard/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that all sections are present for admin
        expected_sections = ['volunteers', 'events', 'assignments', 'tasks', 'reports', 'system']
        for section in expected_sections:
            self.assertIn(section, response.data)
        
        # Check volunteer stats structure
        volunteer_stats = response.data['volunteers']
        self.assertIn('total', volunteer_stats)
        self.assertIn('active', volunteer_stats)
        self.assertIn('pending', volunteer_stats)
        self.assertIn('approval_rate', volunteer_stats)
    
    def test_dashboard_volunteer(self):
        """Test dashboard endpoint for volunteer user"""
        self.client.force_authenticate(user=self.volunteer_user)
        
        url = '/api/reporting/analytics/dashboard/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only allowed sections are present for volunteer
        expected_sections = ['volunteers', 'events', 'tasks']
        for section in expected_sections:
            self.assertIn(section, response.data)
        
        # Check that restricted sections are not present
        restricted_sections = ['reports', 'system']
        for section in restricted_sections:
            self.assertNotIn(section, response.data)
    
    def test_trends(self):
        """Test trends endpoint"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/analytics/trends/'
        response = self.client.get(url, {'period': '7'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check trends structure
        expected_trends = ['volunteer_registrations', 'report_generations', 'task_completions']
        for trend in expected_trends:
            self.assertIn(trend, response.data)
            self.assertIsInstance(response.data[trend], list)
            self.assertEqual(len(response.data[trend]), 7)  # 7 days
            
            # Check daily data structure
            if response.data[trend]:
                daily_data = response.data[trend][0]
                self.assertIn('date', daily_data)
                self.assertIn('count', daily_data)


class ReportPermissionTestCase(APITestCase):
    """Test case for report permissions"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.vmt_user = User.objects.create_user(
            email='vmt@test.com',
            password='testpass123',
            user_type='VMT'
        )
        
        self.volunteer_user = User.objects.create_user(
            email='volunteer@test.com',
            password='testpass123',
            user_type='VOLUNTEER'
        )
        
        self.report = Report.objects.create(
            name='Test Report',
            report_type='VOLUNTEER_SUMMARY',
            created_by=self.vmt_user
        )
        
        self.client = APIClient()
    
    def test_admin_can_access_all_reports(self):
        """Test that admin can access all reports"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = f'/api/reporting/reports/{self.report.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_vmt_can_access_own_reports(self):
        """Test that VMT can access their own reports"""
        self.client.force_authenticate(user=self.vmt_user)
        
        url = f'/api/reporting/reports/{self.report.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_volunteer_cannot_access_others_reports(self):
        """Test that volunteers cannot access other users' reports"""
        self.client.force_authenticate(user=self.volunteer_user)
        
        url = f'/api/reporting/reports/{self.report.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access reports"""
        url = '/api/reporting/reports/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_bulk_operations_permission(self):
        """Test bulk operations permission"""
        # Admin should be able to perform bulk operations
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/reporting/reports/bulk-operations/'
        data = {
            'report_ids': [str(self.report.id)],
            'action': 'delete'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Volunteer should not be able to perform bulk operations
        self.client.force_authenticate(user=self.volunteer_user)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ReportIntegrationTestCase(APITestCase):
    """Integration tests for reporting system"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='ADMIN',
            is_staff=True
        )
        
        # Create test data for reports
        self.volunteer_profile = VolunteerProfile.objects.create(
            user=self.admin_user,
            status='ACTIVE'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_end_to_end_report_generation(self):
        """Test complete report generation workflow"""
        # 1. Create report
        url = '/api/reporting/reports/'
        data = {
            'name': 'Integration Test Report',
            'description': 'End-to-end test',
            'report_type': 'VOLUNTEER_SUMMARY',
            'export_format': 'CSV'
        }
        
        with patch('reporting.views.generate_report') as mock_generate:
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report_id = response.data['id']
        
        # 2. Check progress
        progress_url = f'/api/reporting/reports/{report_id}/progress/'
        response = self.client.get(progress_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Simulate completion
        report = Report.objects.get(id=report_id)
        report.status = 'COMPLETED'
        report.file_path = '/tmp/test_report.csv'
        report.save()
        
        # 4. Create share
        share_url = f'/api/reporting/reports/{report_id}/share/'
        share_data = {
            'share_type': 'LINK',
            'can_download': True
        }
        response = self.client.post(share_url, share_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 5. Check metrics
        ReportMetrics.objects.create(
            report=report,
            rows_processed=50,
            columns_included=8
        )
        
        metrics_url = f'/api/reporting/reports/{report_id}/metrics/'
        response = self.client.get(metrics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rows_processed'], 50)
    
    def test_template_workflow(self):
        """Test template creation and usage workflow"""
        # 1. Create template
        template_url = '/api/reporting/templates/'
        template_data = {
            'name': 'Integration Template',
            'description': 'Template for integration test',
            'report_type': 'VOLUNTEER_SUMMARY',
            'default_parameters': {'status_filter': 'ACTIVE'},
            'is_public': True
        }
        
        response = self.client.post(template_url, template_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        template_id = response.data['id']
        
        # 2. Use template to create report
        use_url = f'/api/reporting/templates/{template_id}/use/'
        use_data = {
            'name': 'Report from Integration Template',
            'parameters': {'additional_filter': 'test'}
        }
        
        with patch('reporting.views.generate_report') as mock_generate:
            response = self.client.post(use_url, use_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that report was created with merged parameters
        report = Report.objects.get(name='Report from Integration Template')
        self.assertIn('status_filter', report.parameters)
        self.assertIn('additional_filter', report.parameters)
        self.assertEqual(report.parameters['status_filter'], 'ACTIVE')
        self.assertEqual(report.parameters['additional_filter'], 'test') 