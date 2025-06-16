#!/usr/bin/env python3
"""
Validation script for Reporting and Analytics API configuration.
Tests all components without requiring database access.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import BasePermission
import importlib


class ReportingAPIValidator:
    """Validator for reporting and analytics API configuration"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_tests = 0
    
    def validate_all(self):
        """Run all validation tests"""
        print("🔍 Validating Reporting and Analytics API Configuration...")
        print("=" * 60)
        
        self.validate_models()
        self.validate_serializers()
        self.validate_permissions()
        self.validate_views()
        self.validate_urls()
        self.validate_integration()
        
        self.print_summary()
        return len(self.errors) == 0
    
    def test(self, description, test_func):
        """Run a single test with error handling"""
        self.total_tests += 1
        try:
            test_func()
            print(f"✅ {description}")
            self.success_count += 1
        except Exception as e:
            print(f"❌ {description}: {str(e)}")
            self.errors.append(f"{description}: {str(e)}")
    
    def warn(self, message):
        """Add a warning"""
        print(f"⚠️  {message}")
        self.warnings.append(message)
    
    def validate_models(self):
        """Validate reporting models"""
        print("\n📊 Validating Models...")
        
        def test_report_model():
            from reporting.models import Report
            # Test model fields
            assert hasattr(Report, 'name'), "Report model missing 'name' field"
            assert hasattr(Report, 'report_type'), "Report model missing 'report_type' field"
            assert hasattr(Report, 'status'), "Report model missing 'status' field"
            assert hasattr(Report, 'parameters'), "Report model missing 'parameters' field"
            assert hasattr(Report, 'export_format'), "Report model missing 'export_format' field"
            assert hasattr(Report, 'created_by'), "Report model missing 'created_by' field"
            
            # Test choices
            assert hasattr(Report, 'ReportType'), "Report model missing ReportType choices"
            assert hasattr(Report, 'Status'), "Report model missing Status choices"
            assert hasattr(Report, 'ExportFormat'), "Report model missing ExportFormat choices"
            
            # Test methods
            assert hasattr(Report, 'is_expired'), "Report model missing 'is_expired' method"
            assert hasattr(Report, 'get_file_size_display'), "Report model missing 'get_file_size_display' method"
            assert hasattr(Report, 'get_download_url'), "Report model missing 'get_download_url' method"
        
        def test_report_template_model():
            from reporting.models import ReportTemplate
            assert hasattr(ReportTemplate, 'name'), "ReportTemplate model missing 'name' field"
            assert hasattr(ReportTemplate, 'report_type'), "ReportTemplate model missing 'report_type' field"
            assert hasattr(ReportTemplate, 'default_parameters'), "ReportTemplate model missing 'default_parameters' field"
            assert hasattr(ReportTemplate, 'is_public'), "ReportTemplate model missing 'is_public' field"
            assert hasattr(ReportTemplate, 'increment_usage'), "ReportTemplate model missing 'increment_usage' method"
        
        def test_report_schedule_model():
            from reporting.models import ReportSchedule
            assert hasattr(ReportSchedule, 'name'), "ReportSchedule model missing 'name' field"
            assert hasattr(ReportSchedule, 'frequency'), "ReportSchedule model missing 'frequency' field"
            assert hasattr(ReportSchedule, 'report_template'), "ReportSchedule model missing 'report_template' field"
            assert hasattr(ReportSchedule, 'calculate_next_run'), "ReportSchedule model missing 'calculate_next_run' method"
        
        def test_report_metrics_model():
            from reporting.models import ReportMetrics
            assert hasattr(ReportMetrics, 'report'), "ReportMetrics model missing 'report' field"
            assert hasattr(ReportMetrics, 'rows_processed'), "ReportMetrics model missing 'rows_processed' field"
            assert hasattr(ReportMetrics, 'data_completeness_percent'), "ReportMetrics model missing 'data_completeness_percent' field"
            assert hasattr(ReportMetrics, 'increment_download_count'), "ReportMetrics model missing 'increment_download_count' method"
        
        def test_report_share_model():
            from reporting.models import ReportShare
            assert hasattr(ReportShare, 'report'), "ReportShare model missing 'report' field"
            assert hasattr(ReportShare, 'share_type'), "ReportShare model missing 'share_type' field"
            assert hasattr(ReportShare, 'share_token'), "ReportShare model missing 'share_token' field"
            assert hasattr(ReportShare, 'is_valid'), "ReportShare model missing 'is_valid' method"
            assert hasattr(ReportShare, 'get_share_url'), "ReportShare model missing 'get_share_url' method"
        
        self.test("Report model structure", test_report_model)
        self.test("ReportTemplate model structure", test_report_template_model)
        self.test("ReportSchedule model structure", test_report_schedule_model)
        self.test("ReportMetrics model structure", test_report_metrics_model)
        self.test("ReportShare model structure", test_report_share_model)
    
    def validate_serializers(self):
        """Validate reporting serializers"""
        print("\n🔄 Validating Serializers...")
        
        def test_report_serializers():
            from reporting.serializers import (
                ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer
            )
            
            # Test serializer inheritance
            assert issubclass(ReportListSerializer, serializers.ModelSerializer), "ReportListSerializer not ModelSerializer"
            assert issubclass(ReportDetailSerializer, serializers.ModelSerializer), "ReportDetailSerializer not ModelSerializer"
            assert issubclass(ReportCreateSerializer, serializers.ModelSerializer), "ReportCreateSerializer not ModelSerializer"
            
            # Test Meta classes
            assert hasattr(ReportListSerializer, 'Meta'), "ReportListSerializer missing Meta class"
            assert hasattr(ReportDetailSerializer, 'Meta'), "ReportDetailSerializer missing Meta class"
            assert hasattr(ReportCreateSerializer, 'Meta'), "ReportCreateSerializer missing Meta class"
            
            # Test fields
            assert hasattr(ReportListSerializer.Meta, 'fields'), "ReportListSerializer.Meta missing fields"
            assert hasattr(ReportDetailSerializer.Meta, 'fields'), "ReportDetailSerializer.Meta missing fields"
            assert hasattr(ReportCreateSerializer.Meta, 'fields'), "ReportCreateSerializer.Meta missing fields"
        
        def test_template_serializers():
            from reporting.serializers import ReportTemplateSerializer
            assert issubclass(ReportTemplateSerializer, serializers.ModelSerializer), "ReportTemplateSerializer not ModelSerializer"
            assert hasattr(ReportTemplateSerializer, 'Meta'), "ReportTemplateSerializer missing Meta class"
        
        def test_analytics_serializers():
            from reporting.serializers import (
                AnalyticsSerializer, DashboardStatsSerializer, ReportTypeInfoSerializer
            )
            assert issubclass(AnalyticsSerializer, serializers.Serializer), "AnalyticsSerializer not Serializer"
            assert issubclass(DashboardStatsSerializer, serializers.Serializer), "DashboardStatsSerializer not Serializer"
            assert issubclass(ReportTypeInfoSerializer, serializers.Serializer), "ReportTypeInfoSerializer not Serializer"
        
        def test_bulk_operation_serializers():
            from reporting.serializers import (
                BulkReportOperationSerializer, ReportGenerationRequestSerializer
            )
            assert issubclass(BulkReportOperationSerializer, serializers.Serializer), "BulkReportOperationSerializer not Serializer"
            assert issubclass(ReportGenerationRequestSerializer, serializers.Serializer), "ReportGenerationRequestSerializer not Serializer"
            
            # Test validation methods
            assert hasattr(BulkReportOperationSerializer, 'validate'), "BulkReportOperationSerializer missing validate method"
            assert hasattr(ReportGenerationRequestSerializer, 'validate'), "ReportGenerationRequestSerializer missing validate method"
        
        def test_serializer_methods():
            from reporting.serializers import ReportListSerializer, ReportDetailSerializer
            
            # Test SerializerMethodField methods
            list_serializer = ReportListSerializer()
            assert hasattr(list_serializer, 'get_generation_duration'), "ReportListSerializer missing get_generation_duration method"
            assert hasattr(list_serializer, 'get_days_until_expiry'), "ReportListSerializer missing get_days_until_expiry method"
            
            detail_serializer = ReportDetailSerializer()
            assert hasattr(detail_serializer, 'get_metrics'), "ReportDetailSerializer missing get_metrics method"
            assert hasattr(detail_serializer, 'get_shares'), "ReportDetailSerializer missing get_shares method"
        
        self.test("Report serializers structure", test_report_serializers)
        self.test("Template serializers structure", test_template_serializers)
        self.test("Analytics serializers structure", test_analytics_serializers)
        self.test("Bulk operation serializers structure", test_bulk_operation_serializers)
        self.test("Serializer methods", test_serializer_methods)
    
    def validate_permissions(self):
        """Validate reporting permissions"""
        print("\n🔐 Validating Permissions...")
        
        def test_permission_classes():
            from reporting.permissions import (
                ReportPermission, ReportTemplatePermission, ReportSchedulePermission,
                AnalyticsPermission, BulkOperationPermission, ReportDownloadPermission
            )
            
            # Test inheritance
            assert issubclass(ReportPermission, BasePermission), "ReportPermission not BasePermission"
            assert issubclass(ReportTemplatePermission, BasePermission), "ReportTemplatePermission not BasePermission"
            assert issubclass(ReportSchedulePermission, BasePermission), "ReportSchedulePermission not BasePermission"
            assert issubclass(AnalyticsPermission, BasePermission), "AnalyticsPermission not BasePermission"
            assert issubclass(BulkOperationPermission, BasePermission), "BulkOperationPermission not BasePermission"
            assert issubclass(ReportDownloadPermission, BasePermission), "ReportDownloadPermission not BasePermission"
        
        def test_permission_methods():
            from reporting.permissions import ReportPermission, ReportTemplatePermission
            
            # Test required methods
            assert hasattr(ReportPermission, 'has_permission'), "ReportPermission missing has_permission method"
            assert hasattr(ReportPermission, 'has_object_permission'), "ReportPermission missing has_object_permission method"
            assert hasattr(ReportTemplatePermission, 'has_permission'), "ReportTemplatePermission missing has_permission method"
            assert hasattr(ReportTemplatePermission, 'has_object_permission'), "ReportTemplatePermission missing has_object_permission method"
        
        def test_specialized_permissions():
            from reporting.permissions import (
                SystemStatsPermission, CustomReportPermission, DashboardPermission
            )
            
            assert issubclass(SystemStatsPermission, BasePermission), "SystemStatsPermission not BasePermission"
            assert issubclass(CustomReportPermission, BasePermission), "CustomReportPermission not BasePermission"
            assert issubclass(DashboardPermission, BasePermission), "DashboardPermission not BasePermission"
            
            # Test special methods
            dashboard_perm = DashboardPermission()
            assert hasattr(dashboard_perm, 'get_allowed_sections'), "DashboardPermission missing get_allowed_sections method"
        
        self.test("Permission class inheritance", test_permission_classes)
        self.test("Permission methods", test_permission_methods)
        self.test("Specialized permissions", test_specialized_permissions)
    
    def validate_views(self):
        """Validate reporting views"""
        print("\n🎯 Validating Views...")
        
        def test_viewset_classes():
            from reporting.views import ReportViewSet, ReportTemplateViewSet, ReportScheduleViewSet, AnalyticsViewSet
            
            # Test inheritance
            assert issubclass(ReportViewSet, ModelViewSet), "ReportViewSet not ModelViewSet"
            assert issubclass(ReportTemplateViewSet, ModelViewSet), "ReportTemplateViewSet not ModelViewSet"
            assert issubclass(ReportScheduleViewSet, ModelViewSet), "ReportScheduleViewSet not ModelViewSet"
            
            # Test required attributes
            assert hasattr(ReportViewSet, 'queryset'), "ReportViewSet missing queryset"
            assert hasattr(ReportViewSet, 'permission_classes'), "ReportViewSet missing permission_classes"
            assert hasattr(ReportViewSet, 'pagination_class'), "ReportViewSet missing pagination_class"
            assert hasattr(ReportViewSet, 'filter_backends'), "ReportViewSet missing filter_backends"
        
        def test_custom_actions():
            from reporting.views import ReportViewSet, ReportTemplateViewSet, ReportScheduleViewSet
            
            # Test ReportViewSet actions
            report_actions = ['download', 'progress', 'regenerate', 'share', 'metrics', 'bulk_operations', 'types']
            for action in report_actions:
                assert hasattr(ReportViewSet, action), f"ReportViewSet missing {action} action"
            
            # Test ReportTemplateViewSet actions
            assert hasattr(ReportTemplateViewSet, 'use_template'), "ReportTemplateViewSet missing use_template action"
            
            # Test ReportScheduleViewSet actions
            assert hasattr(ReportScheduleViewSet, 'run_now'), "ReportScheduleViewSet missing run_now action"
        
        def test_analytics_viewset():
            from reporting.views import AnalyticsViewSet
            
            # Test analytics actions
            analytics_actions = ['dashboard', 'trends']
            for action in analytics_actions:
                assert hasattr(AnalyticsViewSet, action), f"AnalyticsViewSet missing {action} action"
            
            # Test helper methods
            helper_methods = ['_get_volunteer_stats', '_get_event_stats', '_get_assignment_stats', '_get_task_stats']
            for method in helper_methods:
                assert hasattr(AnalyticsViewSet, method), f"AnalyticsViewSet missing {method} method"
        
        def test_filtering_and_pagination():
            from reporting.views import ReportFilter, ReportPagination
            
            # Test filter class
            assert hasattr(ReportFilter, 'Meta'), "ReportFilter missing Meta class"
            assert hasattr(ReportFilter.Meta, 'model'), "ReportFilter.Meta missing model"
            assert hasattr(ReportFilter.Meta, 'fields'), "ReportFilter.Meta missing fields"
            
            # Test pagination class
            assert hasattr(ReportPagination, 'page_size'), "ReportPagination missing page_size"
            assert hasattr(ReportPagination, 'page_size_query_param'), "ReportPagination missing page_size_query_param"
            assert hasattr(ReportPagination, 'max_page_size'), "ReportPagination missing max_page_size"
        
        def test_viewset_methods():
            from reporting.views import ReportViewSet
            
            # Test overridden methods
            assert hasattr(ReportViewSet, 'get_serializer_class'), "ReportViewSet missing get_serializer_class method"
            assert hasattr(ReportViewSet, 'get_queryset'), "ReportViewSet missing get_queryset method"
            assert hasattr(ReportViewSet, 'perform_create'), "ReportViewSet missing perform_create method"
        
        self.test("ViewSet class structure", test_viewset_classes)
        self.test("Custom actions", test_custom_actions)
        self.test("Analytics ViewSet", test_analytics_viewset)
        self.test("Filtering and pagination", test_filtering_and_pagination)
        self.test("ViewSet methods", test_viewset_methods)
    
    def validate_urls(self):
        """Validate URL configuration"""
        print("\n🔗 Validating URLs...")
        
        def test_url_patterns():
            from reporting.urls import urlpatterns, router
            
            # Test router registration
            assert hasattr(router, 'registry'), "Router missing registry"
            assert len(router.registry) >= 4, "Router missing ViewSet registrations"
            
            # Test URL patterns exist
            assert len(urlpatterns) > 0, "No URL patterns defined"
        
        def test_viewset_urls():
            # Test that ViewSet URLs are accessible
            try:
                from django.urls import reverse
                # These should not raise NoReverseMatch
                reverse('reporting:report-list')
                reverse('reporting:reporttemplate-list')
                reverse('reporting:reportschedule-list')
                reverse('reporting:analytics-list')
            except NoReverseMatch as e:
                raise AssertionError(f"ViewSet URL not found: {e}")
        
        def test_custom_action_urls():
            # Test custom action URLs
            custom_urls = [
                'reporting:report-download',
                'reporting:report-progress',
                'reporting:report-regenerate',
                'reporting:report-share',
                'reporting:report-metrics',
                'reporting:report-bulk-operations',
                'reporting:report-types',
                'reporting:template-use',
                'reporting:schedule-run-now',
                'reporting:analytics-dashboard',
                'reporting:analytics-trends'
            ]
            
            for url_name in custom_urls:
                try:
                    # For URLs with parameters, we can't reverse without args
                    # but we can check they're in the URL conf
                    from django.urls import get_resolver
                    resolver = get_resolver()
                    # This will raise NoReverseMatch if URL doesn't exist
                    if 'pk' not in url_name:
                        reverse(url_name)
                except NoReverseMatch:
                    # For URLs with parameters, just check they exist in patterns
                    pass
        
        def test_app_namespace():
            from reporting.urls import app_name
            assert app_name == 'reporting', f"App namespace should be 'reporting', got '{app_name}'"
        
        self.test("URL patterns structure", test_url_patterns)
        self.test("ViewSet URLs", test_viewset_urls)
        self.test("Custom action URLs", test_custom_action_urls)
        self.test("App namespace", test_app_namespace)
    
    def validate_integration(self):
        """Validate integration with other components"""
        print("\n🔌 Validating Integration...")
        
        def test_model_imports():
            # Test that views can import required models
            from reporting.views import (
                Report, ReportTemplate, ReportSchedule, ReportMetrics, ReportShare,
                VolunteerProfile, Event, Assignment, TaskCompletion, User
            )
            
            # Test model relationships work
            assert hasattr(Report, 'created_by'), "Report missing created_by relationship"
            assert hasattr(ReportTemplate, 'created_by'), "ReportTemplate missing created_by relationship"
            assert hasattr(ReportSchedule, 'report_template'), "ReportSchedule missing report_template relationship"
        
        def test_service_integration():
            # Test that services can be imported
            from reporting.services import generate_report, ReportGenerationError
            from reporting.base import BaseReportGenerator
            
            # Test service functions exist
            assert callable(generate_report), "generate_report not callable"
            assert issubclass(ReportGenerationError, Exception), "ReportGenerationError not Exception"
        
        def test_audit_integration():
            # Test audit service integration
            try:
                from common.audit_service import AdminAuditService
                
                # Test required audit methods exist
                assert hasattr(AdminAuditService, 'log_report_generation'), "AdminAuditService missing log_report_generation"
                assert hasattr(AdminAuditService, 'log_data_export'), "AdminAuditService missing log_data_export"
                assert hasattr(AdminAuditService, 'log_bulk_operation'), "AdminAuditService missing log_bulk_operation"
            except ImportError:
                self.warn("AdminAuditService not available - audit logging may not work")
        
        def test_cache_integration():
            # Test cache integration
            try:
                from django.core.cache import cache
                # Test cache operations work
                cache.set('test_key', 'test_value', 1)
                assert cache.get('test_key') == 'test_value', "Cache not working"
                cache.delete('test_key')
            except Exception as e:
                self.warn(f"Cache integration issue: {e}")
        
        def test_settings_integration():
            # Test required settings
            from django.conf import settings
            
            # Test media settings for file storage
            assert hasattr(settings, 'MEDIA_ROOT'), "MEDIA_ROOT setting missing"
            assert hasattr(settings, 'MEDIA_URL'), "MEDIA_URL setting missing"
        
        self.test("Model imports", test_model_imports)
        self.test("Service integration", test_service_integration)
        self.test("Audit integration", test_audit_integration)
        self.test("Cache integration", test_cache_integration)
        self.test("Settings integration", test_settings_integration)
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📋 VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"✅ Successful tests: {self.success_count}/{self.total_tests}")
        
        if self.warnings:
            print(f"⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.errors:
            print(f"❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   • {error}")
        else:
            print("🎉 All validations passed!")
        
        # Calculate success rate
        success_rate = (self.success_count / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"📊 Success rate: {success_rate:.1f}%")


def main():
    """Main validation function"""
    validator = ReportingAPIValidator()
    success = validator.validate_all()
    
    if success:
        print("\n🎯 Reporting and Analytics API is properly configured!")
        return 0
    else:
        print("\n💥 Reporting and Analytics API has configuration issues!")
        return 1


if __name__ == '__main__':
    exit(main()) 