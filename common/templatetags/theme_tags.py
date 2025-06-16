"""
Template tags for theme management
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from ..models import Theme, UserThemePreference

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_css(context):
    """
    Generate CSS for the current theme
    """
    request = context.get('request')
    if not request:
        return ''
    
    try:
        # Determine theme type
        if request.path.startswith('/admin/'):
            theme_type = 'ADMIN'
        elif request.path.startswith('/mobile-admin/'):
            theme_type = 'MOBILE'
        else:
            theme_type = 'PUBLIC'
        
        # Get current theme
        if request.user.is_authenticated:
            try:
                user_preference = UserThemePreference.objects.get(user=request.user)
                current_theme = user_preference.get_effective_theme(theme_type)
            except UserThemePreference.DoesNotExist:
                current_theme = Theme.get_active_theme(theme_type)
        else:
            current_theme = Theme.get_active_theme(theme_type)
        
        if current_theme:
            css = current_theme.generate_css()
            return mark_safe(f'<style type="text/css">\n{css}\n</style>')
    
    except Exception:
        pass
    
    return ''


@register.simple_tag(takes_context=True)
def theme_variables(context):
    """
    Generate CSS custom properties for the current theme
    """
    request = context.get('request')
    if not request:
        return {}
    
    try:
        # Determine theme type
        if request.path.startswith('/admin/'):
            theme_type = 'ADMIN'
        elif request.path.startswith('/mobile-admin/'):
            theme_type = 'MOBILE'
        else:
            theme_type = 'PUBLIC'
        
        # Get current theme
        if request.user.is_authenticated:
            try:
                user_preference = UserThemePreference.objects.get(user=request.user)
                current_theme = user_preference.get_effective_theme(theme_type)
            except UserThemePreference.DoesNotExist:
                current_theme = Theme.get_active_theme(theme_type)
        else:
            current_theme = Theme.get_active_theme(theme_type)
        
        if current_theme:
            return current_theme.get_css_variables()
    
    except Exception:
        pass
    
    return {}


@register.simple_tag
def theme_color(theme, color_name):
    """
    Get a specific color from a theme
    Usage: {% theme_color current_theme 'primary_color' %}
    """
    if not theme:
        return ''
    
    return getattr(theme, color_name, '')


@register.filter
def theme_contrast_color(color):
    """
    Get contrasting text color (black or white) for a given background color
    Usage: {{ theme.primary_color|theme_contrast_color }}
    """
    if not color or not color.startswith('#'):
        return '#000000'
    
    try:
        # Remove # and convert to RGB
        hex_color = color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Calculate luminance
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        # Return black or white based on luminance
        return '#FFFFFF' if luminance < 0.5 else '#000000'
    
    except (ValueError, IndexError):
        return '#000000'


@register.inclusion_tag('admin/theme_selector.html', takes_context=True)
def theme_selector(context):
    """
    Render theme selector widget for authenticated users
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return {'themes': [], 'current_theme': None}
    
    try:
        # Get available themes for admin interface
        admin_themes = Theme.objects.filter(theme_type='ADMIN', is_active=True)
        
        # Get user's current preference
        try:
            user_preference = UserThemePreference.objects.get(user=request.user)
            current_theme = user_preference.admin_theme
        except UserThemePreference.DoesNotExist:
            current_theme = Theme.get_active_theme('ADMIN')
        
        return {
            'themes': admin_themes,
            'current_theme': current_theme,
            'user': request.user
        }
    
    except Exception:
        return {'themes': [], 'current_theme': None}


@register.simple_tag
def theme_status_badge(theme):
    """
    Generate status badge HTML for a theme
    """
    badges = []
    
    if theme.is_active:
        badges.append('<span class="theme-badge theme-active">Active</span>')
    
    if theme.is_default:
        badges.append('<span class="theme-badge theme-default">Default</span>')
    
    if theme.is_dark_mode:
        badges.append('<span class="theme-badge theme-dark">Dark Mode</span>')
    
    if theme.accessibility_compliant:
        badges.append('<span class="theme-badge theme-accessible">Accessible</span>')
    
    return mark_safe(' '.join(badges))


@register.simple_tag
def theme_color_palette(theme):
    """
    Generate color palette HTML for a theme
    """
    if not theme:
        return ''
    
    colors = [
        ('Primary', theme.primary_color),
        ('Secondary', theme.secondary_color),
        ('Accent', theme.accent_color),
        ('Success', theme.success_color),
        ('Warning', theme.warning_color),
        ('Error', theme.error_color),
        ('Info', theme.info_color),
    ]
    
    palette_html = '<div class="theme-color-palette">'
    for name, color in colors:
        palette_html += format_html(
            '<div class="color-swatch" style="background-color: {};" title="{}"></div>',
            color, f'{name}: {color}'
        )
    palette_html += '</div>'
    
    return mark_safe(palette_html) 