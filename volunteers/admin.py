from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.http import HttpResponse
import csv
from datetime import datetime, timedelta

from .models import VolunteerProfile
from .eoi_models import EOISubmission, EOIProfileInformation, EOIRecruitmentPreferences, EOIGamesInformation, CorporateVolunteerGroup
from accounts.models import User


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for VolunteerProfile with comprehensive search,
    filtering, and management capabilities.
    """
    
    # List display configuration
    list_display = (
        'user', 'status', 'experience_level', 'availability_level',
        'application_date', 'approval_date', 'performance_rating',
        'is_corporate_volunteer', 'background_check_status'
    )
    
    # Advanced filtering
    list_filter = (
        'status', 'experience_level', 'availability_level',
        'background_check_status', 'reference_check_status',
        'is_corporate_volunteer', 'has_own_transport',
        ('application_date', admin.DateFieldListFilter),
        ('approval_date', admin.DateFieldListFilter),
        ('review_date', admin.DateFieldListFilter),
        'reviewed_by', 't_shirt_size'
    )
    
    # Search fields
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'preferred_name', 'emergency_contact_name', 'corporate_group_name',
        'special_skills', 'previous_events', 'notes'
    )
    
    # Ordering
    ordering = ('-application_date', 'user__last_name', 'user__first_name')
    
    # Items per page
    list_per_page = 25
    
    # Fieldsets for organized form layout
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'status', 'preferred_name'),
            'classes': ('wide',)
        }),
        (_('Application Status'), {
            'fields': (
                'application_date', 'review_date', 'approval_date',
                'reviewed_by', 'status_changed_at', 'status_changed_by'
            ),
            'classes': ('collapse',)
        }),
        (_('Emergency Contact'), {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            ),
            'classes': ('wide',)
        }),
        (_('Medical Information'), {
            'fields': ('medical_conditions', 'dietary_requirements', 'mobility_requirements'),
            'classes': ('collapse',)
        }),
        (_('Experience & Skills'), {
            'fields': (
                'experience_level', 'previous_events', 'special_skills',
                'languages_spoken'
            ),
            'classes': ('wide',)
        }),
        (_('Availability'), {
            'fields': (
                'availability_level', 'available_dates', 'unavailable_dates',
                'preferred_time_slots', 'max_hours_per_day'
            ),
            'classes': ('collapse',)
        }),
        (_('Preferences'), {
            'fields': (
                'preferred_roles', 'preferred_venues', 'preferred_sports',
                'role_restrictions'
            ),
            'classes': ('collapse',)
        }),
        (_('Physical Capabilities'), {
            'fields': (
                'can_lift_heavy_items', 'can_stand_long_periods',
                'can_work_outdoors', 'can_work_with_crowds'
            ),
            'classes': ('collapse',)
        }),
        (_('Transport & Logistics'), {
            'fields': ('has_own_transport', 'transport_method'),
            'classes': ('collapse',)
        }),
        (_('Uniform & Equipment'), {
            'fields': ('t_shirt_size', 'requires_uniform', 'has_own_equipment'),
            'classes': ('collapse',)
        }),
        (_('Communication'), {
            'fields': ('preferred_communication_method', 'communication_frequency'),
            'classes': ('collapse',)
        }),
        (_('Training'), {
            'fields': ('training_completed', 'training_required', 'training_preferences'),
            'classes': ('collapse',)
        }),
        (_('Background Checks'), {
            'fields': (
                'background_check_status', 'background_check_date',
                'background_check_expiry', 'references', 'reference_check_status'
            ),
            'classes': ('collapse',)
        }),
        (_('Corporate Volunteering'), {
            'fields': (
                'is_corporate_volunteer', 'corporate_group_name',
                'group_leader_contact'
            ),
            'classes': ('collapse',)
        }),
        (_('Consent & Marketing'), {
            'fields': ('social_media_consent', 'photo_consent', 'testimonial_consent'),
            'classes': ('collapse',)
        }),
        (_('Performance'), {
            'fields': ('performance_rating', 'feedback_summary', 'commendations'),
            'classes': ('collapse',)
        }),
        (_('Administrative'), {
            'fields': ('notes', 'tags'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'application_date',
        'status_changed_at'
    )
    
    # Raw ID fields for better performance
    raw_id_fields = ('user', 'reviewed_by', 'status_changed_by')
    
    # Bulk actions
    actions = [
        'approve_volunteers', 'reject_volunteers', 'activate_volunteers',
        'suspend_volunteers', 'export_volunteer_data'
    ]
    
    def approve_volunteers(self, request, queryset):
        """Bulk approve volunteer applications"""
        updated = 0
        for volunteer in queryset.filter(status__in=['PENDING', 'UNDER_REVIEW']):
            volunteer.approve(approved_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'Successfully approved {updated} volunteer applications.',
            messages.SUCCESS
        )
    approve_volunteers.short_description = _('Approve selected volunteer applications')
    
    def reject_volunteers(self, request, queryset):
        """Bulk reject volunteer applications"""
        updated = 0
        for volunteer in queryset.filter(status__in=['PENDING', 'UNDER_REVIEW']):
            volunteer.reject(rejected_by=request.user, reason='Bulk rejection via admin')
            updated += 1
        
        self.message_user(
            request,
            f'Successfully rejected {updated} volunteer applications.',
            messages.WARNING
        )
    reject_volunteers.short_description = _('Reject selected volunteer applications')
    
    def activate_volunteers(self, request, queryset):
        """Bulk activate approved volunteers"""
        updated = 0
        for volunteer in queryset.filter(status='APPROVED'):
            volunteer.activate(activated_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'Successfully activated {updated} volunteers.',
            messages.SUCCESS
        )
    activate_volunteers.short_description = _('Activate selected volunteers')
    
    def suspend_volunteers(self, request, queryset):
        """Bulk suspend volunteers"""
        updated = 0
        for volunteer in queryset.filter(status='ACTIVE'):
            volunteer.suspend(suspended_by=request.user, reason='Bulk suspension via admin')
            updated += 1
        
        self.message_user(
            request,
            f'Successfully suspended {updated} volunteers.',
            messages.WARNING
        )
    suspend_volunteers.short_description = _('Suspend selected volunteers')
    
    def export_volunteer_data(self, request, queryset):
        """Export volunteer data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="volunteer_data.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User', 'Email', 'Status', 'Experience Level', 'Application Date',
            'Approval Date', 'Emergency Contact', 'Phone', 'T-Shirt Size',
            'Background Check Status', 'Performance Rating'
        ])
        
        for volunteer in queryset:
            writer.writerow([
                str(volunteer.user),
                volunteer.user.email,
                volunteer.get_status_display(),
                volunteer.get_experience_level_display(),
                volunteer.application_date.strftime('%Y-%m-%d') if volunteer.application_date else '',
                volunteer.approval_date.strftime('%Y-%m-%d') if volunteer.approval_date else '',
                volunteer.emergency_contact_name,
                volunteer.emergency_contact_phone,
                volunteer.get_t_shirt_size_display(),
                volunteer.get_background_check_status_display(),
                volunteer.performance_rating or ''
            ])
        
        return response
    export_volunteer_data.short_description = _('Export volunteer data to CSV')


@admin.register(EOISubmission)
class EOISubmissionAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for EOI submissions with progress tracking and review capabilities.
    """
    
    # List display configuration
    list_display = (
        'get_applicant_name', 'volunteer_type', 'status', 'completion_percentage',
        'created_at', 'submitted_at', 'reviewed_by'
    )
    
    # Advanced filtering
    list_filter = (
        'status', 'volunteer_type',
        'profile_section_complete', 'recruitment_section_complete', 'games_section_complete',
        ('created_at', admin.DateFieldListFilter),
        ('submitted_at', admin.DateFieldListFilter),
        ('reviewed_at', admin.DateFieldListFilter),
        'reviewed_by', 'confirmation_email_sent'
    )
    
    # Search fields
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'session_key', 'review_notes'
    )
    
    # Ordering
    ordering = ('-created_at',)
    
    # Items per page
    list_per_page = 25
    
    # Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'volunteer_type', 'status', 'session_key'),
            'classes': ('wide',)
        }),
        (_('Progress Tracking'), {
            'fields': (
                'completion_percentage', 'profile_section_complete',
                'recruitment_section_complete', 'games_section_complete'
            ),
            'classes': ('wide',)
        }),
        (_('Review Information'), {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
        (_('Communication'), {
            'fields': ('confirmation_email_sent', 'confirmation_email_sent_at'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'submitted_at', 'reviewed_at',
        'confirmation_email_sent_at', 'completion_percentage'
    )
    
    # Raw ID fields
    raw_id_fields = ('user', 'reviewed_by')
    
    def get_applicant_name(self, obj):
        """Get applicant name from user or profile information"""
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        try:
            profile = obj.profile_information
            return f"{profile.first_name} {profile.last_name}"
        except:
            return "Anonymous"
    get_applicant_name.short_description = _('Applicant Name')
    get_applicant_name.admin_order_field = 'user__last_name'


@admin.register(EOIProfileInformation)
class EOIProfileInformationAdmin(admin.ModelAdmin):
    """
    Admin interface for EOI Profile Information
    """
    
    list_display = (
        'get_full_name', 'email', 'phone_number', 'date_of_birth',
        'city', 'created_at'
    )
    
    list_filter = (
        'gender', 'education_level', 'employment_status',
        'country', 'state_province',
        ('date_of_birth', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter)
    )
    
    search_fields = (
        'first_name', 'last_name', 'preferred_name', 'email',
        'phone_number', 'city', 'emergency_contact_name'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = _('Full Name')
    get_full_name.admin_order_field = 'last_name'


@admin.register(EOIRecruitmentPreferences)
class EOIRecruitmentPreferencesAdmin(admin.ModelAdmin):
    """
    Admin interface for EOI Recruitment Preferences
    """
    
    list_display = (
        'eoi_submission', 'volunteer_experience_level', 'availability_level',
        'has_own_transport', 'leadership_interest', 'created_at'
    )
    
    list_filter = (
        'volunteer_experience_level', 'availability_level',
        'has_own_transport', 'leadership_interest',
        'can_lift_heavy_items', 'can_stand_long_periods',
        'can_work_outdoors', 'can_work_with_crowds',
        'transport_method', 'preferred_communication_method',
        ('created_at', admin.DateFieldListFilter)
    )
    
    search_fields = (
        'eoi_submission__user__username', 'motivation', 'volunteer_goals',
        'special_skills', 'previous_events'
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EOIGamesInformation)
class EOIGamesInformationAdmin(admin.ModelAdmin):
    """
    Admin interface for EOI Games Information
    """
    
    list_display = (
        'eoi_submission', 't_shirt_size', 'photo_consent',
        'has_food_allergies', 'requires_accommodation',
        'is_part_of_group', 'created_at'
    )
    
    list_filter = (
        't_shirt_size', 'photo_consent', 'social_media_consent',
        'testimonial_consent', 'has_food_allergies',
        'requires_accommodation', 'is_part_of_group',
        'uniform_collection_preference',
        'terms_accepted', 'privacy_policy_accepted',
        'code_of_conduct_accepted',
        ('created_at', admin.DateFieldListFilter)
    )
    
    search_fields = (
        'eoi_submission__user__username', 'dietary_requirements',
        'food_allergy_details', 'group_name', 'group_leader_name',
        'additional_information', 'how_did_you_hear'
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CorporateVolunteerGroup)
class CorporateVolunteerGroupAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Corporate Volunteer Groups
    """
    
    list_display = (
        'name', 'primary_contact_name', 'primary_contact_email',
        'expected_volunteer_count', 'status', 'created_at'
    )
    
    list_filter = (
        'status', 'industry_sector', 'country', 'state_province',
        ('created_at', admin.DateFieldListFilter),
        ('approved_at', admin.DateFieldListFilter),
        'approved_by'
    )
    
    search_fields = (
        'name', 'description', 'primary_contact_name',
        'primary_contact_email', 'industry_sector', 'city'
    )
    
    ordering = ('name',)
    
    fieldsets = (
        (_('Group Information'), {
            'fields': ('name', 'description', 'website', 'industry_sector'),
            'classes': ('wide',)
        }),
        (_('Contact Information'), {
            'fields': (
                'primary_contact_name', 'primary_contact_email',
                'primary_contact_phone'
            ),
            'classes': ('wide',)
        }),
        (_('Address'), {
            'fields': (
                'address_line_1', 'address_line_2', 'city',
                'state_province', 'postal_code', 'country'
            ),
            'classes': ('collapse',)
        }),
        (_('Group Details'), {
            'fields': (
                'status', 'expected_volunteer_count',
                'preferred_volunteer_roles', 'preferred_venues',
                'group_requirements'
            ),
            'classes': ('wide',)
        }),
        (_('Approval'), {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    raw_id_fields = ('approved_by',)


# Customize admin site header and title
admin.site.site_header = "SOI Hub Administration"
admin.site.site_title = "SOI Hub Admin"
admin.site.index_title = "ISG 2026 Volunteer Management System"
