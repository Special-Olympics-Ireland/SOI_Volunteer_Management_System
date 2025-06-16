from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Enhanced admin interface for the custom User model supporting multiple user types
    """
    
    # List display configuration
    list_display = (
        'username', 'email', 'get_full_name_display', 'user_type', 'volunteer_type',
        'is_approved', 'profile_complete', 'email_verified', 'justgo_sync_status',
        'created_at', 'last_login'
    )
    
    list_filter = (
        'user_type', 'volunteer_type', 'is_approved', 'profile_complete', 
        'email_verified', 'phone_verified', 'justgo_sync_status', 
        'justgo_membership_type', 'is_active', 'is_staff', 'is_superuser',
        'gdpr_consent', 'marketing_consent', 'created_at', 'last_login'
    )
    
    search_fields = (
        'username', 'email', 'first_name', 'last_name', 'phone_number',
        'mobile_number', 'justgo_member_id', 'employee_id'
    )
    
    ordering = ('-created_at',)
    
    # Fieldsets for add/edit forms
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('username', 'password', 'email', 'first_name', 'last_name')
        }),
        (_('User Type & Classification'), {
            'fields': ('user_type', 'volunteer_type', 'is_active', 'is_staff', 'is_superuser'),
            'classes': ('wide',)
        }),
        (_('Contact Information'), {
            'fields': (
                'phone_number', 'mobile_number', 'preferred_language',
                'email_notifications', 'sms_notifications'
            ),
            'classes': ('collapse',)
        }),
        (_('Address Information'), {
            'fields': (
                'address_line_1', 'address_line_2', 'city', 'county', 
                'postal_code', 'country'
            ),
            'classes': ('collapse',)
        }),
        (_('Personal Details'), {
            'fields': (
                'date_of_birth', 'emergency_contact_name', 'emergency_contact_relationship',
                'emergency_phone'
            ),
            'classes': ('collapse',)
        }),
        (_('Staff Information'), {
            'fields': ('department', 'position', 'employee_id'),
            'classes': ('collapse',),
            'description': _('Only applicable for staff and management users')
        }),
        (_('JustGo Integration'), {
            'fields': (
                'justgo_member_id', 'justgo_membership_type', 'justgo_sync_status',
                'justgo_last_sync'
            ),
            'classes': ('collapse',)
        }),
        (_('Verification & Approval'), {
            'fields': (
                'profile_complete', 'email_verified', 'phone_verified',
                'is_approved', 'approval_date', 'approved_by'
            ),
            'classes': ('wide',)
        }),
        (_('GDPR & Consent'), {
            'fields': (
                'gdpr_consent', 'gdpr_consent_date', 'marketing_consent'
            ),
            'classes': ('collapse',)
        }),
        (_('Activity & Audit'), {
            'fields': (
                'last_login', 'last_activity', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        (_('Groups & Permissions'), {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Internal Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',),
            'description': _('Internal notes for administrative use only')
        }),
    )
    
    # Fieldsets for adding new users
    add_fieldsets = (
        (_('Basic Information'), {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        (_('User Type'), {
            'classes': ('wide',),
            'fields': ('user_type', 'volunteer_type'),
        }),
        (_('Personal Information'), {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'phone_number'),
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'last_login', 'last_activity',
        'profile_complete', 'justgo_last_sync'
    )
    
    # Custom methods for list display
    def get_full_name_display(self, obj):
        """Display full name with fallback to username"""
        full_name = obj.get_full_name()
        if full_name:
            return full_name
        return f"({obj.username})"
    get_full_name_display.short_description = _('Full Name')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance"""
        return super().get_queryset(request).select_related('approved_by')
    
    # Custom actions
    actions = ['approve_users', 'revoke_approval', 'mark_email_verified', 'sync_with_justgo']
    
    def approve_users(self, request, queryset):
        """Bulk approve selected users"""
        updated = 0
        for user in queryset.filter(is_approved=False):
            user.approve_account(request.user)
            updated += 1
        
        self.message_user(
            request,
            f'{updated} user(s) were successfully approved.'
        )
    approve_users.short_description = _('Approve selected users')
    
    def revoke_approval(self, request, queryset):
        """Bulk revoke approval for selected users"""
        updated = queryset.filter(is_approved=True).update(
            is_approved=False,
            approval_date=None,
            approved_by=None
        )
        
        self.message_user(
            request,
            f'{updated} user(s) had their approval revoked.'
        )
    revoke_approval.short_description = _('Revoke approval for selected users')
    
    def mark_email_verified(self, request, queryset):
        """Mark selected users' emails as verified"""
        updated = queryset.filter(email_verified=False).update(email_verified=True)
        
        self.message_user(
            request,
            f'{updated} user(s) were marked as email verified.'
        )
    mark_email_verified.short_description = _('Mark emails as verified')
    
    def sync_with_justgo(self, request, queryset):
        """Mark selected users for JustGo synchronization"""
        updated = queryset.filter(
            user_type=User.UserType.VOLUNTEER,
            justgo_sync_status__in=['NOT_REQUIRED', 'ERROR']
        ).update(justgo_sync_status='PENDING')
        
        self.message_user(
            request,
            f'{updated} user(s) were marked for JustGo synchronization.'
        )
    sync_with_justgo.short_description = _('Mark for JustGo sync')
    
    # Custom form handling
    def save_model(self, request, obj, form, change):
        """Custom save handling with audit trail"""
        if not change:  # New user
            # Set created by information if available
            if hasattr(obj, 'created_by'):
                obj.created_by = request.user
        
        # Auto-approve if admin is creating the user
        if not change and request.user.is_superuser:
            obj.is_approved = True
            obj.approved_by = request.user
        
        super().save_model(request, obj, form, change)
    
    # Custom display methods
    def has_change_permission(self, request, obj=None):
        """Custom permission checking"""
        if obj is None:
            return super().has_change_permission(request, obj)
        
        # Superusers can edit anyone
        if request.user.is_superuser:
            return True
        
        # Users can edit their own profile (limited fields)
        if obj == request.user:
            return True
        
        # Management users can edit volunteers
        if request.user.is_management() and obj.is_volunteer():
            return True
        
        return super().has_change_permission(request, obj)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit fields for non-superusers
        if not request.user.is_superuser:
            # Remove sensitive fields for non-superusers
            sensitive_fields = ['is_superuser', 'user_permissions', 'groups']
            for field in sensitive_fields:
                if field in form.base_fields:
                    del form.base_fields[field]
        
        return form
    
    # Enhanced filtering
    def get_list_filter(self, request):
        """Dynamic list filters based on user permissions"""
        filters = list(self.list_filter)
        
        # Add additional filters for superusers
        if request.user.is_superuser:
            filters.extend(['approved_by', 'department'])
        
        return filters
