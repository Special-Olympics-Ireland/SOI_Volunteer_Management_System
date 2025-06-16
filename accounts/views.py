from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import User
from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserAdminSerializer, UserJustGoSerializer,
    UserStatsSerializer, PasswordChangeSerializer, UserLoginSerializer,
    UserPreferencesSerializer, UserPreferencesUpdateSerializer,
    UserProfileCompletionSerializer, UserSecuritySerializer,
    UserNotificationSettingsSerializer, UserVerificationSerializer
)
from .permissions import UserPermissions
from common.audit_service import AdminAuditService


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for user lists"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(
        summary="List users",
        description="Get a paginated list of users with filtering and search capabilities",
        tags=["Authentication"]
    ),
    create=extend_schema(
        summary="Create user",
        description="Create a new user account",
        tags=["Authentication"]
    ),
    retrieve=extend_schema(
        summary="Get user details",
        description="Get detailed information about a specific user",
        tags=["Authentication"]
    ),
    update=extend_schema(
        summary="Update user",
        description="Update user information",
        tags=["Authentication"]
    ),
    partial_update=extend_schema(
        summary="Partially update user",
        description="Partially update user information",
        tags=["Authentication"]
    ),
    destroy=extend_schema(
        summary="Delete user",
        description="Delete a user account (admin only)",
        tags=["Authentication"]
    )
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management with comprehensive CRUD operations
    """
    queryset = User.objects.all()
    permission_classes = [UserPermissions]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['created_at', 'last_login', 'username', 'email']
    ordering = ['-created_at']
    filterset_fields = {
        'user_type': ['exact', 'in'],
        'volunteer_type': ['exact', 'in'],
        'is_approved': ['exact'],
        'email_verified': ['exact'],
        'profile_complete': ['exact'],
        'created_at': ['gte', 'lte'],
        'last_login': ['gte', 'lte'],
    }

    def get_serializer_class(self):
        """Return appropriate serializer based on action and permissions"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.request.user.is_staff:
            return UserAdminSerializer
        return UserSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = User.objects.all()
        
        if not self.request.user.is_authenticated:
            return queryset.none()
        
        # Regular users can only see their own profile
        if not self.request.user.is_staff:
            return queryset.filter(id=self.request.user.id)
        
        return queryset

    def perform_create(self, serializer):
        """Create user with audit logging"""
        user = serializer.save()
        
        # Log user creation
        AdminAuditService.log_user_management(
            admin_user=self.request.user,
            action='CREATE_USER',
            target_user=user,
        )

    def perform_update(self, serializer):
        """Update user with audit logging"""
        old_data = {
            'user_type': serializer.instance.user_type,
            'is_approved': serializer.instance.is_approved,
            'email': serializer.instance.email,
        }
        
        user = serializer.save()
        
        # Log user update
        AdminAuditService.log_user_management(
            admin_user=self.request.user,
            action='UPDATE_USER',
            target_user=user,
        )

    def perform_destroy(self, instance):
        """Delete user with audit logging"""
        AdminAuditService.log_user_management(
            admin_user=self.request.user,
            action='DELETE_USER',
            target_user=instance,
        )
        instance.delete()

    @extend_schema(
        summary="Get user statistics",
        description="Get comprehensive user statistics and metrics",
        responses={200: UserStatsSerializer},
        tags=["Authentication"]
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def stats(self, request):
        """Get user statistics"""
        stats = {
            'total_users': User.objects.count(),
            'volunteers': User.objects.filter(user_type=User.UserType.VOLUNTEER).count(),
            'staff': User.objects.filter(user_type=User.UserType.STAFF).count(),
            'vmt': User.objects.filter(user_type=User.UserType.VMT).count(),
            'cvt': User.objects.filter(user_type=User.UserType.CVT).count(),
            'goc': User.objects.filter(user_type=User.UserType.GOC).count(),
            'admin': User.objects.filter(user_type=User.UserType.ADMIN).count(),
            'approved_users': User.objects.filter(is_approved=True).count(),
            'pending_approval': User.objects.filter(is_approved=False).count(),
            'email_verified': User.objects.filter(email_verified=True).count(),
            'profile_complete': User.objects.filter(profile_complete=True).count(),
            'justgo_synced': User.objects.exclude(justgo_member_id__isnull=True).count(),
            'recent_registrations': User.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)

    @extend_schema(
        summary="Approve user",
        description="Approve a user account (admin only)",
        tags=["Authentication"]
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve a user"""
        user = self.get_object()
        user.is_approved = True
        user.approved_by = request.user
        user.approved_at = timezone.now()
        user.save()

        # Log approval
        AdminAuditService.log_user_management(
            admin_user=request.user,
            action='APPROVE_USER',
            target_user=user,
            details={'approved_via': 'API'}
        )

        return Response({'status': 'User approved successfully'})

    @extend_schema(
        summary="Reject user",
        description="Reject a user account (admin only)",
        tags=["Authentication"]
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a user"""
        user = self.get_object()
        user.is_approved = False
        user.approved_by = None
        user.approved_at = None
        user.save()

        # Log rejection
        AdminAuditService.log_user_management(
            admin_user=request.user,
            action='REJECT_USER',
            target_user=user,
            details={'rejected_via': 'API'}
        )

        return Response({'status': 'User rejected successfully'})


@extend_schema(
    summary="User login",
    description="Authenticate user and return authentication token",
    request=UserLoginSerializer,
    responses={
        200: UserDetailSerializer,
        400: "Invalid credentials"
    },
    tags=["Authentication"]
)
class LoginView(APIView):
    """
    User authentication endpoint
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Authenticate user and return token"""
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check if user is approved
            if not user.is_approved and user.user_type != User.UserType.ADMIN:
                return Response(
                    {'error': _('Your account is pending approval.')},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create or get token
            token, created = Token.objects.get_or_create(user=user)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Log successful login
            
            # Return user data and token
            user_serializer = UserDetailSerializer(user)
            return Response({
                'token': token.key,
                'user': user_serializer.data
            })
        
        # Log failed login attempt
        username = request.data.get('username', 'unknown')
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="User logout",
    description="Logout user and invalidate authentication token",
    responses={200: "Logout successful"},
    tags=["Authentication"]
)
class LogoutView(APIView):
    """
    User logout endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Logout user and delete token"""
        try:
            # Delete the user's token
            token = Token.objects.get(user=request.user)
            token.delete()
            
            # Log logout
            
            return Response({'status': 'Logout successful'})
        except Token.DoesNotExist:
            return Response({'status': 'No active session found'})


@extend_schema(
    summary="User registration",
    description="Register a new user account",
    request=UserCreateSerializer,
    responses={
        201: UserDetailSerializer,
        400: "Validation errors"
    },
    tags=["Authentication"]
)
class RegisterView(APIView):
    """
    User registration endpoint
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Register a new user"""
        serializer = UserCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log registration
            AdminAuditService.log_user_management(
                admin_user=None,
                action='REGISTER_USER',
                target_user=user,
            )
            
            # Send welcome email (if configured)
            if hasattr(settings, 'SEND_WELCOME_EMAIL') and settings.SEND_WELCOME_EMAIL:
                self.send_welcome_email(user)
            
            # Return user data
            user_serializer = UserDetailSerializer(user)
            return Response(user_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_welcome_email(self, user):
        """Send welcome email to new user"""
        try:
            subject = _('Welcome to SOI Hub')
            message = _(
                'Welcome to the SOI Hub volunteer management system. '
                'Your account has been created and is pending approval.'
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )
        except Exception:
            pass  # Don't fail registration if email fails


@extend_schema(
    summary="Change password",
    description="Change user password",
    request=PasswordChangeSerializer,
    responses={200: "Password changed successfully"},
    tags=["Authentication"]
)
class PasswordChangeView(APIView):
    """
    Password change endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(data=request.data, context={'user': request.user})
        
        if serializer.is_valid():
            serializer.save()
            
            # Log password change
            
            return Response({'status': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get current user profile",
    description="Get the current authenticated user's profile",
    responses={200: UserDetailSerializer},
    tags=["Authentication"]
)
class ProfileView(APIView):
    """
    Current user profile endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user profile"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    summary="Update current user profile",
    description="Update the current authenticated user's profile",
    request=UserUpdateSerializer,
    responses={200: UserDetailSerializer},
    tags=["Authentication"]
)
class ProfileUpdateView(APIView):
    """
    Current user profile update endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        """Update current user profile"""
        serializer = UserUpdateSerializer(request.user, data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log profile update
            AdminAuditService.log_user_management(
                admin_user=request.user,
                action='UPDATE_PROFILE',
                target_user=user,
            )
            
            # Return updated profile
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Partially update current user profile"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log profile update
            AdminAuditService.log_user_management(
                admin_user=request.user,
                action='UPDATE_PROFILE',
                target_user=user,
            )
            
            # Return updated profile
            response_serializer = UserDetailSerializer(user)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Password reset request",
    description="Request a password reset email",
    responses={200: "Password reset email sent"},
    tags=["Authentication"]
)
class PasswordResetView(APIView):
    """
    Password reset request endpoint
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Request password reset"""
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': _('Email address is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Send reset email (if configured)
            if hasattr(settings, 'SEND_PASSWORD_RESET_EMAIL') and settings.SEND_PASSWORD_RESET_EMAIL:
                self.send_reset_email(user, token, uid)
            
            # Log password reset request
            
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            pass
        
        # Always return success to prevent email enumeration
        return Response({'status': 'Password reset email sent if account exists'})

    def send_reset_email(self, user, token, uid):
        """Send password reset email"""
        try:
            subject = _('Password Reset - SOI Hub')
            message = _(
                'You have requested a password reset for your SOI Hub account. '
                'Please use the following token to reset your password: {token}'
            ).format(token=token)
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )
        except Exception:
            pass  # Don't fail if email fails


@extend_schema(
    summary="Obtain authentication token",
    description="Obtain authentication token using username/email and password",
    request=UserLoginSerializer,
    responses={200: "Authentication token"},
    tags=["Authentication"]
)
class ObtainAuthTokenView(ObtainAuthToken):
    """
    Custom token authentication endpoint with enhanced logging
    """
    
    def post(self, request, *args, **kwargs):
        """Obtain authentication token with audit logging"""
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get user from serializer
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                
                # Log successful token creation
        
        return response


@extend_schema(
    summary="Get user preferences",
    description="Get current user's preferences and settings",
    responses={200: UserPreferencesSerializer},
    tags=["User Management"]
)
class UserPreferencesView(APIView):
    """
    User preferences endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user preferences"""
        serializer = UserPreferencesSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    summary="Update user preferences",
    description="Update current user's preferences and settings",
    request=UserPreferencesUpdateSerializer,
    responses={200: UserPreferencesSerializer},
    tags=["User Management"]
)
class UserPreferencesUpdateView(APIView):
    """
    User preferences update endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        """Update user preferences"""
        serializer = UserPreferencesUpdateSerializer(
            request.user, 
            data=request.data
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log preferences update
            AdminAuditService.log_user_management(
                admin_user=request.user,
                action='UPDATE_PREFERENCES',
                target_user=user,
            )
            
            # Return updated preferences
            response_serializer = UserPreferencesSerializer(user)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Partially update user preferences"""
        serializer = UserPreferencesUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log preferences update
            AdminAuditService.log_user_management(
                admin_user=request.user,
                action='UPDATE_PREFERENCES',
                target_user=user,
            )
            
            # Return updated preferences
            response_serializer = UserPreferencesSerializer(user)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get profile completion status",
    description="Get current user's profile completion status and missing fields",
    responses={200: UserProfileCompletionSerializer},
    tags=["User Management"]
)
class UserProfileCompletionView(APIView):
    """
    User profile completion status endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get profile completion status"""
        serializer = UserProfileCompletionSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    summary="Get user security information",
    description="Get current user's security information and login history",
    responses={200: UserSecuritySerializer},
    tags=["User Management"]
)
class UserSecurityView(APIView):
    """
    User security information endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user security information"""
        serializer = UserSecuritySerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    summary="Get notification settings",
    description="Get current user's notification settings",
    responses={200: UserNotificationSettingsSerializer},
    tags=["User Management"]
)
class UserNotificationSettingsView(APIView):
    """
    User notification settings endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get notification settings"""
        serializer = UserNotificationSettingsSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    summary="Update notification settings",
    description="Update current user's notification settings",
    request=UserNotificationSettingsSerializer,
    responses={200: UserNotificationSettingsSerializer},
    tags=["User Management"]
)
class UserNotificationSettingsUpdateView(APIView):
    """
    User notification settings update endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        """Update notification settings"""
        serializer = UserNotificationSettingsSerializer(
            request.user, 
            data=request.data
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log notification settings update
            AdminAuditService.log_user_management(
                admin_user=request.user,
                action='UPDATE_NOTIFICATION_SETTINGS',
                target_user=user,
            )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Partially update notification settings"""
        serializer = UserNotificationSettingsSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log notification settings update
            AdminAuditService.log_user_management(
                admin_user=request.user,
                action='UPDATE_NOTIFICATION_SETTINGS',
                target_user=user,
            )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Request verification",
    description="Request email or phone verification",
    request=UserVerificationSerializer,
    responses={200: "Verification request sent"},
    tags=["User Management"]
)
class UserVerificationRequestView(APIView):
    """
    User verification request endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Request verification"""
        serializer = UserVerificationSerializer(
            data=request.data,
            context={'user': request.user}
        )
        
        if serializer.is_valid():
            verification_type = serializer.validated_data['verification_type']
            
            if verification_type == 'email':
                self.send_email_verification(request.user)
                message = _('Email verification sent to your email address.')
            elif verification_type == 'phone':
                self.send_phone_verification(request.user)
                message = _('Phone verification code sent to your phone number.')
            
            # Log verification request
            
            return Response({'message': message})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_email_verification(self, user):
        """Send email verification"""
        # Implementation would depend on your email verification system
        # For now, just log the request
        pass

    def send_phone_verification(self, user):
        """Send phone verification"""
        # Implementation would depend on your SMS verification system
        # For now, just log the request
        pass


@extend_schema(
    summary="Delete user account",
    description="Delete current user's account (self-deletion)",
    responses={204: "Account deleted successfully"},
    tags=["User Management"]
)
class UserAccountDeletionView(APIView):
    """
    User account deletion endpoint
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        """Delete user account"""
        user = request.user
        
        # Log account deletion
        AdminAuditService.log_user_management(
            admin_user=user,
            action='DELETE_ACCOUNT_SELF',
            target_user=user,
        )
        
        # Perform soft delete or mark as inactive
        user.is_active = False
        user.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
