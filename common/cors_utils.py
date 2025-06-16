"""
CORS utility functions for SOI Hub.
Provides testing and debugging capabilities for CORS configuration.
"""

import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger('soi_hub.cors')


class CORSTestView(View):
    """
    View for testing CORS configuration.
    Provides endpoints to test different CORS scenarios.
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """
        Test GET request with CORS headers.
        """
        origin = request.META.get('HTTP_ORIGIN', 'No Origin')
        
        response_data = {
            'message': 'CORS GET test successful',
            'origin': origin,
            'method': 'GET',
            'timestamp': self._get_timestamp(),
            'headers_received': self._get_request_headers(request),
            'cors_config': self._get_cors_config(),
        }
        
        logger.info(f"CORS GET test from origin: {origin}")
        return JsonResponse(response_data)
    
    def post(self, request):
        """
        Test POST request with CORS headers.
        """
        origin = request.META.get('HTTP_ORIGIN', 'No Origin')
        
        try:
            request_data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            request_data = {'error': 'Invalid JSON in request body'}
        
        response_data = {
            'message': 'CORS POST test successful',
            'origin': origin,
            'method': 'POST',
            'timestamp': self._get_timestamp(),
            'request_data': request_data,
            'headers_received': self._get_request_headers(request),
            'cors_config': self._get_cors_config(),
        }
        
        logger.info(f"CORS POST test from origin: {origin}")
        return JsonResponse(response_data)
    
    def options(self, request):
        """
        Handle preflight OPTIONS request.
        """
        origin = request.META.get('HTTP_ORIGIN', 'No Origin')
        
        response_data = {
            'message': 'CORS OPTIONS (preflight) test successful',
            'origin': origin,
            'method': 'OPTIONS',
            'timestamp': self._get_timestamp(),
            'preflight_headers': {
                'Access-Control-Request-Method': request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD'),
                'Access-Control-Request-Headers': request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS'),
            },
            'cors_config': self._get_cors_config(),
        }
        
        logger.info(f"CORS OPTIONS test from origin: {origin}")
        return JsonResponse(response_data)
    
    def _get_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _get_request_headers(self, request):
        """Extract relevant headers from request."""
        relevant_headers = [
            'HTTP_ORIGIN',
            'HTTP_REFERER',
            'HTTP_USER_AGENT',
            'HTTP_AUTHORIZATION',
            'HTTP_X_REQUESTED_WITH',
            'HTTP_CONTENT_TYPE',
            'HTTP_ACCEPT',
        ]
        
        headers = {}
        for header in relevant_headers:
            value = request.META.get(header)
            if value:
                headers[header.replace('HTTP_', '').replace('_', '-').lower()] = value
        
        return headers
    
    def _get_cors_config(self):
        """Get current CORS configuration."""
        return {
            'allowed_origins': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            'allow_credentials': getattr(settings, 'CORS_ALLOW_CREDENTIALS', False),
            'allowed_methods': getattr(settings, 'CORS_ALLOWED_METHODS', []),
            'allowed_headers': getattr(settings, 'CORS_ALLOWED_HEADERS', []),
            'expose_headers': getattr(settings, 'CORS_EXPOSE_HEADERS', []),
            'preflight_max_age': getattr(settings, 'CORS_PREFLIGHT_MAX_AGE', 86400),
            'debug_mode': settings.DEBUG,
        }


def validate_cors_origin(origin):
    """
    Validate if an origin is allowed by current CORS configuration.
    
    Args:
        origin (str): The origin to validate
        
    Returns:
        dict: Validation result with details
    """
    from .cors_middleware import SOIHubCORSMiddleware
    
    middleware = SOIHubCORSMiddleware(lambda x: x)
    is_allowed = middleware.is_origin_allowed(origin)
    
    result = {
        'origin': origin,
        'allowed': is_allowed,
        'reason': '',
        'config': {
            'allowed_origins': middleware.allowed_origins,
            'allowed_origin_regexes': middleware.allowed_origin_regexes,
            'debug_mode': settings.DEBUG,
        }
    }
    
    if is_allowed:
        if origin in middleware.allowed_origins:
            result['reason'] = 'Exact match in allowed origins'
        elif settings.DEBUG and origin.startswith(('http://localhost:', 'http://127.0.0.1:')):
            result['reason'] = 'Development mode localhost/127.0.0.1 allowance'
        else:
            result['reason'] = 'Matched regex pattern'
    else:
        result['reason'] = 'Origin not in allowed list and no regex match'
    
    return result


def get_cors_preflight_response(origin, method, headers):
    """
    Generate a CORS preflight response for testing.
    
    Args:
        origin (str): Request origin
        method (str): Requested method
        headers (str): Requested headers (comma-separated)
        
    Returns:
        dict: Preflight response details
    """
    from .cors_middleware import SOIHubCORSMiddleware
    
    middleware = SOIHubCORSMiddleware(lambda x: x)
    
    # Check origin
    origin_allowed = middleware.is_origin_allowed(origin)
    
    # Check method
    method_allowed = method in middleware.allowed_methods if method else True
    
    # Check headers
    headers_allowed = True
    rejected_headers = []
    
    if headers:
        requested_headers = [h.strip().lower() for h in headers.split(',')]
        allowed_headers_lower = [h.lower() for h in middleware.allowed_headers]
        
        for header in requested_headers:
            if header not in allowed_headers_lower:
                headers_allowed = False
                rejected_headers.append(header)
    
    return {
        'origin': origin,
        'requested_method': method,
        'requested_headers': headers,
        'origin_allowed': origin_allowed,
        'method_allowed': method_allowed,
        'headers_allowed': headers_allowed,
        'rejected_headers': rejected_headers,
        'overall_allowed': origin_allowed and method_allowed and headers_allowed,
        'response_headers': {
            'Access-Control-Allow-Origin': origin if origin_allowed else None,
            'Access-Control-Allow-Methods': ', '.join(middleware.allowed_methods),
            'Access-Control-Allow-Headers': ', '.join(middleware.allowed_headers),
            'Access-Control-Allow-Credentials': 'true' if middleware.allow_credentials else 'false',
            'Access-Control-Max-Age': str(middleware.preflight_max_age),
        }
    }


def log_cors_configuration():
    """
    Log current CORS configuration for debugging.
    """
    config = {
        'CORS_ALLOWED_ORIGINS': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
        'CORS_ALLOWED_ORIGIN_REGEXES': getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', []),
        'CORS_ALLOW_CREDENTIALS': getattr(settings, 'CORS_ALLOW_CREDENTIALS', False),
        'CORS_ALLOWED_METHODS': getattr(settings, 'CORS_ALLOWED_METHODS', []),
        'CORS_ALLOWED_HEADERS': getattr(settings, 'CORS_ALLOWED_HEADERS', []),
        'CORS_EXPOSE_HEADERS': getattr(settings, 'CORS_EXPOSE_HEADERS', []),
        'CORS_PREFLIGHT_MAX_AGE': getattr(settings, 'CORS_PREFLIGHT_MAX_AGE', 86400),
        'SOI_CORS_ENABLE_LOGGING': getattr(settings, 'SOI_CORS_ENABLE_LOGGING', False),
        'SOI_CORS_STRICT_MODE': getattr(settings, 'SOI_CORS_STRICT_MODE', True),
        'DEBUG': settings.DEBUG,
    }
    
    logger.info("Current CORS Configuration:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    return config


def test_cors_scenarios():
    """
    Test common CORS scenarios and return results.
    
    Returns:
        dict: Test results for various scenarios
    """
    test_origins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'https://specialolympics.ie',
        'https://volunteers.specialolympics.ie',
        'https://isg2026.specialolympics.ie',
        'https://malicious-site.com',
        'http://localhost:8080',
    ]
    
    test_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
    
    test_headers = [
        'content-type',
        'authorization',
        'x-custom-header',
        'x-csrftoken',
    ]
    
    results = {
        'origin_tests': {},
        'method_tests': {},
        'header_tests': {},
        'preflight_tests': {},
    }
    
    # Test origins
    for origin in test_origins:
        results['origin_tests'][origin] = validate_cors_origin(origin)
    
    # Test methods (using first allowed origin)
    if test_origins:
        first_origin = test_origins[0]
        for method in test_methods:
            results['method_tests'][method] = get_cors_preflight_response(
                first_origin, method, 'content-type'
            )
    
    # Test headers (using first allowed origin and GET method)
    if test_origins:
        first_origin = test_origins[0]
        for header in test_headers:
            results['header_tests'][header] = get_cors_preflight_response(
                first_origin, 'GET', header
            )
    
    # Test preflight scenarios
    preflight_scenarios = [
        ('http://localhost:3000', 'POST', 'content-type,authorization'),
        ('https://malicious-site.com', 'GET', 'content-type'),
        ('http://localhost:3000', 'DELETE', 'authorization'),
    ]
    
    for i, (origin, method, headers) in enumerate(preflight_scenarios):
        results['preflight_tests'][f'scenario_{i+1}'] = get_cors_preflight_response(
            origin, method, headers
        )
    
    return results


def generate_cors_report():
    """
    Generate a comprehensive CORS configuration report.
    
    Returns:
        dict: Detailed CORS report
    """
    report = {
        'timestamp': None,
        'environment': 'development' if settings.DEBUG else 'production',
        'configuration': log_cors_configuration(),
        'test_results': test_cors_scenarios(),
        'recommendations': [],
        'warnings': [],
    }
    
    # Add timestamp
    from datetime import datetime
    report['timestamp'] = datetime.now().isoformat()
    
    # Generate recommendations
    config = report['configuration']
    
    if settings.DEBUG:
        report['recommendations'].append(
            "Development mode detected - ensure CORS settings are updated for production"
        )
    
    if config['CORS_ALLOW_CREDENTIALS'] and '*' in config.get('CORS_ALLOWED_ORIGINS', []):
        report['warnings'].append(
            "SECURITY WARNING: CORS_ALLOW_CREDENTIALS is True with wildcard origin"
        )
    
    if not settings.DEBUG:
        insecure_origins = [
            origin for origin in config.get('CORS_ALLOWED_ORIGINS', [])
            if origin.startswith('http://')
        ]
        if insecure_origins:
            report['warnings'].append(
                f"SECURITY WARNING: Insecure HTTP origins in production: {insecure_origins}"
            )
    
    if not config.get('SOI_CORS_ENABLE_LOGGING', False) and settings.DEBUG:
        report['recommendations'].append(
            "Consider enabling SOI_CORS_ENABLE_LOGGING for development debugging"
        )
    
    return report


# CORS testing URLs for inclusion in URL patterns
def get_cors_test_urls():
    """
    Get URL patterns for CORS testing endpoints.
    """
    from django.urls import path
    
    return [
        path('cors/test/', CORSTestView.as_view(), name='cors-test'),
        path('cors/validate/<str:origin>/', cors_validate_view, name='cors-validate'),
        path('cors/report/', cors_report_view, name='cors-report'),
    ]


@require_http_methods(["GET"])
def cors_validate_view(request, origin):
    """
    View to validate a specific origin.
    """
    result = validate_cors_origin(origin)
    return JsonResponse(result)


@require_http_methods(["GET"])
def cors_report_view(request):
    """
    View to generate CORS configuration report.
    """
    report = generate_cors_report()
    return JsonResponse(report, json_dumps_params={'indent': 2}) 