#!/usr/bin/env python3
"""
Quick test script for the notification system implementation.
Focuses on core functionality without complex setup.
"""

import os
import sys
import django
import uuid
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

def test_imports():
    """Test that all notification components can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from common.notification_models import (
            NotificationTemplate, Notification, NotificationPreference,
            NotificationChannel, NotificationLog
        )
        print("✅ Notification models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import notification models: {e}")
        return False
    
    try:
        from common.notification_service import NotificationService
        print("✅ Notification service imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import notification service: {e}")
        return False
    
    try:
        from common.notification_serializers import (
            NotificationListSerializer, NotificationCreateSerializer,
            NotificationPreferenceSerializer
        )
        print("✅ Notification serializers imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import notification serializers: {e}")
        return False
    
    try:
        from common.notification_views import NotificationViewSet, NotificationPreferenceViewSet
        print("✅ Notification views imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import notification views: {e}")
        return False
    
    try:
        from common.consumers import NotificationConsumer, SystemNotificationConsumer
        print("✅ WebSocket consumers imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import WebSocket consumers: {e}")
        return False
    
    return True

def test_django_settings():
    """Test Django settings configuration"""
    print("\n🔧 Testing Django settings...")
    
    from django.conf import settings
    
    # Test INSTALLED_APPS
    if 'channels' in settings.INSTALLED_APPS:
        print("✅ Channels in INSTALLED_APPS")
    else:
        print("❌ Channels not in INSTALLED_APPS")
        return False
    
    # Test ASGI_APPLICATION
    if hasattr(settings, 'ASGI_APPLICATION'):
        asgi_app = settings.ASGI_APPLICATION
        if asgi_app == 'soi_hub.asgi.application':
            print("✅ ASGI application configured correctly")
        else:
            print(f"⚠️  ASGI application: {asgi_app} (expected: soi_hub.asgi.application)")
    else:
        print("❌ ASGI_APPLICATION not configured")
        return False
    
    # Test CHANNEL_LAYERS
    if hasattr(settings, 'CHANNEL_LAYERS'):
        channel_layers = settings.CHANNEL_LAYERS
        default_backend = channel_layers.get('default', {}).get('BACKEND', '')
        if 'redis' in default_backend.lower():
            print("✅ Redis channel layer configured")
        else:
            print(f"⚠️  Channel layer backend: {default_backend}")
    else:
        print("❌ CHANNEL_LAYERS not configured")
        return False
    
    return True

def test_models():
    """Test notification models"""
    print("\n📊 Testing notification models...")
    
    from common.notification_models import NotificationTemplate, Notification, NotificationPreference
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Create a unique test user
        unique_id = uuid.uuid4().hex[:8]
        unique_email = f'test_quick_{unique_id}@example.com'
        test_user = User.objects.create(
            email=unique_email,
            username=f'test_quick_{unique_id}',
            first_name='Test',
            last_name='QuickUser',
            user_type='VOLUNTEER',
            is_active=True
        )
        print(f"✅ Test user created: {test_user.email}")
        
        # Test NotificationTemplate
        template = NotificationTemplate.objects.create(
            name=f'test_template_{uuid.uuid4().hex[:8]}',
            notification_type='VOLUNTEER_APPLICATION',
            title_template='Test: {volunteer_name}',
            message_template='Hello {volunteer_name}, your application is {status}',
            default_priority='MEDIUM',
            target_user_types=['VOLUNTEER'],
            is_active=True
        )
        print("✅ NotificationTemplate created successfully")
        
        # Test template rendering
        context = {'volunteer_name': 'John Doe', 'status': 'approved'}
        rendered_title = template.render_title(context)
        rendered_message = template.render_message(context)
        
        if rendered_title == 'Test: John Doe' and 'John Doe' in rendered_message:
            print("✅ Template rendering works correctly")
        else:
            print(f"❌ Template rendering failed: Title: {rendered_title}, Message: {rendered_message}")
            return False
        
        # Test Notification
        notification = Notification.objects.create(
            template=template,
            recipient=test_user,
            title='Test Notification',
            message='Test message',
            priority='MEDIUM',
            channels=['IN_APP', 'WEBSOCKET']
        )
        print("✅ Notification created successfully")
        
        # Test NotificationPreference
        preference = NotificationPreference.objects.create(
            user=test_user,
            is_enabled=True,
            quiet_hours_start='22:00',
            quiet_hours_end='08:00',
            timezone='UTC'
        )
        print("✅ NotificationPreference created successfully")
        
        # Cleanup
        notification.delete()
        template.delete()
        preference.delete()
        test_user.delete()
        print("✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def test_service():
    """Test notification service"""
    print("\n🔧 Testing notification service...")
    
    try:
        from common.notification_service import NotificationService
        
        # Test service initialization
        service = NotificationService()
        print("✅ NotificationService initialized")
        
        # Test Redis connection (if available)
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            print("✅ Redis connection successful")
        except Exception as e:
            print(f"⚠️  Redis not available: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

def test_api_urls():
    """Test API URL configuration"""
    print("\n🌐 Testing API URLs...")
    
    try:
        from django.urls import reverse, NoReverseMatch
        
        # Test notification URLs
        try:
            url = reverse('notification-list')
            print(f"✅ Notification API URL: {url}")
        except NoReverseMatch:
            print("❌ Notification API URLs not configured")
            return False
        
        try:
            url = reverse('notification-preference-list')
            print(f"✅ NotificationPreference API URL: {url}")
        except NoReverseMatch:
            print("❌ NotificationPreference API URLs not configured")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ URL test failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        'common/notification_models.py',
        'common/notification_service.py',
        'common/notification_serializers.py',
        'common/notification_views.py',
        'common/notification_urls.py',
        'common/consumers.py',
        'common/routing.py',
        'soi_hub/asgi.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def main():
    """Main test execution"""
    print("🚀 SOI Volunteer Management - Quick Notification System Test")
    print("Testing Sub-task 6.11: Real-time notifications and WebSocket support")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Django Settings", test_django_settings),
        ("Component Imports", test_imports),
        ("Models", test_models),
        ("Service", test_service),
        ("API URLs", test_api_urls),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("🎉 All notification system tests passed!")
        print("✅ Sub-task 6.11 is ready!")
        print("📋 Next: Sub-task 6.12 - Add API documentation with Swagger/OpenAPI")
        return 0
    else:
        print(f"⚠️  {total - passed} tests failed. Please review the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 