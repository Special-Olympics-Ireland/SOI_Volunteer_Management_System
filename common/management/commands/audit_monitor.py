"""
Management command for comprehensive audit monitoring and reporting.

This command provides functionality for:
- Monitoring critical operations and security events
- Generating audit summaries and security reports
- Managing audit log retention and cleanup
- Sending security alerts for suspicious activities
"""

import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q
from django.contrib.auth import get_user_model

from common.models import AuditLog
from common.audit_service import AdminAuditService

User = get_user_model()


class Command(BaseCommand):
    help = 'Monitor audit logs and generate security reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to analyze (default: 24)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days for summary reports (default: 7)'
        )
        
        parser.add_argument(
            '--security-alerts',
            action='store_true',
            help='Generate security alerts for suspicious activities'
        )
        
        parser.add_argument(
            '--summary-report',
            action='store_true',
            help='Generate audit summary report'
        )
        
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old audit logs (older than retention period)'
        )
        
        parser.add_argument(
            '--retention-days',
            type=int,
            default=365,
            help='Audit log retention period in days (default: 365)'
        )
        
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email notifications for alerts and reports'
        )
        
        parser.add_argument(
            '--email-recipients',
            nargs='+',
            help='Email recipients for notifications'
        )
        
        parser.add_argument(
            '--export-format',
            choices=['json', 'csv'],
            default='json',
            help='Export format for reports (default: json)'
        )
        
        parser.add_argument(
            '--output-file',
            help='Output file for reports'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        try:
            if options['security_alerts']:
                self._generate_security_alerts(options)
            
            if options['summary_report']:
                self._generate_summary_report(options)
            
            if options['cleanup']:
                self._cleanup_old_logs(options)
            
            # If no specific action is specified, run security monitoring
            if not any([options['security_alerts'], options['summary_report'], options['cleanup']]):
                self._run_security_monitoring(options)
                
        except Exception as e:
            raise CommandError(f'Audit monitoring failed: {str(e)}')
    
    def _run_security_monitoring(self, options):
        """Run comprehensive security monitoring."""
        self._log_info("Starting comprehensive security monitoring...")
        
        # Generate security alerts
        self._generate_security_alerts(options)
        
        # Generate summary report
        self._generate_summary_report(options)
        
        self._log_success("Security monitoring completed successfully.")
    
    def _generate_security_alerts(self, options):
        """Generate security alerts for suspicious activities."""
        hours = options['hours']
        self._log_info(f"Generating security alerts for the last {hours} hours...")
        
        # Get security alerts
        alerts = AdminAuditService.get_security_alerts(hours=hours)
        
        if not alerts:
            self._log_info("No security alerts found.")
            return
        
        # Categorize alerts by severity
        high_severity = [a for a in alerts if a['severity'] == 'HIGH']
        medium_severity = [a for a in alerts if a['severity'] == 'MEDIUM']
        low_severity = [a for a in alerts if a['severity'] == 'LOW']
        
        self._log_warning(f"Security alerts found: {len(high_severity)} HIGH, {len(medium_severity)} MEDIUM, {len(low_severity)} LOW")
        
        # Display high severity alerts
        if high_severity:
            self._log_error("HIGH SEVERITY ALERTS:")
            for alert in high_severity[:10]:  # Show top 10
                self._log_error(f"  - {alert['timestamp']}: {alert['user']} - {alert['description']} (IP: {alert['ip_address']})")
        
        # Generate detailed report
        report = {
            'timestamp': timezone.now().isoformat(),
            'period_hours': hours,
            'total_alerts': len(alerts),
            'high_severity_count': len(high_severity),
            'medium_severity_count': len(medium_severity),
            'low_severity_count': len(low_severity),
            'high_severity_alerts': high_severity[:20],  # Top 20 high severity
            'summary': {
                'unique_users': len(set(a['user'] for a in alerts)),
                'unique_ips': len(set(a['ip_address'] for a in alerts if a['ip_address'])),
                'failed_operations': len([a for a in alerts if 'failed' in a['description'].lower()]),
                'admin_overrides': len([a for a in alerts if 'override' in a['action'].lower()])
            }
        }
        
        # Save or output report
        if options['output_file']:
            self._save_report(report, options['output_file'], options['export_format'])
        
        # Send email alerts if requested
        if options['send_email'] and high_severity:
            self._send_security_alert_email(report, options)
        
        self._log_success(f"Security alerts analysis completed. {len(alerts)} total alerts found.")
    
    def _generate_summary_report(self, options):
        """Generate comprehensive audit summary report."""
        days = options['days']
        self._log_info(f"Generating audit summary report for the last {days} days...")
        
        # Get audit summary
        summary = AdminAuditService.get_audit_summary(days=days)
        
        # Enhanced analysis
        start_date = timezone.now() - timedelta(days=days)
        audit_logs = AuditLog.objects.filter(timestamp__gte=start_date)
        
        # Additional statistics
        enhanced_summary = {
            **summary,
            'analysis': {
                'most_active_hours': self._get_most_active_hours(audit_logs),
                'top_ip_addresses': self._get_top_ip_addresses(audit_logs),
                'failed_operations_by_type': self._get_failed_operations_by_type(audit_logs),
                'bulk_operations_summary': self._get_bulk_operations_summary(audit_logs),
                'admin_override_summary': self._get_admin_override_summary(audit_logs),
                'performance_metrics': self._get_performance_metrics(audit_logs)
            },
            'recommendations': self._generate_recommendations(audit_logs)
        }
        
        # Display summary
        self._display_summary_report(enhanced_summary)
        
        # Save or output report
        if options['output_file']:
            self._save_report(enhanced_summary, options['output_file'], options['export_format'])
        
        # Send email report if requested
        if options['send_email']:
            self._send_summary_report_email(enhanced_summary, options)
        
        self._log_success("Audit summary report generated successfully.")
    
    def _cleanup_old_logs(self, options):
        """Clean up old audit logs based on retention policy."""
        retention_days = options['retention_days']
        self._log_info(f"Cleaning up audit logs older than {retention_days} days...")
        
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        old_logs = AuditLog.objects.filter(timestamp__lt=cutoff_date)
        
        count = old_logs.count()
        if count == 0:
            self._log_info("No old audit logs found for cleanup.")
            return
        
        # Archive critical logs before deletion (optional)
        critical_logs = old_logs.filter(metadata__critical_operation=True)
        if critical_logs.exists():
            self._log_warning(f"Found {critical_logs.count()} critical logs that will be deleted. Consider archiving them first.")
        
        # Perform cleanup
        deleted_count, _ = old_logs.delete()
        
        self._log_success(f"Cleaned up {deleted_count} old audit logs.")
        
        # Log the cleanup operation
        AdminAuditService.log_system_management_operation(
            operation='audit_log_cleanup',
            user=None,  # System operation
            details={
                'retention_days': retention_days,
                'cutoff_date': cutoff_date.isoformat(),
                'deleted_count': deleted_count,
                'cleanup_method': 'management_command'
            }
        )
    
    def _get_most_active_hours(self, audit_logs):
        """Get most active hours of the day."""
        from django.db.models import Extract
        
        hourly_activity = audit_logs.extra(
            select={'hour': "EXTRACT(hour FROM timestamp)"}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return list(hourly_activity)
    
    def _get_top_ip_addresses(self, audit_logs):
        """Get top IP addresses by activity."""
        return list(
            audit_logs.exclude(ip_address__isnull=True)
            .exclude(ip_address='')
            .values('ip_address')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
    
    def _get_failed_operations_by_type(self, audit_logs):
        """Get failed operations grouped by type."""
        return list(
            audit_logs.filter(response_status__gte=400)
            .values('action_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
    
    def _get_bulk_operations_summary(self, audit_logs):
        """Get summary of bulk operations."""
        bulk_ops = audit_logs.filter(metadata__bulk_operation=True)
        return {
            'total_bulk_operations': bulk_ops.count(),
            'by_type': list(
                bulk_ops.values('action_type')
                .annotate(count=Count('id'))
                .order_by('-count')
            )
        }
    
    def _get_admin_override_summary(self, audit_logs):
        """Get summary of admin overrides."""
        overrides = audit_logs.filter(
            Q(action_type__icontains='override') | 
            Q(metadata__admin_override=True)
        )
        return {
            'total_overrides': overrides.count(),
            'by_user': list(
                overrides.exclude(user__isnull=True)
                .values('user__username')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
        }
    
    def _get_performance_metrics(self, audit_logs):
        """Get performance metrics from audit logs."""
        logs_with_duration = audit_logs.exclude(duration_ms__isnull=True)
        
        if not logs_with_duration.exists():
            return {'message': 'No performance data available'}
        
        from django.db.models import Avg, Max, Min
        
        stats = logs_with_duration.aggregate(
            avg_duration=Avg('duration_ms'),
            max_duration=Max('duration_ms'),
            min_duration=Min('duration_ms')
        )
        
        slow_operations = logs_with_duration.filter(duration_ms__gt=1000).count()
        
        return {
            'average_duration_ms': round(stats['avg_duration'], 2) if stats['avg_duration'] else 0,
            'max_duration_ms': stats['max_duration'],
            'min_duration_ms': stats['min_duration'],
            'slow_operations_count': slow_operations,
            'total_operations_with_timing': logs_with_duration.count()
        }
    
    def _generate_recommendations(self, audit_logs):
        """Generate security and performance recommendations."""
        recommendations = []
        
        # Check for suspicious patterns
        failed_logins = audit_logs.filter(
            action_type='FAILED_LOGIN',
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        if failed_logins > 10:
            recommendations.append({
                'type': 'security',
                'priority': 'high',
                'message': f'High number of failed login attempts ({failed_logins}) in the last 24 hours. Consider implementing rate limiting.'
            })
        
        # Check for admin overrides
        recent_overrides = audit_logs.filter(
            metadata__admin_override=True,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if recent_overrides > 5:
            recommendations.append({
                'type': 'governance',
                'priority': 'medium',
                'message': f'{recent_overrides} admin overrides in the last week. Review override policies and approval processes.'
            })
        
        # Check for performance issues
        slow_operations = audit_logs.filter(
            duration_ms__gt=5000,
            timestamp__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        if slow_operations > 0:
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'message': f'{slow_operations} slow operations (>5s) detected. Consider performance optimization.'
            })
        
        return recommendations
    
    def _display_summary_report(self, summary):
        """Display summary report in console."""
        if self.verbosity < 1:
            return
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("AUDIT SUMMARY REPORT"))
        self.stdout.write("="*60)
        
        self.stdout.write(f"Period: {summary['period_days']} days ({summary['start_date']} to {summary['end_date']})")
        self.stdout.write(f"Total Operations: {summary['total_operations']}")
        self.stdout.write(f"Critical Operations: {summary['critical_operations']}")
        self.stdout.write(f"Security Events: {summary['security_events']}")
        self.stdout.write(f"Failed Operations: {summary['failed_operations']}")
        
        if summary['top_users']:
            self.stdout.write("\nTop Users:")
            for username, count in summary['top_users'][:5]:
                self.stdout.write(f"  - {username}: {count} operations")
        
        if summary['analysis']['recommendations']:
            self.stdout.write("\nRecommendations:")
            for rec in summary['analysis']['recommendations']:
                priority_color = self.style.ERROR if rec['priority'] == 'high' else self.style.WARNING
                self.stdout.write(f"  - [{rec['type'].upper()}] {priority_color(rec['priority'].upper())}: {rec['message']}")
        
        self.stdout.write("="*60 + "\n")
    
    def _save_report(self, report, filename, format_type):
        """Save report to file."""
        try:
            if format_type == 'json':
                with open(filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
            elif format_type == 'csv':
                # For CSV, we'll save a simplified version
                import csv
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Metric', 'Value'])
                    
                    if 'total_operations' in report:
                        writer.writerow(['Total Operations', report['total_operations']])
                        writer.writerow(['Critical Operations', report['critical_operations']])
                        writer.writerow(['Security Events', report['security_events']])
                        writer.writerow(['Failed Operations', report['failed_operations']])
            
            self._log_success(f"Report saved to {filename}")
            
        except Exception as e:
            self._log_error(f"Failed to save report: {str(e)}")
    
    def _send_security_alert_email(self, report, options):
        """Send security alert email."""
        if not options.get('email_recipients'):
            self._log_warning("No email recipients specified for security alerts.")
            return
        
        subject = f"SOI Hub Security Alert - {report['high_severity_count']} High Severity Issues"
        
        message = f"""
Security Alert Report
Generated: {report['timestamp']}
Period: Last {report['period_hours']} hours

SUMMARY:
- Total Alerts: {report['total_alerts']}
- High Severity: {report['high_severity_count']}
- Medium Severity: {report['medium_severity_count']}
- Low Severity: {report['low_severity_count']}

HIGH SEVERITY ALERTS:
"""
        
        for alert in report['high_severity_alerts'][:10]:
            message += f"- {alert['timestamp']}: {alert['user']} - {alert['description']} (IP: {alert['ip_address']})\n"
        
        message += f"""
STATISTICS:
- Unique Users: {report['summary']['unique_users']}
- Unique IPs: {report['summary']['unique_ips']}
- Failed Operations: {report['summary']['failed_operations']}
- Admin Overrides: {report['summary']['admin_overrides']}

Please review these alerts and take appropriate action.
"""
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                options['email_recipients'],
                fail_silently=False
            )
            self._log_success("Security alert email sent successfully.")
        except Exception as e:
            self._log_error(f"Failed to send security alert email: {str(e)}")
    
    def _send_summary_report_email(self, summary, options):
        """Send summary report email."""
        if not options.get('email_recipients'):
            self._log_warning("No email recipients specified for summary report.")
            return
        
        subject = f"SOI Hub Audit Summary - {summary['period_days']} Days"
        
        message = f"""
Audit Summary Report
Generated: {summary['end_date']}
Period: {summary['period_days']} days

OVERVIEW:
- Total Operations: {summary['total_operations']}
- Critical Operations: {summary['critical_operations']}
- Security Events: {summary['security_events']}
- Failed Operations: {summary['failed_operations']}

TOP USERS:
"""
        
        for username, count in summary['top_users'][:5]:
            message += f"- {username}: {count} operations\n"
        
        if summary['analysis']['recommendations']:
            message += "\nRECOMMENDATIONS:\n"
            for rec in summary['analysis']['recommendations']:
                message += f"- [{rec['type'].upper()}] {rec['priority'].upper()}: {rec['message']}\n"
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                options['email_recipients'],
                fail_silently=False
            )
            self._log_success("Summary report email sent successfully.")
        except Exception as e:
            self._log_error(f"Failed to send summary report email: {str(e)}")
    
    def _log_info(self, message):
        """Log info message."""
        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(f"[INFO] {message}"))
    
    def _log_warning(self, message):
        """Log warning message."""
        if self.verbosity >= 1:
            self.stdout.write(self.style.WARNING(f"[WARNING] {message}"))
    
    def _log_error(self, message):
        """Log error message."""
        if self.verbosity >= 1:
            self.stdout.write(self.style.ERROR(f"[ERROR] {message}"))
    
    def _log_success(self, message):
        """Log success message."""
        if self.verbosity >= 1:
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] {message}")) 