"""
URL patterns for theme management
"""

from django.urls import path
from . import theme_views

app_name = 'themes'

urlpatterns = [
    # User theme management
    path('selector/', theme_views.theme_selector, name='selector'),
    path('update-preference/', theme_views.update_theme_preference, name='update_preference'),
    path('current-css/', theme_views.get_current_theme_css, name='current_css'),
    path('preview/<int:theme_id>/', theme_views.theme_preview, name='preview'),
    path('css/<int:theme_id>/', theme_views.get_theme_css, name='css'),
    
    # Staff theme management
    path('management/', theme_views.theme_management, name='management'),
    path('activate/<int:theme_id>/', theme_views.activate_theme, name='activate'),
    path('deactivate/<int:theme_id>/', theme_views.deactivate_theme, name='deactivate'),
    path('duplicate/<int:theme_id>/', theme_views.duplicate_theme, name='duplicate'),
    
    # Advanced theme management with ThemeService
    path('analytics/', theme_views.theme_analytics, name='analytics'),
    path('validation/<int:theme_id>/', theme_views.theme_validation, name='validation'),
    path('create-from-color/', theme_views.create_theme_from_color, name='create_from_color'),
    path('export-css/<int:theme_id>/', theme_views.export_theme_css, name='export_css'),
    path('api/palette/<int:theme_id>/', theme_views.theme_color_palette_api, name='palette_api'),
] 