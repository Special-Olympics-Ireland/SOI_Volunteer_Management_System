"""
Django management command for monitoring JustGo API health and generating reports.

Usage:
    python manage.py justgo_health_monitor --check-all
    python manage.py justgo_health_monitor --check-connectivity
    python manage.py justgo_health_monitor --check-credentials
    python manage.py justgo_health_monitor --generate-report
"""

import json
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from integrations.justgo import JustGoAPIClient, JustGoAPIError
from integrations.models import IntegrationLog, JustGoMemberMapping, JustGoCredentialCache


class Command(BaseCommand):
    help = 'Monitor JustGo API health and generate status reports'

    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            '--check-all',
            action='store_true',
            help='Perform all health checks'
        )
        
        parser.add_argument(
            '--check-connectivity',
            action='store_true',
            help='Check API connectivity and authentication'
        )
        
        parser.add_argument(
            '--check-credentials',
            action='store_true',
            help='Check credential expiry status'
        )
        
        parser.add_argument(
            '--check-sync-status',
            action='store_true',
            help='Check synchronization status and conflicts'
        )
        
        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate comprehensive health report'
        )
        
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send health report via email'
        )
        
        parser.add_argument(
            '--email-recipients',
            type=str,
            help='Comma-separated list of email recipients'
        )
        
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=30,
            help='Days ahead to check for credential expiry (default: 30)'
        )
        
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file path for the health report'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.options = options
        
        # Initialize JustGo client
        try:
            self.client = JustGoAPIClient()
        except Exception as e:
            raise CommandError(f"Failed to initialize JustGo client: {e}")
        
        # Determine what checks to run
        checks_to_run = []
        
        if options['check_all']:
            checks_to_run = ['connectivity', 'credentials', 'sync_status']
        else:
            if options['check_connectivity']:
                checks_to_run.append('connectivity')
            if options['check_credentials']:
                checks_to_run.append('credentials')
            if options['check_sync_status']:
                checks_to_run.append('sync_status')
        
        if not checks_to_run and not options['generate_report']:
            raise CommandError("No checks specified. Use --check-all or specific check options.")
        
        # Run health checks
        health_results = {}
        
        if 'connectivity' in checks_to_run:
            self.stdout.write("Checking API connectivity...")
            health_results['connectivity'] = self.check_connectivity()
        
        if 'credentials' in checks_to_run:
            self.stdout.write("Checking credential status...")
            health_results['credentials'] = self.check_credentials()
        
        if 'sync_status' in checks_to_run:
            self.stdout.write("Checking synchronization status...")
            health_results['sync_status'] = self.check_sync_status()
        
        # Generate report
        if options['generate_report'] or checks_to_run:
            report = self.generate_health_report(health_results)
            
            # Output report
            if options['output_file']:
                self.save_report_to_file(report, options['output_file'])
            else:
                self.display_report(report)
            
            # Send email if requested
            if options['send_email']:
                self.send_email_report(report, options.get('email_recipients'))

    def check_connectivity(self) -> dict:
        """Check JustGo API connectivity and authentication"""
        connectivity_result = {
            'status': 'unknown',
            'checks': [],
            'errors': [],
            'response_times': [],
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # Test 1: Health check
            start_time = time.time()
            health_check = self.client.health_check()
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            connectivity_result['checks'].append({
                'test': 'health_check',
                'status': health_check.get('status', 'unknown'),
                'response_time_ms': round(response_time, 2),
                'authenticated': health_check.get('authenticated', False)
            })
            connectivity_result['response_times'].append(response_time)
            
            # Test 2: Authentication
            start_time = time.time()
            auth_result = self.client.authenticate()
            response_time = (time.time() - start_time) * 1000
            
            connectivity_result['checks'].append({
                'test': 'authentication',
                'status': 'success' if auth_result.get('accessToken') else 'failed',
                'response_time_ms': round(response_time, 2),
                'token_expires_at': self.client._token_expires_at.isoformat() if self.client._token_expires_at else None
            })
            connectivity_result['response_times'].append(response_time)
            
            # Test 3: Sample API call (member search)
            try:
                start_time = time.time()
                sample_result = self.client.find_member_by_mid('TEST000001')  # Non-existent member
                response_time = (time.time() - start_time) * 1000
                
                connectivity_result['checks'].append({
                    'test': 'sample_api_call',
                    'status': 'success',  # Even 404 is a successful API call
                    'response_time_ms': round(response_time, 2)
                })
                connectivity_result['response_times'].append(response_time)
                
            except Exception as e:
                connectivity_result['checks'].append({
                    'test': 'sample_api_call',
                    'status': 'failed',
                    'error': str(e)
                })
                connectivity_result['errors'].append(f"Sample API call failed: {e}")
            
            # Calculate overall status
            failed_checks = [c for c in connectivity_result['checks'] if c['status'] == 'failed']
            if not failed_checks:
                connectivity_result['status'] = 'healthy'
            elif len(failed_checks) < len(connectivity_result['checks']):
                connectivity_result['status'] = 'degraded'
            else:
                connectivity_result['status'] = 'unhealthy'
            
            # Calculate average response time
            if connectivity_result['response_times']:
                connectivity_result['avg_response_time_ms'] = round(
                    sum(connectivity_result['response_times']) / len(connectivity_result['response_times']), 2
                )
            
        except Exception as e:
            connectivity_result['status'] = 'unhealthy'
            connectivity_result['errors'].append(f"Connectivity check failed: {e}")
        
        return connectivity_result

    def check_credentials(self) -> dict:
        """Check credential expiry status for all cached credentials"""
        credentials_result = {
            'status': 'unknown',
            'total_credentials': 0,
            'active_credentials': 0,
            'expired_credentials': 0,
            'expiring_soon': 0,
            'expiring_credentials': [],
            'expired_credentials_list': [],
            'credential_types': {},
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            days_ahead = self.options.get('days_ahead', 30)
            
            # Get all cached credentials
            all_credentials = JustGoCredentialCache.objects.all()
            credentials_result['total_credentials'] = all_credentials.count()
            
            # Analyze credentials
            for credential in all_credentials:
                # Count by status
                if credential.status == JustGoCredentialCache.CredentialStatus.ACTIVE:
                    credentials_result['active_credentials'] += 1
                elif credential.status == JustGoCredentialCache.CredentialStatus.EXPIRED:
                    credentials_result['expired_credentials'] += 1
                    credentials_result['expired_credentials_list'].append({
                        'member_id': credential.member_mapping.justgo_member_id,
                        'credential_name': credential.credential_name,
                        'credential_type': credential.credential_type,
                        'expiry_date': credential.expiry_date.isoformat() if credential.expiry_date else None
                    })
                
                # Check for expiring soon
                if credential.is_expiring_soon(days_ahead):
                    credentials_result['expiring_soon'] += 1
                    credentials_result['expiring_credentials'].append({
                        'member_id': credential.member_mapping.justgo_member_id,
                        'credential_name': credential.credential_name,
                        'credential_type': credential.credential_type,
                        'expiry_date': credential.expiry_date.isoformat() if credential.expiry_date else None,
                        'days_until_expiry': credential.days_until_expiry
                    })
                
                # Count by type
                cred_type = credential.credential_type
                if cred_type not in credentials_result['credential_types']:
                    credentials_result['credential_types'][cred_type] = {
                        'total': 0, 'active': 0, 'expired': 0, 'expiring_soon': 0
                    }
                
                credentials_result['credential_types'][cred_type]['total'] += 1
                if credential.status == JustGoCredentialCache.CredentialStatus.ACTIVE:
                    credentials_result['credential_types'][cred_type]['active'] += 1
                elif credential.status == JustGoCredentialCache.CredentialStatus.EXPIRED:
                    credentials_result['credential_types'][cred_type]['expired'] += 1
                
                if credential.is_expiring_soon(days_ahead):
                    credentials_result['credential_types'][cred_type]['expiring_soon'] += 1
            
            # Determine overall status
            if credentials_result['expired_credentials'] > 0:
                credentials_result['status'] = 'critical'
            elif credentials_result['expiring_soon'] > 0:
                credentials_result['status'] = 'warning'
            else:
                credentials_result['status'] = 'healthy'
            
        except Exception as e:
            credentials_result['status'] = 'error'
            credentials_result['error'] = str(e)
        
        return credentials_result

    def check_sync_status(self) -> dict:
        """Check synchronization status and conflicts"""
        sync_result = {
            'status': 'unknown',
            'total_mappings': 0,
            'active_mappings': 0,
            'pending_mappings': 0,
            'conflict_mappings': 0,
            'inactive_mappings': 0,
            'conflicts': [],
            'recent_syncs': [],
            'sync_statistics': {},
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # Get all member mappings
            all_mappings = JustGoMemberMapping.objects.all()
            sync_result['total_mappings'] = all_mappings.count()
            
            # Count by status
            for mapping in all_mappings:
                if mapping.status == JustGoMemberMapping.MappingStatus.ACTIVE:
                    sync_result['active_mappings'] += 1
                elif mapping.status == JustGoMemberMapping.MappingStatus.PENDING:
                    sync_result['pending_mappings'] += 1
                elif mapping.status == JustGoMemberMapping.MappingStatus.CONFLICT:
                    sync_result['conflict_mappings'] += 1
                    sync_result['conflicts'].append({
                        'member_id': mapping.justgo_member_id,
                        'local_user_email': mapping.local_user.email,
                        'conflicts': mapping.sync_conflicts,
                        'last_synced': mapping.last_synced_at.isoformat() if mapping.last_synced_at else None
                    })
                elif mapping.status == JustGoMemberMapping.MappingStatus.INACTIVE:
                    sync_result['inactive_mappings'] += 1
            
            # Get recent sync operations
            from integrations.models import JustGoSync
            recent_syncs = JustGoSync.objects.order_by('-started_at')[:10]
            
            for sync in recent_syncs:
                sync_result['recent_syncs'].append({
                    'id': str(sync.id),
                    'sync_type': sync.get_sync_type_display(),
                    'status': sync.get_status_display(),
                    'started_at': sync.started_at.isoformat(),
                    'completed_at': sync.completed_at.isoformat() if sync.completed_at else None,
                    'success_rate': sync.success_rate,
                    'processed_records': sync.processed_records,
                    'successful_records': sync.successful_records,
                    'failed_records': sync.failed_records
                })
            
            # Calculate sync statistics
            sync_result['sync_statistics'] = {
                'mapping_health_score': (sync_result['active_mappings'] / sync_result['total_mappings'] * 100) if sync_result['total_mappings'] > 0 else 0,
                'conflict_rate': (sync_result['conflict_mappings'] / sync_result['total_mappings'] * 100) if sync_result['total_mappings'] > 0 else 0,
                'pending_rate': (sync_result['pending_mappings'] / sync_result['total_mappings'] * 100) if sync_result['total_mappings'] > 0 else 0
            }
            
            # Determine overall status
            if sync_result['conflict_mappings'] > 0:
                sync_result['status'] = 'warning'
            elif sync_result['pending_mappings'] > sync_result['total_mappings'] * 0.1:  # More than 10% pending
                sync_result['status'] = 'degraded'
            else:
                sync_result['status'] = 'healthy'
            
        except Exception as e:
            sync_result['status'] = 'error'
            sync_result['error'] = str(e)
        
        return sync_result

    def generate_health_report(self, health_results: dict) -> dict:
        """Generate comprehensive health report"""
        report = {
            'generated_at': timezone.now().isoformat(),
            'overall_status': 'unknown',
            'summary': {},
            'details': health_results,
            'recommendations': []
        }
        
        # Calculate overall status
        statuses = []
        for check_name, result in health_results.items():
            status = result.get('status', 'unknown')
            statuses.append(status)
        
        if 'unhealthy' in statuses or 'critical' in statuses or 'error' in statuses:
            report['overall_status'] = 'critical'
        elif 'degraded' in statuses or 'warning' in statuses:
            report['overall_status'] = 'warning'
        elif all(s == 'healthy' for s in statuses):
            report['overall_status'] = 'healthy'
        else:
            report['overall_status'] = 'unknown'
        
        # Generate summary
        if 'connectivity' in health_results:
            conn = health_results['connectivity']
            report['summary']['connectivity'] = {
                'status': conn['status'],
                'avg_response_time': conn.get('avg_response_time_ms', 0),
                'failed_checks': len([c for c in conn.get('checks', []) if c['status'] == 'failed'])
            }
        
        if 'credentials' in health_results:
            creds = health_results['credentials']
            report['summary']['credentials'] = {
                'status': creds['status'],
                'total': creds['total_credentials'],
                'expired': creds['expired_credentials'],
                'expiring_soon': creds['expiring_soon']
            }
        
        if 'sync_status' in health_results:
            sync = health_results['sync_status']
            report['summary']['sync_status'] = {
                'status': sync['status'],
                'total_mappings': sync['total_mappings'],
                'conflicts': sync['conflict_mappings'],
                'health_score': sync.get('sync_statistics', {}).get('mapping_health_score', 0)
            }
        
        # Generate recommendations
        report['recommendations'] = self.generate_recommendations(health_results)
        
        return report

    def generate_recommendations(self, health_results: dict) -> list:
        """Generate recommendations based on health check results"""
        recommendations = []
        
        # Connectivity recommendations
        if 'connectivity' in health_results:
            conn = health_results['connectivity']
            if conn['status'] == 'unhealthy':
                recommendations.append({
                    'priority': 'high',
                    'category': 'connectivity',
                    'message': 'JustGo API connectivity is down. Check network connection and API credentials.'
                })
            elif conn.get('avg_response_time_ms', 0) > 5000:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'connectivity',
                    'message': 'JustGo API response times are slow. Consider checking network performance.'
                })
        
        # Credentials recommendations
        if 'credentials' in health_results:
            creds = health_results['credentials']
            if creds['expired_credentials'] > 0:
                recommendations.append({
                    'priority': 'high',
                    'category': 'credentials',
                    'message': f"{creds['expired_credentials']} credentials have expired. Update immediately."
                })
            if creds['expiring_soon'] > 0:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'credentials',
                    'message': f"{creds['expiring_soon']} credentials are expiring soon. Plan renewal process."
                })
        
        # Sync recommendations
        if 'sync_status' in health_results:
            sync = health_results['sync_status']
            if sync['conflict_mappings'] > 0:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'sync',
                    'message': f"{sync['conflict_mappings']} member mappings have conflicts. Review and resolve."
                })
            
            health_score = sync.get('sync_statistics', {}).get('mapping_health_score', 0)
            if health_score < 80:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'sync',
                    'message': f"Mapping health score is {health_score:.1f}%. Consider running bulk synchronization."
                })
        
        return recommendations

    def display_report(self, report: dict):
        """Display health report to stdout"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("JustGo API Health Report"))
        self.stdout.write("="*60)
        
        # Overall status
        status_style = self.style.SUCCESS if report['overall_status'] == 'healthy' else \
                      self.style.WARNING if report['overall_status'] == 'warning' else \
                      self.style.ERROR
        
        self.stdout.write(f"Overall Status: {status_style(report['overall_status'].upper())}")
        self.stdout.write(f"Generated: {report['generated_at']}")
        
        # Summary
        if report['summary']:
            self.stdout.write("\n" + "-"*40)
            self.stdout.write("SUMMARY")
            self.stdout.write("-"*40)
            
            for check_name, summary in report['summary'].items():
                self.stdout.write(f"\n{check_name.replace('_', ' ').title()}:")
                for key, value in summary.items():
                    self.stdout.write(f"  {key}: {value}")
        
        # Recommendations
        if report['recommendations']:
            self.stdout.write("\n" + "-"*40)
            self.stdout.write("RECOMMENDATIONS")
            self.stdout.write("-"*40)
            
            for rec in report['recommendations']:
                priority_style = self.style.ERROR if rec['priority'] == 'high' else \
                               self.style.WARNING if rec['priority'] == 'medium' else \
                               self.style.SUCCESS
                
                self.stdout.write(f"\n[{priority_style(rec['priority'].upper())}] {rec['message']}")

    def save_report_to_file(self, report: dict, file_path: str):
        """Save health report to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.stdout.write(f"Health report saved to: {file_path}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to save report: {e}"))

    def send_email_report(self, report: dict, recipients: str = None):
        """Send health report via email"""
        try:
            if not recipients:
                recipients = getattr(settings, 'JUSTGO_HEALTH_REPORT_RECIPIENTS', [])
            else:
                recipients = [email.strip() for email in recipients.split(',')]
            
            if not recipients:
                self.stdout.write(self.style.WARNING("No email recipients specified"))
                return
            
            subject = f"JustGo API Health Report - {report['overall_status'].upper()}"
            
            # Create email body
            body = f"""
JustGo API Health Report
Generated: {report['generated_at']}
Overall Status: {report['overall_status'].upper()}

SUMMARY:
"""
            
            for check_name, summary in report['summary'].items():
                body += f"\n{check_name.replace('_', ' ').title()}:\n"
                for key, value in summary.items():
                    body += f"  {key}: {value}\n"
            
            if report['recommendations']:
                body += "\nRECOMMENDATIONS:\n"
                for rec in report['recommendations']:
                    body += f"\n[{rec['priority'].upper()}] {rec['message']}\n"
            
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=recipients,
                fail_silently=False
            )
            
            self.stdout.write(f"Health report sent to: {', '.join(recipients)}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send email: {e}")) 