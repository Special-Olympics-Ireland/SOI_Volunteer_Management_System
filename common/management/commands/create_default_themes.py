"""
Management command to create default themes for SOI Hub
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from common.models import Theme

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default themes for SOI Hub'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of themes even if they exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        # Get or create admin user for theme creation
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
        except User.DoesNotExist:
            admin_user = None
        
        themes_created = 0
        themes_updated = 0
        
        # Default themes configuration
        default_themes = [
            {
                'name': 'SOI Default Admin',
                'theme_type': 'ADMIN',
                'description': 'Default SOI Hub admin interface theme with green branding',
                'is_active': True,
                'is_default': True,
                'accessibility_compliant': True,
                'primary_color': '#2E7D32',
                'secondary_color': '#1B5E20',
                'accent_color': '#FFD700',
                'background_color': '#FFFFFF',
                'surface_color': '#F8F9FA',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'text_on_primary': '#FFFFFF',
                'success_color': '#28A745',
                'warning_color': '#FFC107',
                'error_color': '#DC3545',
                'info_color': '#17A2B8',
            },
            {
                'name': 'SOI Dark Mode Admin',
                'theme_type': 'ADMIN',
                'description': 'Dark mode theme for SOI Hub admin interface',
                'is_active': False,
                'is_default': False,
                'is_dark_mode': True,
                'accessibility_compliant': True,
                'primary_color': '#2E7D32',
                'secondary_color': '#1B5E20',
                'accent_color': '#FFD700',
                'background_color': '#121212',
                'surface_color': '#1E1E1E',
                'text_primary': '#FFFFFF',
                'text_secondary': '#B0B0B0',
                'text_on_primary': '#FFFFFF',
                'success_color': '#4CAF50',
                'warning_color': '#FF9800',
                'error_color': '#F44336',
                'info_color': '#2196F3',
            },
            {
                'name': 'SOI High Contrast Admin',
                'theme_type': 'ADMIN',
                'description': 'High contrast theme for accessibility compliance',
                'is_active': False,
                'is_default': False,
                'accessibility_compliant': True,
                'primary_color': '#000000',
                'secondary_color': '#333333',
                'accent_color': '#FFFF00',
                'background_color': '#FFFFFF',
                'surface_color': '#F0F0F0',
                'text_primary': '#000000',
                'text_secondary': '#333333',
                'text_on_primary': '#FFFFFF',
                'success_color': '#008000',
                'warning_color': '#FF8000',
                'error_color': '#FF0000',
                'info_color': '#0000FF',
            },
            {
                'name': 'SOI Default Mobile',
                'theme_type': 'MOBILE',
                'description': 'Default SOI Hub mobile interface theme',
                'is_active': True,
                'is_default': True,
                'accessibility_compliant': True,
                'primary_color': '#2E7D32',
                'secondary_color': '#1B5E20',
                'accent_color': '#FFD700',
                'background_color': '#FFFFFF',
                'surface_color': '#F8F9FA',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'text_on_primary': '#FFFFFF',
                'success_color': '#28A745',
                'warning_color': '#FFC107',
                'error_color': '#DC3545',
                'info_color': '#17A2B8',
                'font_size_base': '16px',  # Larger for mobile
            },
            {
                'name': 'SOI Default Public',
                'theme_type': 'PUBLIC',
                'description': 'Default SOI Hub public website theme',
                'is_active': True,
                'is_default': True,
                'accessibility_compliant': True,
                'primary_color': '#2E7D32',
                'secondary_color': '#1B5E20',
                'accent_color': '#FFD700',
                'background_color': '#FFFFFF',
                'surface_color': '#F8F9FA',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'text_on_primary': '#FFFFFF',
                'success_color': '#28A745',
                'warning_color': '#FFC107',
                'error_color': '#DC3545',
                'info_color': '#17A2B8',
            },
            {
                'name': 'SOI Email Template',
                'theme_type': 'EMAIL',
                'description': 'Default SOI Hub email template theme',
                'is_active': True,
                'is_default': True,
                'accessibility_compliant': True,
                'primary_color': '#2E7D32',
                'secondary_color': '#1B5E20',
                'accent_color': '#FFD700',
                'background_color': '#FFFFFF',
                'surface_color': '#F8F9FA',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'text_on_primary': '#FFFFFF',
                'success_color': '#28A745',
                'warning_color': '#FFC107',
                'error_color': '#DC3545',
                'info_color': '#17A2B8',
                'font_family_primary': 'Arial, sans-serif',  # Better email compatibility
            },
        ]
        
        for theme_data in default_themes:
            theme_name = theme_data['name']
            theme_type = theme_data['theme_type']
            
            try:
                # Check if theme exists
                theme, created = Theme.objects.get_or_create(
                    name=theme_name,
                    defaults={
                        **theme_data,
                        'created_by': admin_user
                    }
                )
                
                if created:
                    themes_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Created theme: {theme_name}')
                    )
                elif force:
                    # Update existing theme
                    for key, value in theme_data.items():
                        if key != 'name':  # Don't update the name
                            setattr(theme, key, value)
                    theme.save()
                    themes_updated += 1
                    self.stdout.write(
                        self.style.WARNING(f'🔄 Updated theme: {theme_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Theme already exists: {theme_name}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error creating theme {theme_name}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'📊 SUMMARY:')
        self.stdout.write(f'   • Themes created: {themes_created}')
        self.stdout.write(f'   • Themes updated: {themes_updated}')
        self.stdout.write(f'   • Total themes in system: {Theme.objects.count()}')
        
        # Show active themes by type
        self.stdout.write('\n🎨 ACTIVE THEMES BY TYPE:')
        for theme_type, display_name in Theme.THEME_TYPES:
            active_theme = Theme.objects.filter(
                theme_type=theme_type, 
                is_active=True
            ).first()
            if active_theme:
                self.stdout.write(f'   • {display_name}: {active_theme.name}')
            else:
                self.stdout.write(f'   • {display_name}: No active theme')
        
        self.stdout.write('\n✅ Default themes setup complete!')
        self.stdout.write('💡 You can now manage themes in the admin interface at /admin/common/theme/') 