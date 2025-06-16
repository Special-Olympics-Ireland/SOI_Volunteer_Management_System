"""
URL configuration for soi_hub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .api_docs import api_docs_urlpatterns
from django.views.generic import TemplateView
from common.views import ComprehensiveAPIDocsView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Django Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Admin Help System
    path('help/', include('common.help_urls')),
    
    # Theme Management System
    path('themes/', include('common.theme_urls')),
    
    # Mobile Admin Interface
    path('mobile-admin/', include('common.mobile_admin_urls')),
    
    # API Documentation
    *api_docs_urlpatterns,
    
    # API v1 endpoints - Direct mapping to app API paths
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/events/', include('events.urls')),
    path('api/v1/volunteers/', include('volunteers.urls')),
    path('api/v1/tasks/', include('tasks.urls')),
    path('api/v1/integrations/', include('integrations.urls')),
    path('api/v1/reporting/', include('reporting.urls')),
    path('api/v1/notifications/', include('common.notification_urls')),
    
    # App URLs (for web interface)
    path('accounts/', include('accounts.urls')),
    path('events/', include('events.urls')),
    path('volunteers/', include('volunteers.urls')),
    path('tasks/', include('tasks.urls')),
    path('integrations/', include('integrations.urls')),
    path('reporting/', include('reporting.urls')),
    path('common/', include('common.urls')),
    
    # Test pages
    path('test-theme/', TemplateView.as_view(template_name='admin/test_theme.html'), name='test_theme'),
    path('test-template/', TemplateView.as_view(template_name='admin/test_template.html'), name='test_template'),
    path('test-js/', TemplateView.as_view(template_name='admin/test_js.html'), name='test_js'),
    
    # API test frontend
    path('api-test/', TemplateView.as_view(template_name='api_test_frontend.html'), name='api_test_frontend'),
    
    # Comprehensive API Documentation - One-stop site for all APIs
    path('api-docs-comprehensive/', ComprehensiveAPIDocsView.as_view(), name='api_comprehensive_docs'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 