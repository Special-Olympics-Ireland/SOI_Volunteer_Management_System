"""
Comprehensive System Testing Command
Tests all major components of the SOI Hub system before proceeding with development.
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.cache import cache
import time
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'Comprehensive system testing - validates all components before proceeding'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Run quick tests only (skip performance tests)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for all tests',
        )

    def handle(self, *args, **options):
        self.quick = options['quick']
        self.verbose = options['verbose']
        self.client = Client()
        
        self.stdout.write(self.style.SUCCESS('🚀 SOI Hub Comprehensive System Testing'))
        self.stdout.write('=' * 60)
        
        # Test categories
        test_results = {
            'database': self.test_database_connectivity(),
            'models': self.test_model_functionality(),
            'admin': self.test_admin_interface(),
            'theme': self.test_theme_system(),
            'help': self.test_help_system(),
            'static': self.test_static_files(),
            'cache': self.test_cache_system(),
        }
        
        if not self.quick:
            test_results.update({
                'performance': self.test_performance(),
            })
        
        # Summary
        self.print_summary(test_results)
        
        # Exit with error code if any tests failed
        if not all(test_results.values()):
            sys.exit(1)

    def test_database_connectivity(self):
        """Test database connection and basic operations"""
        self.stdout.write('\n📊 Testing Database Connectivity...')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] != 1:
                    raise Exception("Database query failed")
            
            user_count = User.objects.count()
            self.log_verbose(f"✓ Database connected, {user_count} users found")
            
            self.stdout.write(self.style.SUCCESS('✓ Database tests passed'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database test failed: {str(e)}'))
            return False

    def test_model_functionality(self):
        """Test core model functionality"""
        self.stdout.write('\n🏗️  Testing Model Functionality...')
        try:
            from accounts.models import User
            from events.models import Event, Venue, Role
            from volunteers.models import VolunteerProfile
            from tasks.models import Task
            from common.models import Theme, AdminOverride
            
            models_to_test = [
                (User, 'Users'),
                (Event, 'Events'),
                (Venue, 'Venues'),
                (Role, 'Roles'),
                (VolunteerProfile, 'Volunteer Profiles'),
                (Task, 'Tasks'),
                (Theme, 'Themes'),
                (AdminOverride, 'Admin Overrides'),
            ]
            
            for model, name in models_to_test:
                count = model.objects.count()
                self.log_verbose(f"✓ {name}: {count} records")
            
            if Theme.objects.exists():
                theme = Theme.objects.first()
                css = theme.generate_css()
                if len(css) < 100:
                    raise Exception("Theme CSS generation failed")
                self.log_verbose(f"✓ Theme CSS generation: {len(css)} characters")
            
            self.stdout.write(self.style.SUCCESS('✓ Model tests passed'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Model test failed: {str(e)}'))
            return False

    def test_admin_interface(self):
        """Test admin interface accessibility"""
        self.stdout.write('\n👨‍💼 Testing Admin Interface...')
        try:
            response = self.client.get('/admin/')
            if response.status_code not in [200, 302]:
                raise Exception(f"Admin page returned {response.status_code}")
            
            admin_urls = [
                '/admin/',
                '/admin/accounts/user/',
                '/admin/events/event/',
                '/admin/volunteers/volunteerprofile/',
                '/admin/common/theme/',
            ]
            
            for url in admin_urls:
                response = self.client.get(url)
                if response.status_code not in [200, 302]:
                    self.stdout.write(self.style.WARNING(f"⚠️  {url} returned {response.status_code}"))
                else:
                    self.log_verbose(f"✓ {url} accessible")
            
            self.stdout.write(self.style.SUCCESS('✓ Admin interface tests passed'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Admin interface test failed: {str(e)}'))
            return False

    def test_theme_system(self):
        """Test theme system functionality"""
        self.stdout.write('\n🎨 Testing Theme System...')
        try:
            from common.models import Theme
            
            themes = Theme.objects.all()
            if not themes.exists():
                self.stdout.write(self.style.WARNING('⚠️  No themes found'))
                return False
            
            for theme in themes[:3]:
                css = theme.generate_css()
                if len(css) < 1000:
                    raise Exception(f"Theme {theme.name} CSS too short: {len(css)} chars")
                self.log_verbose(f"✓ Theme '{theme.name}': {len(css)} chars CSS")
            
            response = self.client.get('/static/admin/css/theme-admin.css')
            if response.status_code != 200:
                raise Exception("Theme admin CSS not accessible")
            
            self.stdout.write(self.style.SUCCESS('✓ Theme system tests passed'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Theme system test failed: {str(e)}'))
            return False

    def test_help_system(self):
        """Test help system functionality"""
        self.stdout.write('\n📚 Testing Help System...')
        try:
            help_urls = [
                '/help/',
                '/help/getting-started/',
                '/help/user-management/',
                '/help/volunteer-management/',
                '/help/event-management/',
                '/help/task-management/',
                '/help/reporting/',
                '/help/system-admin/',
                '/help/troubleshooting/',
            ]
            
            working_pages = 0
            for url in help_urls:
                response = self.client.get(url)
                if response.status_code in [200, 302]:
                    working_pages += 1
                    self.log_verbose(f"✓ {url} accessible")
                else:
                    self.log_verbose(f"✗ {url} returned {response.status_code}")
            
            if working_pages >= len(help_urls) * 0.9:
                self.stdout.write(self.style.SUCCESS(f'✓ Help system tests passed ({working_pages}/{len(help_urls)} pages working)'))
                return True
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  Help system partial ({working_pages}/{len(help_urls)} pages working)'))
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Help system test failed: {str(e)}'))
            return False

    def test_static_files(self):
        """Test static file serving"""
        self.stdout.write('\n📁 Testing Static Files...')
        try:
            static_files = [
                '/static/admin/css/theme-admin.css',
                '/static/admin/js/theme-admin.js',
                '/static/admin/css/mobile-responsive.css',
                '/static/admin/css/help-system.css',
            ]
            
            working_files = 0
            for file_url in static_files:
                response = self.client.get(file_url)
                if response.status_code == 200:
                    working_files += 1
                    self.log_verbose(f"✓ {file_url} accessible")
                else:
                    self.log_verbose(f"✗ {file_url} returned {response.status_code}")
            
            if working_files >= len(static_files) * 0.8:
                self.stdout.write(self.style.SUCCESS(f'✓ Static files tests passed ({working_files}/{len(static_files)} files working)'))
                return True
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  Static files partial ({working_files}/{len(static_files)} files working)'))
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Static files test failed: {str(e)}'))
            return False

    def test_cache_system(self):
        """Test cache functionality"""
        self.stdout.write('\n💾 Testing Cache System...')
        try:
            test_key = 'test_cache_key'
            test_value = 'test_cache_value'
            
            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception("Cache set/get failed")
            
            cache.delete(test_key)
            self.log_verbose("✓ Cache set/get/delete working")
            
            self.stdout.write(self.style.SUCCESS('✓ Cache system tests passed'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Cache system test failed: {str(e)}'))
            return False

    def test_performance(self):
        """Test system performance"""
        self.stdout.write('\n⚡ Testing Performance...')
        try:
            start_time = time.time()
            
            User.objects.count()
            response = self.client.get('/admin/')
            
            end_time = time.time()
            total_time = end_time - start_time
            
            if total_time > 5.0:
                self.stdout.write(self.style.WARNING(f'⚠️  Performance test slow: {total_time:.2f}s'))
                return False
            
            self.log_verbose(f"✓ Performance test: {total_time:.2f}s")
            self.stdout.write(self.style.SUCCESS('✓ Performance tests passed'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Performance test failed: {str(e)}'))
            return False

    def log_verbose(self, message):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            self.stdout.write(f"  {message}")

    def print_summary(self, results):
        """Print test summary"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📋 TEST SUMMARY'))
        self.stdout.write('=' * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = '✓ PASS' if result else '✗ FAIL'
            color = self.style.SUCCESS if result else self.style.ERROR
            self.stdout.write(f"{test_name.upper():.<20} {color(status)}")
        
        self.stdout.write('-' * 60)
        
        if passed == total:
            self.stdout.write(self.style.SUCCESS(f'🎉 ALL TESTS PASSED ({passed}/{total})'))
            self.stdout.write(self.style.SUCCESS('✅ System is ready for development!'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  PARTIAL SUCCESS ({passed}/{total})'))
            self.stdout.write(self.style.WARNING('🔧 Please fix failing tests before proceeding'))
        
        self.stdout.write('=' * 60) 