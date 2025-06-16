#!/usr/bin/env python
"""
Test script for authentication API endpoints
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

def test_authentication_endpoints():
    """Test all authentication endpoints"""
    base_url = "http://127.0.0.1:8000/api/v1/accounts"
    
    print("🔐 Testing Authentication API Endpoints")
    print("=" * 50)
    
    # Test data
    test_user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "user_type": "VOLUNTEER",
        "volunteer_type": "NEW"
    }
    
    # 1. Test User Registration
    print("\n1. Testing User Registration...")
    try:
        response = requests.post(f"{base_url}/api/auth/register/", json=test_user_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ Registration successful")
            user_data = response.json()
            print(f"   User ID: {user_data.get('id')}")
        else:
            print(f"   ❌ Registration failed: {response.text}")
    except requests.exceptions.ConnectionError:
        print("   ⚠️  Server not running. Please start with: python manage.py runserver")
        return
    
    # 2. Test User Login
    print("\n2. Testing User Login...")
    try:
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
            token = None
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        token = None
    
    # 3. Test Token Authentication
    print("\n3. Testing Token Authentication...")
    try:
        token_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = requests.post(f"{base_url}/api/auth/token/", json=token_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Token authentication successful")
            token_response = response.json()
            auth_token = token_response.get('token')
            print(f"   Auth Token: {auth_token[:20]}..." if auth_token else "   No token received")
        else:
            print(f"   ❌ Token authentication failed: {response.text}")
            auth_token = None
    except Exception as e:
        print(f"   ❌ Token authentication error: {e}")
        auth_token = None
    
    # 4. Test Profile Access (requires authentication)
    if token or auth_token:
        print("\n4. Testing Profile Access...")
        try:
            headers = {"Authorization": f"Token {token or auth_token}"}
            response = requests.get(f"{base_url}/api/profile/", headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Profile access successful")
                profile_data = response.json()
                print(f"   Username: {profile_data.get('username')}")
                print(f"   Email: {profile_data.get('email')}")
            else:
                print(f"   ❌ Profile access failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Profile access error: {e}")
    
    # 5. Test User List (admin endpoint)
    print("\n5. Testing User List (Admin)...")
    try:
        if token or auth_token:
            headers = {"Authorization": f"Token {token or auth_token}"}
            response = requests.get(f"{base_url}/api/users/", headers=headers)
        else:
            response = requests.get(f"{base_url}/api/users/")
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ User list access successful")
            users_data = response.json()
            print(f"   Total users: {users_data.get('count', 'N/A')}")
        elif response.status_code == 403:
            print("   ⚠️  Access forbidden (expected for non-admin users)")
        else:
            print(f"   ❌ User list access failed: {response.text}")
    except Exception as e:
        print(f"   ❌ User list error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Authentication API Test Complete")
    print("\nTo run the server: python manage.py runserver")
    print("Then run this script again to test the endpoints.")

if __name__ == "__main__":
    test_authentication_endpoints() 