"""
JustGo API Integration Client

This module provides a comprehensive client for integrating with the JustGo API v2.1.
Supports authentication, rate limiting, member management, credentials, and events.

Based on JustGo API Documentation - June 13, 2025
Base URL: https://api.justgo.com
API Version: v2.1
"""

import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

# Import audit logging utilities
try:
    from common.audit import log_admin_override, log_justgo_sync, AuditEvent
    AUDIT_AVAILABLE = True
except ImportError:
    # Graceful fallback if audit module not available
    AUDIT_AVAILABLE = False
    def log_admin_override(*args, **kwargs):
        pass
    def log_justgo_sync(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)


@dataclass
class JustGoCredentials:
    """JustGo API credentials configuration"""
    secret: str
    base_url: str = "https://api.justgo.com"
    api_version: str = "v2.1"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.5  # Seconds between requests


@dataclass
class JustGoMemberIds:
    """Container for extracted member identifiers"""
    member_id: Optional[str] = None
    member_doc_id: Optional[int] = None
    mid: Optional[str] = None
    candidate_id: Optional[str] = None
    booking_ids: List[str] = None
    event_ids: List[str] = None
    ticket_ids: List[str] = None
    credential_ids: List[str] = None
    club_ids: List[str] = None
    membership_ids: List[str] = None

    def __post_init__(self):
        """Initialize list fields if None"""
        if self.booking_ids is None:
            self.booking_ids = []
        if self.event_ids is None:
            self.event_ids = []
        if self.ticket_ids is None:
            self.ticket_ids = []
        if self.credential_ids is None:
            self.credential_ids = []
        if self.club_ids is None:
            self.club_ids = []
        if self.membership_ids is None:
            self.membership_ids = []


class JustGoAPIError(Exception):
    """Base exception for JustGo API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class JustGoAuthenticationError(JustGoAPIError):
    """Authentication-specific errors"""
    pass


class JustGoRateLimitError(JustGoAPIError):
    """Rate limiting errors"""
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class JustGoTimeoutError(JustGoAPIError):
    """Request timeout errors"""
    pass


class JustGoConnectionError(JustGoAPIError):
    """Connection-related errors"""
    pass


class JustGoNotFoundError(JustGoAPIError):
    """Resource not found errors"""
    pass


class JustGoAPIClient:
    """
    JustGo API Client with comprehensive functionality
    
    Features:
    - Automatic authentication and token management
    - Rate limiting and retry logic
    - Member lookup and management
    - Credential retrieval and validation
    - Event management and booking operations
    - Comprehensive error handling and logging
    """

    def __init__(self, credentials: Optional[JustGoCredentials] = None):
        """
        Initialize JustGo API client
        
        Args:
            credentials: JustGo API credentials. If None, loads from Django settings.
        """
        self.credentials = credentials or self._load_credentials_from_settings()
        self.session = requests.Session()
        self.session.timeout = self.credentials.timeout
        
        # Authentication state
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Rate limiting
        self._last_request_time: float = 0
        self._request_count: int = 0
        
        # Setup session headers
        self.session.headers.update({
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'SOI-Hub-JustGo-Client/1.0'
        })
        
        logger.info(f"JustGo API Client initialized for {self.credentials.base_url}")

    def _load_credentials_from_settings(self) -> JustGoCredentials:
        """Load JustGo credentials from Django settings"""
        try:
            justgo_config = getattr(settings, 'JUSTGO_API', {})
            return JustGoCredentials(
                secret=justgo_config.get('SECRET', ''),
                base_url=justgo_config.get('BASE_URL', 'https://api.justgo.com'),
                api_version=justgo_config.get('API_VERSION', 'v2.1'),
                timeout=justgo_config.get('TIMEOUT', 30),
                max_retries=justgo_config.get('MAX_RETRIES', 3),
                rate_limit_delay=justgo_config.get('RATE_LIMIT_DELAY', 0.5)
            )
        except Exception as e:
            logger.error(f"Failed to load JustGo credentials from settings: {e}")
            raise JustGoAPIError(f"Invalid JustGo configuration: {e}")

    def _get_api_url(self, endpoint: str) -> str:
        """Construct full API URL for endpoint"""
        endpoint = endpoint.lstrip('/')
        return f"{self.credentials.base_url}/api/{self.credentials.api_version}/{endpoint}"

    def _apply_rate_limiting(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.credentials.rate_limit_delay:
            sleep_time = self.credentials.rate_limit_delay - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
        self._request_count += 1

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response with comprehensive error checking
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON response data
            
        Raises:
            JustGoAPIError: For various API errors
        """
        try:
            # Log request details
            logger.debug(f"JustGo API Request: {response.request.method} {response.url}")
            logger.debug(f"JustGo API Response: {response.status_code}")
            
            # Handle HTTP errors
            if response.status_code == 401:
                logger.error("JustGo API authentication failed")
                raise JustGoAuthenticationError("Authentication failed", response.status_code)
            elif response.status_code == 404:
                logger.warning(f"JustGo API resource not found: {response.url}")
                raise JustGoNotFoundError("Resource not found", response.status_code)
            elif response.status_code == 429:
                # Extract retry-after header if available
                retry_after = None
                if 'Retry-After' in response.headers:
                    try:
                        retry_after = int(response.headers['Retry-After'])
                    except ValueError:
                        pass
                elif 'X-RateLimit-Reset' in response.headers:
                    try:
                        reset_time = int(response.headers['X-RateLimit-Reset'])
                        retry_after = max(1, reset_time - int(time.time()))
                    except ValueError:
                        pass
                
                logger.warning(f"JustGo API rate limit exceeded, retry after: {retry_after} seconds")
                raise JustGoRateLimitError("Rate limit exceeded", retry_after=retry_after, status_code=response.status_code)
            elif response.status_code >= 400:
                logger.error(f"JustGo API error: {response.status_code} - {response.text}")
                raise JustGoAPIError(f"API error: {response.status_code}", response.status_code)
            
            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"Failed to parse JustGo API response as JSON: {e}")
                raise JustGoAPIError(f"Invalid JSON response: {e}")
            
            # Check API-level status
            if isinstance(data, dict):
                status_code = data.get('statusCode')
                if status_code and status_code != 200:
                    message = data.get('message', 'Unknown API error')
                    logger.error(f"JustGo API returned error: {status_code} - {message}")
                    raise JustGoAPIError(f"API error: {message}", status_code, data)
            
            logger.debug(f"JustGo API successful response: {len(str(data))} characters")
            return data
            
        except JustGoAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error handling JustGo API response: {e}")
            raise JustGoAPIError(f"Response handling error: {e}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated API request with comprehensive error handling and retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            API response data
            
        Raises:
            JustGoTimeoutError: For timeout errors
            JustGoConnectionError: For connection errors
            JustGoRateLimitError: For rate limiting errors
            JustGoAPIError: For other API errors
        """
        url = self._get_api_url(endpoint)
        
        # Ensure authentication
        self._ensure_authenticated()
        
        # Apply rate limiting
        self._apply_rate_limiting()
        
        # Add authorization header
        if self._access_token:
            self.session.headers['Authorization'] = f'Bearer {self._access_token}'
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.credentials.timeout
        
        # Retry logic with exponential backoff
        last_exception = None
        base_delay = 1.0
        
        for attempt in range(self.credentials.max_retries):
            try:
                logger.debug(f"JustGo API request attempt {attempt + 1}/{self.credentials.max_retries}: {method} {url}")
                
                response = self.session.request(method, url, **kwargs)
                return self._handle_response(response)
                
            except JustGoAuthenticationError:
                # Re-authenticate and retry (don't count against retry limit)
                logger.info("Re-authenticating due to auth error")
                self._access_token = None
                self._token_expires_at = None
                try:
                    self._ensure_authenticated()
                    continue  # Retry immediately after re-auth
                except Exception as auth_error:
                    logger.error(f"Re-authentication failed: {auth_error}")
                    raise JustGoAuthenticationError(f"Re-authentication failed: {auth_error}")
                
            except JustGoRateLimitError as e:
                # Handle rate limiting with exponential backoff
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    wait_time = retry_after
                else:
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                
                logger.warning(f"Rate limited (attempt {attempt + 1}), waiting {wait_time} seconds")
                time.sleep(wait_time)
                last_exception = e
                
            except requests.exceptions.Timeout as e:
                # Handle timeout errors
                logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                last_exception = JustGoTimeoutError(f"Request timeout: {e}", response_data={'timeout': kwargs.get('timeout')})
                
                if attempt < self.credentials.max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(f"Retrying after timeout in {wait_time} seconds")
                    time.sleep(wait_time)
                
            except requests.exceptions.ConnectionError as e:
                # Handle connection errors
                logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                last_exception = JustGoConnectionError(f"Connection error: {e}")
                
                if attempt < self.credentials.max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(f"Retrying after connection error in {wait_time} seconds")
                    time.sleep(wait_time)
                
            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors
                logger.warning(f"HTTP error (attempt {attempt + 1}): {e}")
                last_exception = JustGoAPIError(f"HTTP error: {e}", status_code=e.response.status_code if e.response else None)
                
                # Don't retry on client errors (4xx), but retry on server errors (5xx)
                if e.response and 400 <= e.response.status_code < 500:
                    break  # Don't retry client errors
                elif attempt < self.credentials.max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    time.sleep(wait_time)
                
            except requests.exceptions.RequestException as e:
                # Handle other request errors
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                last_exception = JustGoAPIError(f"Request error: {e}")
                
                if attempt < self.credentials.max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    time.sleep(wait_time)
                
            except JustGoAPIError as e:
                # Handle JustGo-specific errors
                logger.warning(f"JustGo API error (attempt {attempt + 1}): {e}")
                last_exception = e
                
                # Don't retry on certain error types
                if isinstance(e, (JustGoNotFoundError, JustGoAuthenticationError)):
                    break
                elif attempt < self.credentials.max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    time.sleep(wait_time)
                
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                last_exception = JustGoAPIError(f"Unexpected error: {e}")
                
                if attempt < self.credentials.max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    time.sleep(wait_time)
        
        # All retries failed
        if last_exception:
            logger.error(f"All {self.credentials.max_retries} retry attempts failed for {method} {url}")
            raise last_exception
        else:
            raise JustGoAPIError(f"All {self.credentials.max_retries} retry attempts failed")

    def authenticate(self) -> Dict[str, Any]:
        """
        Authenticate with JustGo API and get access token
        
        Returns:
            Authentication response data
            
        Raises:
            JustGoAuthenticationError: If authentication fails
        """
        if not self.credentials.secret:
            raise JustGoAuthenticationError("No API secret provided")
        
        logger.info("Authenticating with JustGo API")
        
        auth_data = {
            "secret": self.credentials.secret
        }
        
        try:
            # Don't use _make_request for auth to avoid circular dependency
            url = self._get_api_url('Auth')
            response = self.session.post(url, json=auth_data)
            
            if response.status_code != 200:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                raise JustGoAuthenticationError(f"Authentication failed: {response.status_code}")
            
            data = response.json()
            
            # Extract token information
            self._access_token = data.get('accessToken')
            expires_in = data.get('expiresIn', 3600)  # Default 1 hour
            
            if not self._access_token:
                raise JustGoAuthenticationError("No access token in response")
            
            # Calculate expiry time (with 5 minute buffer)
            self._token_expires_at = timezone.now() + timedelta(seconds=expires_in - 300)
            
            logger.info(f"JustGo authentication successful, token expires at {self._token_expires_at}")
            
            # Cache token for other instances
            cache.set('justgo_access_token', self._access_token, expires_in - 300)
            cache.set('justgo_token_expires_at', self._token_expires_at, expires_in - 300)
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Network error during authentication: {e}")
            raise JustGoAuthenticationError(f"Network error: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON in authentication response: {e}")
            raise JustGoAuthenticationError(f"Invalid response format: {e}")

    def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        # Check if token is still valid
        if (self._access_token and self._token_expires_at and 
            timezone.now() < self._token_expires_at):
            return
        
        # Try to get cached token
        cached_token = cache.get('justgo_access_token')
        cached_expires = cache.get('justgo_token_expires_at')
        
        if cached_token and cached_expires and timezone.now() < cached_expires:
            self._access_token = cached_token
            self._token_expires_at = cached_expires
            logger.debug("Using cached JustGo access token")
            return
        
        # Need to authenticate
        self.authenticate()

    def is_authenticated(self) -> bool:
        """Check if client is currently authenticated"""
        return (self._access_token is not None and 
                self._token_expires_at is not None and 
                timezone.now() < self._token_expires_at)

    # Member Management Methods
    
    def find_member_by_mid(self, mid: str) -> Dict[str, Any]:
        """
        Find member by Member ID (MID)
        
        Args:
            mid: Member ID (e.g., "15004822")
            
        Returns:
            Member search results
        """
        logger.info(f"Finding member by MID: {mid}")
        return self._make_request('GET', f'Members/FindByAttributes?MID={mid}')

    def get_member_by_id(self, member_id: str) -> Dict[str, Any]:
        """
        Get detailed member information by member GUID
        
        Args:
            member_id: Member GUID
            
        Returns:
            Detailed member information
        """
        logger.info(f"Getting member details for ID: {member_id}")
        return self._make_request('GET', f'Members/{member_id}')

    def find_member_by_email(self, email: str) -> Dict[str, Any]:
        """
        Find member by email address
        
        Args:
            email: Email address
            
        Returns:
            Member search results
        """
        logger.info(f"Finding member by email: {email}")
        return self._make_request('GET', f'Members/FindByAttributes?Email={email}')

    # Credential Management Methods
    
    def get_member_credentials(self, member_id: str) -> Dict[str, Any]:
        """
        Get all credentials for a member
        
        Args:
            member_id: Member GUID
            
        Returns:
            Member credentials data
        """
        logger.info(f"Getting credentials for member: {member_id}")
        return self._make_request('GET', f'Credentials/FindByAttributes?memberId={member_id}')

    # Event Management Methods
    
    def find_event_candidates(self, event_id: str) -> Dict[str, Any]:
        """
        Find candidates for a specific event
        
        Args:
            event_id: Event GUID
            
        Returns:
            Event candidates data
        """
        logger.info(f"Finding candidates for event: {event_id}")
        return self._make_request('GET', f'Events/Candidate/FindByAttributes?eventID={event_id}')

    def update_candidate_status(self, booking_id: str, status: str, issue_awards: bool = False) -> Dict[str, Any]:
        """
        Update a candidate's status for an event booking
        
        Args:
            booking_id: Booking GUID
            status: New status (e.g., "completed")
            issue_awards: Whether to issue awards
            
        Returns:
            Update response data
        """
        logger.info(f"Updating candidate status for booking {booking_id}: {status}")
        
        data = {
            "status": status,
            "issueAwards": issue_awards
        }
        
        return self._make_request('PUT', f'Events/Candidates/{booking_id}', json=data)

    def add_candidate_to_event(self, event_id: str, ticket_id: str, candidate_id: str) -> Dict[str, Any]:
        """
        Add a candidate to an event
        
        Args:
            event_id: Event GUID
            ticket_id: Ticket GUID
            candidate_id: Candidate/Member GUID
            
        Returns:
            Addition response data
        """
        logger.info(f"Adding candidate {candidate_id} to event {event_id}")
        
        data = {
            "ticketId": ticket_id,
            "candidateId": candidate_id
        }
        
        return self._make_request('POST', f'Events/{event_id}/Candidates', json=data)

    # Profile Creation Methods
    
    def create_member_profile(self, member_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new member profile in JustGo
        
        ⚠️ WARNING: This is a WRITE operation that modifies live JustGo data!
        Only use in development/testing environments.
        
        Args:
            member_data: Dictionary containing member information
                Required fields: firstName, lastName, emailAddress, dateOfBirth
                Optional fields: phoneNumber, address1, address2, county, country, etc.
                
        Returns:
            Creation response data
        """
        # SAFETY CHECK: Prevent accidental production writes
        if getattr(settings, 'JUSTGO_READONLY_MODE', True):
            raise JustGoAPIError(
                "SAFETY: Profile creation is disabled in read-only mode. "
                "Set JUSTGO_READONLY_MODE=False in settings to enable writes."
            )
        
        logger.warning(f"⚠️ WRITE OPERATION: Creating new member profile for: {member_data.get('emailAddress', 'Unknown')}")
        
        # Validate required fields
        required_fields = ['firstName', 'lastName', 'emailAddress', 'dateOfBirth']
        missing_fields = [field for field in required_fields if not member_data.get(field)]
        
        if missing_fields:
            raise JustGoAPIError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Format data for JustGo API
        formatted_data = self._format_member_data_for_creation(member_data)
        
        return self._make_request('POST', 'Members', json=formatted_data)

    def _format_member_data_for_creation(self, member_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format member data for JustGo API creation
        
        Args:
            member_data: Raw member data
            
        Returns:
            Formatted data for API
        """
        # Map our field names to JustGo field names
        field_mapping = {
            'first_name': 'firstName',
            'last_name': 'lastName',
            'email': 'emailAddress',
            'email_address': 'emailAddress',
            'phone': 'phoneNumber',
            'phone_number': 'phoneNumber',
            'date_of_birth': 'dateOfBirth',
            'dob': 'dateOfBirth',
            'address_line_1': 'address1',
            'address_line_2': 'address2',
            'post_code': 'postCode',
            'postal_code': 'postCode',
            'zip_code': 'postCode',
        }
        
        formatted_data = {}
        
        # Apply field mapping
        for key, value in member_data.items():
            if value is not None and value != '':
                mapped_key = field_mapping.get(key, key)
                formatted_data[mapped_key] = value
        
        # Set default values
        defaults = {
            'country': 'Ireland',
            'memberStatus': 'Pending',
            'gender': member_data.get('gender', 'Not Specified')
        }
        
        for key, default_value in defaults.items():
            if key not in formatted_data:
                formatted_data[key] = default_value
        
        return formatted_data

    def update_member_profile(self, member_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing member profile
        
        ⚠️ WARNING: This is a WRITE operation that modifies live JustGo data!
        Only use in development/testing environments.
        
        Args:
            member_id: Member GUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Update response data
        """
        # SAFETY CHECK: Prevent accidental production writes
        if getattr(settings, 'JUSTGO_READONLY_MODE', True):
            raise JustGoAPIError(
                "SAFETY: Profile updates are disabled in read-only mode. "
                "Set JUSTGO_READONLY_MODE=False in settings to enable writes."
            )
        
        logger.warning(f"⚠️ WRITE OPERATION: Updating member profile: {member_id}")
        
        formatted_data = self._format_member_data_for_creation(update_data)
        
        return self._make_request('PUT', f'Members/{member_id}', json=formatted_data)

    # Synchronization Methods
    
    def sync_member_to_local(self, mid: str, local_user_model) -> Dict[str, Any]:
        """
        Synchronize JustGo member data to local database
        
        Args:
            mid: Member ID to sync
            local_user_model: Django User model class
            
        Returns:
            Synchronization results
        """
        logger.info(f"Syncing member {mid} to local database")
        
        try:
            # Get complete member journey from JustGo
            member_journey = self.get_member_journey(mid)
            
            # Extract member data
            search_result = member_journey.get('search_result', {})
            detailed_info = member_journey.get('detailed_info', {})
            credentials = member_journey.get('credentials', {})
            
            if not search_result.get('data'):
                raise JustGoNotFoundError(f"Member not found: {mid}")
            
            member_basic = search_result['data'][0]
            member_detail = detailed_info.get('data', {})
            
            # Map JustGo data to local model fields
            local_data = self._map_justgo_to_local_fields(member_basic, member_detail)
            
            # Create or update local user
            user, created = local_user_model.objects.update_or_create(
                email=local_data['email'],
                defaults=local_data
            )
            
            # Store JustGo metadata
            user.justgo_member_id = member_basic.get('memberId')
            user.justgo_mid = member_basic.get('mid')
            user.justgo_last_sync = timezone.now()
            user.save()
            
            # Process credentials
            credential_summary = self._process_member_credentials(credentials)
            
            sync_result = {
                'status': 'success',
                'action': 'created' if created else 'updated',
                'user_id': user.id,
                'justgo_member_id': member_basic.get('memberId'),
                'justgo_mid': member_basic.get('mid'),
                'credentials_processed': len(credential_summary.get('all_credentials', [])),
                'active_credentials': len(credential_summary.get('active_credentials', [])),
                'expired_credentials': len(credential_summary.get('expired_credentials', [])),
                'sync_timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Successfully synced member {mid} - {sync_result['action']}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Failed to sync member {mid}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'justgo_mid': mid,
                'sync_timestamp': timezone.now().isoformat()
            }

    def sync_local_to_justgo(self, user, create_if_missing: bool = False) -> Dict[str, Any]:
        """
        Synchronize local user data to JustGo
        
        ⚠️ WARNING: This is a WRITE operation that modifies live JustGo data!
        Only use in development/testing environments.
        
        Args:
            user: Local Django user instance
            create_if_missing: Whether to create new profile if not found
            
        Returns:
            Synchronization results
        """
        # SAFETY CHECK: Prevent accidental production writes
        if getattr(settings, 'JUSTGO_READONLY_MODE', True):
            raise JustGoAPIError(
                "SAFETY: Local to JustGo sync is disabled in read-only mode. "
                "Set JUSTGO_READONLY_MODE=False in settings to enable writes."
            )
        
        logger.warning(f"⚠️ WRITE OPERATION: Syncing local user {user.email} to JustGo")
        
        try:
            # Check if user has JustGo member ID
            justgo_member_id = getattr(user, 'justgo_member_id', None)
            
            if justgo_member_id:
                # Update existing profile
                update_data = self._map_local_to_justgo_fields(user)
                result = self.update_member_profile(justgo_member_id, update_data)
                
                sync_result = {
                    'status': 'success',
                    'action': 'updated',
                    'justgo_member_id': justgo_member_id,
                    'local_user_id': user.id,
                    'sync_timestamp': timezone.now().isoformat()
                }
                
            else:
                # Try to find existing profile by email
                try:
                    search_result = self.find_member_by_email(user.email)
                    
                    if search_result.get('data') and len(search_result['data']) > 0:
                        # Found existing profile, link it
                        member_data = search_result['data'][0]
                        user.justgo_member_id = member_data.get('memberId')
                        user.justgo_mid = member_data.get('mid')
                        user.save()
                        
                        sync_result = {
                            'status': 'success',
                            'action': 'linked',
                            'justgo_member_id': member_data.get('memberId'),
                            'justgo_mid': member_data.get('mid'),
                            'local_user_id': user.id,
                            'sync_timestamp': timezone.now().isoformat()
                        }
                        
                    elif create_if_missing:
                        # Create new profile
                        create_data = self._map_local_to_justgo_fields(user)
                        result = self.create_member_profile(create_data)
                        
                        # Update local user with JustGo IDs
                        if result.get('data'):
                            user.justgo_member_id = result['data'].get('memberId')
                            user.justgo_mid = result['data'].get('mid')
                            user.save()
                        
                        sync_result = {
                            'status': 'success',
                            'action': 'created',
                            'justgo_member_id': result.get('data', {}).get('memberId'),
                            'justgo_mid': result.get('data', {}).get('mid'),
                            'local_user_id': user.id,
                            'sync_timestamp': timezone.now().isoformat()
                        }
                        
                    else:
                        sync_result = {
                            'status': 'not_found',
                            'message': 'No JustGo profile found and create_if_missing=False',
                            'local_user_id': user.id,
                            'sync_timestamp': timezone.now().isoformat()
                        }
                        
                except JustGoNotFoundError:
                    if create_if_missing:
                        # Create new profile
                        create_data = self._map_local_to_justgo_fields(user)
                        result = self.create_member_profile(create_data)
                        
                        sync_result = {
                            'status': 'success',
                            'action': 'created',
                            'justgo_member_id': result.get('data', {}).get('memberId'),
                            'local_user_id': user.id,
                            'sync_timestamp': timezone.now().isoformat()
                        }
                    else:
                        sync_result = {
                            'status': 'not_found',
                            'message': 'No JustGo profile found and create_if_missing=False',
                            'local_user_id': user.id,
                            'sync_timestamp': timezone.now().isoformat()
                        }
            
            logger.info(f"Successfully synced local user {user.email} - {sync_result.get('action', 'no action')}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Failed to sync local user {user.email}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'local_user_id': user.id,
                'sync_timestamp': timezone.now().isoformat()
            }

    def _map_justgo_to_local_fields(self, member_basic: Dict, member_detail: Dict) -> Dict[str, Any]:
        """
        Map JustGo member data to local model fields
        
        Args:
            member_basic: Basic member data from search
            member_detail: Detailed member data
            
        Returns:
            Dictionary with local model field mappings
        """
        return {
            'email': member_basic.get('emailAddress', ''),
            'first_name': member_basic.get('firstName', ''),
            'last_name': member_basic.get('lastName', ''),
            'phone_number': member_basic.get('phoneNumber', ''),
            'date_of_birth': member_basic.get('dob'),
            'gender': member_basic.get('gender', ''),
            'address_line_1': member_basic.get('address1', ''),
            'address_line_2': member_basic.get('address2', ''),
            'county': member_basic.get('county', ''),
            'country': member_basic.get('country', 'Ireland'),
            'post_code': member_basic.get('postCode', ''),
            'town': member_basic.get('town', ''),
            'is_active': member_basic.get('memberStatus') == 'Registered',
        }

    def _map_local_to_justgo_fields(self, user) -> Dict[str, Any]:
        """
        Map local user data to JustGo fields
        
        Args:
            user: Local Django user instance
            
        Returns:
            Dictionary with JustGo field mappings
        """
        data = {
            'firstName': user.first_name,
            'lastName': user.last_name,
            'emailAddress': user.email,
        }
        
        # Add optional fields if they exist
        optional_fields = {
            'phoneNumber': getattr(user, 'phone_number', None),
            'dateOfBirth': getattr(user, 'date_of_birth', None),
            'gender': getattr(user, 'gender', None),
            'address1': getattr(user, 'address_line_1', None),
            'address2': getattr(user, 'address_line_2', None),
            'county': getattr(user, 'county', None),
            'country': getattr(user, 'country', 'Ireland'),
            'postCode': getattr(user, 'post_code', None),
            'town': getattr(user, 'town', None),
        }
        
        for key, value in optional_fields.items():
            if value:
                data[key] = str(value)
        
        return data

    def _process_member_credentials(self, credentials_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process member credentials for local storage
        
        Args:
            credentials_data: Credentials data from JustGo
            
        Returns:
            Processed credential summary
        """
        extractor = JustGoDataExtractor()
        
        all_credentials = credentials_data.get('data', [])
        active_credentials = extractor.extract_active_credentials(credentials_data)
        expired_credentials = extractor.extract_expired_credentials(credentials_data)
        grouped_credentials = extractor.group_credentials_by_type(credentials_data)
        expiring_soon = extractor.check_credential_expiry(credentials_data, 30)
        
        return {
            'all_credentials': all_credentials,
            'active_credentials': active_credentials,
            'expired_credentials': expired_credentials,
            'grouped_credentials': grouped_credentials,
            'expiring_soon': expiring_soon,
            'summary': {
                'total': len(all_credentials),
                'active': len(active_credentials),
                'expired': len(expired_credentials),
                'expiring_soon': len(expiring_soon),
                'types': list(grouped_credentials.keys())
            }
        }

    # Credential Validation Methods
    
    def validate_member_credentials_for_role(self, member_id: str, role_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate member credentials against role requirements
        
        Args:
            member_id: Member GUID or MID
            role_requirements: Dictionary of role credential requirements
                Example: {
                    'required_credentials': ['Garda Vetting', 'First Aid'],
                    'minimum_age': 18,
                    'valid_until': '2026-06-21'
                }
                
        Returns:
            Validation results with pass/fail status and details
        """
        logger.info(f"Validating credentials for member {member_id}")
        
        try:
            # Get member credentials
            if len(member_id) < 10:  # Assume it's a MID
                member_journey = self.get_member_journey(member_id)
                credentials_data = member_journey.get('credentials', {})
                member_data = member_journey.get('search_result', {}).get('data', [{}])[0]
            else:  # Assume it's a member GUID
                credentials_data = self.get_member_credentials(member_id)
                member_data = self.get_member_by_id(member_id).get('data', {})
            
            # Process credentials
            extractor = JustGoDataExtractor()
            active_credentials = extractor.extract_active_credentials(credentials_data)
            grouped_credentials = extractor.group_credentials_by_type(credentials_data)
            expiring_soon = extractor.check_credential_expiry(credentials_data, 30)
            
            # Validate requirements
            validation_results = {
                'member_id': member_id,
                'validation_timestamp': timezone.now().isoformat(),
                'overall_status': 'pass',
                'requirements_met': [],
                'requirements_failed': [],
                'warnings': [],
                'credential_summary': {
                    'total_active': len(active_credentials),
                    'expiring_soon': len(expiring_soon),
                    'types_available': list(grouped_credentials.keys())
                }
            }
            
            # Check required credentials
            required_credentials = role_requirements.get('required_credentials', [])
            for required_cred in required_credentials:
                found_active = False
                
                for cred in active_credentials:
                    if required_cred.lower() in cred.get('name', '').lower():
                        found_active = True
                        validation_results['requirements_met'].append({
                            'requirement': required_cred,
                            'status': 'met',
                            'credential_name': cred.get('name'),
                            'expiry_date': cred.get('expiryDate'),
                            'credential_id': cred.get('credentialId')
                        })
                        break
                
                if not found_active:
                    validation_results['requirements_failed'].append({
                        'requirement': required_cred,
                        'status': 'missing',
                        'message': f'Required credential "{required_cred}" not found or expired'
                    })
                    validation_results['overall_status'] = 'fail'
            
            # Check age requirement
            minimum_age = role_requirements.get('minimum_age')
            if minimum_age and member_data.get('dob'):
                try:
                    from datetime import datetime
                    dob = datetime.strptime(member_data['dob'], '%Y-%m-%d').date()
                    age = (timezone.now().date() - dob).days // 365
                    
                    if age >= minimum_age:
                        validation_results['requirements_met'].append({
                            'requirement': f'Minimum age {minimum_age}',
                            'status': 'met',
                            'actual_age': age
                        })
                    else:
                        validation_results['requirements_failed'].append({
                            'requirement': f'Minimum age {minimum_age}',
                            'status': 'failed',
                            'actual_age': age,
                            'message': f'Member is {age} years old, minimum required is {minimum_age}'
                        })
                        validation_results['overall_status'] = 'fail'
                        
                except ValueError:
                    validation_results['warnings'].append({
                        'type': 'age_validation',
                        'message': 'Could not parse date of birth for age validation'
                    })
            
            # Check credential expiry warnings
            valid_until = role_requirements.get('valid_until')
            if valid_until:
                try:
                    valid_until_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
                    
                    for cred in expiring_soon:
                        expiry_date = datetime.strptime(cred.get('expiryDate', ''), '%Y-%m-%d').date()
                        if expiry_date < valid_until_date:
                            validation_results['warnings'].append({
                                'type': 'credential_expiry',
                                'credential_name': cred.get('name'),
                                'expiry_date': cred.get('expiryDate'),
                                'message': f'Credential expires before role end date ({valid_until})'
                            })
                            
                except ValueError:
                    validation_results['warnings'].append({
                        'type': 'date_validation',
                        'message': 'Could not parse valid_until date for expiry checking'
                    })
            
            logger.info(f"Credential validation completed for {member_id}: {validation_results['overall_status']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Credential validation failed for {member_id}: {e}")
            return {
                'member_id': member_id,
                'validation_timestamp': timezone.now().isoformat(),
                'overall_status': 'error',
                'error': str(e),
                'requirements_met': [],
                'requirements_failed': [],
                'warnings': []
            }

    def get_credential_expiry_report(self, member_ids: List[str], days_ahead: int = 90) -> Dict[str, Any]:
        """
        Generate credential expiry report for multiple members
        
        Args:
            member_ids: List of member IDs (MIDs or GUIDs)
            days_ahead: Number of days to look ahead for expiry
            
        Returns:
            Comprehensive expiry report
        """
        logger.info(f"Generating credential expiry report for {len(member_ids)} members")
        
        report = {
            'report_timestamp': timezone.now().isoformat(),
            'days_ahead': days_ahead,
            'total_members': len(member_ids),
            'members_processed': 0,
            'members_with_expiring_credentials': 0,
            'total_expiring_credentials': 0,
            'member_reports': [],
            'summary_by_credential_type': {},
            'errors': []
        }
        
        extractor = JustGoDataExtractor()
        
        for member_id in member_ids:
            try:
                # Get member credentials
                if len(member_id) < 10:  # MID
                    member_journey = self.get_member_journey(member_id)
                    credentials_data = member_journey.get('credentials', {})
                    member_name = f"{member_journey.get('search_result', {}).get('data', [{}])[0].get('firstName', '')} {member_journey.get('search_result', {}).get('data', [{}])[0].get('lastName', '')}"
                else:  # GUID
                    credentials_data = self.get_member_credentials(member_id)
                    member_detail = self.get_member_by_id(member_id).get('data', {})
                    member_name = f"{member_detail.get('firstName', '')} {member_detail.get('lastName', '')}"
                
                # Check for expiring credentials
                expiring_credentials = extractor.check_credential_expiry(credentials_data, days_ahead)
                
                if expiring_credentials:
                    report['members_with_expiring_credentials'] += 1
                    report['total_expiring_credentials'] += len(expiring_credentials)
                    
                    member_report = {
                        'member_id': member_id,
                        'member_name': member_name.strip(),
                        'expiring_credentials': expiring_credentials,
                        'expiring_count': len(expiring_credentials)
                    }
                    
                    report['member_reports'].append(member_report)
                    
                    # Update summary by credential type
                    for cred in expiring_credentials:
                        cred_type = cred.get('type', 'Unknown')
                        if cred_type not in report['summary_by_credential_type']:
                            report['summary_by_credential_type'][cred_type] = {
                                'count': 0,
                                'members': []
                            }
                        
                        report['summary_by_credential_type'][cred_type]['count'] += 1
                        if member_id not in report['summary_by_credential_type'][cred_type]['members']:
                            report['summary_by_credential_type'][cred_type]['members'].append(member_id)
                
                report['members_processed'] += 1
                
                # Rate limiting
                self._apply_rate_limiting()
                
            except Exception as e:
                logger.error(f"Error processing member {member_id}: {e}")
                report['errors'].append({
                    'member_id': member_id,
                    'error': str(e)
                })
        
        logger.info(f"Credential expiry report completed: {report['members_with_expiring_credentials']} members with expiring credentials")
        return report

    # High-level workflow methods
    
    def get_member_journey(self, mid: str) -> Dict[str, Any]:
        """
        Complete member journey: find member, get details, and credentials
        
        Args:
            mid: Member ID
            
        Returns:
            Complete member information including:
            - search_result: Initial search result
            - detailed_info: Detailed member information
            - credentials: Member credentials
            - extracted_ids: Extracted identifiers
        """
        logger.info(f"Starting complete member journey for MID: {mid}")
        
        try:
            # Step 1: Find member by MID
            search_result = self.find_member_by_mid(mid)
            
            # Extract member ID from search result
            if not search_result.get('data') or len(search_result['data']) == 0:
                raise JustGoNotFoundError(f"Member not found with MID: {mid}")
            
            member_data = search_result['data'][0]
            member_id = member_data.get('memberId')
            
            if not member_id:
                raise JustGoAPIError("No member ID found in search result")
            
            # Step 2: Get detailed member information
            detailed_info = self.get_member_by_id(member_id)
            
            # Step 3: Get member credentials
            credentials = self.get_member_credentials(member_id)
            
            # Step 4: Extract all identifiers
            extractor = JustGoDataExtractor()
            extracted_ids = extractor.extract_member_ids(detailed_info.get('data', {}))
            
            result = {
                'search_result': search_result,
                'detailed_info': detailed_info,
                'credentials': credentials,
                'extracted_ids': extracted_ids
            }
            
            logger.info(f"Member journey completed successfully for MID: {mid}")
            return result
            
        except Exception as e:
            logger.error(f"Member journey failed for MID {mid}: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check by attempting authentication
        
        Returns:
            Health check results
        """
        try:
            auth_result = self.authenticate()
            return {
                'status': 'healthy',
                'authenticated': True,
                'timestamp': timezone.now().isoformat(),
                'token_expires_at': self._token_expires_at.isoformat() if self._token_expires_at else None
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'authenticated': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }

    # Admin Override Methods
    def create_member_profile_with_override(self, member_data: Dict[str, Any], admin_user, 
                                          justification: str, request=None) -> Dict[str, Any]:
        """
        Create member profile with admin override (bypasses read-only mode)
        
        Args:
            member_data: Member data for profile creation
            admin_user: Admin user performing the override
            justification: Justification for the override
            request: HTTP request object for audit logging
            
        Returns:
            Profile creation result with override audit trail
        """
        if not admin_user or not admin_user.is_staff:
            raise JustGoAPIError("Only staff users can perform admin overrides")
        
        logger.warning(f"⚠️ ADMIN OVERRIDE: Profile creation by {admin_user.email}")
        
        # Log the admin override
        if AUDIT_AVAILABLE and request:
            log_admin_override(
                admin_user=admin_user,
                request=request,
                override_type='justgo_profile_creation',
                resource_type='justgo_member',
                resource_id=member_data.get('emailAddress', 'unknown'),
                justification=justification,
                new_value=member_data
            )
        
        # Temporarily bypass read-only mode for this operation
        original_readonly = getattr(settings, 'JUSTGO_READONLY_MODE', True)
        try:
            # Override read-only mode
            settings.JUSTGO_READONLY_MODE = False
            
            # Create the profile
            result = self.create_member_profile(member_data)
            
            # Add override metadata to result
            result['admin_override'] = {
                'performed_by': admin_user.email,
                'justification': justification,
                'timestamp': timezone.now().isoformat(),
                'override_type': 'profile_creation'
            }
            
            logger.info(f"Admin override profile creation successful for {member_data.get('emailAddress')}")
            return result
            
        finally:
            # Restore original read-only mode
            settings.JUSTGO_READONLY_MODE = original_readonly

    def update_member_profile_with_override(self, member_id: str, update_data: Dict[str, Any], 
                                          admin_user, justification: str, request=None) -> Dict[str, Any]:
        """
        Update member profile with admin override (bypasses read-only mode)
        
        Args:
            member_id: JustGo member ID
            update_data: Data to update
            admin_user: Admin user performing the override
            justification: Justification for the override
            request: HTTP request object for audit logging
            
        Returns:
            Profile update result with override audit trail
        """
        if not admin_user or not admin_user.is_staff:
            raise JustGoAPIError("Only staff users can perform admin overrides")
        
        logger.warning(f"⚠️ ADMIN OVERRIDE: Profile update by {admin_user.email}")
        
        # Get original values for audit trail
        try:
            original_data = self.get_member_by_id(member_id)
        except Exception:
            original_data = None
        
        # Log the admin override
        if AUDIT_AVAILABLE and request:
            log_admin_override(
                admin_user=admin_user,
                request=request,
                override_type='justgo_profile_update',
                resource_type='justgo_member',
                resource_id=member_id,
                justification=justification,
                original_value=original_data,
                new_value=update_data
            )
        
        # Temporarily bypass read-only mode for this operation
        original_readonly = getattr(settings, 'JUSTGO_READONLY_MODE', True)
        try:
            # Override read-only mode
            settings.JUSTGO_READONLY_MODE = False
            
            # Update the profile
            result = self.update_member_profile(member_id, update_data)
            
            # Add override metadata to result
            result['admin_override'] = {
                'performed_by': admin_user.email,
                'justification': justification,
                'timestamp': timezone.now().isoformat(),
                'override_type': 'profile_update',
                'original_data': original_data
            }
            
            logger.info(f"Admin override profile update successful for member {member_id}")
            return result
            
        finally:
            # Restore original read-only mode
            settings.JUSTGO_READONLY_MODE = original_readonly

    def sync_with_override(self, sync_type: str, admin_user, justification: str, 
                          request=None, **sync_kwargs) -> Dict[str, Any]:
        """
        Perform synchronization with admin override (bypasses read-only mode)
        
        Args:
            sync_type: Type of sync ('local_to_justgo' or 'justgo_to_local')
            admin_user: Admin user performing the override
            justification: Justification for the override
            request: HTTP request object for audit logging
            **sync_kwargs: Additional arguments for sync operation
            
        Returns:
            Sync result with override audit trail
        """
        if not admin_user or not admin_user.is_staff:
            raise JustGoAPIError("Only staff users can perform admin overrides")
        
        logger.warning(f"⚠️ ADMIN OVERRIDE: {sync_type} sync by {admin_user.email}")
        
        # Log the admin override
        if AUDIT_AVAILABLE and request:
            log_admin_override(
                admin_user=admin_user,
                request=request,
                override_type=f'justgo_{sync_type}_sync',
                resource_type='justgo_sync',
                resource_id=f"{sync_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                justification=justification,
                new_value=sync_kwargs
            )
        
        # Temporarily bypass read-only mode for this operation
        original_readonly = getattr(settings, 'JUSTGO_READONLY_MODE', True)
        try:
            # Override read-only mode
            settings.JUSTGO_READONLY_MODE = False
            
            # Perform the sync
            if sync_type == 'local_to_justgo':
                result = self.sync_local_to_justgo(**sync_kwargs)
            elif sync_type == 'justgo_to_local':
                result = self.sync_member_to_local(**sync_kwargs)
            else:
                raise JustGoAPIError(f"Unknown sync type: {sync_type}")
            
            # Add override metadata to result
            result['admin_override'] = {
                'performed_by': admin_user.email,
                'justification': justification,
                'timestamp': timezone.now().isoformat(),
                'override_type': f'{sync_type}_sync'
            }
            
            # Log sync completion
            if AUDIT_AVAILABLE:
                log_justgo_sync(
                    user=admin_user,
                    sync_type=sync_type,
                    success=result.get('status') == 'success',
                    records_processed=1,
                    errors=result.get('errors', [])
                )
            
            logger.info(f"Admin override {sync_type} sync successful")
            return result
            
        finally:
            # Restore original read-only mode
            settings.JUSTGO_READONLY_MODE = original_readonly

    def bypass_credential_validation_with_override(self, member_id: str, role_requirements: Dict[str, Any],
                                                 admin_user, justification: str, request=None) -> Dict[str, Any]:
        """
        Bypass credential validation with admin override
        
        Args:
            member_id: JustGo member ID
            role_requirements: Role requirements to bypass
            admin_user: Admin user performing the override
            justification: Justification for the override
            request: HTTP request object for audit logging
            
        Returns:
            Validation result with override approval
        """
        if not admin_user or not admin_user.is_staff:
            raise JustGoAPIError("Only staff users can perform admin overrides")
        
        logger.warning(f"⚠️ ADMIN OVERRIDE: Credential validation bypass by {admin_user.email}")
        
        # Get actual validation results first
        actual_validation = self.validate_member_credentials_for_role(member_id, role_requirements)
        
        # Log the admin override
        if AUDIT_AVAILABLE and request:
            log_admin_override(
                admin_user=admin_user,
                request=request,
                override_type='justgo_credential_bypass',
                resource_type='justgo_validation',
                resource_id=f"{member_id}_{role_requirements.get('role_name', 'unknown')}",
                justification=justification,
                original_value=actual_validation,
                new_value={'validation_bypassed': True}
            )
        
        # Create override result
        override_result = {
            'validation_status': 'passed_with_override',
            'member_id': member_id,
            'role_requirements': role_requirements,
            'actual_validation': actual_validation,
            'admin_override': {
                'performed_by': admin_user.email,
                'justification': justification,
                'timestamp': timezone.now().isoformat(),
                'override_type': 'credential_validation_bypass'
            },
            'requirements_met': True,  # Override makes this true
            'validation_passed': True,  # Override makes this true
            'warnings': [
                'ADMIN OVERRIDE: Credential requirements bypassed by administrative decision'
            ],
            'override_details': {
                'bypassed_requirements': actual_validation.get('failed_requirements', []),
                'missing_credentials': actual_validation.get('missing_credentials', []),
                'expired_credentials': actual_validation.get('expired_credentials', [])
            }
        }
        
        logger.info(f"Admin override credential validation bypass for member {member_id}")
        return override_result

    # Membership Type Handling Methods
    def get_member_memberships(self, member_id: str) -> Dict[str, Any]:
        """
        Get all memberships for a member
        
        Args:
            member_id: JustGo member ID
            
        Returns:
            Member memberships data
        """
        logger.info(f"Getting memberships for member: {member_id}")
        
        try:
            # Get detailed member info which includes memberships
            member_data = self.get_member_by_id(member_id)
            
            if not member_data.get('data'):
                return {'memberships': [], 'total_count': 0}
            
            memberships = member_data['data'].get('memberships', [])
            
            # Process and categorize memberships
            processed_memberships = []
            for membership in memberships:
                processed_membership = self._process_membership_data(membership)
                processed_memberships.append(processed_membership)
            
            return {
                'memberships': processed_memberships,
                'total_count': len(processed_memberships),
                'member_id': member_id,
                'retrieved_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get memberships for member {member_id}: {e}")
            raise JustGoAPIError(f"Failed to retrieve memberships: {e}")

    def _process_membership_data(self, membership: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and standardize membership data
        
        Args:
            membership: Raw membership data from JustGo
            
        Returns:
            Processed membership data
        """
        return {
            'membership_id': membership.get('membershipId'),
            'membership_type': membership.get('membershipType', 'Unknown'),
            'club_id': membership.get('clubId'),
            'club_name': membership.get('clubName', ''),
            'status': membership.get('status', 'Unknown'),
            'start_date': membership.get('startDate'),
            'end_date': membership.get('endDate'),
            'is_active': membership.get('status') == 'Active',
            'membership_category': self._categorize_membership_type(membership.get('membershipType', '')),
            'raw_data': membership
        }

    def _categorize_membership_type(self, membership_type: str) -> str:
        """
        Categorize membership type into standard categories
        
        Args:
            membership_type: Raw membership type from JustGo
            
        Returns:
            Standardized membership category
        """
        membership_type_lower = membership_type.lower()
        
        # Define membership categories
        if 'volunteer' in membership_type_lower:
            return 'Volunteer'
        elif 'event' in membership_type_lower or 'games' in membership_type_lower:
            return 'Event Only'
        elif 'auxiliary' in membership_type_lower or 'support' in membership_type_lower:
            return 'Auxiliary'
        elif 'athlete' in membership_type_lower or 'competitor' in membership_type_lower:
            return 'Athlete'
        elif 'coach' in membership_type_lower or 'official' in membership_type_lower:
            return 'Official'
        elif 'family' in membership_type_lower or 'carer' in membership_type_lower:
            return 'Family/Carer'
        else:
            return 'Other'

    def validate_membership_for_role(self, member_id: str, role_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate member's membership types against role requirements
        
        Args:
            member_id: JustGo member ID
            role_requirements: Role requirements including membership types
            
        Returns:
            Validation results
        """
        logger.info(f"Validating membership for member {member_id} against role requirements")
        
        try:
            # Get member memberships
            memberships_data = self.get_member_memberships(member_id)
            memberships = memberships_data.get('memberships', [])
            
            # Extract required membership types
            required_types = role_requirements.get('required_membership_types', [])
            allowed_types = role_requirements.get('allowed_membership_types', [])
            excluded_types = role_requirements.get('excluded_membership_types', [])
            
            # Get member's active membership types
            active_memberships = [m for m in memberships if m.get('is_active', False)]
            member_types = [m.get('membership_category', 'Other') for m in active_memberships]
            member_raw_types = [m.get('membership_type', '') for m in active_memberships]
            
            validation_result = {
                'member_id': member_id,
                'validation_passed': True,
                'requirements_met': True,
                'active_memberships': active_memberships,
                'member_membership_types': member_types,
                'member_raw_types': member_raw_types,
                'required_types': required_types,
                'allowed_types': allowed_types,
                'excluded_types': excluded_types,
                'validation_details': [],
                'warnings': [],
                'errors': []
            }
            
            # Check required membership types
            if required_types:
                missing_required = []
                for required_type in required_types:
                    if required_type not in member_types:
                        missing_required.append(required_type)
                
                if missing_required:
                    validation_result['validation_passed'] = False
                    validation_result['requirements_met'] = False
                    validation_result['errors'].append(
                        f"Missing required membership types: {', '.join(missing_required)}"
                    )
                    validation_result['validation_details'].append({
                        'check': 'required_membership_types',
                        'status': 'failed',
                        'missing_types': missing_required
                    })
                else:
                    validation_result['validation_details'].append({
                        'check': 'required_membership_types',
                        'status': 'passed'
                    })
            
            # Check allowed membership types (if specified)
            if allowed_types:
                invalid_types = []
                for member_type in member_types:
                    if member_type not in allowed_types:
                        invalid_types.append(member_type)
                
                if invalid_types:
                    validation_result['validation_passed'] = False
                    validation_result['requirements_met'] = False
                    validation_result['errors'].append(
                        f"Invalid membership types for this role: {', '.join(invalid_types)}"
                    )
                    validation_result['validation_details'].append({
                        'check': 'allowed_membership_types',
                        'status': 'failed',
                        'invalid_types': invalid_types
                    })
                else:
                    validation_result['validation_details'].append({
                        'check': 'allowed_membership_types',
                        'status': 'passed'
                    })
            
            # Check excluded membership types
            if excluded_types:
                conflicting_types = []
                for member_type in member_types:
                    if member_type in excluded_types:
                        conflicting_types.append(member_type)
                
                if conflicting_types:
                    validation_result['validation_passed'] = False
                    validation_result['requirements_met'] = False
                    validation_result['errors'].append(
                        f"Conflicting membership types (excluded for this role): {', '.join(conflicting_types)}"
                    )
                    validation_result['validation_details'].append({
                        'check': 'excluded_membership_types',
                        'status': 'failed',
                        'conflicting_types': conflicting_types
                    })
                else:
                    validation_result['validation_details'].append({
                        'check': 'excluded_membership_types',
                        'status': 'passed'
                    })
            
            # Add warnings for inactive memberships
            inactive_memberships = [m for m in memberships if not m.get('is_active', False)]
            if inactive_memberships:
                validation_result['warnings'].append(
                    f"Member has {len(inactive_memberships)} inactive membership(s)"
                )
            
            # Check if member has any active memberships
            if not active_memberships:
                validation_result['validation_passed'] = False
                validation_result['requirements_met'] = False
                validation_result['errors'].append("Member has no active memberships")
            
            logger.info(f"Membership validation completed for member {member_id}: {'PASSED' if validation_result['validation_passed'] else 'FAILED'}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Membership validation failed for member {member_id}: {e}")
            return {
                'member_id': member_id,
                'validation_passed': False,
                'requirements_met': False,
                'error': str(e),
                'validation_details': [],
                'warnings': [],
                'errors': [f"Validation error: {e}"]
            }

    def get_membership_summary_report(self, member_ids: List[str]) -> Dict[str, Any]:
        """
        Generate membership summary report for multiple members
        
        Args:
            member_ids: List of JustGo member IDs
            
        Returns:
            Comprehensive membership summary report
        """
        logger.info(f"Generating membership summary report for {len(member_ids)} members")
        
        report = {
            'total_members': len(member_ids),
            'processed_members': 0,
            'failed_members': 0,
            'membership_statistics': {},
            'membership_type_breakdown': {},
            'active_membership_count': 0,
            'inactive_membership_count': 0,
            'member_details': [],
            'errors': [],
            'generated_at': timezone.now().isoformat()
        }
        
        membership_type_counts = {}
        category_counts = {}
        
        for member_id in member_ids:
            try:
                memberships_data = self.get_member_memberships(member_id)
                memberships = memberships_data.get('memberships', [])
                
                member_summary = {
                    'member_id': member_id,
                    'total_memberships': len(memberships),
                    'active_memberships': len([m for m in memberships if m.get('is_active', False)]),
                    'membership_types': list(set([m.get('membership_category', 'Other') for m in memberships])),
                    'raw_membership_types': list(set([m.get('membership_type', '') for m in memberships])),
                    'memberships': memberships
                }
                
                report['member_details'].append(member_summary)
                report['processed_members'] += 1
                
                # Update statistics
                for membership in memberships:
                    membership_type = membership.get('membership_type', 'Unknown')
                    category = membership.get('membership_category', 'Other')
                    
                    membership_type_counts[membership_type] = membership_type_counts.get(membership_type, 0) + 1
                    category_counts[category] = category_counts.get(category, 0) + 1
                    
                    if membership.get('is_active', False):
                        report['active_membership_count'] += 1
                    else:
                        report['inactive_membership_count'] += 1
                
            except Exception as e:
                logger.error(f"Failed to process member {member_id}: {e}")
                report['failed_members'] += 1
                report['errors'].append({
                    'member_id': member_id,
                    'error': str(e)
                })
        
        # Finalize statistics
        report['membership_type_breakdown'] = membership_type_counts
        report['membership_category_breakdown'] = category_counts
        report['membership_statistics'] = {
            'total_memberships': report['active_membership_count'] + report['inactive_membership_count'],
            'active_memberships': report['active_membership_count'],
            'inactive_memberships': report['inactive_membership_count'],
            'unique_membership_types': len(membership_type_counts),
            'unique_categories': len(category_counts),
            'success_rate': (report['processed_members'] / report['total_members']) * 100 if report['total_members'] > 0 else 0
        }
        
        logger.info(f"Membership summary report completed: {report['processed_members']}/{report['total_members']} members processed")
        return report


class JustGoDataExtractor:
    """
    Utility class for extracting and processing JustGo API data
    """

    def extract_member_ids(self, member_data: Dict[str, Any]) -> JustGoMemberIds:
        """
        Extract all identifiers from member data
        
        Args:
            member_data: Member data from API response
            
        Returns:
            JustGoMemberIds object with extracted identifiers
        """
        ids = JustGoMemberIds()
        
        # Basic member identifiers
        ids.member_id = member_data.get('memberId')
        ids.member_doc_id = member_data.get('memberDocId')
        ids.mid = member_data.get('mid')
        ids.candidate_id = ids.member_id  # Same as member_id
        
        # Extract booking identifiers
        bookings = member_data.get('bookings', [])
        for booking in bookings:
            if booking.get('bookingId'):
                ids.booking_ids.append(booking['bookingId'])
            if booking.get('eventId'):
                ids.event_ids.append(booking['eventId'])
            if booking.get('ticketId'):
                ids.ticket_ids.append(booking['ticketId'])
        
        # Extract credential identifiers
        awards = member_data.get('awards', [])
        for award in awards:
            if award.get('credentialId'):
                ids.credential_ids.append(award['credentialId'])
        
        # Extract club identifiers
        clubs = member_data.get('clubs', [])
        for club in clubs:
            if club.get('clubId'):
                ids.club_ids.append(club['clubId'])
        
        # Extract membership identifiers
        memberships = member_data.get('memberships', [])
        for membership in memberships:
            if membership.get('membershipId'):
                ids.membership_ids.append(membership['membershipId'])
        
        return ids

    def extract_active_credentials(self, credentials_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract only active credentials from credentials data
        
        Args:
            credentials_data: Credentials data from API response
            
        Returns:
            List of active credentials
        """
        credentials = credentials_data.get('data', [])
        return [cred for cred in credentials if cred.get('status') == 'Active']

    def extract_expired_credentials(self, credentials_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract expired credentials from credentials data
        
        Args:
            credentials_data: Credentials data from API response
            
        Returns:
            List of expired credentials
        """
        credentials = credentials_data.get('data', [])
        return [cred for cred in credentials if cred.get('status') == 'Expired']

    def group_credentials_by_type(self, credentials_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group credentials by type
        
        Args:
            credentials_data: Credentials data from API response
            
        Returns:
            Dictionary with credential types as keys and lists of credentials as values
        """
        credentials = credentials_data.get('data', [])
        grouped = {}
        
        for cred in credentials:
            cred_type = cred.get('type', 'Unknown')
            if cred_type not in grouped:
                grouped[cred_type] = []
            grouped[cred_type].append(cred)
        
        return grouped

    def check_credential_expiry(self, credentials_data: Dict[str, Any], days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Find credentials expiring within specified days
        
        Args:
            credentials_data: Credentials data from API response
            days_ahead: Number of days to look ahead for expiry
            
        Returns:
            List of credentials expiring soon
        """
        credentials = credentials_data.get('data', [])
        expiring_soon = []
        cutoff_date = timezone.now().date() + timedelta(days=days_ahead)
        
        for cred in credentials:
            if cred.get('status') == 'Active' and cred.get('expiryDate'):
                try:
                    expiry_date = datetime.strptime(cred['expiryDate'], '%Y-%m-%d').date()
                    if expiry_date <= cutoff_date:
                        expiring_soon.append(cred)
                except ValueError:
                    logger.warning(f"Invalid expiry date format: {cred.get('expiryDate')}")
        
        return expiring_soon


# Convenience function for quick client creation
def create_justgo_client(secret: Optional[str] = None) -> JustGoAPIClient:
    """
    Create a JustGo API client with optional secret override
    
    Args:
        secret: Optional API secret. If None, loads from settings.
        
    Returns:
        Configured JustGoAPIClient instance
    """
    if secret:
        credentials = JustGoCredentials(secret=secret)
        return JustGoAPIClient(credentials)
    else:
        return JustGoAPIClient() 