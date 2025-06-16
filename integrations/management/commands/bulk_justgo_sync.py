"""
Django management command for bulk JustGo synchronization operations.

Usage:
    python manage.py bulk_justgo_sync --sync-type local_to_justgo --batch-size 50
    python manage.py bulk_justgo_sync --sync-type justgo_to_local --filter-active-only
    python manage.py bulk_justgo_sync --sync-type bidirectional --dry-run
    python manage.py bulk_justgo_sync --sync-type credential_sync --member-ids ME000001,ME000002
"""

import time
import logging
from typing import List, Dict, Any
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.db import models
from integrations.justgo import JustGoAPIClient, JustGoAPIError
from integrations.models import JustGoSync, JustGoMemberMapping, IntegrationLog

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Perform bulk synchronization operations with JustGo API'

    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            '--sync-type',
            type=str,
            choices=['local_to_justgo', 'justgo_to_local', 'bidirectional', 'credential_sync'],
            required=True,
            help='Type of synchronization to perform'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of records to process in each batch (default: 50)'
        )
        
        parser.add_argument(
            '--member-ids',
            type=str,
            help='Comma-separated list of specific member IDs to sync (MIDs or member GUIDs)'
        )
        
        parser.add_argument(
            '--filter-active-only',
            action='store_true',
            help='Only sync active members/mappings'
        )
        
        parser.add_argument(
            '--filter-modified-since',
            type=str,
            help='Only sync records modified since date (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without making actual changes'
        )
        
        parser.add_argument(
            '--force-override',
            action='store_true',
            help='Force sync with admin override (bypasses read-only mode)'
        )
        
        parser.add_argument(
            '--override-justification',
            type=str,
            default='Bulk sync operation via management command',
            help='Justification for admin override if --force-override is used'
        )
        
        parser.add_argument(
            '--max-errors',
            type=int,
            default=10,
            help='Maximum number of errors before stopping (default: 10)'
        )
        
        parser.add_argument(
            '--delay-between-batches',
            type=float,
            default=1.0,
            help='Delay in seconds between batches (default: 1.0)'
        )
        
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Create missing profiles during sync'
        )
        
        parser.add_argument(
            '--update-credentials',
            action='store_true',
            help='Update credential cache during sync'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.options = options
        self.sync_type = options['sync_type']
        self.batch_size = options['batch_size']
        self.dry_run = options['dry_run']
        self.force_override = options['force_override']
        self.max_errors = options['max_errors']
        
        # Initialize JustGo client
        try:
            self.client = JustGoAPIClient()
        except Exception as e:
            raise CommandError(f"Failed to initialize JustGo client: {e}")
        
        # Create sync operation record
        self.sync_operation = self.create_sync_operation()
        
        try:
            self.stdout.write(
                self.style.SUCCESS(f"Starting bulk {self.sync_type} synchronization...")
            )
            
            if self.dry_run:
                self.stdout.write(
                    self.style.WARNING("DRY RUN MODE - No actual changes will be made")
                )
            
            # Perform the sync based on type
            if self.sync_type == 'local_to_justgo':
                self.sync_local_to_justgo()
            elif self.sync_type == 'justgo_to_local':
                self.sync_justgo_to_local()
            elif self.sync_type == 'bidirectional':
                self.sync_bidirectional()
            elif self.sync_type == 'credential_sync':
                self.sync_credentials()
            
            # Complete the sync operation
            self.sync_operation.complete(JustGoSync.SyncStatus.COMPLETED)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Bulk synchronization completed successfully!\n"
                    f"Processed: {self.sync_operation.processed_records}\n"
                    f"Successful: {self.sync_operation.successful_records}\n"
                    f"Failed: {self.sync_operation.failed_records}\n"
                    f"Success Rate: {self.sync_operation.success_rate:.1f}%"
                )
            )
            
        except Exception as e:
            self.sync_operation.complete(JustGoSync.SyncStatus.FAILED)
            self.sync_operation.error_details.append({
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            })
            self.sync_operation.save()
            
            logger.error(f"Bulk sync failed: {e}")
            raise CommandError(f"Bulk synchronization failed: {e}")

    def create_sync_operation(self) -> JustGoSync:
        """Create a sync operation record"""
        sync_type_mapping = {
            'local_to_justgo': JustGoSync.SyncType.LOCAL_TO_JUSTGO,
            'justgo_to_local': JustGoSync.SyncType.JUSTGO_TO_LOCAL,
            'bidirectional': JustGoSync.SyncType.BIDIRECTIONAL,
            'credential_sync': JustGoSync.SyncType.CREDENTIAL_SYNC
        }
        
        return JustGoSync.objects.create(
            sync_type=sync_type_mapping[self.sync_type],
            status=JustGoSync.SyncStatus.IN_PROGRESS,
            is_admin_override=self.force_override,
            override_justification=self.options.get('override_justification', ''),
            sync_config={
                'batch_size': self.batch_size,
                'dry_run': self.dry_run,
                'force_override': self.force_override,
                'filter_active_only': self.options.get('filter_active_only', False),
                'filter_modified_since': self.options.get('filter_modified_since'),
                'member_ids': self.options.get('member_ids'),
                'create_missing': self.options.get('create_missing', False),
                'update_credentials': self.options.get('update_credentials', False)
            }
        )

    def get_local_users_to_sync(self) -> List[User]:
        """Get local users that need to be synced"""
        queryset = User.objects.all()
        
        # Apply filters
        if self.options.get('filter_active_only'):
            queryset = queryset.filter(is_active=True)
        
        if self.options.get('filter_modified_since'):
            from datetime import datetime
            modified_since = datetime.strptime(
                self.options['filter_modified_since'], '%Y-%m-%d'
            ).date()
            queryset = queryset.filter(updated_at__date__gte=modified_since)
        
        if self.options.get('member_ids'):
            member_ids = [mid.strip() for mid in self.options['member_ids'].split(',')]
            # Filter by email or existing JustGo mappings
            queryset = queryset.filter(
                models.Q(email__in=member_ids) |
                models.Q(justgo_mapping__justgo_mid__in=member_ids) |
                models.Q(justgo_mapping__justgo_member_id__in=member_ids)
            )
        
        return list(queryset)

    def get_justgo_members_to_sync(self) -> List[str]:
        """Get JustGo member IDs that need to be synced"""
        if self.options.get('member_ids'):
            return [mid.strip() for mid in self.options['member_ids'].split(',')]
        
        # Get all mapped members
        mappings = JustGoMemberMapping.objects.all()
        
        if self.options.get('filter_active_only'):
            mappings = mappings.filter(status=JustGoMemberMapping.MappingStatus.ACTIVE)
        
        return [mapping.justgo_member_id for mapping in mappings]

    def sync_local_to_justgo(self):
        """Sync local users to JustGo"""
        users = self.get_local_users_to_sync()
        self.sync_operation.total_records = len(users)
        self.sync_operation.save()
        
        self.stdout.write(f"Syncing {len(users)} local users to JustGo...")
        
        error_count = 0
        processed = 0
        successful = 0
        failed = 0
        
        # Process in batches
        for i in range(0, len(users), self.batch_size):
            batch = users[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(users) + self.batch_size - 1) // self.batch_size
            
            self.stdout.write(f"Processing batch {batch_num}/{total_batches}...")
            
            for user in batch:
                try:
                    if self.dry_run:
                        self.stdout.write(f"  [DRY RUN] Would sync user: {user.email}")
                        successful += 1
                    else:
                        if self.force_override:
                            # Use admin override
                            admin_user = self.get_admin_user()
                            result = self.client.sync_with_override(
                                'local_to_justgo',
                                admin_user,
                                self.options['override_justification'],
                                user=user,
                                create_if_missing=self.options.get('create_missing', False)
                            )
                        else:
                            # Regular sync
                            result = self.client.sync_local_to_justgo(
                                user, 
                                create_if_missing=self.options.get('create_missing', False)
                            )
                        
                        if result.get('status') == 'success':
                            successful += 1
                            self.stdout.write(f"  ✓ Synced: {user.email}")
                        else:
                            failed += 1
                            self.stdout.write(
                                self.style.ERROR(f"  ✗ Failed: {user.email} - {result.get('message', 'Unknown error')}")
                            )
                    
                    processed += 1
                    
                except Exception as e:
                    failed += 1
                    error_count += 1
                    logger.error(f"Failed to sync user {user.email}: {e}")
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Error syncing {user.email}: {e}")
                    )
                    
                    if error_count >= self.max_errors:
                        raise CommandError(f"Too many errors ({error_count}), stopping sync")
                
                # Update progress
                self.sync_operation.update_progress(
                    processed, successful, failed, f"Processing user: {user.email}"
                )
            
            # Delay between batches
            if self.options['delay_between_batches'] > 0:
                time.sleep(self.options['delay_between_batches'])

    def sync_justgo_to_local(self):
        """Sync JustGo members to local database"""
        member_ids = self.get_justgo_members_to_sync()
        self.sync_operation.total_records = len(member_ids)
        self.sync_operation.save()
        
        self.stdout.write(f"Syncing {len(member_ids)} JustGo members to local database...")
        
        error_count = 0
        processed = 0
        successful = 0
        failed = 0
        
        # Process in batches
        for i in range(0, len(member_ids), self.batch_size):
            batch = member_ids[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(member_ids) + self.batch_size - 1) // self.batch_size
            
            self.stdout.write(f"Processing batch {batch_num}/{total_batches}...")
            
            for member_id in batch:
                try:
                    if self.dry_run:
                        self.stdout.write(f"  [DRY RUN] Would sync member: {member_id}")
                        successful += 1
                    else:
                        # Get member data from JustGo
                        member_data = self.client.get_member_by_id(member_id)
                        
                        if member_data.get('data'):
                            # Sync to local database
                            result = self.client.sync_member_to_local(
                                member_id, User
                            )
                            
                            if result.get('status') == 'success':
                                successful += 1
                                self.stdout.write(f"  ✓ Synced: {member_id}")
                                
                                # Update credentials if requested
                                if self.options.get('update_credentials'):
                                    self.update_member_credentials(member_id)
                            else:
                                failed += 1
                                self.stdout.write(
                                    self.style.ERROR(f"  ✗ Failed: {member_id} - {result.get('message', 'Unknown error')}")
                                )
                        else:
                            failed += 1
                            self.stdout.write(
                                self.style.ERROR(f"  ✗ No data found for member: {member_id}")
                            )
                    
                    processed += 1
                    
                except Exception as e:
                    failed += 1
                    error_count += 1
                    logger.error(f"Failed to sync member {member_id}: {e}")
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Error syncing {member_id}: {e}")
                    )
                    
                    if error_count >= self.max_errors:
                        raise CommandError(f"Too many errors ({error_count}), stopping sync")
                
                # Update progress
                self.sync_operation.update_progress(
                    processed, successful, failed, f"Processing member: {member_id}"
                )
            
            # Delay between batches
            if self.options['delay_between_batches'] > 0:
                time.sleep(self.options['delay_between_batches'])

    def sync_bidirectional(self):
        """Perform bidirectional synchronization"""
        self.stdout.write("Performing bidirectional synchronization...")
        
        # First sync local to JustGo
        self.stdout.write("Phase 1: Syncing local users to JustGo...")
        self.sync_local_to_justgo()
        
        # Then sync JustGo to local
        self.stdout.write("Phase 2: Syncing JustGo members to local...")
        self.sync_justgo_to_local()

    def sync_credentials(self):
        """Sync credentials for existing mappings"""
        mappings = JustGoMemberMapping.objects.filter(
            status=JustGoMemberMapping.MappingStatus.ACTIVE
        )
        
        if self.options.get('member_ids'):
            member_ids = [mid.strip() for mid in self.options['member_ids'].split(',')]
            mappings = mappings.filter(
                models.Q(justgo_mid__in=member_ids) |
                models.Q(justgo_member_id__in=member_ids)
            )
        
        self.sync_operation.total_records = mappings.count()
        self.sync_operation.save()
        
        self.stdout.write(f"Syncing credentials for {mappings.count()} members...")
        
        error_count = 0
        processed = 0
        successful = 0
        failed = 0
        
        for mapping in mappings:
            try:
                if self.dry_run:
                    self.stdout.write(f"  [DRY RUN] Would sync credentials for: {mapping.justgo_member_id}")
                    successful += 1
                else:
                    self.update_member_credentials(mapping.justgo_member_id)
                    successful += 1
                    self.stdout.write(f"  ✓ Updated credentials: {mapping.justgo_member_id}")
                
                processed += 1
                
            except Exception as e:
                failed += 1
                error_count += 1
                logger.error(f"Failed to sync credentials for {mapping.justgo_member_id}: {e}")
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error syncing credentials {mapping.justgo_member_id}: {e}")
                )
                
                if error_count >= self.max_errors:
                    raise CommandError(f"Too many errors ({error_count}), stopping sync")
            
            # Update progress
            self.sync_operation.update_progress(
                processed, successful, failed, f"Processing credentials: {mapping.justgo_member_id}"
            )

    def update_member_credentials(self, member_id: str):
        """Update cached credentials for a member"""
        from integrations.models import JustGoCredentialCache
        
        try:
            # Get mapping
            mapping = JustGoMemberMapping.objects.get(justgo_member_id=member_id)
            
            # Get credentials from JustGo
            credentials_data = self.client.get_member_credentials(member_id)
            
            if credentials_data.get('data'):
                # Clear existing cached credentials
                JustGoCredentialCache.objects.filter(member_mapping=mapping).delete()
                
                # Cache new credentials
                for cred in credentials_data['data']:
                    JustGoCredentialCache.objects.create(
                        member_mapping=mapping,
                        justgo_credential_id=cred.get('credentialId', ''),
                        credential_type=cred.get('type', 'Unknown'),
                        credential_name=cred.get('name', ''),
                        status=cred.get('status', 'Unknown'),
                        issued_date=cred.get('issuedDate'),
                        expiry_date=cred.get('expiryDate'),
                        credential_data=cred
                    )
                
                self.stdout.write(f"    Cached {len(credentials_data['data'])} credentials")
            
        except JustGoMemberMapping.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f"    No mapping found for member: {member_id}")
            )
        except Exception as e:
            raise Exception(f"Failed to update credentials: {e}")

    def get_admin_user(self) -> User:
        """Get an admin user for override operations"""
        admin_user = User.objects.filter(is_staff=True, is_active=True).first()
        if not admin_user:
            raise CommandError("No active admin user found for override operations")
        return admin_user 