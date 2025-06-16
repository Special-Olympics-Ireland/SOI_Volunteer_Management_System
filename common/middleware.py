"""
Common middleware for SOI Hub application
"""

import logging
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    """
    Middleware to log user actions for audit purposes
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)
        
        # Log user actions if authenticated
        if request.user.is_authenticated and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            try:
                # Log the action
                logger.info(
                    f"User {request.user.username} performed {request.method} on {request.path}"
                )
            except Exception as e:
                logger.error(f"Error in AuditLogMiddleware: {e}")
        
        return response


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response 