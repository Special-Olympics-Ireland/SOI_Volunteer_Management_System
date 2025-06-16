"""
Django management command to test CORS configuration.
Usage: python manage.py test_cors [--origin ORIGIN] [--report] [--validate-all]
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import json


class Command(BaseCommand):
    help = 'Test CORS configuration for SOI Hub'

    def add_arguments(self, parser):
        parser.add_argument(
            '--origin',
            type=str,
            help='Test a specific origin',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate a comprehensive CORS report',
        )
        parser.add_argument(
            '--validate-all',
            action='store_true',
            help='Validate all configured origins',
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Save report to file',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('SOI Hub CORS Configuration Test')
        )
        self.stdout.write('=' * 50)

        try:
            from common.cors_utils import (
                validate_cors_origin,
                generate_cors_report,
                log_cors_configuration,
                test_cors_scenarios
            )
            from common.cors_middleware import CORSConfigValidator
        except ImportError as e:
            raise CommandError(f'Failed to import CORS utilities: {e}')

        # Validate CORS configuration first
        try:
            CORSConfigValidator.validate_settings()
            self.stdout.write(
                self.style.SUCCESS('✓ CORS configuration validation passed')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ CORS configuration validation failed: {e}')
            )
            return

        # Handle specific origin test
        if options['origin']:
            self._test_origin(options['origin'])
            return

        # Handle comprehensive report
        if options['report']:
            self._generate_report(options.get('output_file'))
            return

        # Handle validate all origins
        if options['validate_all']:
            self._validate_all_origins()
            return

        # Default: show current configuration
        self._show_configuration()

    def _test_origin(self, origin):
        """Test a specific origin."""
        from common.cors_utils import validate_cors_origin

        self.stdout.write(f'\nTesting origin: {origin}')
        self.stdout.write('-' * 30)

        result = validate_cors_origin(origin)

        if result['allowed']:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Origin allowed: {result["reason"]}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Origin rejected: {result["reason"]}')
            )

        self.stdout.write(f'\nConfiguration used:')
        for key, value in result['config'].items():
            self.stdout.write(f'  {key}: {value}')

    def _generate_report(self, output_file=None):
        """Generate comprehensive CORS report."""
        from common.cors_utils import generate_cors_report

        self.stdout.write('\nGenerating comprehensive CORS report...')
        
        report = generate_cors_report()
        
        # Format report for console output
        self._display_report(report)
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2)
                self.stdout.write(
                    self.style.SUCCESS(f'\n✓ Report saved to: {output_file}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to save report: {e}')
                )

    def _validate_all_origins(self):
        """Validate all configured origins."""
        from common.cors_utils import validate_cors_origin

        origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        
        if not origins:
            self.stdout.write(
                self.style.WARNING('No origins configured in CORS_ALLOWED_ORIGINS')
            )
            return

        self.stdout.write(f'\nValidating {len(origins)} configured origins:')
        self.stdout.write('-' * 40)

        for origin in origins:
            result = validate_cors_origin(origin)
            if result['allowed']:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {origin}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ {origin} - {result["reason"]}')
                )

    def _show_configuration(self):
        """Show current CORS configuration."""
        from common.cors_utils import log_cors_configuration

        self.stdout.write('\nCurrent CORS Configuration:')
        self.stdout.write('-' * 30)

        config = log_cors_configuration()
        
        for key, value in config.items():
            if isinstance(value, list):
                self.stdout.write(f'{key}:')
                for item in value:
                    self.stdout.write(f'  - {item}')
            else:
                self.stdout.write(f'{key}: {value}')

        # Show environment-specific recommendations
        self._show_recommendations()

    def _show_recommendations(self):
        """Show environment-specific recommendations."""
        self.stdout.write('\nRecommendations:')
        self.stdout.write('-' * 15)

        if settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    '• Development mode detected - ensure production settings are configured'
                )
            )
            self.stdout.write(
                '• Consider enabling SOI_CORS_ENABLE_LOGGING for debugging'
            )
        else:
            self.stdout.write(
                '• Production mode - verify all origins use HTTPS'
            )
            self.stdout.write(
                '• Ensure SOI_CORS_STRICT_MODE is enabled'
            )

        origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        if 'http://localhost:3000' in origins and not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR(
                    '• SECURITY WARNING: localhost origins found in production'
                )
            )

    def _display_report(self, report):
        """Display formatted report to console."""
        self.stdout.write(f'\nCORS Report - {report["environment"].title()} Environment')
        self.stdout.write(f'Generated: {report["timestamp"]}')
        self.stdout.write('=' * 60)

        # Configuration summary
        self.stdout.write('\nConfiguration Summary:')
        config = report['configuration']
        self.stdout.write(f'  Allowed Origins: {len(config.get("CORS_ALLOWED_ORIGINS", []))}')
        self.stdout.write(f'  Allow Credentials: {config.get("CORS_ALLOW_CREDENTIALS", False)}')
        self.stdout.write(f'  Allowed Methods: {len(config.get("CORS_ALLOWED_METHODS", []))}')
        self.stdout.write(f'  Allowed Headers: {len(config.get("CORS_ALLOWED_HEADERS", []))}')

        # Test results summary
        test_results = report['test_results']
        self.stdout.write('\nTest Results Summary:')
        
        origin_tests = test_results.get('origin_tests', {})
        allowed_origins = sum(1 for result in origin_tests.values() if result['allowed'])
        self.stdout.write(f'  Origin Tests: {allowed_origins}/{len(origin_tests)} passed')

        # Warnings
        warnings = report.get('warnings', [])
        if warnings:
            self.stdout.write('\nWarnings:')
            for warning in warnings:
                self.stdout.write(
                    self.style.ERROR(f'  ⚠ {warning}')
                )

        # Recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            self.stdout.write('\nRecommendations:')
            for rec in recommendations:
                self.stdout.write(f'  • {rec}')

        # Detailed test results
        self.stdout.write('\nDetailed Test Results:')
        self.stdout.write('-' * 25)
        
        for origin, result in origin_tests.items():
            status = '✓' if result['allowed'] else '✗'
            style = self.style.SUCCESS if result['allowed'] else self.style.ERROR
            self.stdout.write(
                style(f'{status} {origin} - {result["reason"]}')
            ) 