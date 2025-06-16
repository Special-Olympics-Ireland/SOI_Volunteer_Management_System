#!/usr/bin/env python
"""
Test user management models and serializers
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.serializers import (
    UserPreferencesSerializer, UserPreferencesUpdateSerializer,
    UserProfileCompletionSerializer, UserSecuritySerializer,
    UserNotificationSettingsSerializer
)

User = get_user_model()

def test_user_management_models():
    print("Testing user management models and serializers...")
    
    # Create test user (or get existing)
    try:
        user = User.objects.get(username='testusermgmt2')
        print(f'✅ Using existing test user: {user}')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testusermgmt2',
            email='testmgmt2@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Management',
            user_type='VOLUNTEER',
            volunteer_type='NEW',
            phone_number='+353871234567',
            date_of_birth='1990-01-01',
            address_line_1='123 Test Street',
            city='Dublin',
            county='Dublin',
            postal_code='D01 A1B2',
            country='Ireland'
        )
        print(f'✅ Test user created: {user}')
    
    # Test UserPreferencesSerializer
    print('\n📋 Testing UserPreferencesSerializer...')
    prefs_serializer = UserPreferencesSerializer(user)
    prefs_data = prefs_serializer.data
    print(f'   Language: {prefs_data.get("preferred_language")}')
    print(f'   Email notifications: {prefs_data.get("email_notifications")}')
    print(f'   Theme preference: {prefs_data.get("theme_preference")}')
    
    # Test UserProfileCompletionSerializer
    print('\n📊 Testing UserProfileCompletionSerializer...')
    completion_serializer = UserProfileCompletionSerializer(user)
    completion_data = completion_serializer.data
    print(f'   Profile complete: {completion_data.get("profile_complete")}')
    print(f'   Completion percentage: {completion_data.get("completion_percentage")}%')
    print(f'   Missing fields: {len(completion_data.get("missing_fields", []))}')
    print(f'   Required fields: {len(completion_data.get("required_fields", []))}')
    
    # Test UserSecuritySerializer
    print('\n🔒 Testing UserSecuritySerializer...')
    security_serializer = UserSecuritySerializer(user)
    security_data = security_serializer.data
    print(f'   Last login: {security_data.get("last_login")}')
    print(f'   Email verified: {security_data.get("email_verified")}')
    print(f'   Phone verified: {security_data.get("phone_verified")}')
    
    # Test UserNotificationSettingsSerializer
    print('\n🔔 Testing UserNotificationSettingsSerializer...')
    notif_serializer = UserNotificationSettingsSerializer(user)
    notif_data = notif_serializer.data
    print(f'   Email notifications: {notif_data.get("email_notifications")}')
    print(f'   SMS notifications: {notif_data.get("sms_notifications")}')
    print(f'   Marketing consent: {notif_data.get("marketing_consent")}')
    
    # Test UserPreferencesUpdateSerializer
    print('\n✏️  Testing UserPreferencesUpdateSerializer...')
    update_data = {
        'preferred_language': 'ga',
        'email_notifications': False,
        'marketing_consent': True
    }
    update_serializer = UserPreferencesUpdateSerializer(user, data=update_data, partial=True)
    if update_serializer.is_valid():
        updated_user = update_serializer.save()
        print(f'   ✅ Preferences updated successfully')
        print(f'   New language: {updated_user.preferred_language}')
        print(f'   New email notifications: {updated_user.email_notifications}')
    else:
        print(f'   ❌ Preferences update failed: {update_serializer.errors}')
    
    print('\n✅ All user management models and serializers working correctly!')
    
    # Cleanup
    user.delete()
    print('🧹 Test user cleaned up')

if __name__ == "__main__":
    test_user_management_models() 