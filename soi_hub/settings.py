"""
Django settings for soi_hub project.

ISG 2026 Volunteer Management Backend System
Special Olympics Ireland

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,192.168.168.3,195.7.35.202', cast=Csv())

# Application definition
DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',  # Move admin to end for template loading
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'channels',
]

LOCAL_APPS = [
    'common',  # Move common first for template loading priority
    'accounts',
    'events',
    'volunteers',
    'tasks',
    'integrations',
    'reporting',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'common.middleware.AuditLogMiddleware',  # Custom audit logging
]

ROOT_URLCONF = 'soi_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'common.context_processors.theme_context',
                'common.context_processors.system_config_context',
                'common.context_processors.user_context',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'soi_hub.wsgi.application'
ASGI_APPLICATION = 'soi_hub.asgi.application'

# Channel Layer Configuration for WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://localhost:6379/1')],
            "capacity": 1500,  # Maximum number of messages to store
            "expiry": 60,      # Message expiry time in seconds
        },
    },
}

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='soi_hub_db'),
        'USER': config('DB_USER', default='soi_user'),
        'PASSWORD': config('DB_PASSWORD', default='soi_password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            # PostgreSQL specific options
        },
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-ie'
TIME_ZONE = 'Europe/Dublin'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'

# Custom CORS middleware settings
CORS_SECURITY_ENABLED = os.getenv('CORS_SECURITY_ENABLED', 'True').lower() == 'true'
CORS_LOG_REQUESTS = os.getenv('CORS_LOG_REQUESTS', 'True').lower() == 'true'

# Enhanced CORS settings for SOI Hub
CORS_ALLOWED_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-soi-hub-version',
    'cache-control',
]

CORS_EXPOSE_HEADERS = [
    'x-soi-hub-version',
    'x-soi-hub-environment',
    'x-total-count',
    'x-page-count',
]

CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# SOI Hub specific CORS settings
SOI_CORS_ENABLE_LOGGING = config('SOI_CORS_ENABLE_LOGGING', default=DEBUG, cast=bool)
SOI_CORS_STRICT_MODE = config('SOI_CORS_STRICT_MODE', default=not DEBUG, cast=bool)

# CORS origin regex patterns for dynamic subdomains
CORS_ALLOWED_ORIGIN_REGEXES = []

if not DEBUG:
    # Production regex patterns
    CORS_ALLOWED_ORIGIN_REGEXES.extend([
        r"^https://.*\.specialolympics\.ie$",
        r"^https://isg2026\.specialolympics\.ie$",
    ])
else:
    # Development regex patterns
    CORS_ALLOWED_ORIGIN_REGEXES.extend([
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
    ])

# Cache Configuration (Local Memory - for development without Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'soi_hub_cache',
        'TIMEOUT': 300,  # 5 minutes default timeout
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Session Configuration (Database sessions - for development without Redis)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Email Configuration
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@specialolympics.ie')

# JustGo API Configuration
JUSTGO_API = {
    'SECRET': config('JUSTGO_API_SECRET', default=''),
    'BASE_URL': config('JUSTGO_API_BASE_URL', default='https://api.justgo.com'),
    'API_VERSION': config('JUSTGO_API_VERSION', default='v2.1'),
    'TIMEOUT': config('JUSTGO_API_TIMEOUT', default=30, cast=int),
    'MAX_RETRIES': config('JUSTGO_API_MAX_RETRIES', default=3, cast=int),
    'RATE_LIMIT_DELAY': config('JUSTGO_API_RATE_LIMIT_DELAY', default=0.5, cast=float),
}

# JustGo Safety Settings
# Set to False ONLY in development/testing to enable write operations
JUSTGO_READONLY_MODE = config('JUSTGO_READONLY_MODE', default=True, cast=bool)

# SOI Branding Configuration
SOI_BRAND_COLORS = {
    'PRIMARY_GREEN': '#228B22',
    'WHITE': '#FFFFFF',
    'GOLD': '#FFD700',
    'DARK_GREEN': '#006400',
    'LIGHT_GREEN': '#90EE90',
}

# Admin Site Configuration
ADMIN_SITE_HEADER = 'SOI Hub Administration'
ADMIN_SITE_TITLE = 'SOI Hub Admin'
ADMIN_INDEX_TITLE = 'ISG 2026 Volunteer Management System'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'audit': {
            'format': '[AUDIT] {asctime} {name} {levelname} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} {name} {levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'audit.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 20,  # Keep more audit logs
            'formatter': 'audit',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 20,  # Keep more security logs
            'formatter': 'security',
        },
        'justgo_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'justgo.log'),
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'soi_hub.audit': {
            'handlers': ['audit_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'soi_hub.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'soi_hub.justgo': {
            'handlers': ['justgo_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'soi_hub.volunteers': {
            'handlers': ['audit_file', 'file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'soi_hub.events': {
            'handlers': ['audit_file', 'file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'soi_hub.tasks': {
            'handlers': ['audit_file', 'file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'soi_hub.integrations': {
            'handlers': ['justgo_file', 'audit_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'soi_hub.reporting': {
            'handlers': ['audit_file', 'file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# ISG 2026 Specific Configuration
ISG_2026_CONFIG = {
    'EVENT_NAME': 'ISG 2026',
    'EVENT_START_DATE': '2026-06-18',
    'EVENT_END_DATE': '2026-06-21',
    'VOLUNTEER_TARGET': 5000,
    'MIN_VOLUNTEER_AGE': 15,
    'VENUE_PREFERENCES_LIMIT': 3,
    'PHOTO_UPLOAD_MAX_SIZE': 2097152,  # 2MB
    'SUPPORTED_PHOTO_FORMATS': ['JPEG', 'JPG', 'PNG'],
}

# Volunteer Type Configuration
VOLUNTEER_TYPES = {
    'GENERAL': 'General Volunteer',
    'GOC': 'Games Operations Committee',
    'CVT': 'Competition Venue Team',
    'VMT': 'Venue Management Team',
    'COMMUNITY': 'Community Volunteer',
    'CORPORATE': 'Corporate Volunteer',
    'THIRD_PARTY': '3rd Party Volunteer',
    'ATHLETE': 'Athlete Volunteer',
}

# Task Type Configuration
TASK_TYPES = {
    'CHECKBOX': 'Checkbox Completion',
    'PHOTO': 'Photo Upload',
    'TEXT': 'Text Submission',
    'CUSTOM': 'Custom Field',
}

# Professional Skills Configuration
PROFESSIONAL_SKILLS = [
    'Administration',
    'Catering',
    'Communications',
    'Content Creator',
    'Event Management',
    'Graphic Design',
    'Health & Safety',
    'Human Resources',
    'Logistics',
    'Marketing / Media / PR',
    'Photography',
    'Professional Driver',
    'Project Management',
    'Teacher / Lecturer / Tutor',
    'Security',
    'Transport Planning',
    'Videographer',
]

# T-Shirt Sizes Configuration
TSHIRT_SIZES = [
    ('XS', 'Extra Small'),
    ('S', 'Small'),
    ('M', 'Medium'),
    ('L', 'Large'),
    ('XL', 'Extra Large'),
    ('2XL', '2X Large'),
    ('3XL', '3X Large'),
]

# Dietary Requirements Configuration
DIETARY_REQUIREMENTS = [
    'Coeliac',
    'Lactose Intolerant',
    'Diabetic',
    'Vegetarian',
    'Vegan',
    'No Pork',
    'No Nuts',
    'No Shellfish',
    'Other',
]

# Additional Support Needs Configuration
SUPPORT_NEEDS = [
    'Mobility',
    'Audio',
    'Visual',
    'Speech, Language and Communication',
    'Other',
]

# DRF Spectacular Configuration (API Documentation)
from .api_docs import SPECTACULAR_SETTINGS

# Django Authentication Settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/accounts/login/' 