"""
Management command for monitoring admin overrides.

This command checks for expiring overrides, validates active overrides,
and sends notifications to relevant stakeholders.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from datetime import timedelta
import logging

from common.models import AdminOverride, AuditLog
from common.override_service import AdminOverrideService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor admin overrides for expiration, validation, and notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=7,
            help='Number of days ahead to check for expiring overrides (default: 7)'
        )
        
        parser.add_argument(
            '--send-notifications',
            action='store_true',
            help='Send email notifications for expiring overrides'
        )
        
        parser.add_argument(
            '--auto-expire',
            action='store_true',
            help='Automatically expire overrides that have passed their end date'
        )
        
        parser.add_argument(
            '--emergency-only',
            action='store_true',
            help='Only process emergency overrides'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        self.dry_run = options['dry_run']
        self.days_ahead = options['days_ahead']
        self.send_notifications = options['send_notifications']
        self.auto_expire = options['auto_expire']
        self.emergency_only = options['emergency_only']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting admin override monitoring (dry_run={self.dry_run})"
            )
        )
        
        try:
            # Check for expiring overrides
            expiring_count = self.check_expiring_overrides()
            
            # Auto-expire overrides if requested
            expired_count = 0
            if self.auto_expire:
                expired_count = self.auto_expire_overrides()
            
            # Check for pending overrides requiring attention
            pending_count = self.check_pending_overrides()
            
            # Generate summary report
            self.generate_summary_report(expiring_count, expired_count, pending_count)
            
            self.stdout.write(
                self.style.SUCCESS("Admin override monitoring completed successfully")
            )
            
        except Exception as e:
            logger.error(f"Error in override monitoring: {str(e)}")
            raise CommandError(f"Override monitoring failed: {str(e)}")
    
    def check_expiring_overrides(self):
        """Check for overrides expiring within the specified timeframe"""
        
        self.stdout.write("Checking for expiring overrides...")
        
        expiring_overrides = AdminOverrideService.get_expiring_overrides(self.days_ahead)
        
        if self.emergency_only:
            expiring_overrides = [o for o in expiring_overrides if o.is_emergency]
        
        if not expiring_overrides:
            self.stdout.write("  No expiring overrides found")
            return 0
        
        self.stdout.write(
            self.style.WARNING(
                f"  Found {len(expiring_overrides)} override(s) expiring within {self.days_ahead} days"
            )
        )
        
        for override in expiring_overrides:
            days_remaining = (override.effective_until - timezone.now()).days
            emergency_flag = " [EMERGENCY]" if override.is_emergency else ""
            
            self.stdout.write(
                f"    - {override.title} (ID: {override.id}) expires in {days_remaining} days{emergency_flag}"
            )
            
            # Send notifications if requested
            if self.send_notifications and not self.dry_run:
                self.send_expiration_notification(override, days_remaining)
        
        return len(expiring_overrides)
    
    def auto_expire_overrides(self):
        """Automatically expire overrides that have passed their end date"""
        
        self.stdout.write("Checking for overrides to auto-expire...")
        
        now = timezone.now()
        expired_overrides = AdminOverride.objects.filter(
            status='ACTIVE',
            effective_until__lt=now
        )
        
        if self.emergency_only:
            expired_overrides = expired_overrides.filter(is_emergency=True)
        
        if not expired_overrides.exists():
            self.stdout.write("  No overrides to auto-expire")
            return 0
        
        count = expired_overrides.count()
        self.stdout.write(
            self.style.WARNING(f"  Found {count} override(s) to auto-expire")
        )
        
        if not self.dry_run:
            for override in expired_overrides:
                try:
                    override.status = 'EXPIRED'
                    override.save()
                    
                    # Log the auto-expiration
                    AuditLog.objects.create(
                        action_type='UPDATE',
                        action_description=f'Admin override auto-expired: {override.title}',
                        object_representation=str(override),
                        changes={'status': 'EXPIRED', 'auto_expired': True}
                    )
                    
                    self.stdout.write(f"    - Expired: {override.title} (ID: {override.id})")
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    - Failed to expire {override.title}: {str(e)}"
                        )
                    )
        else:
            for override in expired_overrides:
                self.stdout.write(f"    - Would expire: {override.title} (ID: {override.id})")
        
        return count
    
    def check_pending_overrides(self):
        """Check for pending overrides requiring attention"""
        
        self.stdout.write("Checking pending overrides...")
        
        # Get pending overrides older than 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        old_pending = AdminOverride.objects.filter(
            status='PENDING',
            created_at__lt=cutoff_time
        )
        
        if self.emergency_only:
            old_pending = old_pending.filter(is_emergency=True)
        
        # Get emergency pending overrides (any age)
        emergency_pending = AdminOverride.objects.filter(
            status='PENDING',
            is_emergency=True
        )
        
        total_pending = old_pending.count() + emergency_pending.exclude(
            id__in=old_pending.values_list('id', flat=True)
        ).count()
        
        if total_pending == 0:
            self.stdout.write("  No pending overrides requiring attention")
            return 0
        
        self.stdout.write(
            self.style.WARNING(
                f"  Found {total_pending} pending override(s) requiring attention"
            )
        )
        
        # Report old pending overrides
        if old_pending.exists():
            self.stdout.write(f"    - {old_pending.count()} pending for >24 hours")
            for override in old_pending[:5]:  # Show first 5
                age_hours = (timezone.now() - override.created_at).total_seconds() / 3600
                self.stdout.write(
                    f"      * {override.title} (pending {age_hours:.1f} hours)"
                )
        
        # Report emergency pending overrides
        emergency_count = emergency_pending.count()
        if emergency_count > 0:
            self.stdout.write(f"    - {emergency_count} emergency override(s) pending")
        
        return total_pending
    
    def send_expiration_notification(self, override, days_remaining):
        """Send email notification for expiring override"""
        
        try:
            # Determine recipients
            recipients = []
            
            if override.requested_by and override.requested_by.email:
                recipients.append(override.requested_by.email)
            
            if override.approved_by and override.approved_by.email:
                recipients.append(override.approved_by.email)
            
            if not recipients:
                self.stdout.write(
                    self.style.WARNING(
                        f"    - No email recipients for {override.title}"
                    )
                )
                return
            
            # Prepare email content
            subject = f"Admin Override Expiring: {override.title}"
            
            if override.is_emergency:
                subject = f"[EMERGENCY] {subject}"
            
            message = f"""
Admin Override Expiration Notice

Override: {override.title}
Type: {override.get_override_type_display()}
Risk Level: {override.get_risk_level_display()}
Status: {override.get_status_display()}
Days Remaining: {days_remaining}
Expires: {override.effective_until.strftime('%Y-%m-%d %H:%M:%S')}

Description: {override.description}

Justification: {override.justification}

Please review this override and take appropriate action if needed.

Override ID: {override.id}
            """.strip()
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=list(set(recipients)),  # Remove duplicates
                fail_silently=False
            )
            
            # Log the notification
            override.add_communication_log(
                f'Expiration notification sent to {len(recipients)} recipient(s)',
                None
            )
            
            self.stdout.write(
                f"    - Notification sent for {override.title} to {len(recipients)} recipient(s)"
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"    - Failed to send notification for {override.title}: {str(e)}"
                )
            )
    
    def generate_summary_report(self, expiring_count, expired_count, pending_count):
        """Generate and display summary report"""
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("ADMIN OVERRIDE MONITORING SUMMARY"))
        self.stdout.write("="*60)
        
        self.stdout.write(f"Monitoring Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Days Ahead Checked: {self.days_ahead}")
        self.stdout.write(f"Emergency Only: {self.emergency_only}")
        self.stdout.write(f"Dry Run Mode: {self.dry_run}")
        
        self.stdout.write("\nResults:")
        self.stdout.write(f"  - Expiring Overrides: {expiring_count}")
        self.stdout.write(f"  - Auto-Expired Overrides: {expired_count}")
        self.stdout.write(f"  - Pending Requiring Attention: {pending_count}")
        
        # Overall status
        total_issues = expiring_count + pending_count
        if total_issues == 0:
            self.stdout.write(
                self.style.SUCCESS("\nOverall Status: All overrides are in good standing")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"\nOverall Status: {total_issues} item(s) require attention")
            )
        
        self.stdout.write("="*60) 