"""
Context processors for SOI Hub
Provides global template context including theme data and system configuration.
"""

from django.conf import settings
from .models import Theme, UserThemePreference, SystemConfig


def theme_context(request):
    """
    Add theme information to template context
    """
    context = {
        'current_theme': None,
        'theme_css_vars': {},
        'user_theme_preference': None,
    }
    
    try:
        # Determine theme type based on request
        if request.path.startswith('/admin/'):
            theme_type = 'ADMIN'
        elif request.path.startswith('/mobile-admin/'):
            theme_type = 'MOBILE'
        else:
            theme_type = 'PUBLIC'
        
        # Get user theme preference if authenticated
        if request.user.is_authenticated:
            try:
                user_preference = UserThemePreference.objects.get(user=request.user)
                context['user_theme_preference'] = user_preference
                
                # Get user's preferred theme
                current_theme = user_preference.get_effective_theme(theme_type)
            except UserThemePreference.DoesNotExist:
                # Use system default theme
                current_theme = Theme.get_active_theme(theme_type)
        else:
            # Use system default theme for anonymous users
            current_theme = Theme.get_active_theme(theme_type)
        
        if current_theme:
            context['current_theme'] = current_theme
            context['theme_css_vars'] = current_theme.get_css_variables()
            context['theme_css'] = current_theme.generate_css()
    
    except Exception:
        # Fallback to default values if anything goes wrong
        pass
    
    return context


def system_config_context(request):
    """
    Add system configuration to template context
    """
    context = {
        'system_config': {},
        'site_name': 'SOI Hub',
        'site_tagline': 'Volunteer Management System',
    }
    
    try:
        # Get public system configurations
        public_configs = SystemConfig.objects.filter(
            is_active=True,
            is_public=True
        ).values('key', 'value')
        
        for config in public_configs:
            context['system_config'][config['key']] = config['value']
        
        # Override with specific configs if they exist
        try:
            site_name_config = SystemConfig.objects.get(key='SITE_NAME', is_active=True)
            context['site_name'] = site_name_config.value
        except SystemConfig.DoesNotExist:
            pass
        
        try:
            site_tagline_config = SystemConfig.objects.get(key='SITE_TAGLINE', is_active=True)
            context['site_tagline'] = site_tagline_config.value
        except SystemConfig.DoesNotExist:
            pass
    
    except Exception:
        # Fallback to default values if anything goes wrong
        pass
    
    return context


def user_context(request):
    """
    Add user-specific context information
    """
    context = {
        'user_display_name': '',
        'user_role': '',
        'user_permissions': [],
    }
    
    if request.user.is_authenticated:
        # User display name
        if request.user.first_name and request.user.last_name:
            context['user_display_name'] = f"{request.user.first_name} {request.user.last_name}"
        else:
            context['user_display_name'] = request.user.username
        
        # User role
        if hasattr(request.user, 'user_type'):
            context['user_role'] = request.user.get_user_type_display()
        
        # User permissions (simplified)
        context['user_permissions'] = [
            'can_view_admin' if request.user.is_staff else '',
            'can_manage_users' if request.user.has_perm('accounts.change_user') else '',
            'can_manage_volunteers' if request.user.has_perm('volunteers.change_volunteerprofile') else '',
            'can_manage_events' if request.user.has_perm('events.change_event') else '',
            'can_view_reports' if request.user.has_perm('reporting.view_report') else '',
        ]
        # Remove empty permissions
        context['user_permissions'] = [p for p in context['user_permissions'] if p]
    
    return context 