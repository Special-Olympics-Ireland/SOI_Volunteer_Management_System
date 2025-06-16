"""
Theme service for SOI Hub
Provides advanced theme management functionality including validation, 
color analysis, accessibility checking, and theme generation.
"""

import colorsys
import re
from typing import Dict, List, Tuple, Optional, Any
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Theme, UserThemePreference

User = get_user_model()


class ThemeService:
    """
    Service class for advanced theme management operations
    """
    
    # WCAG AA contrast ratio requirements
    WCAG_AA_NORMAL = 4.5
    WCAG_AA_LARGE = 3.0
    WCAG_AAA_NORMAL = 7.0
    WCAG_AAA_LARGE = 4.5
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: {hex_color}")
        
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            raise ValueError(f"Invalid hex color: {hex_color}")
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB values to hex color"""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def get_luminance(hex_color: str) -> float:
        """Calculate relative luminance of a color"""
        r, g, b = ThemeService.hex_to_rgb(hex_color)
        
        # Convert to sRGB
        def srgb_to_linear(c):
            c = c / 255.0
            if c <= 0.03928:
                return c / 12.92
            else:
                return pow((c + 0.055) / 1.055, 2.4)
        
        r_linear = srgb_to_linear(r)
        g_linear = srgb_to_linear(g)
        b_linear = srgb_to_linear(b)
        
        # Calculate luminance
        return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear
    
    @staticmethod
    def get_contrast_ratio(color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors"""
        lum1 = ThemeService.get_luminance(color1)
        lum2 = ThemeService.get_luminance(color2)
        
        # Ensure lighter color is in numerator
        if lum1 > lum2:
            return (lum1 + 0.05) / (lum2 + 0.05)
        else:
            return (lum2 + 0.05) / (lum1 + 0.05)
    
    @staticmethod
    def is_dark_color(hex_color: str) -> bool:
        """Determine if a color is considered dark"""
        luminance = ThemeService.get_luminance(hex_color)
        return luminance < 0.5
    
    @staticmethod
    def adjust_color_brightness(hex_color: str, factor: float) -> str:
        """Adjust color brightness by a factor (-1.0 to 1.0)"""
        r, g, b = ThemeService.hex_to_rgb(hex_color)
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        
        # Adjust lightness
        l = max(0, min(1, l + factor))
        
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return ThemeService.rgb_to_hex(int(r*255), int(g*255), int(b*255))
    
    @staticmethod
    def generate_color_palette(base_color: str) -> Dict[str, str]:
        """Generate a harmonious color palette from a base color"""
        r, g, b = ThemeService.hex_to_rgb(base_color)
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        
        # Generate palette
        palette = {
            'primary': base_color,
            'secondary': ThemeService.adjust_color_brightness(base_color, -0.2),
            'accent': ThemeService.rgb_to_hex(
                *[int(c*255) for c in colorsys.hls_to_rgb((h + 0.5) % 1.0, l, s)]
            ),
            'success': '#28A745',
            'warning': '#FFC107',
            'error': '#DC3545',
            'info': '#17A2B8',
        }
        
        # Determine if we need light or dark backgrounds
        if ThemeService.is_dark_color(base_color):
            palette.update({
                'background': '#FFFFFF',
                'surface': '#F8F9FA',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'text_on_primary': '#FFFFFF',
            })
        else:
            palette.update({
                'background': '#121212',
                'surface': '#1E1E1E',
                'text_primary': '#FFFFFF',
                'text_secondary': '#B0B0B0',
                'text_on_primary': '#000000',
            })
        
        return palette
    
    @staticmethod
    def validate_theme_colors(theme_data: Dict[str, Any]) -> List[str]:
        """Validate theme colors for accessibility and consistency"""
        errors = []
        
        # Required color fields
        required_colors = [
            'primary_color', 'secondary_color', 'accent_color',
            'background_color', 'surface_color', 'text_primary',
            'text_secondary', 'text_on_primary', 'success_color',
            'warning_color', 'error_color', 'info_color'
        ]
        
        # Validate hex format
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        for field in required_colors:
            if field in theme_data:
                color = theme_data[field]
                if not hex_pattern.match(color):
                    errors.append(f"{field}: Invalid hex color format '{color}'")
        
        # Check contrast ratios for accessibility
        if all(field in theme_data for field in ['primary_color', 'text_on_primary']):
            contrast = ThemeService.get_contrast_ratio(
                theme_data['primary_color'], 
                theme_data['text_on_primary']
            )
            if contrast < ThemeService.WCAG_AA_NORMAL:
                errors.append(
                    f"Primary color and text on primary have insufficient contrast ratio: {contrast:.2f} "
                    f"(minimum: {ThemeService.WCAG_AA_NORMAL})"
                )
        
        if all(field in theme_data for field in ['background_color', 'text_primary']):
            contrast = ThemeService.get_contrast_ratio(
                theme_data['background_color'], 
                theme_data['text_primary']
            )
            if contrast < ThemeService.WCAG_AA_NORMAL:
                errors.append(
                    f"Background and primary text have insufficient contrast ratio: {contrast:.2f} "
                    f"(minimum: {ThemeService.WCAG_AA_NORMAL})"
                )
        
        if all(field in theme_data for field in ['surface_color', 'text_primary']):
            contrast = ThemeService.get_contrast_ratio(
                theme_data['surface_color'], 
                theme_data['text_primary']
            )
            if contrast < ThemeService.WCAG_AA_NORMAL:
                errors.append(
                    f"Surface and primary text have insufficient contrast ratio: {contrast:.2f} "
                    f"(minimum: {ThemeService.WCAG_AA_NORMAL})"
                )
        
        return errors
    
    @staticmethod
    def analyze_theme_accessibility(theme: Theme) -> Dict[str, Any]:
        """Analyze theme for accessibility compliance"""
        analysis = {
            'is_compliant': True,
            'issues': [],
            'recommendations': [],
            'contrast_ratios': {},
            'color_analysis': {}
        }
        
        # Check contrast ratios
        contrast_checks = [
            ('primary_color', 'text_on_primary', 'Primary button text'),
            ('background_color', 'text_primary', 'Main content text'),
            ('background_color', 'text_secondary', 'Secondary content text'),
            ('surface_color', 'text_primary', 'Card/surface text'),
            ('success_color', '#FFFFFF', 'Success message text'),
            ('warning_color', '#000000', 'Warning message text'),
            ('error_color', '#FFFFFF', 'Error message text'),
            ('info_color', '#FFFFFF', 'Info message text'),
        ]
        
        for bg_field, text_color, description in contrast_checks:
            bg_color = getattr(theme, bg_field, None)
            if bg_color:
                try:
                    contrast = ThemeService.get_contrast_ratio(bg_color, text_color)
                    analysis['contrast_ratios'][description] = {
                        'ratio': contrast,
                        'aa_compliant': contrast >= ThemeService.WCAG_AA_NORMAL,
                        'aaa_compliant': contrast >= ThemeService.WCAG_AAA_NORMAL,
                    }
                    
                    if contrast < ThemeService.WCAG_AA_NORMAL:
                        analysis['is_compliant'] = False
                        analysis['issues'].append(
                            f"{description} has insufficient contrast: {contrast:.2f}"
                        )
                        analysis['recommendations'].append(
                            f"Improve contrast for {description} to at least {ThemeService.WCAG_AA_NORMAL}"
                        )
                except ValueError as e:
                    analysis['issues'].append(f"Invalid color in {description}: {str(e)}")
        
        # Analyze color properties
        colors_to_analyze = [
            ('primary_color', 'Primary'),
            ('secondary_color', 'Secondary'),
            ('background_color', 'Background'),
            ('text_primary', 'Primary Text'),
        ]
        
        for field, name in colors_to_analyze:
            color = getattr(theme, field, None)
            if color:
                try:
                    analysis['color_analysis'][name] = {
                        'hex': color,
                        'rgb': ThemeService.hex_to_rgb(color),
                        'luminance': ThemeService.get_luminance(color),
                        'is_dark': ThemeService.is_dark_color(color),
                    }
                except ValueError as e:
                    analysis['issues'].append(f"Invalid {name} color: {str(e)}")
        
        # Check for sufficient color differentiation
        primary_lum = ThemeService.get_luminance(theme.primary_color)
        secondary_lum = ThemeService.get_luminance(theme.secondary_color)
        
        if abs(primary_lum - secondary_lum) < 0.1:
            analysis['recommendations'].append(
                "Primary and secondary colors are too similar - consider increasing contrast"
            )
        
        return analysis
    
    @staticmethod
    def create_theme_from_palette(
        name: str, 
        theme_type: str, 
        base_color: str, 
        created_by: Optional[User] = None,
        **kwargs
    ) -> Theme:
        """Create a new theme from a base color palette"""
        palette = ThemeService.generate_color_palette(base_color)
        
        # Validate the generated palette
        validation_errors = ThemeService.validate_theme_colors(palette)
        if validation_errors:
            raise ValidationError(f"Generated palette has issues: {'; '.join(validation_errors)}")
        
        # Create theme with generated colors
        theme_data = {
            'name': name,
            'theme_type': theme_type,
            'primary_color': palette['primary'],
            'secondary_color': palette['secondary'],
            'accent_color': palette['accent'],
            'background_color': palette['background'],
            'surface_color': palette['surface'],
            'text_primary': palette['text_primary'],
            'text_secondary': palette['text_secondary'],
            'text_on_primary': palette['text_on_primary'],
            'success_color': palette['success'],
            'warning_color': palette['warning'],
            'error_color': palette['error'],
            'info_color': palette['info'],
            'created_by': created_by,
            'accessibility_compliant': True,
            'is_dark_mode': ThemeService.is_dark_color(base_color),
            **kwargs
        }
        
        return Theme.objects.create(**theme_data)
    
    @staticmethod
    def get_user_effective_theme(user: User, theme_type: str = 'ADMIN') -> Theme:
        """Get the effective theme for a user"""
        try:
            preference = UserThemePreference.objects.get(user=user)
            return preference.get_effective_theme(theme_type)
        except UserThemePreference.DoesNotExist:
            return Theme.get_active_theme(theme_type)
    
    @staticmethod
    def apply_theme_to_user(user: User, theme: Theme) -> UserThemePreference:
        """Apply a theme to a user's preferences"""
        preference, created = UserThemePreference.objects.get_or_create(user=user)
        
        if theme.theme_type == 'ADMIN':
            preference.admin_theme = theme
        elif theme.theme_type == 'MOBILE':
            preference.mobile_theme = theme
        
        preference.save()
        return preference
    
    @staticmethod
    def get_theme_statistics() -> Dict[str, Any]:
        """Get comprehensive theme usage statistics"""
        stats = {
            'total_themes': Theme.objects.count(),
            'active_themes': Theme.objects.filter(is_active=True).count(),
            'themes_by_type': {},
            'accessibility_stats': {
                'compliant_themes': Theme.objects.filter(accessibility_compliant=True).count(),
                'non_compliant_themes': Theme.objects.filter(accessibility_compliant=False).count(),
            },
            'user_preferences': {
                'total_users_with_preferences': UserThemePreference.objects.count(),
                'dark_mode_users': UserThemePreference.objects.filter(use_dark_mode=True).count(),
                'high_contrast_users': UserThemePreference.objects.filter(use_high_contrast=True).count(),
            },
            'theme_usage': {}
        }
        
        # Themes by type
        for theme_type, display_name in Theme.THEME_TYPES:
            stats['themes_by_type'][theme_type] = {
                'total': Theme.objects.filter(theme_type=theme_type).count(),
                'active': Theme.objects.filter(theme_type=theme_type, is_active=True).count(),
                'dark_mode': Theme.objects.filter(theme_type=theme_type, is_dark_mode=True).count(),
            }
        
        # Theme usage statistics
        admin_theme_usage = UserThemePreference.objects.exclude(admin_theme=None).values_list('admin_theme__name', flat=True)
        mobile_theme_usage = UserThemePreference.objects.exclude(mobile_theme=None).values_list('mobile_theme__name', flat=True)
        
        from collections import Counter
        stats['theme_usage'] = {
            'admin_themes': dict(Counter(admin_theme_usage)),
            'mobile_themes': dict(Counter(mobile_theme_usage)),
        }
        
        return stats
    
    @staticmethod
    def export_theme_css(theme: Theme, include_variables_only: bool = False) -> str:
        """Export theme as CSS with optional variables-only mode"""
        if include_variables_only:
            css_vars = theme.get_css_variables()
            css = ":root {\n"
            for var, value in css_vars.items():
                css += f"  {var}: {value};\n"
            css += "}\n"
            return css
        else:
            return theme.generate_css()
    
    @staticmethod
    def import_theme_from_css(css_content: str, theme_name: str, theme_type: str = 'ADMIN') -> Dict[str, str]:
        """Extract theme colors from CSS content"""
        colors = {}
        
        # Extract CSS custom properties
        var_pattern = re.compile(r'--soi-([^:]+):\s*([^;]+);')
        matches = var_pattern.findall(css_content)
        
        # Map CSS variables to theme fields
        var_mapping = {
            'primary': 'primary_color',
            'secondary': 'secondary_color',
            'accent': 'accent_color',
            'background': 'background_color',
            'surface': 'surface_color',
            'text-primary': 'text_primary',
            'text-secondary': 'text_secondary',
            'text-on-primary': 'text_on_primary',
            'success': 'success_color',
            'warning': 'warning_color',
            'error': 'error_color',
            'info': 'info_color',
        }
        
        for var_name, value in matches:
            if var_name in var_mapping:
                # Clean up the value (remove whitespace, quotes)
                clean_value = value.strip().strip('"\'')
                if re.match(r'^#[0-9A-Fa-f]{6}$', clean_value):
                    colors[var_mapping[var_name]] = clean_value
        
        return colors
    
    @staticmethod
    def suggest_theme_improvements(theme: Theme) -> List[str]:
        """Suggest improvements for a theme"""
        suggestions = []
        
        # Analyze accessibility
        accessibility = ThemeService.analyze_theme_accessibility(theme)
        suggestions.extend(accessibility['recommendations'])
        
        # Check color harmony
        try:
            primary_rgb = ThemeService.hex_to_rgb(theme.primary_color)
            secondary_rgb = ThemeService.hex_to_rgb(theme.secondary_color)
            
            # Check if colors are too similar
            color_distance = sum(abs(a - b) for a, b in zip(primary_rgb, secondary_rgb))
            if color_distance < 100:
                suggestions.append("Primary and secondary colors are too similar - consider more contrast")
            
            # Check if accent color provides enough contrast
            accent_contrast = ThemeService.get_contrast_ratio(theme.accent_color, theme.background_color)
            if accent_contrast < 3.0:
                suggestions.append("Accent color needs more contrast against background")
                
        except ValueError:
            suggestions.append("Some colors have invalid hex format")
        
        # Check typography
        if theme.font_size_base:
            try:
                size_value = int(theme.font_size_base.replace('px', '').replace('rem', '').replace('em', ''))
                if size_value < 12:
                    suggestions.append("Base font size is too small for accessibility (minimum 12px recommended)")
                elif size_value > 20:
                    suggestions.append("Base font size might be too large for most users")
            except (ValueError, AttributeError):
                suggestions.append("Font size format should be specified with units (px, rem, em)")
        
        return suggestions 