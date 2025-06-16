#!/usr/bin/env python3
"""
Simple validation script for Task Management API configuration
This script checks if all the API endpoints are properly configured without requiring database access.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.conf import settings
from tasks.views import TaskViewSet, TaskCompletionViewSet
from tasks.serializers import (
    TaskListSerializer, TaskDetailSerializer, TaskCreateSerializer,
    TaskCompletionListSerializer, TaskCompletionDetailSerializer
)

def test_url_patterns():
    """Test that all URL patterns are properly configured"""
    print("🔗 Testing URL Patterns...")
    
    url_tests = [
        ('tasks:task-list', 'Task List'),
        ('tasks:taskcompletion-list', 'Task Completion List'),
        ('tasks:task-stats', 'Global Task Stats'),
    ]
    
    passed = 0
    failed = 0
    
    for url_name, description in url_tests:
        try:
            url = reverse(url_name)
            print(f"  ✅ {description}: {url}")
            passed += 1
        except NoReverseMatch as e:
            print(f"  ❌ {description}: {str(e)}")
            failed += 1
    
    print(f"  📊 URL Tests: {passed} passed, {failed} failed\n")
    return failed == 0

def test_viewsets():
    """Test that ViewSets are properly configured"""
    print("🎯 Testing ViewSets...")
    
    viewset_tests = [
        (TaskViewSet, 'TaskViewSet'),
        (TaskCompletionViewSet, 'TaskCompletionViewSet'),
    ]
    
    passed = 0
    failed = 0
    
    for viewset_class, name in viewset_tests:
        try:
            # Check if viewset has required attributes
            if hasattr(viewset_class, 'queryset'):
                print(f"  ✅ {name}: Has queryset")
            else:
                print(f"  ⚠️  {name}: No queryset defined")
            
            if hasattr(viewset_class, 'serializer_class'):
                print(f"  ✅ {name}: Has serializer_class")
            else:
                print(f"  ⚠️  {name}: No serializer_class defined")
            
            # Check for custom actions
            actions = [attr for attr in dir(viewset_class) if hasattr(getattr(viewset_class, attr), 'mapping')]
            if actions:
                print(f"  ✅ {name}: Custom actions: {', '.join(actions)}")
            
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {str(e)}")
            failed += 1
    
    print(f"  📊 ViewSet Tests: {passed} passed, {failed} failed\n")
    return failed == 0

def test_serializers():
    """Test that serializers are properly configured"""
    print("📝 Testing Serializers...")
    
    serializer_tests = [
        (TaskListSerializer, 'TaskListSerializer'),
        (TaskDetailSerializer, 'TaskDetailSerializer'),
        (TaskCreateSerializer, 'TaskCreateSerializer'),
        (TaskCompletionListSerializer, 'TaskCompletionListSerializer'),
        (TaskCompletionDetailSerializer, 'TaskCompletionDetailSerializer'),
    ]
    
    passed = 0
    failed = 0
    
    for serializer_class, name in serializer_tests:
        try:
            # Check if serializer has Meta class
            if hasattr(serializer_class, 'Meta'):
                meta = serializer_class.Meta
                if hasattr(meta, 'model'):
                    print(f"  ✅ {name}: Has model ({meta.model.__name__})")
                else:
                    print(f"  ⚠️  {name}: No model defined")
                
                if hasattr(meta, 'fields'):
                    field_count = len(meta.fields) if isinstance(meta.fields, (list, tuple)) else 'all'
                    print(f"  ✅ {name}: Has fields ({field_count})")
                else:
                    print(f"  ⚠️  {name}: No fields defined")
            else:
                print(f"  ❌ {name}: No Meta class")
                failed += 1
                continue
            
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {str(e)}")
            failed += 1
    
    print(f"  📊 Serializer Tests: {passed} passed, {failed} failed\n")
    return failed == 0

def test_model_imports():
    """Test that all required models can be imported"""
    print("📦 Testing Model Imports...")
    
    try:
        from tasks.models import Task, TaskCompletion
        from events.models import Event, Venue, Role, Assignment
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        print("  ✅ Task model imported successfully")
        print("  ✅ TaskCompletion model imported successfully")
        print("  ✅ Event models imported successfully")
        print("  ✅ User model imported successfully")
        print("  📊 Model Import Tests: All passed\n")
        return True
        
    except ImportError as e:
        print(f"  ❌ Model import failed: {str(e)}")
        print("  📊 Model Import Tests: Failed\n")
        return False

def test_permissions():
    """Test that permission classes can be imported"""
    print("🔐 Testing Permissions...")
    
    try:
        from tasks.permissions import (
            TaskManagementPermission, TaskCompletionPermission, 
            TaskVerificationPermission, TaskBulkOperationPermission, TaskStatsPermission
        )
        
        print("  ✅ All permission classes imported successfully")
        print("  📊 Permission Tests: All passed\n")
        return True
        
    except ImportError as e:
        print(f"  ❌ Permission import failed: {str(e)}")
        print("  📊 Permission Tests: Failed\n")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Task Management API Validation")
    print("=" * 50)
    
    tests = [
        test_model_imports,
        test_serializers,
        test_permissions,
        test_viewsets,
        test_url_patterns,
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        if test_func():
            passed_tests += 1
    
    print("=" * 50)
    print(f"🎯 Final Results: {passed_tests}/{total_tests} test categories passed")
    
    if passed_tests == total_tests:
        print("🎉 All validation tests passed! Task Management API is properly configured.")
        return True
    else:
        print("⚠️  Some validation tests failed. Please check the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 