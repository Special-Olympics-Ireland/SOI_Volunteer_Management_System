"""
API Documentation configuration for SOI Hub.
Uses DRF Spectacular for OpenAPI schema generation.
"""

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from django.urls import path

# API Documentation URLs
api_docs_urlpatterns = [
    # OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ReDoc UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'SOI Hub API',
    'DESCRIPTION': '''
    # ISG 2026 Volunteer Management Backend System API
    
    ## Overview
    The SOI Hub API provides comprehensive volunteer management capabilities for the 
    Ireland Special Olympics Games 2026. This RESTful API enables efficient management 
    of volunteers, events, tasks, and real-time communications.
    
    ## Key Features
    - **User Management**: Authentication, authorization, and user profiles
    - **Volunteer Management**: EOI system, profile management, and status tracking
    - **Event Management**: Event creation, venue management, and volunteer assignments
    - **Task Management**: Task assignment, progress tracking, and completion workflows
    - **Real-time Notifications**: WebSocket-based notifications and user preferences
    - **Reporting & Analytics**: Comprehensive reporting and data export capabilities
    - **External Integrations**: JustGo API integration for membership validation
    - **Admin Overrides**: Audit-logged administrative override capabilities
    
    ## Authentication
    The API uses Token-based authentication. Include your token in the Authorization header:
    ```
    Authorization: Token your_token_here
    ```
    
    ## Rate Limiting
    API requests are rate-limited to ensure fair usage and system stability.
    
    ## Support
    For technical support, contact the SOI IT Team at it@specialolympics.ie
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Development server'
        },
        {
            'url': 'https://195.7.35.202',
            'description': 'Production server'
        }
    ],
    'TAGS': [
        {
            'name': 'Authentication',
            'description': '''
            User authentication and authorization endpoints.
            
            **Features:**
            - User registration and login
            - Token-based authentication
            - Password reset and email verification
            - User profile management
            - Role-based access control (RBAC)
            - User preferences and settings
            '''
        },
        {
            'name': 'Volunteers',
            'description': '''
            Volunteer management and Expression of Interest (EOI) system.
            
            **Features:**
            - Three-part EOI form system (Profile, Recruitment, Games)
            - Volunteer profile management with comprehensive fields
            - Status workflow (Pending, Approved, Active, Suspended)
            - Skills and qualifications tracking
            - Availability and scheduling management
            - Corporate volunteer group management
            - JustGo integration for membership validation
            - Bulk operations and filtering
            '''
        },
        {
            'name': 'Events',
            'description': '''
            Event, venue, and role management system.
            
            **Features:**
            - Event creation and lifecycle management
            - Venue management with accessibility information
            - Role definition with capacity and requirements
            - Volunteer assignment and scheduling
            - Event status tracking and workflows
            - Capacity management and utilization tracking
            - Assignment workflows with check-in/check-out
            - Bulk operations and admin overrides
            '''
        },
        {
            'name': 'Tasks',
            'description': '''
            Task assignment and completion tracking system.
            
            **Features:**
            - Dynamic task types (Checkbox, Photo, Text, Custom)
            - Task assignment and delegation workflows
            - Progress tracking and completion validation
            - Prerequisites and dependency management
            - Verification processes and approval workflows
            - Template management for recurring tasks
            - Bulk operations and analytics
            - Role-specific task creation and assignment
            '''
        },
        {
            'name': 'Notifications',
            'description': '''
            Real-time notification system with multi-channel delivery.
            
            **Features:**
            - Real-time WebSocket notifications
            - Multi-channel delivery (In-app, Email, Push, SMS)
            - User notification preferences and quiet hours
            - Template system with 17+ notification types
            - Priority levels and targeting by user types/roles
            - Notification history and read status tracking
            - Bulk notification capabilities
            - Comprehensive audit logging
            '''
        },
        {
            'name': 'Integrations',
            'description': '''
            External system integrations and API connections.
            
            **Features:**
            - JustGo API integration for membership validation
            - Bi-directional data synchronization
            - Credential validation and caching
            - Health monitoring and error handling
            - Bulk synchronization operations
            - Integration audit logging
            - Admin override capabilities
            '''
        },
        {
            'name': 'Reporting',
            'description': '''
            Analytics, reporting, and data export capabilities.
            
            **Features:**
            - Comprehensive report generation
            - Template-based reporting system
            - Scheduled report execution
            - Multiple export formats (PDF, Excel, CSV)
            - Real-time analytics and dashboards
            - Custom report creation
            - Report sharing and collaboration
            - Performance metrics and KPIs
            '''
        },
        {
            'name': 'Admin',
            'description': '''
            Administrative functions and system management.
            
            **Features:**
            - Admin override system with audit logging
            - System configuration management
            - User management and role assignment
            - Bulk operations and data management
            - System health monitoring
            - Audit trail and security logging
            - Emergency access procedures
            '''
        }
    ],
    'CONTACT': {
        'name': 'SOI IT Team',
        'email': 'it@specialolympics.ie',
        'url': 'https://specialolympics.ie'
    },
    'LICENSE': {
        'name': 'Proprietary - Special Olympics Ireland',
        'url': 'https://specialolympics.ie'
    },
    'EXTERNAL_DOCS': {
        'description': 'SOI Hub Documentation',
        'url': 'https://docs.specialolympics.ie/soi-hub'
    },
    # Enhanced schema generation settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
        'supportedSubmitMethods': ['get', 'post', 'put', 'patch', 'delete'],
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'hideLoading': False,
        'nativeScrollbars': False,
        'pathInMiddlePanel': True,
        'requiredPropsFirst': True,
        'scrollYOffset': 0,
        'sortPropsAlphabetically': True,
        'suppressWarnings': False,
        'theme': {
            'colors': {
                'primary': {
                    'main': '#2E7D32'  # SOI Green
                }
            }
        }
    },
    # Schema customization
    # 'PREPROCESSING_HOOKS': [
    #     'soi_hub.api_hooks.custom_preprocessing_hook',
    # ],
    # 'POSTPROCESSING_HOOKS': [
    #     'soi_hub.api_hooks.custom_postprocessing_hook',
    # ],
    'ENUM_NAME_OVERRIDES': {
        'UserTypeEnum': 'accounts.models.User.UserType',
        'VolunteerStatusEnum': 'volunteers.models.VolunteerProfile.Status',
        'EventStatusEnum': 'events.models.Event.Status',
        'TaskStatusEnum': 'tasks.models.Task.Status',
        'NotificationTypeEnum': 'common.notification_models.NotificationTemplate.NotificationType',
        'PriorityEnum': 'common.notification_models.NotificationTemplate.Priority',
    },
    'COMPONENT_SPLIT_PATCH': True,
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': True,
    'DISABLE_ERRORS_AND_WARNINGS': False,
} 