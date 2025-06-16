from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Standard user serializer for general API responses
    """
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    full_address = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'volunteer_type', 'phone_number', 'mobile_number',
            'date_of_birth', 'age', 'full_address', 'preferred_language',
            'profile_complete', 'email_verified', 'phone_verified',
            'is_approved', 'created_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'profile_complete', 'email_verified', 'phone_verified',
            'is_approved', 'created_at', 'last_login', 'full_name', 'age', 'full_address'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.get_age()
    
    def get_full_address(self, obj):
        return obj.get_full_address()

class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer for profile management
    """
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    full_address = serializers.SerializerMethodField()
    is_eligible_volunteer = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'volunteer_type', 'phone_number', 'mobile_number',
            'date_of_birth', 'age', 'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_phone', 'address_line_1', 'address_line_2', 'city', 'county',
            'postal_code', 'country', 'full_address', 'department', 'position',
            'preferred_language', 'email_notifications', 'sms_notifications',
            'profile_complete', 'email_verified', 'phone_verified', 'is_approved',
            'gdpr_consent', 'gdpr_consent_date', 'marketing_consent',
            'is_eligible_volunteer', 'created_at', 'updated_at', 'last_login', 'last_activity'
        ]
        read_only_fields = [
            'id', 'profile_complete', 'email_verified', 'phone_verified',
            'is_approved', 'created_at', 'updated_at', 'last_login', 'last_activity',
            'full_name', 'age', 'full_address', 'is_eligible_volunteer', 'gdpr_consent_date'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.get_age()
    
    def get_full_address(self, obj):
        return obj.get_full_address()
    
    def get_is_eligible_volunteer(self, obj):
        return obj.is_eligible_volunteer()

class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration/creation
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'user_type', 'volunteer_type',
            'phone_number', 'mobile_number', 'date_of_birth',
            'address_line_1', 'address_line_2', 'city', 'county',
            'postal_code', 'country', 'preferred_language',
            'gdpr_consent', 'marketing_consent'
        ]
    
    def validate(self, attrs):
        """Custom validation for user creation"""
        # Check password confirmation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _('Password confirmation does not match.')
            })
        
        # Validate age for volunteers
        if attrs.get('user_type') == User.UserType.VOLUNTEER:
            if not attrs.get('date_of_birth'):
                raise serializers.ValidationError({
                    'date_of_birth': _('Date of birth is required for volunteers.')
                })
            
            # Calculate age
            today = timezone.now().date()
            age = today.year - attrs['date_of_birth'].year
            if today < attrs['date_of_birth'].replace(year=today.year):
                age -= 1
            
            if age < 15:
                raise serializers.ValidationError({
                    'date_of_birth': _('Volunteers must be at least 15 years old.')
                })
        
        # Validate GDPR consent for volunteers
        if attrs.get('user_type') == User.UserType.VOLUNTEER:
            if not attrs.get('gdpr_consent'):
                raise serializers.ValidationError({
                    'gdpr_consent': _('GDPR consent is required for volunteers.')
                })
        
        # Validate volunteer type
        if attrs.get('user_type') == User.UserType.VOLUNTEER:
            if not attrs.get('volunteer_type'):
                attrs['volunteer_type'] = User.VolunteerType.GENERAL
        elif attrs.get('volunteer_type'):
            # Clear volunteer_type if not a volunteer
            attrs['volunteer_type'] = None
        
        return attrs
    
    def create(self, validated_data):
        """Create user with proper password hashing"""
        # Remove password confirmation
        validated_data.pop('password_confirm', None)
        
        # Set GDPR consent date if consent is given
        if validated_data.get('gdpr_consent'):
            validated_data['gdpr_consent_date'] = timezone.now()
        
        # Create user
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'mobile_number',
            'date_of_birth', 'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_phone', 'address_line_1', 'address_line_2', 'city', 'county',
            'postal_code', 'country', 'department', 'position',
            'preferred_language', 'email_notifications', 'sms_notifications',
            'marketing_consent'
        ]
    
    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value and self.instance and self.instance.is_volunteer():
            # Calculate age
            today = timezone.now().date()
            age = today.year - value.year
            if today < value.replace(year=today.year):
                age -= 1
            
            if age < 15:
                raise serializers.ValidationError(
                    _('Volunteers must be at least 15 years old.')
                )
        
        return value

class UserAdminSerializer(serializers.ModelSerializer):
    """
    Admin serializer with full access to all fields
    """
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    full_address = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_login', 'last_activity',
            'full_name', 'age', 'full_address', 'approved_by_name'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.get_age()
    
    def get_full_address(self, obj):
        return obj.get_full_address()
    
    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None

class UserJustGoSerializer(serializers.ModelSerializer):
    """
    Serializer for JustGo integration data
    """
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number',
            'date_of_birth', 'address_line_1', 'address_line_2', 'city',
            'county', 'postal_code', 'country', 'justgo_member_id',
            'justgo_membership_type', 'justgo_sync_status', 'justgo_last_sync'
        ]
        read_only_fields = [
            'id', 'justgo_member_id', 'justgo_sync_status', 'justgo_last_sync'
        ]

class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user statistics
    """
    total_users = serializers.IntegerField()
    volunteers = serializers.IntegerField()
    staff = serializers.IntegerField()
    vmt = serializers.IntegerField()
    cvt = serializers.IntegerField()
    goc = serializers.IntegerField()
    admin = serializers.IntegerField()
    approved_users = serializers.IntegerField()
    pending_approval = serializers.IntegerField()
    email_verified = serializers.IntegerField()
    profile_complete = serializers.IntegerField()
    justgo_synced = serializers.IntegerField()
    recent_registrations = serializers.IntegerField()

class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_('Old password is incorrect.'))
        return value
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _('Password confirmation does not match.')
            })
        return attrs
    
    def save(self):
        """Change user password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Authenticate user"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Try to authenticate with username or email
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(
                        request=self.context.get('request'),
                        username=user_obj.username,
                        password=password
                    )
                except User.DoesNotExist:
                    pass
            
            if not user:
                raise serializers.ValidationError(
                    _('Unable to log in with provided credentials.')
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    _('User account is disabled.')
                )
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                _('Must include "username" and "password".')
            )

class UserPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for user preferences and settings
    """
    theme_preference = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'preferred_language', 'email_notifications', 'sms_notifications',
            'marketing_consent', 'theme_preference'
        ]
    
    def get_theme_preference(self, obj):
        """Get user theme preferences"""
        try:
            from common.models import UserThemePreference
            preference = UserThemePreference.objects.get(user=obj)
            return {
                'admin_theme': preference.admin_theme.name if preference.admin_theme else None,
                'mobile_theme': preference.mobile_theme.name if preference.mobile_theme else None,
                'use_dark_mode': preference.use_dark_mode,
                'use_high_contrast': preference.use_high_contrast,
                'font_size_preference': preference.font_size_preference,
            }
        except:
            return None

class UserPreferencesUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user preferences
    """
    theme_preferences = serializers.DictField(required=False, write_only=True)
    
    class Meta:
        model = User
        fields = [
            'preferred_language', 'email_notifications', 'sms_notifications',
            'marketing_consent', 'theme_preferences'
        ]
    
    def update(self, instance, validated_data):
        """Update user preferences including theme preferences"""
        theme_preferences = validated_data.pop('theme_preferences', None)
        
        # Update basic preferences
        instance = super().update(instance, validated_data)
        
        # Update theme preferences if provided
        if theme_preferences:
            try:
                from common.models import UserThemePreference, Theme
                user_theme_pref, created = UserThemePreference.objects.get_or_create(
                    user=instance
                )
                
                if 'admin_theme_id' in theme_preferences:
                    if theme_preferences['admin_theme_id']:
                        admin_theme = Theme.objects.get(
                            id=theme_preferences['admin_theme_id'],
                            theme_type='ADMIN'
                        )
                        user_theme_pref.admin_theme = admin_theme
                    else:
                        user_theme_pref.admin_theme = None
                
                if 'mobile_theme_id' in theme_preferences:
                    if theme_preferences['mobile_theme_id']:
                        mobile_theme = Theme.objects.get(
                            id=theme_preferences['mobile_theme_id'],
                            theme_type='MOBILE'
                        )
                        user_theme_pref.mobile_theme = mobile_theme
                    else:
                        user_theme_pref.mobile_theme = None
                
                if 'use_dark_mode' in theme_preferences:
                    user_theme_pref.use_dark_mode = theme_preferences['use_dark_mode']
                
                if 'use_high_contrast' in theme_preferences:
                    user_theme_pref.use_high_contrast = theme_preferences['use_high_contrast']
                
                if 'font_size_preference' in theme_preferences:
                    user_theme_pref.font_size_preference = theme_preferences['font_size_preference']
                
                user_theme_pref.save()
            except Exception as e:
                # Don't fail the entire update if theme preferences fail
                pass
        
        return instance

class UserProfileCompletionSerializer(serializers.ModelSerializer):
    """
    Serializer for profile completion status and requirements
    """
    completion_percentage = serializers.SerializerMethodField()
    missing_fields = serializers.SerializerMethodField()
    required_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'profile_complete', 'completion_percentage', 'missing_fields', 
            'required_fields', 'email_verified', 'phone_verified'
        ]
        read_only_fields = ['profile_complete', 'email_verified', 'phone_verified']
    
    def get_completion_percentage(self, obj):
        """Calculate profile completion percentage"""
        required_fields = self.get_required_fields(obj)
        completed_fields = 0
        
        for field in required_fields:
            if hasattr(obj, field) and getattr(obj, field):
                completed_fields += 1
        
        if len(required_fields) == 0:
            return 100
        
        return int((completed_fields / len(required_fields)) * 100)
    
    def get_missing_fields(self, obj):
        """Get list of missing required fields"""
        required_fields = self.get_required_fields(obj)
        missing = []
        
        for field in required_fields:
            if not hasattr(obj, field) or not getattr(obj, field):
                missing.append(field)
        
        return missing
    
    def get_required_fields(self, obj):
        """Get list of required fields based on user type"""
        base_fields = [
            'first_name', 'last_name', 'email', 'phone_number', 
            'date_of_birth', 'address_line_1', 'city', 'county', 'postal_code'
        ]
        
        if obj.is_volunteer():
            base_fields.extend([
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            ])
        
        if obj.is_staff:
            base_fields.extend(['department', 'position'])
        
        return base_fields

class UserSecuritySerializer(serializers.ModelSerializer):
    """
    Serializer for user security information
    """
    last_password_change = serializers.SerializerMethodField()
    login_history = serializers.SerializerMethodField()
    active_sessions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'last_login', 'last_password_change', 'login_history', 
            'active_sessions', 'email_verified', 'phone_verified'
        ]
        read_only_fields = ['last_login', 'email_verified', 'phone_verified']
    
    def get_last_password_change(self, obj):
        """Get last password change date"""
        # This would require additional tracking in the User model
        # For now, return None or implement based on audit logs
        return None
    
    def get_login_history(self, obj):
        """Get recent login history"""
        # This would require audit log integration
        return []
    
    def get_active_sessions(self, obj):
        """Get active user sessions"""
        # This would require session tracking
        return []

class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for user notification settings
    """
    class Meta:
        model = User
        fields = [
            'email_notifications', 'sms_notifications', 'marketing_consent',
            'preferred_language'
        ]

class UserVerificationSerializer(serializers.Serializer):
    """
    Serializer for user verification requests
    """
    verification_type = serializers.ChoiceField(
        choices=[
            ('email', 'Email Verification'),
            ('phone', 'Phone Verification'),
        ]
    )
    
    def validate_verification_type(self, value):
        """Validate verification type"""
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError("User context required")
        
        if value == 'email' and user.email_verified:
            raise serializers.ValidationError("Email is already verified")
        
        if value == 'phone' and user.phone_verified:
            raise serializers.ValidationError("Phone is already verified")
        
        return value 