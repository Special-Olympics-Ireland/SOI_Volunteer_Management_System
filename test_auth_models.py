#!/usr/bin/env python
"""
Test authentication models
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

def test_auth_models():
    print("Testing authentication models...")
    
    # Test user creation
    user, created = User.objects.get_or_create(
        username='testapi',
        defaults={
            'email': 'testapi@example.com',
            'first_name': 'Test',
            'last_name': 'API',
            'user_type': 'VOLUNTEER',
            'volunteer_type': 'NEW'
        }
    )
    print(f'User created: {created}, User: {user}')
    
    # Test token creation
    token, token_created = Token.objects.get_or_create(user=user)
    print(f'Token created: {token_created}, Token: {token.key[:20]}...')
    
    print('✅ Authentication system models working correctly!')

if __name__ == "__main__":
    test_auth_models() 