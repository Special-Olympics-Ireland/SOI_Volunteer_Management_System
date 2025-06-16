#!/usr/bin/env python
"""
Simple test script for Event Management API endpoints.

Usage:
    python manage.py shell < test_event_api_simple.py
"""

import os
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.contrib.auth import get_user_model
from events.models import Event, Venue
from rest_framework.test import APIClient
from django.test import override_settings

User = get_user_model()

def test_event_api():
    """Simple test of Event API endpoints"""
    print("🚀 Testing Event Management API...")
    
    # Get or create test user
    try:
        admin_user, created = User.objects.get_or_create(
            username='test_admin',
            defaults={
                'email': 'test@example.com',
                'user_type': 'ADMIN',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('testpass123')
            admin_user.save()
            print("✅ Test user created")
        else:
            print("✅ Test user already exists")
    except Exception as e:
        print(f"❌ Error with user: {e}")
        return False
    
    # Get or create test event
    try:
        test_event, created = Event.objects.get_or_create(
            slug='test-event-api',
            defaults={
                'name': 'Test Event API',
                'event_type': 'NATIONAL_GAMES',
                'start_date': date.today() + timedelta(days=30),
                'end_date': date.today() + timedelta(days=37),
                'host_city': 'Dublin',
                'volunteer_target': 500,
                'created_by': admin_user,
                'is_public': True,
                'is_active': True
            }
        )
        if created:
            print("✅ Test event created")
        else:
            print("✅ Test event already exists")
    except Exception as e:
        print(f"❌ Error with event: {e}")
        return False
    
    # Test API client
    client = APIClient()
    
    # Test public event list (no auth required)
    try:
        with override_settings(ALLOWED_HOSTS=['testserver']):
            response = client.get('/events/api/events/')
            if response.status_code == 200:
                print("✅ Public event list API works")
                data = response.json()
                print(f"   Found {data.get('count', 0)} events")
            else:
                print(f"❌ Event list API failed: {response.status_code}")
                print(f"   Response: {response.content}")
    except Exception as e:
        print(f"❌ Error testing event list API: {e}")
    
    # Test event detail
    try:
        with override_settings(ALLOWED_HOSTS=['testserver']):
            response = client.get(f'/events/api/events/{test_event.id}/')
            if response.status_code == 200:
                print("✅ Event detail API works")
                data = response.json()
                print(f"   Event name: {data.get('name')}")
            else:
                print(f"❌ Event detail API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing event detail API: {e}")
    
    # Test authenticated operations
    client.force_authenticate(user=admin_user)
    
    # Test event creation
    try:
        with override_settings(ALLOWED_HOSTS=['testserver']):
            import time
            timestamp = str(int(time.time()))
            event_data = {
                'name': f'API Created Event {timestamp}',
                'slug': f'api-created-event-{timestamp}',
                'event_type': 'LOCAL_EVENT',
                'start_date': (date.today() + timedelta(days=60)).isoformat(),
                'end_date': (date.today() + timedelta(days=67)).isoformat(),
                'host_city': 'Cork',
                'volunteer_target': 200,
                'is_public': True
            }
            response = client.post('/events/api/events/', event_data, format='json')
            if response.status_code == 201:
                print("✅ Event creation API works")
                data = response.json()
                print(f"   Created event: {data.get('name')}")
            else:
                print(f"❌ Event creation API failed: {response.status_code}")
                print(f"   Response: {response.content}")
    except Exception as e:
        print(f"❌ Error testing event creation API: {e}")
    
    # Test venue creation
    try:
        with override_settings(ALLOWED_HOSTS=['testserver']):
            import time
            timestamp = str(int(time.time()))
            venue_data = {
                'event': str(test_event.id),
                'name': f'API Test Venue {timestamp}',
                'slug': f'api-test-venue-{timestamp}',
                'venue_type': 'GYMNASIUM',
                'address_line_1': '123 API Street',
                'city': 'Dublin',
                'country': 'Ireland',
                'total_capacity': 1000,
                'volunteer_capacity': 50,
                'is_active': True
            }
            response = client.post('/events/api/venues/', venue_data, format='json')
            if response.status_code == 201:
                print("✅ Venue creation API works")
                data = response.json()
                print(f"   Created venue: {data.get('name')}")
            else:
                print(f"❌ Venue creation API failed: {response.status_code}")
                print(f"   Response: {response.content}")
    except Exception as e:
        print(f"❌ Error testing venue creation API: {e}")
    
    # Test custom actions
    try:
        with override_settings(ALLOWED_HOSTS=['testserver']):
            # Test event stats
            response = client.get(f'/events/api/events/{test_event.id}/stats/')
            if response.status_code == 200:
                print("✅ Event stats API works")
            else:
                print(f"❌ Event stats API failed: {response.status_code}")
            
            # Test event venues
            response = client.get(f'/events/api/events/{test_event.id}/venues/')
            if response.status_code == 200:
                print("✅ Event venues API works")
            else:
                print(f"❌ Event venues API failed: {response.status_code}")
            
            # Test upcoming events
            response = client.get('/events/api/events/upcoming/')
            if response.status_code == 200:
                print("✅ Upcoming events API works")
            else:
                print(f"❌ Upcoming events API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing custom actions: {e}")
    
    print("\n🏁 Event Management API test completed!")
    return True

if __name__ == '__main__':
    test_event_api() 