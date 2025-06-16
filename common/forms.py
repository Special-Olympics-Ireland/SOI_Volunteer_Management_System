"""
Forms for common app including theme management
"""

from django import forms
from django.contrib.auth import get_user_model
from .models import Theme, UserThemePreference, SystemConfig
from django.core.exceptions import ValidationError
from django.utils.html import format_html
import re

User = get_user_model()


class ColorPresetWidget(forms.Select):
    """
    Professional color preset widget with visual swatches
    """
    def __init__(self, presets=None, *args, **kwargs):
        self.presets = presets or {}
        super().__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None, renderer=None):
        # Add CSS class for styling
        if attrs is None:
            attrs = {}
        attrs['class'] = attrs.get('class', '') + ' color-preset-select'
        
        # Render the select with color swatches
        html = super().render(name, value, attrs, renderer)
        
        # Add JavaScript for live preview
        js = format_html('''
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const select = document.querySelector('select[name="{0}"]');
            if (select) {{
                select.addEventListener('change', function() {{
                    const preview = document.querySelector('.color-preview-{0}');
                    if (preview) {{
                        preview.style.backgroundColor = this.value;
                    }}
                }});
            }}
        }});
        </script>
        ''', name)
        
        # Add color preview
        preview = format_html(
            '<div class="color-preview color-preview-{}" style="width: 40px; height: 40px; border: 1px solid #ccc; border-radius: 4px; display: inline-block; margin-left: 10px; background-color: {};"></div>',
            name, value or '#ffffff'
        )
        
        return html + preview + js


class ThemeForm(forms.ModelForm):
    """
    Professional theme management form with preset colors and live preview
    """
    
    # SOI Brand Color Presets
    SOI_COLOR_PRESETS = [
        ('#2E7D32', '🟢 SOI Primary Green'),
        ('#1B5E20', '🌲 SOI Dark Green'), 
        ('#4CAF50', '🍃 SOI Light Green'),
        ('#388E3C', '🌿 SOI Medium Green'),
        ('#66BB6A', '🌱 SOI Soft Green'),
    ]
    
    ACCENT_COLOR_PRESETS = [
        ('#FFD700', '🟡 SOI Gold'),
        ('#FFC107', '🟨 Amber'),
        ('#FF9800', '🟠 Orange'),
        ('#F44336', '🔴 Red'),
        ('#2196F3', '🔵 Blue'),
        ('#9C27B0', '🟣 Purple'),
    ]
    
    NEUTRAL_COLOR_PRESETS = [
        ('#FFFFFF', '⚪ White'),
        ('#F5F5F5', '⬜ Light Gray'),
        ('#E0E0E0', '🔳 Gray'),
        ('#424242', '⬛ Dark Gray'),
        ('#212121', '⚫ Almost Black'),
        ('#000000', '⚫ Black'),
    ]
    
    # Primary color with presets
    primary_color = forms.ChoiceField(
        choices=SOI_COLOR_PRESETS + [('custom', '🎨 Custom Color...')],
        widget=ColorPresetWidget(presets=dict(SOI_COLOR_PRESETS)),
        help_text="Choose from SOI brand colors or select custom"
    )
    
    primary_color_custom = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'custom-color-input',
            'style': 'width: 60px; height: 40px; border: none; border-radius: 4px;'
        }),
        required=False,
        help_text="Custom color (only used if 'Custom Color' is selected above)"
    )
    
    # Secondary color with presets  
    secondary_color = forms.ChoiceField(
        choices=SOI_COLOR_PRESETS + [('custom', '🎨 Custom Color...')],
        widget=ColorPresetWidget(presets=dict(SOI_COLOR_PRESETS)),
        help_text="Supporting brand color"
    )
    
    secondary_color_custom = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'custom-color-input',
            'style': 'width: 60px; height: 40px; border: none; border-radius: 4px;'
        }),
        required=False
    )
    
    # Accent color with presets
    accent_color = forms.ChoiceField(
        choices=ACCENT_COLOR_PRESETS + [('custom', '🎨 Custom Color...')],
        widget=ColorPresetWidget(presets=dict(ACCENT_COLOR_PRESETS)),
        help_text="Highlight and call-to-action color"
    )
    
    accent_color_custom = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'custom-color-input',
            'style': 'width: 60px; height: 40px; border: none; border-radius: 4px;'
        }),
        required=False
    )

    class Meta:
        model = Theme
        fields = [
            'name', 'theme_type', 'is_active', 'is_default', 'is_dark_mode',
            'primary_color', 'primary_color_custom',
            'secondary_color', 'secondary_color_custom', 
            'accent_color', 'accent_color_custom',
            'background_color', 'surface_color', 'text_primary', 'text_secondary',
            'success_color', 'warning_color', 'error_color', 'info_color',
            'description'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SOI 2026 Theme'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'theme_type': forms.Select(attrs={'class': 'form-control'}),
            
            # Simple color inputs for remaining colors
            'background_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'surface_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'text_primary': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'text_secondary': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'success_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'warning_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'error_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
            'info_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'simple-color-input',
                'style': 'width: 60px; height: 40px;'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Handle custom color logic
        for color_field in ['primary_color', 'secondary_color', 'accent_color']:
            color_value = cleaned_data.get(color_field)
            custom_field = f"{color_field}_custom"
            custom_value = cleaned_data.get(custom_field)
            
            if color_value == 'custom':
                if not custom_value:
                    raise ValidationError(f"Custom {color_field.replace('_', ' ')} is required when 'Custom Color' is selected.")
                # Use the custom color value
                cleaned_data[color_field] = custom_value
            
            # Remove the custom field from cleaned_data as it's not a model field
            if custom_field in cleaned_data:
                del cleaned_data[custom_field]
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for custom fields if instance has custom colors
        if self.instance and self.instance.pk:
            for color_field in ['primary_color', 'secondary_color', 'accent_color']:
                color_value = getattr(self.instance, color_field, '')
                preset_values = dict(getattr(self, f"{color_field.upper()}_PRESETS", []))
                
                if color_value and color_value not in preset_values:
                    # This is a custom color
                    self.fields[color_field].initial = 'custom'
                    self.fields[f"{color_field}_custom"].initial = color_value


class UserThemePreferenceForm(forms.ModelForm):
    """
    Simple user theme preference form
    """
    class Meta:
        model = UserThemePreference
        fields = ['admin_theme', 'mobile_theme', 'use_dark_mode', 'use_high_contrast', 'font_size_preference']
        widgets = {
            'admin_theme': forms.Select(attrs={'class': 'form-control'}),
            'mobile_theme': forms.Select(attrs={'class': 'form-control'}),
            'use_dark_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'use_high_contrast': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'font_size_preference': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter theme choices
        self.fields['admin_theme'].queryset = Theme.objects.filter(
            theme_type='ADMIN', is_active=True
        )
        self.fields['mobile_theme'].queryset = Theme.objects.filter(
            theme_type='MOBILE', is_active=True
        )
        
        # Add empty choice for themes
        self.fields['admin_theme'].empty_label = "Use system default"
        self.fields['mobile_theme'].empty_label = "Use system default"


class SystemConfigForm(forms.ModelForm):
    """
    Form for system configuration
    """
    
    class Meta:
        model = SystemConfig
        fields = [
            'key', 'name', 'description', 'config_type', 'value',
            'is_active', 'is_public', 'is_editable'
        ]
        
        widgets = {
            'key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SETTING_NAME'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Human readable name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'config_type': forms.Select(attrs={'class': 'form-control'}),
            'value': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'JSON value'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_editable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ThemeImportForm(forms.Form):
    """
    Form for importing themes from JSON
    """
    theme_data = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 15,
            'placeholder': 'Paste theme JSON data here...'
        }),
        help_text='Paste the exported theme JSON data'
    )
    
    overwrite_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Overwrite existing theme with the same name'
    )


class BulkThemeActionForm(forms.Form):
    """
    Form for bulk theme actions
    """
    ACTION_CHOICES = [
        ('activate', 'Activate'),
        ('deactivate', 'Deactivate'),
        ('delete', 'Delete'),
        ('export', 'Export'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    theme_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='I confirm this action'
    ) 