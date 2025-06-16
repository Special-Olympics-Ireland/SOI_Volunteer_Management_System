"""
Django management command to test JustGo API integration

This command provides comprehensive testing of the JustGo API client
including authentication, member lookup, credential retrieval, and
data extraction functionality.

Usage:
    python manage.py test_justgo_api
    python manage.py test_justgo_api --member-id ME000001
    python manage.py test_justgo_api --health-check-only
    python manage.py test_justgo_api --verbose
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from integrations.justgo import (
    JustGoAPIClient,
    JustGoCredentials,
    JustGoDataExtractor,
    JustGoAPIError,
    JustGoAuthenticationError,
    JustGoNotFoundError,
    create_justgo_client
)


class Command(BaseCommand):
    help = 'Test JustGo API integration functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--member-id',
            type=str,
            help='Test with specific member ID (MID)',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Test with specific email address',
        )
        parser.add_argument(
            '--health-check-only',
            action='store_true',
            help='Only perform health check',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
        parser.add_argument(
            '--use-test-secret',
            action='store_true',
            help='Use test secret instead of production',
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        try:
            # Initialize client
            client = self._initialize_client(options)
            
            # Perform health check
            self._perform_health_check(client)
            
            if options.get('health_check_only'):
                self.stdout.write(
                    self.style.SUCCESS('✅ Health check completed successfully')
                )
                return
            
            # Test member operations
            if options.get('member_id'):
                self._test_member_by_id(client, options['member_id'])
            elif options.get('email'):
                self._test_member_by_email(client, options['email'])
            else:
                self._run_comprehensive_tests(client)
                
        except JustGoAuthenticationError as e:
            raise CommandError(f'❌ Authentication failed: {e}')
        except JustGoAPIError as e:
            raise CommandError(f'❌ API error: {e}')
        except Exception as e:
            raise CommandError(f'❌ Unexpected error: {e}')

    def _initialize_client(self, options):
        """Initialize JustGo API client"""
        self._log('🔧 Initializing JustGo API client...')
        
        try:
            if options.get('use_test_secret'):
                # Use test credentials
                credentials = JustGoCredentials(
                    secret='test_secret_for_development',
                    base_url='https://test.api.justgo.com'
                )
                client = JustGoAPIClient(credentials)
                self._log('⚠️  Using test credentials')
            else:
                # Use production credentials from settings
                client = create_justgo_client()
                self._log('✅ Using production credentials from settings')
            
            # Check if secret is configured
            if not client.credentials.secret:
                raise CommandError(
                    '❌ No JustGo API secret configured. '
                    'Set JUSTGO_API_SECRET environment variable or use --use-test-secret'
                )
            
            self._log(f'🌐 API Base URL: {client.credentials.base_url}')
            self._log(f'📡 API Version: {client.credentials.api_version}')
            
            return client
            
        except Exception as e:
            raise CommandError(f'Failed to initialize client: {e}')

    def _perform_health_check(self, client):
        """Perform health check"""
        self._log('🏥 Performing health check...')
        
        try:
            health_result = client.health_check()
            
            if health_result['status'] == 'healthy':
                self._log('✅ Health check passed')
                self._log(f'🔐 Authentication: {"✅ Success" if health_result["authenticated"] else "❌ Failed"}')
                if health_result.get('token_expires_at'):
                    self._log(f'⏰ Token expires: {health_result["token_expires_at"]}')
            else:
                self._log('❌ Health check failed')
                self._log(f'🔍 Error: {health_result.get("error", "Unknown error")}')
                raise CommandError('Health check failed')
                
        except Exception as e:
            raise CommandError(f'Health check error: {e}')

    def _test_member_by_id(self, client, member_id):
        """Test member operations with specific MID"""
        self._log(f'👤 Testing member operations for MID: {member_id}')
        
        try:
            # Get complete member journey
            self._log('🔍 Retrieving complete member journey...')
            member_journey = client.get_member_journey(member_id)
            
            # Display results
            self._display_member_results(member_journey)
            
        except JustGoNotFoundError:
            self._log(f'❌ Member not found: {member_id}')
        except Exception as e:
            self._log(f'❌ Error retrieving member {member_id}: {e}')

    def _test_member_by_email(self, client, email):
        """Test member operations with email"""
        self._log(f'📧 Testing member operations for email: {email}')
        
        try:
            # Find member by email
            self._log('🔍 Finding member by email...')
            search_result = client.find_member_by_email(email)
            
            if not search_result.get('data') or len(search_result['data']) == 0:
                self._log(f'❌ No member found with email: {email}')
                return
            
            member_data = search_result['data'][0]
            member_id = member_data.get('memberId')
            mid = member_data.get('mid')
            
            self._log(f'✅ Found member: {mid} ({member_id})')
            
            # Get full member journey
            if mid:
                member_journey = client.get_member_journey(mid)
                self._display_member_results(member_journey)
            
        except Exception as e:
            self._log(f'❌ Error finding member by email {email}: {e}')

    def _run_comprehensive_tests(self, client):
        """Run comprehensive API tests"""
        self._log('🧪 Running comprehensive API tests...')
        
        # Test authentication
        self._test_authentication(client)
        
        # Test data extraction utilities
        self._test_data_extraction()
        
        self._log('✅ Comprehensive tests completed')

    def _test_authentication(self, client):
        """Test authentication functionality"""
        self._log('🔐 Testing authentication...')
        
        try:
            # Test authentication
            auth_result = client.authenticate()
            
            self._log('✅ Authentication successful')
            self._log(f'🎫 Token type: {auth_result.get("tokenType", "Unknown")}')
            self._log(f'⏱️  Expires in: {auth_result.get("expiresIn", "Unknown")} seconds')
            
            # Test authentication status
            is_authenticated = client.is_authenticated()
            self._log(f'🔍 Authentication status: {"✅ Valid" if is_authenticated else "❌ Invalid"}')
            
        except Exception as e:
            self._log(f'❌ Authentication test failed: {e}')

    def _test_data_extraction(self):
        """Test data extraction utilities"""
        self._log('🔧 Testing data extraction utilities...')
        
        try:
            extractor = JustGoDataExtractor()
            
            # Test with sample data
            sample_member_data = {
                'memberId': 'test-member-id',
                'memberDocId': 12345,
                'mid': 'ME000001',
                'bookings': [
                    {'bookingId': 'booking-1', 'eventId': 'event-1', 'ticketId': 'ticket-1'}
                ],
                'awards': [
                    {'credentialId': 'cred-1'}
                ],
                'clubs': [
                    {'clubId': 'club-1'}
                ],
                'memberships': [
                    {'membershipId': 'membership-1'}
                ]
            }
            
            # Extract IDs
            ids = extractor.extract_member_ids(sample_member_data)
            
            self._log('✅ ID extraction test passed')
            self._log(f'🆔 Member ID: {ids.member_id}')
            self._log(f'🔢 MID: {ids.mid}')
            self._log(f'📅 Bookings: {len(ids.booking_ids)}')
            self._log(f'🏆 Credentials: {len(ids.credential_ids)}')
            
            # Test credential processing
            sample_credentials = {
                'data': [
                    {'credentialId': 'cred-1', 'status': 'Active', 'type': 'Medical'},
                    {'credentialId': 'cred-2', 'status': 'Expired', 'type': 'Safeguarding'}
                ]
            }
            
            active_creds = extractor.extract_active_credentials(sample_credentials)
            expired_creds = extractor.extract_expired_credentials(sample_credentials)
            grouped_creds = extractor.group_credentials_by_type(sample_credentials)
            
            self._log('✅ Credential processing test passed')
            self._log(f'✅ Active credentials: {len(active_creds)}')
            self._log(f'❌ Expired credentials: {len(expired_creds)}')
            self._log(f'📊 Credential types: {list(grouped_creds.keys())}')
            
        except Exception as e:
            self._log(f'❌ Data extraction test failed: {e}')

    def _display_member_results(self, member_journey):
        """Display member journey results"""
        self._log('📊 Member Journey Results:')
        self._log('=' * 50)
        
        try:
            # Basic member info
            search_result = member_journey.get('search_result', {})
            detailed_info = member_journey.get('detailed_info', {})
            credentials = member_journey.get('credentials', {})
            extracted_ids = member_journey.get('extracted_ids')
            
            # Display search result
            if search_result.get('data'):
                member_basic = search_result['data'][0]
                self._log(f'👤 Name: {member_basic.get("firstName", "")} {member_basic.get("lastName", "")}')
                self._log(f'🆔 MID: {member_basic.get("mid", "N/A")}')
                self._log(f'📧 Email: {member_basic.get("emailAddress", "N/A")}')
                self._log(f'📱 Phone: {member_basic.get("phoneNumber", "N/A")}')
                self._log(f'📍 County: {member_basic.get("county", "N/A")}')
                self._log(f'📊 Status: {member_basic.get("memberStatus", "N/A")}')
            
            # Display detailed info
            if detailed_info.get('data'):
                member_detail = detailed_info['data']
                
                # Bookings
                bookings = member_detail.get('bookings', [])
                self._log(f'📅 Bookings: {len(bookings)}')
                for i, booking in enumerate(bookings[:3], 1):  # Show first 3
                    self._log(f'  {i}. {booking.get("courseName", "Unknown")} - {booking.get("courseDate", "No date")}')
                
                # Clubs
                clubs = member_detail.get('clubs', [])
                self._log(f'🏛️  Clubs: {len(clubs)}')
                for club in clubs[:3]:  # Show first 3
                    self._log(f'  • {club.get("clubName", "Unknown")} ({club.get("roles", "No role")})')
                
                # Memberships
                memberships = member_detail.get('memberships', [])
                self._log(f'🎫 Memberships: {len(memberships)}')
                for membership in memberships[:3]:  # Show first 3
                    status = membership.get('status', 'Unknown')
                    self._log(f'  • {membership.get("name", "Unknown")} - {status}')
            
            # Display credentials
            if credentials.get('data'):
                creds_data = credentials['data']
                self._log(f'🏆 Total Credentials: {len(creds_data)}')
                
                # Group by status
                active_count = len([c for c in creds_data if c.get('status') == 'Active'])
                expired_count = len([c for c in creds_data if c.get('status') == 'Expired'])
                
                self._log(f'  ✅ Active: {active_count}')
                self._log(f'  ❌ Expired: {expired_count}')
                
                # Show active credentials
                active_creds = [c for c in creds_data if c.get('status') == 'Active']
                for cred in active_creds[:5]:  # Show first 5 active
                    expiry = cred.get('expiryDate', 'No expiry')
                    self._log(f'  • {cred.get("name", "Unknown")} (expires: {expiry})')
            
            # Display extracted IDs summary
            if extracted_ids:
                self._log('🔍 Extracted IDs Summary:')
                self._log(f'  📋 Booking IDs: {len(extracted_ids.booking_ids)}')
                self._log(f'  🎪 Event IDs: {len(extracted_ids.event_ids)}')
                self._log(f'  🎫 Ticket IDs: {len(extracted_ids.ticket_ids)}')
                self._log(f'  🏆 Credential IDs: {len(extracted_ids.credential_ids)}')
                self._log(f'  🏛️  Club IDs: {len(extracted_ids.club_ids)}')
                self._log(f'  🎭 Membership IDs: {len(extracted_ids.membership_ids)}')
            
            self._log('=' * 50)
            
            # Verbose output
            if self.verbose:
                self._log('📄 Raw Data (Verbose Mode):')
                self._log(json.dumps(member_journey, indent=2, default=str))
            
        except Exception as e:
            self._log(f'❌ Error displaying results: {e}')

    def _log(self, message):
        """Log message with appropriate styling"""
        if self.verbosity >= 1:
            # Add timestamp for verbose logging
            if self.verbose:
                timestamp = timezone.now().strftime('%H:%M:%S')
                message = f'[{timestamp}] {message}'
            
            # Style based on message content
            if message.startswith('✅'):
                self.stdout.write(self.style.SUCCESS(message))
            elif message.startswith('❌'):
                self.stdout.write(self.style.ERROR(message))
            elif message.startswith('⚠️'):
                self.stdout.write(self.style.WARNING(message))
            elif message.startswith('🔧') or message.startswith('🔍'):
                self.stdout.write(self.style.HTTP_INFO(message))
            else:
                self.stdout.write(message) 