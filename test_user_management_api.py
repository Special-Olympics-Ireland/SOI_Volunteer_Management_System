#!/usr/bin/env python
"""
Test script for user management API endpoints
"""
import os
import sys
import django
import requests
import json
from django.test import TestCase
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

User = get_user_model()

def test_user_management_endpoints():
    """Test all user management API endpoints"""
    base_url = "http://127.0.0.1:8000/api/v1/accounts"
    
    print("👤 Testing User Management API Endpoints")
    print("=" * 60)
    
    # Test data
    test_user_data = {
        "username": "testusermgmt",
        "email": "testmgmt@example.com",
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "Management",
        "user_type": "VOLUNTEER",
        "volunteer_type": "NEW",
        "phone_number": "+353871234567",
        "date_of_birth": "1990-01-01",
        "address_line_1": "123 Test Street",
        "city": "Dublin",
        "county": "Dublin",
        "postal_code": "D01 A1B2",
        "country": "Ireland",
        "gdpr_consent": True
    }
    
    token = None
    
    try:
        # 1. Register a test user
        print("\n1. Testing User Registration...")
        response = requests.post(f"{base_url}/api/auth/register/", json=test_user_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ Registration successful")
            user_data = response.json()
            print(f"   User ID: {user_data.get('id')}")
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return
        
        # 2. Login to get token
        print("\n2. Testing User Login...")
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = requests.post(f"{base_url}/api/auth/login/", json=login_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Login successful")
            login_response = response.json()
            token = login_response.get('token')
            print(f"   Token: {token[:20]}..." if token else "   No token received")
        else:
            print(f"   ❌ Login failed: {response.text}")
            return
        
        if not token:
            print("   ❌ No authentication token available")
            return
        
        headers = {"Authorization": f"Token {token}"}
        
        # 3. Test Profile Completion Status
        print("\n3. Testing Profile Completion Status...")
        response = requests.get(f"{base_url}/api/profile/completion/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Profile completion check successful")
            completion_data = response.json()
            print(f"   Completion: {completion_data.get('completion_percentage', 'N/A')}%")
            print(f"   Missing fields: {len(completion_data.get('missing_fields', []))}")
        else:
            print(f"   ❌ Profile completion check failed: {response.text}")
        
        # 4. Test User Preferences
        print("\n4. Testing User Preferences...")
        response = requests.get(f"{base_url}/api/preferences/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Preferences retrieval successful")
            prefs_data = response.json()
            print(f"   Language: {prefs_data.get('preferred_language')}")
            print(f"   Email notifications: {prefs_data.get('email_notifications')}")
        else:
            print(f"   ❌ Preferences retrieval failed: {response.text}")
        
        # 5. Test Preferences Update
        print("\n5. Testing Preferences Update...")
        preferences_update = {
            "preferred_language": "ga",
            "email_notifications": False,
            "sms_notifications": True,
            "marketing_consent": False
        }
        response = requests.patch(f"{base_url}/api/preferences/update/", 
                                json=preferences_update, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Preferences update successful")
            updated_prefs = response.json()
            print(f"   Updated language: {updated_prefs.get('preferred_language')}")
            print(f"   Updated email notifications: {updated_prefs.get('email_notifications')}")
        else:
            print(f"   ❌ Preferences update failed: {response.text}")
        
        # 6. Test Notification Settings
        print("\n6. Testing Notification Settings...")
        response = requests.get(f"{base_url}/api/notifications/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Notification settings retrieval successful")
            notif_data = response.json()
            print(f"   Email notifications: {notif_data.get('email_notifications')}")
            print(f"   SMS notifications: {notif_data.get('sms_notifications')}")
        else:
            print(f"   ❌ Notification settings retrieval failed: {response.text}")
        
        # 7. Test Notification Settings Update
        print("\n7. Testing Notification Settings Update...")
        notification_update = {
            "email_notifications": True,
            "sms_notifications": False,
            "preferred_language": "en"
        }
        response = requests.patch(f"{base_url}/api/notifications/update/", 
                                json=notification_update, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Notification settings update successful")
        else:
            print(f"   ❌ Notification settings update failed: {response.text}")
        
        # 8. Test Security Information
        print("\n8. Testing Security Information...")
        response = requests.get(f"{base_url}/api/security/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Security information retrieval successful")
            security_data = response.json()
            print(f"   Last login: {security_data.get('last_login')}")
            print(f"   Email verified: {security_data.get('email_verified')}")
            print(f"   Phone verified: {security_data.get('phone_verified')}")
        else:
            print(f"   ❌ Security information retrieval failed: {response.text}")
        
        # 9. Test Verification Request
        print("\n9. Testing Verification Request...")
        verification_request = {
            "verification_type": "email"
        }
        response = requests.post(f"{base_url}/api/verification/request/", 
                               json=verification_request, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Verification request successful")
            verif_data = response.json()
            print(f"   Message: {verif_data.get('message')}")
        else:
            print(f"   ❌ Verification request failed: {response.text}")
        
        # 10. Test Profile Update
        print("\n10. Testing Profile Update...")
        profile_update = {
            "first_name": "Updated",
            "last_name": "Name",
            "mobile_number": "+353871234568"
        }
        response = requests.patch(f"{base_url}/api/profile/update/", 
                                json=profile_update, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Profile update successful")
            updated_profile = response.json()
            print(f"   Updated name: {updated_profile.get('first_name')} {updated_profile.get('last_name')}")
        else:
            print(f"   ❌ Profile update failed: {response.text}")
        
        # 11. Test User Statistics (Admin endpoint)
        print("\n11. Testing User Statistics (Admin)...")
        response = requests.get(f"{base_url}/api/users/stats/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ User statistics retrieval successful")
            stats_data = response.json()
            print(f"   Total users: {stats_data.get('total_users')}")
            print(f"   Volunteers: {stats_data.get('volunteers')}")
        elif response.status_code == 403:
            print("   ⚠️  Access forbidden (expected for non-admin users)")
        else:
            print(f"   ❌ User statistics retrieval failed: {response.text}")
        
        print("\n" + "=" * 60)
        print("🏁 User Management API Test Complete")
        
        # Cleanup - Delete test user
        print("\n🧹 Cleaning up test user...")
        try:
            test_user = User.objects.get(username=test_user_data["username"])
            test_user.delete()
            print("   ✅ Test user deleted successfully")
        except User.DoesNotExist:
            print("   ⚠️  Test user not found for cleanup")
        
    except requests.exceptions.ConnectionError:
        print("   ⚠️  Server not running. Please start with: python manage.py runserver")
        return
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_user_management_endpoints() 