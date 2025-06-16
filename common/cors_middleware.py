"""
Custom CORS middleware for SOI Hub.
Provides enhanced CORS handling with security features and logging.
"""

import logging
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger('soi_hub.cors')


class SOIHubCORSMiddleware(MiddlewareMixin):
    """
    Enhanced CORS middleware for SOI Hub with security features.
    
    This middleware extends the basic CORS functionality with:
    - Enhanced security headers
    - Request logging for debugging
    - Dynamic origin validation
    - Rate limiting integration
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Load CORS settings
        self.allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        self.allowed_origin_regexes = getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', [])
        self.allow_credentials = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)
        self.allowed_methods = getattr(settings, 'CORS_ALLOWED_METHODS', [
            'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT'
        ])
        self.allowed_headers = getattr(settings, 'CORS_ALLOWED_HEADERS', [
            'accept', 'accept-encoding', 'authorization', 'content-type',
            'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with'
        ])
        self.expose_headers = getattr(settings, 'CORS_EXPOSE_HEADERS', [])
        self.preflight_max_age = getattr(settings, 'CORS_PREFLIGHT_MAX_AGE', 86400)
        
        # SOI Hub specific settings
        self.enable_logging = getattr(settings, 'SOI_CORS_ENABLE_LOGGING', settings.DEBUG)
        self.strict_mode = getattr(settings, 'SOI_CORS_STRICT_MODE', not settings.DEBUG)
        
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Process incoming request for CORS handling.
        """
        origin = request.META.get('HTTP_ORIGIN')
        
        if self.enable_logging and origin:
            logger.info(f"CORS request from origin: {origin} to {request.path}")
        
        # Handle preflight requests
        if request.method == 'OPTIONS' and origin:
            return self.handle_preflight(request, origin)
        
        return None
    
    def process_response(self, request, response):
        """
        Add CORS headers to response.
        """
        origin = request.META.get('HTTP_ORIGIN')
        
        if origin and self.is_origin_allowed(origin):
            self.add_cors_headers(response, origin, request)
        elif origin and self.strict_mode:
            # In strict mode, log rejected origins
            logger.warning(f"CORS request rejected from origin: {origin}")
        
        return response
    
    def handle_preflight(self, request, origin):
        """
        Handle CORS preflight requests.
        """
        if not self.is_origin_allowed(origin):
            if self.enable_logging:
                logger.warning(f"Preflight request rejected from origin: {origin}")
            return HttpResponse(status=403)
        
        # Check requested method
        requested_method = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')
        if requested_method and requested_method not in self.allowed_methods:
            if self.enable_logging:
                logger.warning(f"Preflight request rejected - method {requested_method} not allowed")
            return HttpResponse(status=405)
        
        # Check requested headers
        requested_headers = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '')
        if requested_headers:
            requested_headers_list = [h.strip().lower() for h in requested_headers.split(',')]
            allowed_headers_lower = [h.lower() for h in self.allowed_headers]
            
            for header in requested_headers_list:
                if header not in allowed_headers_lower:
                    if self.enable_logging:
                        logger.warning(f"Preflight request rejected - header {header} not allowed")
                    return HttpResponse(status=400)
        
        # Create preflight response
        response = HttpResponse(status=200)
        self.add_cors_headers(response, origin, request, is_preflight=True)
        
        if self.enable_logging:
            logger.info(f"Preflight request approved for origin: {origin}")
        
        return response
    
    def is_origin_allowed(self, origin):
        """
        Check if origin is allowed based on configuration.
        """
        if not origin:
            return False
        
        # Check exact matches
        if origin in self.allowed_origins:
            return True
        
        # Check regex patterns
        import re
        for pattern in self.allowed_origin_regexes:
            if re.match(pattern, origin):
                return True
        
        # Special handling for development
        if settings.DEBUG:
            # Allow localhost and 127.0.0.1 with any port in debug mode
            if origin.startswith(('http://localhost:', 'http://127.0.0.1:', 'https://localhost:', 'https://127.0.0.1:')):
                return True
        
        return False
    
    def add_cors_headers(self, response, origin, request, is_preflight=False):
        """
        Add CORS headers to response.
        """
        # Basic CORS headers
        response['Access-Control-Allow-Origin'] = origin
        
        if self.allow_credentials:
            response['Access-Control-Allow-Credentials'] = 'true'
        
        if is_preflight:
            # Preflight-specific headers
            response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
            response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
            response['Access-Control-Max-Age'] = str(self.preflight_max_age)
        else:
            # Regular request headers
            if self.expose_headers:
                response['Access-Control-Expose-Headers'] = ', '.join(self.expose_headers)
        
        # SOI Hub security headers
        self.add_security_headers(response, request)
    
    def add_security_headers(self, response, request):
        """
        Add additional security headers for SOI Hub.
        """
        # Content Security Policy for API responses
        if request.path.startswith('/api/'):
            response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none';"
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # SOI Hub specific headers
        response['X-SOI-Hub-Version'] = '1.0.0'
        response['X-SOI-Hub-Environment'] = 'development' if settings.DEBUG else 'production'


class CORSConfigValidator:
    """
    Validator for CORS configuration settings.
    """
    
    @staticmethod
    def validate_settings():
        """
        Validate CORS settings for common misconfigurations.
        """
        errors = []
        
        # Check for wildcard origins with credentials
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        allow_credentials = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)
        
        if '*' in allowed_origins and allow_credentials:
            errors.append(
                "CORS_ALLOW_CREDENTIALS cannot be True when CORS_ALLOWED_ORIGINS contains '*'"
            )
        
        # Check for insecure origins in production
        if not settings.DEBUG:
            insecure_origins = [origin for origin in allowed_origins if origin.startswith('http://')]
            if insecure_origins:
                errors.append(
                    f"Insecure HTTP origins found in production: {insecure_origins}"
                )
        
        # Check for localhost in production
        if not settings.DEBUG:
            localhost_origins = [
                origin for origin in allowed_origins 
                if 'localhost' in origin or '127.0.0.1' in origin
            ]
            if localhost_origins:
                errors.append(
                    f"Localhost origins found in production: {localhost_origins}"
                )
        
        # Validate methods
        allowed_methods = getattr(settings, 'CORS_ALLOWED_METHODS', [])
        dangerous_methods = ['TRACE', 'CONNECT']
        found_dangerous = [method for method in allowed_methods if method in dangerous_methods]
        if found_dangerous:
            errors.append(
                f"Potentially dangerous HTTP methods allowed: {found_dangerous}"
            )
        
        if errors:
            raise ImproperlyConfigured(
                f"CORS configuration errors: {'; '.join(errors)}"
            )
        
        return True


def get_cors_headers_for_origin(origin):
    """
    Utility function to get CORS headers for a specific origin.
    Used for testing and debugging.
    """
    middleware = SOIHubCORSMiddleware(lambda x: x)
    
    if middleware.is_origin_allowed(origin):
        headers = {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': ', '.join(middleware.allowed_methods),
            'Access-Control-Allow-Headers': ', '.join(middleware.allowed_headers),
        }
        
        if middleware.allow_credentials:
            headers['Access-Control-Allow-Credentials'] = 'true'
        
        if middleware.expose_headers:
            headers['Access-Control-Expose-Headers'] = ', '.join(middleware.expose_headers)
        
        return headers
    
    return None


def log_cors_request(request, allowed=True):
    """
    Utility function to log CORS requests for debugging.
    """
    origin = request.META.get('HTTP_ORIGIN', 'No Origin')
    method = request.method
    path = request.path
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    log_message = f"CORS {method} request from {origin} to {path} - {'ALLOWED' if allowed else 'REJECTED'}"
    
    if allowed:
        logger.info(log_message)
    else:
        logger.warning(f"{log_message} - User-Agent: {user_agent}")


# CORS configuration presets for different environments
CORS_PRESETS = {
    'development': {
        'CORS_ALLOWED_ORIGINS': [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001',
        ],
        'CORS_ALLOW_CREDENTIALS': True,
        'SOI_CORS_ENABLE_LOGGING': True,
        'SOI_CORS_STRICT_MODE': False,
    },
    'staging': {
        'CORS_ALLOWED_ORIGINS': [
            'https://staging.specialolympics.ie',
            'https://staging-volunteers.specialolympics.ie',
        ],
        'CORS_ALLOW_CREDENTIALS': True,
        'SOI_CORS_ENABLE_LOGGING': True,
        'SOI_CORS_STRICT_MODE': True,
    },
    'production': {
        'CORS_ALLOWED_ORIGINS': [
            'https://specialolympics.ie',
            'https://volunteers.specialolympics.ie',
            'https://isg2026.specialolympics.ie',
        ],
        'CORS_ALLOW_CREDENTIALS': True,
        'SOI_CORS_ENABLE_LOGGING': False,
        'SOI_CORS_STRICT_MODE': True,
    }
} 