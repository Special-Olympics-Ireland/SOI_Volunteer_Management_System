"""
URL configuration for accounts app.
Handles user authentication, registration, and profile management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

# API router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    # API endpoints - Direct router URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/login/', views.LoginView.as_view(), name='api-login'),
    path('auth/logout/', views.LogoutView.as_view(), name='api-logout'),
    path('auth/register/', views.RegisterView.as_view(), name='api-register'),
    path('auth/password-change/', views.PasswordChangeView.as_view(), name='api-password-change'),
    path('auth/password-reset/', views.PasswordResetView.as_view(), name='api-password-reset'),
    
    # Profile management
    path('profile/', views.ProfileView.as_view(), name='api-profile'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='api-profile-update'),
    path('profile/completion/', views.UserProfileCompletionView.as_view(), name='api-profile-completion'),
    
    # User preferences and settings
    path('preferences/', views.UserPreferencesView.as_view(), name='api-preferences'),
    path('preferences/update/', views.UserPreferencesUpdateView.as_view(), name='api-preferences-update'),
    path('notifications/', views.UserNotificationSettingsView.as_view(), name='api-notifications'),
    path('notifications/update/', views.UserNotificationSettingsUpdateView.as_view(), name='api-notifications-update'),
    
    # User security and verification
    path('security/', views.UserSecurityView.as_view(), name='api-security'),
    path('verification/request/', views.UserVerificationRequestView.as_view(), name='api-verification-request'),
    
    # Account management
    path('account/delete/', views.UserAccountDeletionView.as_view(), name='api-account-delete'),
    
    # Token-based authentication (DRF built-in)
    path('auth/token/', views.ObtainAuthTokenView.as_view(), name='api-token'),
] 