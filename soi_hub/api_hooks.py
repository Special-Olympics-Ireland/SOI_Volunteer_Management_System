"""
Custom API schema hooks for SOI Hub API documentation.
These hooks customize the OpenAPI schema generation process.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def custom_preprocessing_hook(endpoints):
    """
    Custom preprocessing hook for API schema generation.
    
    This hook runs before the schema is generated and can be used to:
    - Filter endpoints
    - Modify endpoint metadata
    - Add custom logic for endpoint processing
    
    Args:
        endpoints: List of (path, method, callback) tuples
        
    Returns:
        Modified list of endpoints
    """
    # Filter out admin-only endpoints from public documentation
    filtered_endpoints = []
    
    for path, method, callback in endpoints:
        # Skip internal admin endpoints
        if '/admin/' in path:
            continue
            
        # Skip debug endpoints in production
        if '/debug/' in path or '/test-' in path:
            continue
            
        # Add custom metadata to notification endpoints
        if '/notifications/' in path:
            # Add notification-specific metadata
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Notifications'],
                    'operation_id_base': 'notification'
                }
        
        # Add custom metadata to volunteer endpoints
        elif '/volunteers/' in path:
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Volunteers'],
                    'operation_id_base': 'volunteer'
                }
        
        # Add custom metadata to event endpoints
        elif '/events/' in path:
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Events'],
                    'operation_id_base': 'event'
                }
        
        # Add custom metadata to task endpoints
        elif '/tasks/' in path:
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Tasks'],
                    'operation_id_base': 'task'
                }
        
        # Add custom metadata to auth endpoints
        elif '/accounts/' in path:
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Authentication'],
                    'operation_id_base': 'auth'
                }
        
        # Add custom metadata to integration endpoints
        elif '/integrations/' in path:
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Integrations'],
                    'operation_id_base': 'integration'
                }
        
        # Add custom metadata to reporting endpoints
        elif '/reporting/' in path:
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Reporting'],
                    'operation_id_base': 'report'
                }
        
        # Add custom metadata to admin endpoints
        elif '/common/' in path and ('override' in path or 'admin' in path):
            if hasattr(callback, 'cls'):
                callback.cls._spectacular_annotation = {
                    'tags': ['Admin'],
                    'operation_id_base': 'admin'
                }
        
        filtered_endpoints.append((path, method, callback))
    
    logger.info(f"Preprocessed {len(filtered_endpoints)} API endpoints for documentation")
    return filtered_endpoints


def custom_postprocessing_hook(result: Dict[str, Any], generator, request, public: bool) -> Dict[str, Any]:
    """
    Custom postprocessing hook for API schema generation.
    
    This hook runs after the schema is generated and can be used to:
    - Modify the final schema
    - Add custom components
    - Enhance documentation
    
    Args:
        result: The generated OpenAPI schema
        generator: The schema generator instance
        request: The HTTP request
        public: Whether this is for public documentation
        
    Returns:
        Modified OpenAPI schema
    """
    # Add custom info to the schema
    if 'info' in result:
        result['info']['x-logo'] = {
            'url': 'https://specialolympics.ie/wp-content/uploads/2023/01/SOI-Logo-Horizontal-Colour.png',
            'altText': 'Special Olympics Ireland Logo'
        }
        
        # Add custom extensions
        result['info']['x-api-id'] = 'soi-hub-api'
        result['info']['x-audience'] = 'internal'
        result['info']['x-api-lifecycle'] = 'production'
    
    # Add custom security schemes
    if 'components' not in result:
        result['components'] = {}
    
    if 'securitySchemes' not in result['components']:
        result['components']['securitySchemes'] = {}
    
    # Enhance token authentication documentation
    result['components']['securitySchemes']['tokenAuth'] = {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': '''
        Token-based authentication for SOI Hub API.
        
        **Format:** `Token your_token_here`
        
        **Example:** `Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b`
        
        **How to get a token:**
        1. Register a user account via `/api/v1/accounts/register/`
        2. Login via `/api/v1/accounts/login/` to receive your token
        3. Include the token in all subsequent requests
        
        **Token Management:**
        - Tokens do not expire automatically
        - You can refresh your token via `/api/v1/accounts/token/refresh/`
        - Keep your token secure and do not share it
        '''
    }
    
    # Add custom response examples
    if 'paths' in result:
        for path, methods in result['paths'].items():
            for method, operation in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    # Add common error responses
                    if 'responses' in operation:
                        # Add 401 Unauthorized response
                        if '401' not in operation['responses']:
                            operation['responses']['401'] = {
                                'description': 'Authentication credentials were not provided or are invalid.',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'detail': {
                                                    'type': 'string',
                                                    'example': 'Authentication credentials were not provided.'
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        
                        # Add 403 Forbidden response for protected endpoints
                        if '403' not in operation['responses'] and 'admin' in path.lower():
                            operation['responses']['403'] = {
                                'description': 'You do not have permission to perform this action.',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'detail': {
                                                    'type': 'string',
                                                    'example': 'You do not have permission to perform this action.'
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        
                        # Add 429 Rate Limited response
                        if '429' not in operation['responses']:
                            operation['responses']['429'] = {
                                'description': 'Request was throttled. Too many requests.',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'detail': {
                                                    'type': 'string',
                                                    'example': 'Request was throttled. Expected available in 60 seconds.'
                                                }
                                            }
                                        }
                                    }
                                }
                            }
    
    # Add custom components for common response schemas
    if 'components' not in result:
        result['components'] = {}
    
    if 'schemas' not in result['components']:
        result['components']['schemas'] = {}
    
    # Add common error response schemas
    result['components']['schemas']['ErrorResponse'] = {
        'type': 'object',
        'properties': {
            'detail': {
                'type': 'string',
                'description': 'A human-readable error message'
            },
            'code': {
                'type': 'string',
                'description': 'An error code for programmatic handling'
            }
        },
        'required': ['detail']
    }
    
    result['components']['schemas']['ValidationErrorResponse'] = {
        'type': 'object',
        'properties': {
            'field_name': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'description': 'List of validation errors for this field'
            }
        },
        'additionalProperties': {
            'type': 'array',
            'items': {
                'type': 'string'
            }
        }
    }
    
    result['components']['schemas']['PaginatedResponse'] = {
        'type': 'object',
        'properties': {
            'count': {
                'type': 'integer',
                'description': 'Total number of items'
            },
            'next': {
                'type': 'string',
                'nullable': True,
                'description': 'URL to the next page of results'
            },
            'previous': {
                'type': 'string',
                'nullable': True,
                'description': 'URL to the previous page of results'
            },
            'results': {
                'type': 'array',
                'items': {},
                'description': 'Array of result items'
            }
        },
        'required': ['count', 'results']
    }
    
    # Add server information
    if 'servers' not in result:
        result['servers'] = []
    
    # Ensure we have proper server descriptions
    for server in result['servers']:
        if server.get('url') == 'http://localhost:8000':
            server['description'] = 'Development server (local)'
        elif '195.7.35.202' in server.get('url', ''):
            server['description'] = 'Production server (SOI Hub)'
    
    logger.info("Applied custom postprocessing to API schema")
    return result 