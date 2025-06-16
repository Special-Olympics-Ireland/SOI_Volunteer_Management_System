"""
Theme management views for SOI Hub
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
import json

from .models import Theme, UserThemePreference
from .forms import ThemeForm, UserThemePreferenceForm
from .theme_service import ThemeService


@login_required
def theme_selector(request):
    """
    Theme selector page for users to choose their preferred themes
    """
    # Get or create user theme preference
    user_preference, created = UserThemePreference.objects.get_or_create(
        user=request.user
    )
    
    # Get available themes by type
    admin_themes = Theme.objects.filter(theme_type='ADMIN', is_active=True)
    mobile_themes = Theme.objects.filter(theme_type='MOBILE', is_active=True)
    
    context = {
        'user_preference': user_preference,
        'admin_themes': admin_themes,
        'mobile_themes': mobile_themes,
        'current_admin_theme': user_preference.get_effective_theme('ADMIN'),
        'current_mobile_theme': user_preference.get_effective_theme('MOBILE'),
    }
    
    return render(request, 'admin/theme_selector.html', context)


@login_required
@require_http_methods(["POST"])
def update_theme_preference(request):
    """
    AJAX endpoint to update user theme preferences
    """
    try:
        data = json.loads(request.body)
        
        # Get or create user preference
        user_preference, created = UserThemePreference.objects.get_or_create(
            user=request.user
        )
        
        # Update preferences based on provided data
        if 'admin_theme_id' in data:
            if data['admin_theme_id']:
                admin_theme = get_object_or_404(Theme, id=data['admin_theme_id'], theme_type='ADMIN')
                user_preference.admin_theme = admin_theme
            else:
                user_preference.admin_theme = None
        
        if 'mobile_theme_id' in data:
            if data['mobile_theme_id']:
                mobile_theme = get_object_or_404(Theme, id=data['mobile_theme_id'], theme_type='MOBILE')
                user_preference.mobile_theme = mobile_theme
            else:
                user_preference.mobile_theme = None
        
        if 'use_dark_mode' in data:
            user_preference.use_dark_mode = bool(data['use_dark_mode'])
        
        if 'use_high_contrast' in data:
            user_preference.use_high_contrast = bool(data['use_high_contrast'])
        
        if 'font_size_preference' in data:
            if data['font_size_preference'] in ['SMALL', 'NORMAL', 'LARGE', 'EXTRA_LARGE']:
                user_preference.font_size_preference = data['font_size_preference']
        
        user_preference.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Theme preferences updated successfully',
            'current_admin_theme': user_preference.get_effective_theme('ADMIN').name if user_preference.get_effective_theme('ADMIN') else 'System Default',
            'current_mobile_theme': user_preference.get_effective_theme('MOBILE').name if user_preference.get_effective_theme('MOBILE') else 'System Default',
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def get_theme_css(request, theme_id):
    """
    Get CSS for a specific theme
    """
    theme = get_object_or_404(Theme, id=theme_id)
    css = theme.generate_css()
    
    return HttpResponse(css, content_type='text/css')


@login_required
def get_current_theme_css(request):
    """
    Get CSS for the user's current theme based on request path
    """
    # Determine theme type based on request path
    if request.path.startswith('/admin/'):
        theme_type = 'ADMIN'
    elif request.path.startswith('/mobile-admin/'):
        theme_type = 'MOBILE'
    else:
        theme_type = 'PUBLIC'
    
    # Get user's effective theme
    try:
        user_preference = UserThemePreference.objects.get(user=request.user)
        current_theme = user_preference.get_effective_theme(theme_type)
    except UserThemePreference.DoesNotExist:
        current_theme = Theme.get_active_theme(theme_type)
    
    if current_theme:
        css = current_theme.generate_css()
        return HttpResponse(css, content_type='text/css')
    else:
        return HttpResponse('/* No theme found */', content_type='text/css')


@staff_member_required
def theme_management(request):
    """
    Theme management dashboard for staff
    """
    # Get themes with filtering
    themes = Theme.objects.all()
    
    # Apply filters
    theme_type = request.GET.get('type')
    if theme_type:
        themes = themes.filter(theme_type=theme_type)
    
    is_active = request.GET.get('active')
    if is_active:
        themes = themes.filter(is_active=is_active.lower() == 'true')
    
    search = request.GET.get('search')
    if search:
        themes = themes.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(themes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_themes': Theme.objects.count(),
        'active_themes': Theme.objects.filter(is_active=True).count(),
        'admin_themes': Theme.objects.filter(theme_type='ADMIN').count(),
        'mobile_themes': Theme.objects.filter(theme_type='MOBILE').count(),
        'public_themes': Theme.objects.filter(theme_type='PUBLIC').count(),
        'email_themes': Theme.objects.filter(theme_type='EMAIL').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'theme_types': Theme.THEME_TYPES,
        'current_filters': {
            'type': theme_type,
            'active': is_active,
            'search': search,
        }
    }
    
    return render(request, 'admin/theme_management.html', context)


@staff_member_required
@require_http_methods(["POST"])
def activate_theme(request, theme_id):
    """
    Activate a specific theme
    """
    theme = get_object_or_404(Theme, id=theme_id)
    
    # Deactivate other themes of the same type
    Theme.objects.filter(theme_type=theme.theme_type, is_active=True).update(is_active=False)
    
    # Activate this theme
    theme.is_active = True
    theme.save()
    
    messages.success(request, f'Theme "{theme.name}" has been activated.')
    return redirect('admin:common_theme_changelist')


@staff_member_required
@require_http_methods(["POST"])
def deactivate_theme(request, theme_id):
    """
    Deactivate a specific theme
    """
    theme = get_object_or_404(Theme, id=theme_id)
    theme.is_active = False
    theme.save()
    
    messages.success(request, f'Theme "{theme.name}" has been deactivated.')
    return redirect('admin:common_theme_changelist')


@staff_member_required
def duplicate_theme(request, theme_id):
    """
    Duplicate an existing theme
    """
    original_theme = get_object_or_404(Theme, id=theme_id)
    
    # Create a copy
    new_theme = Theme.objects.create(
        name=f"{original_theme.name} (Copy)",
        theme_type=original_theme.theme_type,
        description=f"Copy of {original_theme.description}",
        primary_color=original_theme.primary_color,
        secondary_color=original_theme.secondary_color,
        accent_color=original_theme.accent_color,
        background_color=original_theme.background_color,
        surface_color=original_theme.surface_color,
        text_primary=original_theme.text_primary,
        text_secondary=original_theme.text_secondary,
        text_on_primary=original_theme.text_on_primary,
        success_color=original_theme.success_color,
        warning_color=original_theme.warning_color,
        error_color=original_theme.error_color,
        info_color=original_theme.info_color,
        font_family_primary=original_theme.font_family_primary,
        font_family_secondary=original_theme.font_family_secondary,
        font_size_base=original_theme.font_size_base,
        border_radius=original_theme.border_radius,
        box_shadow=original_theme.box_shadow,
        logo_url=original_theme.logo_url,
        favicon_url=original_theme.favicon_url,
        custom_css=original_theme.custom_css,
        is_dark_mode=original_theme.is_dark_mode,
        accessibility_compliant=original_theme.accessibility_compliant,
        created_by=request.user,
    )
    
    messages.success(request, f'Theme "{new_theme.name}" has been created as a copy.')
    return redirect('admin:common_theme_change', new_theme.id)


@login_required
def theme_preview(request, theme_id):
    """
    Preview a theme in a popup window
    """
    theme = get_object_or_404(Theme, id=theme_id)
    
    context = {
        'theme': theme,
        'css': theme.generate_css(),
    }
    
    return render(request, 'admin/theme_preview.html', context)


@staff_member_required
def theme_analytics(request):
    """
    Theme analytics dashboard using ThemeService
    """
    # Get comprehensive theme statistics
    stats = ThemeService.get_theme_statistics()
    
    # Get accessibility analysis for all themes
    themes_analysis = []
    for theme in Theme.objects.all():
        analysis = ThemeService.analyze_theme_accessibility(theme)
        themes_analysis.append({
            'theme': theme,
            'analysis': analysis
        })
    
    context = {
        'stats': stats,
        'themes_analysis': themes_analysis,
    }
    
    return render(request, 'admin/theme_analytics.html', context)


@staff_member_required
def theme_validation(request, theme_id):
    """
    Validate a theme using ThemeService
    """
    theme = get_object_or_404(Theme, id=theme_id)
    
    # Analyze theme accessibility
    accessibility_analysis = ThemeService.analyze_theme_accessibility(theme)
    
    # Get improvement suggestions
    suggestions = ThemeService.suggest_theme_improvements(theme)
    
    # Validate theme colors
    theme_data = {
        'primary_color': theme.primary_color,
        'secondary_color': theme.secondary_color,
        'accent_color': theme.accent_color,
        'background_color': theme.background_color,
        'surface_color': theme.surface_color,
        'text_primary': theme.text_primary,
        'text_secondary': theme.text_secondary,
        'text_on_primary': theme.text_on_primary,
        'success_color': theme.success_color,
        'warning_color': theme.warning_color,
        'error_color': theme.error_color,
        'info_color': theme.info_color,
    }
    
    validation_errors = ThemeService.validate_theme_colors(theme_data)
    
    if request.method == 'POST':
        # Update theme accessibility compliance based on analysis
        theme.accessibility_compliant = accessibility_analysis['is_compliant']
        theme.save()
        
        messages.success(request, f'Theme "{theme.name}" validation completed and compliance status updated.')
        return redirect('admin:common_theme_change', theme.id)
    
    context = {
        'theme': theme,
        'accessibility_analysis': accessibility_analysis,
        'suggestions': suggestions,
        'validation_errors': validation_errors,
    }
    
    return render(request, 'admin/theme_validation.html', context)


@staff_member_required
@require_http_methods(["POST"])
def create_theme_from_color(request):
    """
    Create a new theme from a base color using ThemeService
    """
    try:
        data = json.loads(request.body)
        
        base_color = data.get('base_color')
        theme_name = data.get('name')
        theme_type = data.get('theme_type', 'ADMIN')
        
        if not base_color or not theme_name:
            return JsonResponse({
                'success': False,
                'error': 'Base color and theme name are required'
            }, status=400)
        
        # Create theme using ThemeService
        new_theme = ThemeService.create_theme_from_palette(
            name=theme_name,
            theme_type=theme_type,
            base_color=base_color,
            created_by=request.user,
            description=f"Auto-generated theme from {base_color}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Theme "{new_theme.name}" created successfully',
            'theme_id': new_theme.id,
            'redirect_url': f'/admin/common/theme/{new_theme.id}/change/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@staff_member_required
def export_theme_css(request, theme_id):
    """
    Export theme as CSS file using ThemeService
    """
    theme = get_object_or_404(Theme, id=theme_id)
    
    variables_only = request.GET.get('variables_only', 'false').lower() == 'true'
    css_content = ThemeService.export_theme_css(theme, include_variables_only=variables_only)
    
    response = HttpResponse(css_content, content_type='text/css')
    filename = f"{theme.name.lower().replace(' ', '_')}_{'variables' if variables_only else 'complete'}.css"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@staff_member_required
def theme_color_palette_api(request, theme_id):
    """
    API endpoint to get theme color palette information
    """
    theme = get_object_or_404(Theme, id=theme_id)
    
    # Generate color palette information
    palette = {
        'primary': theme.primary_color,
        'secondary': theme.secondary_color,
        'accent': theme.accent_color,
        'background': theme.background_color,
        'surface': theme.surface_color,
        'text_primary': theme.text_primary,
        'text_secondary': theme.text_secondary,
        'text_on_primary': theme.text_on_primary,
        'success': theme.success_color,
        'warning': theme.warning_color,
        'error': theme.error_color,
        'info': theme.info_color,
    }
    
    # Add color analysis
    color_analysis = {}
    for name, color in palette.items():
        if color:
            try:
                color_analysis[name] = {
                    'hex': color,
                    'rgb': ThemeService.hex_to_rgb(color),
                    'luminance': ThemeService.get_luminance(color),
                    'is_dark': ThemeService.is_dark_color(color),
                }
            except ValueError:
                color_analysis[name] = {'error': 'Invalid color format'}
    
    return JsonResponse({
        'theme_id': theme.id,
        'theme_name': theme.name,
        'palette': palette,
        'color_analysis': color_analysis,
    }) 