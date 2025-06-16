#!/usr/bin/env python3
"""
Admin Override API Configuration Validation Script

This script validates the admin override API configuration including:
- Model structure and methods
- Serializer configuration and validation
- Permission classes and logic
- ViewSet configuration and actions
- URL patterns and routing
- Integration with audit service

Run this script to verify the admin override API is properly configured.
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.insert(0, '/home/itsupport/projects/soi-hub')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

import inspect
from django.urls import reverse, NoReverseMatch
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers, permissions, viewsets
from rest_framework.decorators import action

# Import the components to validate
from common.models import AdminOverride, AuditLog
from common.serializers import (
    AdminOverrideListSerializer, AdminOverrideDetailSerializer,
    AdminOverrideCreateSerializer, AdminOverrideUpdateSerializer,
    AdminOverrideStatusSerializer, AdminOverrideMonitoringSerializer,
    AdminOverrideBulkOperationSerializer, AdminOverrideStatsSerializer
)
from common.permissions import (
    AdminOverridePermission, AdminOverrideApprovalPermission,
    AdminOverrideBulkOperationPermission, AdminOverrideMonitoringPermission,
    AdminOverrideStatsPermission
)
from common.views import AdminOverrideViewSet, AdminOverrideFilter
from common.override_service import AdminOverrideService


class AdminOverrideAPIValidator:
    """Validator for admin override API configuration"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_tests = 0
    
    def validate_all(self):
        """Run all validation tests"""
        print("🔍 Validating Admin Override API Configuration...")
        print("=" * 60)
        
        self.validate_model_structure()
        self.validate_serializers()
        self.validate_permissions()
        self.validate_viewset()
        self.validate_urls()
        self.validate_service_integration()
        self.validate_filtering()
        
        self.print_summary()
        return len(self.errors) == 0
    
    def test(self, description, test_func):
        """Run a test and track results"""
        self.total_tests += 1
        try:
            test_func()
            print(f"✅ {description}")
            self.success_count += 1
            return True
        except Exception as e:
            print(f"❌ {description}: {str(e)}")
            self.errors.append(f"{description}: {str(e)}")
            return False
    
    def warn(self, message):
        """Add a warning"""
        print(f"⚠️  {message}")
        self.warnings.append(message)
    
    def validate_model_structure(self):
        """Validate AdminOverride model structure"""
        print("\n📋 Validating Model Structure...")
        
        def test_model_exists():
            assert AdminOverride is not None, "AdminOverride model not found"
        
        def test_model_fields():
            required_fields = [
                'title', 'override_type', 'description', 'justification',
                'content_type', 'object_id', 'requested_by', 'status',
                'risk_level', 'impact_level', 'is_emergency', 'priority_level'
            ]
            model_fields = [field.name for field in AdminOverride._meta.fields]
            for field in required_fields:
                assert field in model_fields, f"Required field '{field}' not found in AdminOverride model"
        
        def test_model_choices():
            assert hasattr(AdminOverride, 'OverrideType'), "OverrideType choices not found"
            assert hasattr(AdminOverride, 'OverrideStatus'), "OverrideStatus choices not found"
            assert hasattr(AdminOverride, 'RiskLevel'), "RiskLevel choices not found"
            assert hasattr(AdminOverride, 'ImpactLevel'), "ImpactLevel choices not found"
        
        def test_model_methods():
            required_methods = [
                'approve', 'reject', 'activate', 'revoke', 'complete',
                'is_pending', 'is_approved', 'is_active', 'is_expired',
                'is_effective', 'get_duration', 'get_time_remaining'
            ]
            for method in required_methods:
                assert hasattr(AdminOverride, method), f"Method '{method}' not found in AdminOverride model"
        
        def test_model_meta():
            meta = AdminOverride._meta
            assert meta.verbose_name == 'admin override', "Incorrect verbose_name"
            assert meta.verbose_name_plural == 'admin overrides', "Incorrect verbose_name_plural"
            assert len(meta.indexes) > 0, "No database indexes defined"
        
        self.test("AdminOverride model exists", test_model_exists)
        self.test("Required fields present", test_model_fields)
        self.test("Choice classes defined", test_model_choices)
        self.test("Required methods present", test_model_methods)
        self.test("Model meta configuration", test_model_meta)
    
    def validate_serializers(self):
        """Validate serializer configuration"""
        print("\n📝 Validating Serializers...")
        
        def test_list_serializer():
            assert issubclass(AdminOverrideListSerializer, serializers.ModelSerializer)
            assert AdminOverrideListSerializer.Meta.model == AdminOverride
            required_fields = ['id', 'title', 'override_type', 'status', 'risk_level']
            for field in required_fields:
                assert field in AdminOverrideListSerializer.Meta.fields
        
        def test_detail_serializer():
            assert issubclass(AdminOverrideDetailSerializer, serializers.ModelSerializer)
            assert AdminOverrideDetailSerializer.Meta.model == AdminOverride
            assert AdminOverrideDetailSerializer.Meta.fields == '__all__'
        
        def test_create_serializer():
            assert issubclass(AdminOverrideCreateSerializer, serializers.ModelSerializer)
            assert AdminOverrideCreateSerializer.Meta.model == AdminOverride
            assert hasattr(AdminOverrideCreateSerializer, 'validate_title')
            assert hasattr(AdminOverrideCreateSerializer, 'validate_justification')
        
        def test_update_serializer():
            assert issubclass(AdminOverrideUpdateSerializer, serializers.ModelSerializer)
            assert AdminOverrideUpdateSerializer.Meta.model == AdminOverride
            assert 'title' in AdminOverrideUpdateSerializer.Meta.fields
        
        def test_status_serializer():
            assert issubclass(AdminOverrideStatusSerializer, serializers.Serializer)
            # Check if serializer can be instantiated and has expected fields
            serializer = AdminOverrideStatusSerializer()
            assert 'action' in serializer.fields
            assert hasattr(AdminOverrideStatusSerializer, 'validate')
        
        def test_bulk_operation_serializer():
            assert issubclass(AdminOverrideBulkOperationSerializer, serializers.Serializer)
            # Check if serializer can be instantiated and has expected fields
            serializer = AdminOverrideBulkOperationSerializer()
            assert 'override_ids' in serializer.fields
            assert 'action' in serializer.fields
        
        def test_stats_serializer():
            assert issubclass(AdminOverrideStatsSerializer, serializers.Serializer)
            # Check if serializer can be instantiated and has expected fields
            serializer = AdminOverrideStatsSerializer()
            required_fields = ['total_overrides', 'pending_overrides', 'active_overrides']
            for field in required_fields:
                assert field in serializer.fields
        
        self.test("List serializer configuration", test_list_serializer)
        self.test("Detail serializer configuration", test_detail_serializer)
        self.test("Create serializer configuration", test_create_serializer)
        self.test("Update serializer configuration", test_update_serializer)
        self.test("Status serializer configuration", test_status_serializer)
        self.test("Bulk operation serializer configuration", test_bulk_operation_serializer)
        self.test("Statistics serializer configuration", test_stats_serializer)
    
    def validate_permissions(self):
        """Validate permission classes"""
        print("\n🔒 Validating Permissions...")
        
        def test_base_permission():
            assert issubclass(AdminOverridePermission, permissions.BasePermission)
            assert hasattr(AdminOverridePermission, 'has_permission')
            assert hasattr(AdminOverridePermission, 'has_object_permission')
        
        def test_approval_permission():
            assert issubclass(AdminOverrideApprovalPermission, permissions.BasePermission)
            assert hasattr(AdminOverrideApprovalPermission, 'has_permission')
            assert hasattr(AdminOverrideApprovalPermission, 'has_object_permission')
        
        def test_bulk_operation_permission():
            assert issubclass(AdminOverrideBulkOperationPermission, permissions.BasePermission)
            assert hasattr(AdminOverrideBulkOperationPermission, 'has_permission')
        
        def test_monitoring_permission():
            assert issubclass(AdminOverrideMonitoringPermission, permissions.BasePermission)
            assert hasattr(AdminOverrideMonitoringPermission, 'has_permission')
            assert hasattr(AdminOverrideMonitoringPermission, 'has_object_permission')
        
        def test_stats_permission():
            assert issubclass(AdminOverrideStatsPermission, permissions.BasePermission)
            assert hasattr(AdminOverrideStatsPermission, 'has_permission')
        
        self.test("Base permission class", test_base_permission)
        self.test("Approval permission class", test_approval_permission)
        self.test("Bulk operation permission class", test_bulk_operation_permission)
        self.test("Monitoring permission class", test_monitoring_permission)
        self.test("Statistics permission class", test_stats_permission)
    
    def validate_viewset(self):
        """Validate ViewSet configuration"""
        print("\n🎯 Validating ViewSet...")
        
        def test_viewset_inheritance():
            assert issubclass(AdminOverrideViewSet, viewsets.ModelViewSet)
        
        def test_viewset_queryset():
            assert hasattr(AdminOverrideViewSet, 'queryset')
            assert AdminOverrideViewSet.queryset.model == AdminOverride
        
        def test_viewset_permissions():
            assert hasattr(AdminOverrideViewSet, 'permission_classes')
            permission_classes = AdminOverrideViewSet.permission_classes
            assert any(issubclass(pc, permissions.BasePermission) for pc in permission_classes)
        
        def test_viewset_serializer_method():
            assert hasattr(AdminOverrideViewSet, 'get_serializer_class')
            assert callable(AdminOverrideViewSet.get_serializer_class)
        
        def test_viewset_filtering():
            assert hasattr(AdminOverrideViewSet, 'filter_backends')
            assert hasattr(AdminOverrideViewSet, 'filterset_class')
            assert hasattr(AdminOverrideViewSet, 'search_fields')
            assert hasattr(AdminOverrideViewSet, 'ordering_fields')
        
        def test_custom_actions():
            required_actions = [
                'approve', 'reject', 'activate', 'revoke', 'complete',
                'monitoring', 'bulk_operations', 'statistics', 'pending',
                'active', 'expiring', 'types'
            ]
            
            viewset_methods = dir(AdminOverrideViewSet)
            for action_name in required_actions:
                assert action_name in viewset_methods, f"Action '{action_name}' not found in ViewSet"
                
                # Check if method has @action decorator
                method = getattr(AdminOverrideViewSet, action_name)
                assert hasattr(method, 'mapping'), f"Action '{action_name}' missing @action decorator"
        
        def test_crud_methods():
            crud_methods = ['perform_create', 'perform_update', 'perform_destroy']
            for method in crud_methods:
                assert hasattr(AdminOverrideViewSet, method), f"CRUD method '{method}' not found"
        
        self.test("ViewSet inheritance", test_viewset_inheritance)
        self.test("ViewSet queryset", test_viewset_queryset)
        self.test("ViewSet permissions", test_viewset_permissions)
        self.test("ViewSet serializer method", test_viewset_serializer_method)
        self.test("ViewSet filtering configuration", test_viewset_filtering)
        self.test("Custom actions present", test_custom_actions)
        self.test("CRUD methods present", test_crud_methods)
    
    def validate_urls(self):
        """Validate URL configuration"""
        print("\n🌐 Validating URLs...")
        
        def test_basic_crud_urls():
            try:
                reverse('common:adminoverride-list')
                reverse('common:adminoverride-detail', kwargs={'pk': 'test-uuid'})
            except NoReverseMatch as e:
                raise AssertionError(f"Basic CRUD URLs not configured: {e}")
        
        def test_custom_action_urls():
            custom_actions = [
                'approve', 'reject', 'activate', 'revoke', 'complete',
                'monitoring', 'bulk-operations', 'statistics', 'pending',
                'active', 'expiring', 'types'
            ]
            
            for action in custom_actions:
                try:
                    if action in ['bulk-operations', 'statistics', 'pending', 'active', 'expiring', 'types']:
                        reverse(f'common:adminoverride-{action}')
                    else:
                        reverse(f'common:adminoverride-{action}', kwargs={'pk': 'test-uuid'})
                except NoReverseMatch as e:
                    raise AssertionError(f"Custom action URL '{action}' not configured: {e}")
        
        def test_router_registration():
            from common.urls import router
            registered_viewsets = [registration[0] for registration in router.registry]
            assert 'admin-overrides' in registered_viewsets, "AdminOverride ViewSet not registered with router"
        
        self.test("Basic CRUD URLs", test_basic_crud_urls)
        self.test("Custom action URLs", test_custom_action_urls)
        self.test("Router registration", test_router_registration)
    
    def validate_service_integration(self):
        """Validate service integration"""
        print("\n🔧 Validating Service Integration...")
        
        def test_override_service_exists():
            assert AdminOverrideService is not None, "AdminOverrideService not found"
        
        def test_service_methods():
            required_methods = [
                'create_override', 'approve_override', 'reject_override',
                'activate_override', 'revoke_override', 'get_pending_overrides',
                'get_active_overrides', 'get_expiring_overrides', 'update_monitoring'
            ]
            
            for method in required_methods:
                assert hasattr(AdminOverrideService, method), f"Service method '{method}' not found"
                assert callable(getattr(AdminOverrideService, method)), f"Service method '{method}' not callable"
        
        def test_audit_service_integration():
            from common.audit_service import AdminAuditService
            assert hasattr(AdminAuditService, 'log_admin_override'), "log_admin_override method not found in AdminAuditService"
        
        self.test("Override service exists", test_override_service_exists)
        self.test("Service methods present", test_service_methods)
        self.test("Audit service integration", test_audit_service_integration)
    
    def validate_filtering(self):
        """Validate filtering configuration"""
        print("\n🔍 Validating Filtering...")
        
        def test_filter_class_exists():
            assert AdminOverrideFilter is not None, "AdminOverrideFilter not found"
        
        def test_filter_fields():
            filter_instance = AdminOverrideFilter()
            expected_filters = [
                'override_type', 'status', 'risk_level', 'impact_level',
                'is_emergency', 'is_effective', 'is_expired', 'requires_monitoring'
            ]
            
            # Check if filters are defined in the filter class
            for filter_name in expected_filters:
                assert hasattr(filter_instance, filter_name) or filter_name in filter_instance.filters, f"Filter '{filter_name}' not found"
        
        def test_custom_filter_methods():
            filter_instance = AdminOverrideFilter()
            custom_methods = ['filter_is_effective', 'filter_is_expired', 'filter_content_type', 'filter_tags']
            
            for method in custom_methods:
                assert hasattr(filter_instance, method), f"Custom filter method '{method}' not found"
        
        def test_date_filters():
            filter_instance = AdminOverrideFilter()
            date_filters = [
                'requested_after', 'requested_before', 'approved_after', 'approved_before',
                'effective_from_after', 'effective_from_before'
            ]
            
            # Check if date filters are defined in the filter class
            for filter_name in date_filters:
                assert hasattr(filter_instance, filter_name) or filter_name in filter_instance.filters, f"Date filter '{filter_name}' not found"
        
        self.test("Filter class exists", test_filter_class_exists)
        self.test("Filter fields present", test_filter_fields)
        self.test("Custom filter methods", test_custom_filter_methods)
        self.test("Date filters present", test_date_filters)
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        success_rate = (self.success_count / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print(f"✅ Successful tests: {self.success_count}/{self.total_tests} ({success_rate:.1f}%)")
        
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
        
        print("\n📋 ADMIN OVERRIDE API ENDPOINTS:")
        print("=" * 60)
        
        endpoints = [
            ("GET", "/api/admin-overrides/", "List all admin overrides"),
            ("POST", "/api/admin-overrides/", "Create new admin override"),
            ("GET", "/api/admin-overrides/{id}/", "Get admin override details"),
            ("PUT/PATCH", "/api/admin-overrides/{id}/", "Update admin override"),
            ("DELETE", "/api/admin-overrides/{id}/", "Delete admin override"),
            ("POST", "/api/admin-overrides/{id}/approve/", "Approve admin override"),
            ("POST", "/api/admin-overrides/{id}/reject/", "Reject admin override"),
            ("POST", "/api/admin-overrides/{id}/activate/", "Activate admin override"),
            ("POST", "/api/admin-overrides/{id}/revoke/", "Revoke admin override"),
            ("POST", "/api/admin-overrides/{id}/complete/", "Complete admin override"),
            ("POST", "/api/admin-overrides/{id}/monitoring/", "Update monitoring"),
            ("POST", "/api/admin-overrides/bulk-operations/", "Bulk operations"),
            ("GET", "/api/admin-overrides/statistics/", "Get statistics"),
            ("GET", "/api/admin-overrides/pending/", "Get pending overrides"),
            ("GET", "/api/admin-overrides/active/", "Get active overrides"),
            ("GET", "/api/admin-overrides/expiring/", "Get expiring overrides"),
            ("GET", "/api/admin-overrides/types/", "Get override types"),
        ]
        
        for method, endpoint, description in endpoints:
            print(f"{method:10} {endpoint:40} {description}")
        
        print("\n🔒 PERMISSION LEVELS:")
        print("=" * 60)
        print("• ADMIN: Full access to all operations")
        print("• VMT: Most operations except CRITICAL overrides and deletion")
        print("• CVT/GOC: View and create own overrides, update own pending")
        print("• STAFF: View and create own overrides, update own pending")
        print("• VOLUNTEER: No access")
        
        print("\n🎯 KEY FEATURES:")
        print("=" * 60)
        print("• Full CRUD operations with role-based permissions")
        print("• Comprehensive workflow management (approve/reject/activate/revoke)")
        print("• Advanced filtering and search capabilities")
        print("• Bulk operations for efficient management")
        print("• Real-time statistics and analytics")
        print("• Comprehensive audit logging")
        print("• Emergency override handling")
        print("• Risk assessment and monitoring")
        print("• Integration with AdminOverrideService")


def main():
    """Main validation function"""
    validator = AdminOverrideAPIValidator()
    success = validator.validate_all()
    
    if success:
        print(f"\n🎉 Admin Override API validation completed successfully!")
        return 0
    else:
        print(f"\n❌ Admin Override API validation failed with {len(validator.errors)} errors.")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 