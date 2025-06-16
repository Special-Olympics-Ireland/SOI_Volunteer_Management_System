#!/usr/bin/env python3
"""
Debug URL routing for SOI Hub API endpoints
"""

import os
import sys
import django
from django.urls import reverse
from django.core.exceptions import NoReverseMatch

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.urls import get_resolver

def debug_urls():
    """Debug URL patterns"""
    print("🔍 Debugging URL Patterns")
    print("=" * 50)
    
    resolver = get_resolver()
    
    # Test specific API endpoints
    test_endpoints = [
        '/api/v1/accounts/users/',
        '/api/v1/accounts/api/users/',
        '/api/v1/volunteers/profiles/',
        '/api/v1/volunteers/api/profiles/',
        '/api/v1/events/events/',
        '/api/v1/events/api/events/',
        '/api/v1/tasks/tasks/',
        '/api/v1/tasks/api/tasks/',
        '/api/v1/notifications/api/notifications/notifications/',
    ]
    
    print("Testing API endpoint resolution:")
    for endpoint in test_endpoints:
        try:
            match = resolver.resolve(endpoint)
            print(f"✅ {endpoint} -> {match.func}")
        except Exception as e:
            print(f"❌ {endpoint} -> {str(e)}")
    
    print("\n" + "=" * 50)
    print("URL Pattern Analysis Complete")

if __name__ == "__main__":
    debug_urls() 