from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import Event, Venue, Role, Assignment

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for the Event model with comprehensive management features
    """
    
    # List display configuration
    list_display = (
        'name', 'short_name', 'event_type', 'status', 'start_date', 'end_date',
        'volunteer_progress', 'venue_count', 'is_active', 'is_public', 'created_at'
    )
    
    list_filter = (
        'status', 'event_type', 'is_active', 'is_public', 'is_featured',
        'host_country', 'start_date', 'end_date', 'created_at'
    )
    
    search_fields = (
        'name', 'short_name', 'slug', 'description', 'tagline',
        'host_city', 'host_country'
    )
    
    ordering = ('-start_date', 'name')
    
    # Fieldsets for add/edit forms
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'short_name', 'event_type', 'status'),
            'classes': ('wide',)
        }),
        (_('Event Details'), {
            'fields': ('description', 'tagline', 'welcome_message', 'instructions'),
            'classes': ('collapse',)
        }),
        (_('Dates & Timing'), {
            'fields': (
                'start_date', 'end_date', 'timezone',
                'registration_open_date', 'registration_close_date'
            ),
            'classes': ('wide',)
        }),
        (_('Location'), {
            'fields': ('host_city', 'host_country'),
            'classes': ('wide',)
        }),
        (_('Volunteer Management'), {
            'fields': ('volunteer_target', 'volunteer_minimum_age'),
            'classes': ('wide',)
        }),
        (_('Branding & Assets'), {
            'fields': ('logo', 'banner_image'),
            'classes': ('collapse',)
        }),
        (_('Status & Visibility'), {
            'fields': ('is_active', 'is_public', 'is_featured'),
            'classes': ('wide',)
        }),
        (_('Management'), {
            'fields': ('created_by', 'event_managers'),
            'classes': ('collapse',)
        }),
        (_('Configuration'), {
            'fields': (
                'event_configuration', 'volunteer_configuration',
                'venue_configuration', 'role_configuration'
            ),
            'classes': ('collapse',),
            'description': _('JSON configuration fields for flexible event setup')
        }),
        (_('Advanced Settings'), {
            'fields': (
                'features_enabled', 'integrations_config',
                'contact_information', 'brand_colors', 'external_references'
            ),
            'classes': ('collapse',)
        }),
        (_('Audit Information'), {
            'fields': (
                'status_changed_at', 'status_changed_by',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'status_changed_at',
        'volunteer_progress_display', 'venue_count_display', 'role_count_display'
    )
    
    # Prepopulated fields
    prepopulated_fields = {'slug': ('name',)}
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ('event_managers',)
    
    # Custom methods for list display
    def volunteer_progress(self, obj):
        """Display volunteer recruitment progress"""
        if obj.volunteer_target == 0:
            return "No target set"
        
        current = obj.get_volunteer_count()
        target = obj.volunteer_target
        percentage = (current / target) * 100
        
        color = 'green' if percentage >= 80 else 'orange' if percentage >= 50 else 'red'
        
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color, current, target, round(percentage, 1)
        )
    volunteer_progress.short_description = _('Volunteer Progress')
    
    def venue_count(self, obj):
        """Display number of venues"""
        count = obj.get_venue_count()
        if count == 0:
            return format_html('<span style="color: gray;">0</span>')
        return format_html('<strong>{}</strong>', count)
    venue_count.short_description = _('Venues')
    
    def volunteer_progress_display(self, obj):
        """Detailed volunteer progress for readonly display"""
        current = obj.get_volunteer_count()
        target = obj.volunteer_target
        percentage = obj.get_volunteer_target_progress()
        
        return format_html(
            '{} / {} volunteers ({}%)',
            current, target, round(percentage, 1)
        )
    volunteer_progress_display.short_description = _('Volunteer Progress')
    
    def venue_count_display(self, obj):
        """Venue count for readonly display"""
        return obj.get_venue_count()
    venue_count_display.short_description = _('Number of Venues')
    
    def role_count_display(self, obj):
        """Role count for readonly display"""
        return obj.get_role_count()
    role_count_display.short_description = _('Number of Roles')
    
    # Custom actions
    actions = [
        'activate_events', 'deactivate_events', 'make_public', 'make_private',
        'open_registration', 'close_registration', 'mark_featured', 'unmark_featured'
    ]
    
    def activate_events(self, request, queryset):
        """Activate selected events"""
        updated = 0
        for event in queryset.filter(is_active=False):
            event.activate(activated_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'{updated} event(s) were successfully activated.'
        )
    activate_events.short_description = _('Activate selected events')
    
    def deactivate_events(self, request, queryset):
        """Deactivate selected events"""
        updated = 0
        for event in queryset.filter(is_active=True):
            event.deactivate(deactivated_by=request.user, reason="Bulk admin action")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} event(s) were successfully deactivated.'
        )
    deactivate_events.short_description = _('Deactivate selected events')
    
    def make_public(self, request, queryset):
        """Make selected events public"""
        updated = queryset.filter(is_public=False).update(is_public=True)
        
        self.message_user(
            request,
            f'{updated} event(s) were made public.'
        )
    make_public.short_description = _('Make selected events public')
    
    def make_private(self, request, queryset):
        """Make selected events private"""
        updated = queryset.filter(is_public=True).update(is_public=False)
        
        self.message_user(
            request,
            f'{updated} event(s) were made private.'
        )
    make_private.short_description = _('Make selected events private')
    
    def open_registration(self, request, queryset):
        """Open registration for selected events"""
        updated = 0
        for event in queryset.exclude(status=Event.EventStatus.REGISTRATION_OPEN):
            event.change_status(
                Event.EventStatus.REGISTRATION_OPEN,
                changed_by=request.user,
                notes="Registration opened via admin action"
            )
            updated += 1
        
        self.message_user(
            request,
            f'Registration opened for {updated} event(s).'
        )
    open_registration.short_description = _('Open registration for selected events')
    
    def close_registration(self, request, queryset):
        """Close registration for selected events"""
        updated = 0
        for event in queryset.filter(status=Event.EventStatus.REGISTRATION_OPEN):
            event.change_status(
                Event.EventStatus.REGISTRATION_CLOSED,
                changed_by=request.user,
                notes="Registration closed via admin action"
            )
            updated += 1
        
        self.message_user(
            request,
            f'Registration closed for {updated} event(s).'
        )
    close_registration.short_description = _('Close registration for selected events')
    
    def mark_featured(self, request, queryset):
        """Mark selected events as featured"""
        updated = queryset.filter(is_featured=False).update(is_featured=True)
        
        self.message_user(
            request,
            f'{updated} event(s) were marked as featured.'
        )
    mark_featured.short_description = _('Mark selected events as featured')
    
    def unmark_featured(self, request, queryset):
        """Unmark selected events as featured"""
        updated = queryset.filter(is_featured=True).update(is_featured=False)
        
        self.message_user(
            request,
            f'{updated} event(s) were unmarked as featured.'
        )
    unmark_featured.short_description = _('Unmark selected events as featured')
    
    # Custom form handling
    def save_model(self, request, obj, form, change):
        """Custom save handling with audit trail"""
        if not change:  # New event
            obj.created_by = request.user
        
        # Track status changes
        if change and 'status' in form.changed_data:
            obj.status_changed_by = request.user
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance"""
        return super().get_queryset(request).select_related(
            'created_by', 'status_changed_by'
        ).prefetch_related('event_managers')
    
    # Custom display methods
    def has_change_permission(self, request, obj=None):
        """Custom permission checking"""
        if obj is None:
            return super().has_change_permission(request, obj)
        
        # Superusers can edit any event
        if request.user.is_superuser:
            return True
        
        # Event managers can edit their events
        if obj.event_managers.filter(id=request.user.id).exists():
            return True
        
        # GOC and Admin users can edit events
        if request.user.can_manage_events():
            return True
        
        return super().has_change_permission(request, obj)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit fields for non-superusers
        if not request.user.is_superuser:
            # Remove sensitive fields for non-superusers
            sensitive_fields = ['created_by', 'status_changed_by']
            for field in sensitive_fields:
                if field in form.base_fields:
                    form.base_fields[field].widget.attrs['readonly'] = True
        
        return form
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamic readonly fields based on user permissions"""
        readonly = list(self.readonly_fields)
        
        # Add fields based on permissions
        if not request.user.is_superuser:
            readonly.extend(['created_by', 'external_references'])
        
        return readonly
    
    # Enhanced filtering
    def get_list_filter(self, request):
        """Dynamic list filters based on user permissions"""
        filters = list(self.list_filter)
        
        # Add additional filters for superusers
        if request.user.is_superuser:
            filters.extend(['created_by', 'status_changed_by'])
        
        return filters
    
    # Custom admin URLs and views
    def get_urls(self):
        """Add custom admin URLs"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/clone/',
                self.admin_site.admin_view(self.clone_event_view),
                name='events_event_clone'
            ),
            path(
                '<path:object_id>/configuration/',
                self.admin_site.admin_view(self.configuration_view),
                name='events_event_configuration'
            ),
        ]
        return custom_urls + urls
    
    def clone_event_view(self, request, object_id):
        """Custom view for cloning events"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        event = get_object_or_404(Event, pk=object_id)
        
        if request.method == 'POST':
            new_name = request.POST.get('new_name')
            new_slug = request.POST.get('new_slug')
            
            if new_name and new_slug:
                try:
                    new_event = event.clone(new_name, new_slug, request.user)
                    messages.success(
                        request,
                        f'Event "{new_name}" was successfully cloned from "{event.name}".'
                    )
                    return redirect('admin:events_event_change', new_event.id)
                except Exception as e:
                    messages.error(request, f'Error cloning event: {e}')
        
        # Render clone form (would need template)
        return redirect('admin:events_event_changelist')
    
    def configuration_view(self, request, object_id):
        """Custom view for managing event configuration"""
        from django.shortcuts import get_object_or_404, redirect
        
        event = get_object_or_404(Event, pk=object_id)
        
        # Handle configuration updates
        if request.method == 'POST':
            # Process configuration form data
            pass
        
        # Render configuration form (would need template)
        return redirect('admin:events_event_change', object_id)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for the Venue model with comprehensive management features
    """
    
    # List display configuration
    list_display = (
        'name', 'event', 'venue_type', 'status', 'city', 'country',
        'capacity_info', 'accessibility_display', 'is_active', 'is_primary', 'created_at'
    )
    
    list_filter = (
        'event', 'status', 'venue_type', 'accessibility_level',
        'is_active', 'is_primary', 'requires_security_clearance',
        'wheelchair_accessible', 'catering_available', 'wifi_available',
        'city', 'country', 'created_at'
    )
    
    search_fields = (
        'name', 'short_name', 'slug', 'description', 'purpose',
        'address_line_1', 'address_line_2', 'city', 'county',
        'venue_manager', 'contact_email'
    )
    
    ordering = ('event', 'name')
    
    # Fieldsets for add/edit forms
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('event', 'name', 'slug', 'short_name', 'venue_type', 'status'),
            'classes': ('wide',)
        }),
        (_('Venue Details'), {
            'fields': ('description', 'purpose'),
            'classes': ('collapse',)
        }),
        (_('Address & Location'), {
            'fields': (
                'address_line_1', 'address_line_2', 'city', 'county',
                'postal_code', 'country', 'latitude', 'longitude'
            ),
            'classes': ('wide',)
        }),
        (_('Capacity Management'), {
            'fields': ('total_capacity', 'volunteer_capacity', 'spectator_capacity'),
            'classes': ('wide',)
        }),
        (_('Accessibility'), {
            'fields': (
                'accessibility_level', 'wheelchair_accessible', 'accessible_parking',
                'accessible_toilets', 'hearing_loop'
            ),
            'classes': ('wide',)
        }),
        (_('Transport & Parking'), {
            'fields': ('public_transport_access', 'parking_spaces', 'parking_cost'),
            'classes': ('collapse',)
        }),
        (_('Facilities & Amenities'), {
            'fields': ('catering_available', 'wifi_available', 'first_aid_station'),
            'classes': ('wide',)
        }),
        (_('Contact Information'), {
            'fields': ('venue_manager', 'contact_phone', 'contact_email'),
            'classes': ('collapse',)
        }),
        (_('Media & Documentation'), {
            'fields': ('venue_image', 'floor_plan', 'venue_map'),
            'classes': ('collapse',)
        }),
        (_('Status & Management'), {
            'fields': ('is_active', 'is_primary', 'requires_security_clearance'),
            'classes': ('wide',)
        }),
        (_('Venue Coordinators'), {
            'fields': ('created_by', 'venue_coordinators'),
            'classes': ('collapse',)
        }),
        (_('Configuration'), {
            'fields': ('venue_configuration', 'facilities', 'operational_hours', 'equipment_available'),
            'classes': ('collapse',),
            'description': _('JSON configuration fields for flexible venue setup')
        }),
        (_('Emergency Contact'), {
            'fields': ('emergency_contact',),
            'classes': ('collapse',)
        }),
        (_('Audit Information'), {
            'fields': (
                'status_changed_at', 'status_changed_by',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        (_('Notes & References'), {
            'fields': ('notes', 'external_references'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'status_changed_at',
        'capacity_utilization_display', 'role_count_display', 'assigned_volunteers_display'
    )
    
    # Prepopulated fields
    prepopulated_fields = {'slug': ('name',)}
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ('venue_coordinators',)
    
    # Custom methods for list display
    def capacity_info(self, obj):
        """Display capacity information"""
        utilization = obj.get_capacity_utilization()
        color = 'green' if utilization < 80 else 'orange' if utilization < 95 else 'red'
        
        return format_html(
            '<span style="color: {};">Vol: {}/{} ({}%)<br/>Spec: {}</span>',
            color,
            obj.get_assigned_volunteer_count(),
            obj.volunteer_capacity,
            round(utilization, 1),
            obj.spectator_capacity
        )
    capacity_info.short_description = _('Capacity Info')
    
    def accessibility_display(self, obj):
        """Display accessibility information"""
        level_colors = {
            'FULL': 'green',
            'PARTIAL': 'orange',
            'LIMITED': 'red',
            'NOT_ACCESSIBLE': 'darkred',
            'UNKNOWN': 'gray'
        }
        
        color = level_colors.get(obj.accessibility_level, 'gray')
        features = obj.get_accessibility_features()
        
        return format_html(
            '<span style="color: {};">{}<br/><small>{}</small></span>',
            color,
            obj.get_accessibility_level_display(),
            ', '.join(features[:2]) if features else 'No features'
        )
    accessibility_display.short_description = _('Accessibility')
    
    def capacity_utilization_display(self, obj):
        """Detailed capacity utilization for readonly display"""
        utilization = obj.get_capacity_utilization()
        return format_html(
            'Volunteers: {} / {} ({}%)<br/>Available: {}',
            obj.get_assigned_volunteer_count(),
            obj.volunteer_capacity,
            round(utilization, 1),
            obj.get_available_capacity()
        )
    capacity_utilization_display.short_description = _('Capacity Utilization')
    
    def role_count_display(self, obj):
        """Role count for readonly display"""
        return obj.get_role_count()
    role_count_display.short_description = _('Number of Roles')
    
    def assigned_volunteers_display(self, obj):
        """Assigned volunteers count for readonly display"""
        return obj.get_assigned_volunteer_count()
    assigned_volunteers_display.short_description = _('Assigned Volunteers')
    
    # Custom actions
    actions = [
        'activate_venues', 'deactivate_venues', 'set_as_primary', 'unset_as_primary',
        'confirm_venues', 'mark_setup_complete', 'mark_active', 'export_venue_data'
    ]
    
    def activate_venues(self, request, queryset):
        """Activate selected venues"""
        updated = 0
        for venue in queryset.filter(is_active=False):
            venue.activate(activated_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'{updated} venue(s) were successfully activated.'
        )
    activate_venues.short_description = _('Activate selected venues')
    
    def deactivate_venues(self, request, queryset):
        """Deactivate selected venues"""
        updated = 0
        for venue in queryset.filter(is_active=True):
            venue.deactivate(deactivated_by=request.user, reason="Bulk admin action")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} venue(s) were successfully deactivated.'
        )
    deactivate_venues.short_description = _('Deactivate selected venues')
    
    def set_as_primary(self, request, queryset):
        """Set selected venues as primary"""
        updated = 0
        for venue in queryset.filter(is_primary=False):
            venue.set_as_primary(set_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'{updated} venue(s) were set as primary.'
        )
    set_as_primary.short_description = _('Set selected venues as primary')
    
    def unset_as_primary(self, request, queryset):
        """Unset selected venues as primary"""
        updated = queryset.filter(is_primary=True).update(is_primary=False)
        
        self.message_user(
            request,
            f'{updated} venue(s) were unset as primary.'
        )
    unset_as_primary.short_description = _('Unset selected venues as primary')
    
    def confirm_venues(self, request, queryset):
        """Confirm selected venues"""
        updated = 0
        for venue in queryset.exclude(status=Venue.VenueStatus.CONFIRMED):
            venue.change_status(
                Venue.VenueStatus.CONFIRMED,
                changed_by=request.user,
                notes="Venue confirmed via admin action"
            )
            updated += 1
        
        self.message_user(
            request,
            f'{updated} venue(s) were confirmed.'
        )
    confirm_venues.short_description = _('Confirm selected venues')
    
    def mark_setup_complete(self, request, queryset):
        """Mark setup complete for selected venues"""
        updated = 0
        for venue in queryset.exclude(status=Venue.VenueStatus.ACTIVE):
            venue.change_status(
                Venue.VenueStatus.ACTIVE,
                changed_by=request.user,
                notes="Setup completed via admin action"
            )
            updated += 1
        
        self.message_user(
            request,
            f'Setup marked complete for {updated} venue(s).'
        )
    mark_setup_complete.short_description = _('Mark setup complete for selected venues')
    
    def mark_active(self, request, queryset):
        """Mark selected venues as active/operational"""
        updated = 0
        for venue in queryset.exclude(status=Venue.VenueStatus.ACTIVE):
            venue.change_status(
                Venue.VenueStatus.ACTIVE,
                changed_by=request.user,
                notes="Venue marked active via admin action"
            )
            updated += 1
        
        self.message_user(
            request,
            f'{updated} venue(s) were marked as active.'
        )
    mark_active.short_description = _('Mark selected venues as active')
    
    def export_venue_data(self, request, queryset):
        """Export venue data (placeholder for future implementation)"""
        self.message_user(
            request,
            f'Export functionality will be implemented in future version. {queryset.count()} venues selected.'
        )
    export_venue_data.short_description = _('Export venue data')
    
    # Custom form handling
    def save_model(self, request, obj, form, change):
        """Custom save handling with audit trail"""
        if not change:  # New venue
            obj.created_by = request.user
        
        # Track status changes
        if change and 'status' in form.changed_data:
            obj.status_changed_by = request.user
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance"""
        return super().get_queryset(request).select_related(
            'event', 'created_by', 'status_changed_by'
        ).prefetch_related('venue_coordinators')
    
    # Custom display methods
    def has_change_permission(self, request, obj=None):
        """Custom permission checking"""
        if obj is None:
            return super().has_change_permission(request, obj)
        
        # Superusers can edit any venue
        if request.user.is_superuser:
            return True
        
        # Event managers can edit venues for their events
        if obj.event.event_managers.filter(id=request.user.id).exists():
            return True
        
        # Venue coordinators can edit their venues
        if obj.venue_coordinators.filter(id=request.user.id).exists():
            return True
        
        # GOC and Admin users can edit venues
        if request.user.can_manage_events():
            return True
        
        return super().has_change_permission(request, obj)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit event choices for non-superusers
        if not request.user.is_superuser and 'event' in form.base_fields:
            # Filter events to only those the user can manage
            if hasattr(request.user, 'managed_events'):
                form.base_fields['event'].queryset = request.user.managed_events.all()
        
        return form
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamic readonly fields based on user permissions"""
        readonly = list(self.readonly_fields)
        
        # Add fields based on permissions
        if not request.user.is_superuser:
            readonly.extend(['created_by', 'external_references'])
        
        return readonly
    
    # Enhanced filtering
    def get_list_filter(self, request):
        """Dynamic list filters based on user permissions"""
        filters = list(self.list_filter)
        
        # Add additional filters for superusers
        if request.user.is_superuser:
            filters.extend(['created_by', 'status_changed_by'])
        
        return filters


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for the Role model with comprehensive management features
    """
    
    # List display configuration
    list_display = (
        'name', 'event', 'venue', 'role_type', 'status', 'capacity_info',
        'requirements_summary', 'priority_level', 'is_featured', 'is_urgent', 'created_at'
    )
    
    list_filter = (
        'event', 'venue', 'role_type', 'status', 'skill_level_required',
        'commitment_level', 'priority_level', 'is_featured', 'is_urgent', 'is_public',
        'training_required', 'uniform_required', 'requires_garda_vetting',
        'requires_child_protection', 'requires_security_clearance',
        'meal_provided', 'transport_provided', 'accommodation_provided',
        'created_at'
    )
    
    search_fields = (
        'name', 'short_name', 'slug', 'description', 'summary',
        'contact_person', 'contact_email', 'application_process'
    )
    
    ordering = ('event', 'venue', 'priority_level', 'name')
    
    # Fieldsets for add/edit forms
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('event', 'venue', 'name', 'slug', 'short_name', 'role_type', 'status'),
            'classes': ('wide',)
        }),
        (_('Role Details'), {
            'fields': ('description', 'summary'),
            'classes': ('collapse',)
        }),
        (_('Requirements & Qualifications'), {
            'fields': (
                'minimum_age', 'maximum_age', 'skill_level_required',
                'physical_requirements', 'language_requirements'
            ),
            'classes': ('wide',)
        }),
        (_('Credentials & Certifications'), {
            'fields': (
                'required_credentials', 'preferred_credentials', 'justgo_credentials_required',
                'requires_garda_vetting', 'requires_child_protection', 'requires_security_clearance'
            ),
            'classes': ('collapse',)
        }),
        (_('Capacity & Scheduling'), {
            'fields': (
                'total_positions', 'filled_positions', 'minimum_volunteers',
                'commitment_level', 'estimated_hours_per_day', 'total_estimated_hours'
            ),
            'classes': ('wide',)
        }),
        (_('Schedule Requirements'), {
            'fields': ('schedule_requirements', 'availability_windows'),
            'classes': ('collapse',)
        }),
        (_('Training & Preparation'), {
            'fields': (
                'training_required', 'training_duration_hours', 'training_materials'
            ),
            'classes': ('collapse',)
        }),
        (_('Equipment & Uniform'), {
            'fields': (
                'uniform_required', 'uniform_details',
                'equipment_provided', 'equipment_required'
            ),
            'classes': ('collapse',)
        }),
        (_('Benefits & Incentives'), {
            'fields': (
                'benefits', 'meal_provided', 'transport_provided', 'accommodation_provided'
            ),
            'classes': ('collapse',)
        }),
        (_('Contact & Management'), {
            'fields': (
                'role_supervisor', 'contact_person', 'contact_email', 'contact_phone'
            ),
            'classes': ('collapse',)
        }),
        (_('Priority & Visibility'), {
            'fields': ('priority_level', 'is_featured', 'is_urgent', 'is_public'),
            'classes': ('wide',)
        }),
        (_('Application & Selection'), {
            'fields': (
                'application_deadline', 'selection_criteria', 'application_process'
            ),
            'classes': ('collapse',)
        }),
        (_('Role Coordinators'), {
            'fields': ('created_by', 'role_coordinators'),
            'classes': ('collapse',)
        }),
        (_('Configuration'), {
            'fields': ('role_configuration', 'custom_fields'),
            'classes': ('collapse',),
            'description': _('JSON configuration fields for flexible role setup')
        }),
        (_('Audit Information'), {
            'fields': (
                'status_changed_at', 'status_changed_by',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        (_('Notes & References'), {
            'fields': ('notes', 'external_references'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at', 'updated_at', 'status_changed_at',
        'capacity_percentage_display', 'application_status_display', 'requirements_display'
    )
    
    # Prepopulated fields
    prepopulated_fields = {'slug': ('name',)}
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ('role_coordinators',)
    
    # Custom methods for list display
    def capacity_info(self, obj):
        """Display capacity information"""
        percentage = obj.get_capacity_percentage()
        available = obj.get_available_positions()
        
        if obj.is_full():
            color = 'red'
            status = 'FULL'
        elif obj.is_understaffed():
            color = 'orange'
            status = 'UNDERSTAFFED'
        else:
            color = 'green'
            status = 'OK'
        
        return format_html(
            '<span style="color: {};">{}/{} ({}%)<br/><small>{} - {} available</small></span>',
            color,
            obj.filled_positions,
            obj.total_positions,
            round(percentage, 1),
            status,
            available
        )
    capacity_info.short_description = _('Capacity Info')
    
    def requirements_summary(self, obj):
        """Display requirements summary"""
        requirements = []
        
        if obj.minimum_age > 15:
            requirements.append(f'Age: {obj.minimum_age}+')
        
        if obj.required_credentials:
            requirements.append(f'Creds: {len(obj.required_credentials)}')
        
        if obj.requires_garda_vetting:
            requirements.append('Garda')
        
        if obj.requires_security_clearance:
            requirements.append('Security')
        
        if obj.training_required:
            requirements.append('Training')
        
        summary = ', '.join(requirements[:3])
        if len(requirements) > 3:
            summary += f' +{len(requirements) - 3} more'
        
        return format_html('<small>{}</small>', summary or 'Basic requirements')
    requirements_summary.short_description = _('Requirements')
    
    def capacity_percentage_display(self, obj):
        """Detailed capacity information for readonly display"""
        percentage = obj.get_capacity_percentage()
        available = obj.get_available_positions()
        
        return format_html(
            'Filled: {} / {} ({}%)<br/>Available: {}<br/>Minimum needed: {}',
            obj.filled_positions,
            obj.total_positions,
            round(percentage, 1),
            available,
            obj.minimum_volunteers
        )
    capacity_percentage_display.short_description = _('Capacity Details')
    
    def application_status_display(self, obj):
        """Application status for readonly display"""
        if obj.application_deadline:
            days_left = obj.get_days_until_deadline()
            if days_left is not None:
                if days_left > 0:
                    return format_html(
                        'Open - {} days left<br/>Deadline: {}',
                        days_left,
                        obj.application_deadline.strftime('%Y-%m-%d %H:%M')
                    )
                else:
                    return format_html('<span style="color: red;">Deadline passed</span>')
        
        return 'Open' if obj.is_application_open() else 'Closed'
    application_status_display.short_description = _('Application Status')
    
    def requirements_display(self, obj):
        """Detailed requirements for readonly display"""
        requirements = []
        
        requirements.append(f'Age: {obj.minimum_age}-{obj.maximum_age or "∞"}')
        requirements.append(f'Skill Level: {obj.get_skill_level_required_display()}')
        
        if obj.physical_requirements:
            requirements.append(f'Physical: {", ".join(obj.physical_requirements[:3])}')
        
        if obj.required_credentials:
            requirements.append(f'Credentials: {", ".join(obj.required_credentials[:3])}')
        
        if obj.justgo_credentials_required:
            requirements.append(f'JustGo: {", ".join(obj.justgo_credentials_required[:2])}')
        
        return format_html('<br/>'.join(requirements))
    requirements_display.short_description = _('Detailed Requirements')
    
    # Custom actions
    actions = [
        'activate_roles', 'suspend_roles', 'cancel_roles', 'complete_roles',
        'mark_featured', 'unmark_featured', 'mark_urgent', 'unmark_urgent',
        'make_public', 'make_private', 'export_role_data'
    ]
    
    def activate_roles(self, request, queryset):
        """Activate selected roles"""
        updated = 0
        for role in queryset.exclude(status=Role.RoleStatus.ACTIVE):
            role.activate(activated_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'{updated} role(s) were successfully activated.'
        )
    activate_roles.short_description = _('Activate selected roles')
    
    def suspend_roles(self, request, queryset):
        """Suspend selected roles"""
        updated = 0
        for role in queryset.exclude(status=Role.RoleStatus.SUSPENDED):
            role.suspend(suspended_by=request.user, reason="Bulk admin action")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} role(s) were successfully suspended.'
        )
    suspend_roles.short_description = _('Suspend selected roles')
    
    def cancel_roles(self, request, queryset):
        """Cancel selected roles"""
        updated = 0
        for role in queryset.exclude(status=Role.RoleStatus.CANCELLED):
            role.cancel(cancelled_by=request.user, reason="Bulk admin action")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} role(s) were successfully cancelled.'
        )
    cancel_roles.short_description = _('Cancel selected roles')
    
    def complete_roles(self, request, queryset):
        """Mark selected roles as completed"""
        updated = 0
        for role in queryset.exclude(status=Role.RoleStatus.COMPLETED):
            role.complete(completed_by=request.user)
            updated += 1
        
        self.message_user(
            request,
            f'{updated} role(s) were marked as completed.'
        )
    complete_roles.short_description = _('Mark selected roles as completed')
    
    def mark_featured(self, request, queryset):
        """Mark selected roles as featured"""
        updated = queryset.filter(is_featured=False).update(is_featured=True)
        
        self.message_user(
            request,
            f'{updated} role(s) were marked as featured.'
        )
    mark_featured.short_description = _('Mark selected roles as featured')
    
    def unmark_featured(self, request, queryset):
        """Unmark selected roles as featured"""
        updated = queryset.filter(is_featured=True).update(is_featured=False)
        
        self.message_user(
            request,
            f'{updated} role(s) were unmarked as featured.'
        )
    unmark_featured.short_description = _('Unmark selected roles as featured')
    
    def mark_urgent(self, request, queryset):
        """Mark selected roles as urgent"""
        updated = queryset.filter(is_urgent=False).update(is_urgent=True)
        
        self.message_user(
            request,
            f'{updated} role(s) were marked as urgent.'
        )
    mark_urgent.short_description = _('Mark selected roles as urgent')
    
    def unmark_urgent(self, request, queryset):
        """Unmark selected roles as urgent"""
        updated = queryset.filter(is_urgent=True).update(is_urgent=False)
        
        self.message_user(
            request,
            f'{updated} role(s) were unmarked as urgent.'
        )
    unmark_urgent.short_description = _('Unmark selected roles as urgent')
    
    def make_public(self, request, queryset):
        """Make selected roles public"""
        updated = queryset.filter(is_public=False).update(is_public=True)
        
        self.message_user(
            request,
            f'{updated} role(s) were made public.'
        )
    make_public.short_description = _('Make selected roles public')
    
    def make_private(self, request, queryset):
        """Make selected roles private"""
        updated = queryset.filter(is_public=True).update(is_public=False)
        
        self.message_user(
            request,
            f'{updated} role(s) were made private.'
        )
    make_private.short_description = _('Make selected roles private')
    
    def export_role_data(self, request, queryset):
        """Export role data (placeholder for future implementation)"""
        self.message_user(
            request,
            f'Export functionality for {queryset.count()} role(s) will be implemented.'
        )
    export_role_data.short_description = _('Export selected role data')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new role
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'event', 'venue', 'created_by', 'role_supervisor', 'status_changed_by'
        ).prefetch_related('role_coordinators')
    
    def has_change_permission(self, request, obj=None):
        """Custom permission logic"""
        if not super().has_change_permission(request, obj):
            return False
        
        # Allow role coordinators to edit their roles
        if obj and hasattr(request.user, 'coordinated_roles'):
            if obj in request.user.coordinated_roles.all():
                return True
        
        # Allow event managers to edit roles in their events
        if obj and hasattr(request.user, 'managed_events'):
            if obj.event in request.user.managed_events.all():
                return True
        
        # Allow venue coordinators to edit roles in their venues
        if obj and obj.venue and hasattr(request.user, 'coordinated_venues'):
            if obj.venue in request.user.coordinated_venues.all():
                return True
        
        return True
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit event choices based on user permissions
        if hasattr(request.user, 'managed_events'):
            managed_events = request.user.managed_events.all()
            if managed_events.exists():
                form.base_fields['event'].queryset = managed_events
        
        return form
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamic readonly fields based on user permissions"""
        readonly_fields = list(self.readonly_fields)
        
        # Make certain fields readonly for non-superusers
        if not request.user.is_superuser:
            readonly_fields.extend(['created_by', 'external_references'])
        
        return readonly_fields
    
    def get_list_filter(self, request):
        """Dynamic list filters based on user permissions"""
        # Filter by managed events for event managers
        if hasattr(request.user, 'managed_events'):
            return super().get_list_filter(request)
        
        return super().get_list_filter(request)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for the Assignment model with comprehensive management features,
    status tracking, and admin override support.
    """
    
    # List display configuration
    list_display = (
        'volunteer_name', 'role_name', 'event_name', 'venue_name', 'status',
        'assignment_type', 'priority_level', 'schedule_info', 'admin_override_indicator',
        'attendance_status', 'performance_display', 'assigned_date'
    )
    
    list_filter = (
        'status', 'assignment_type', 'priority_level', 'event', 'venue',
        'is_admin_override', 'age_requirement_override', 'credential_requirement_override',
        'capacity_override', 'assigned_date', 'start_date', 'end_date',
        'performance_rating', 'created_at'
    )
    
    search_fields = (
        'volunteer__first_name', 'volunteer__last_name', 'volunteer__email',
        'role__name', 'role__short_name', 'event__name', 'venue__name',
        'special_instructions', 'notes', 'admin_override_reason'
    )
    
    ordering = ('-created_at', 'event', 'role', 'volunteer')
    
    # Fieldsets for add/edit forms
    fieldsets = (
        (_('Assignment Details'), {
            'fields': ('volunteer', 'role', 'event', 'venue', 'assignment_type', 'status', 'priority_level'),
            'classes': ('wide',)
        }),
        (_('Schedule Information'), {
            'fields': ('start_date', 'end_date', 'start_time', 'end_time'),
            'classes': ('wide',)
        }),
        (_('Assignment Configuration'), {
            'fields': ('special_instructions', 'equipment_assigned', 'uniform_assigned'),
            'classes': ('collapse',)
        }),
        (_('Status Tracking'), {
            'fields': (
                'application_date', 'review_date', 'approval_date',
                'confirmation_date', 'completion_date'
            ),
            'classes': ('collapse',)
        }),
        (_('Admin Override'), {
            'fields': (
                'is_admin_override', 'admin_override_reason', 'admin_override_by', 'admin_override_date',
                'age_requirement_override', 'credential_requirement_override', 'capacity_override',
                'override_justification'
            ),
            'classes': ('collapse',),
            'description': _('Admin override settings - use with caution and proper justification')
        }),
        (_('Attendance Tracking'), {
            'fields': (
                'check_in_time', 'check_out_time', 'actual_hours_worked', 'attendance_notes'
            ),
            'classes': ('collapse',)
        }),
        (_('Performance & Feedback'), {
            'fields': (
                'performance_rating', 'feedback_from_volunteer', 'feedback_from_supervisor'
            ),
            'classes': ('collapse',)
        }),
        (_('Communication'), {
            'fields': (
                'notification_preferences', 'last_notification_sent', 'reminder_count'
            ),
            'classes': ('collapse',)
        }),
        (_('Assignment Management'), {
            'fields': ('assigned_by', 'reviewed_by', 'approved_by'),
            'classes': ('collapse',)
        }),
        (_('Status Change Tracking'), {
            'fields': (
                'status_changed_at', 'status_changed_by', 'status_change_reason'
            ),
            'classes': ('collapse',)
        }),
        (_('Configuration'), {
            'fields': ('assignment_configuration',),
            'classes': ('collapse',),
            'description': _('JSON configuration for assignment-specific settings')
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        (_('Notes & References'), {
            'fields': ('notes', 'external_references'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = (
        'assigned_date', 'created_at', 'updated_at', 'status_changed_at',
        'admin_override_date', 'last_notification_sent',
        'schedule_display', 'time_commitment_display', 'validation_status_display'
    )
    
    # Raw ID fields for better performance with large datasets
    raw_id_fields = ('volunteer', 'role', 'event', 'venue')
    
    # Custom methods for list display
    def volunteer_name(self, obj):
        """Display volunteer name with link"""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.volunteer.id,
            obj.volunteer.get_full_name()
        )
    volunteer_name.short_description = _('Volunteer')
    volunteer_name.admin_order_field = 'volunteer__last_name'
    
    def role_name(self, obj):
        """Display role name with link"""
        return format_html(
            '<a href="/admin/events/role/{}/change/">{}</a>',
            obj.role.id,
            obj.role.name
        )
    role_name.short_description = _('Role')
    role_name.admin_order_field = 'role__name'
    
    def event_name(self, obj):
        """Display event name"""
        return obj.event.short_name or obj.event.name
    event_name.short_description = _('Event')
    event_name.admin_order_field = 'event__name'
    
    def venue_name(self, obj):
        """Display venue name"""
        return obj.venue.short_name or obj.venue.name if obj.venue else '-'
    venue_name.short_description = _('Venue')
    venue_name.admin_order_field = 'venue__name'
    
    def schedule_info(self, obj):
        """Display schedule information"""
        if obj.start_date and obj.end_date:
            if obj.start_date == obj.end_date:
                date_str = obj.start_date.strftime('%m/%d')
            else:
                date_str = f"{obj.start_date.strftime('%m/%d')}-{obj.end_date.strftime('%m/%d')}"
            
            if obj.start_time and obj.end_time:
                time_str = f"{obj.start_time.strftime('%H:%M')}-{obj.end_time.strftime('%H:%M')}"
                return format_html('<small>{}<br/>{}</small>', date_str, time_str)
            else:
                return format_html('<small>{}</small>', date_str)
        
        return format_html('<small style="color: gray;">Not scheduled</small>')
    schedule_info.short_description = _('Schedule')
    
    def admin_override_indicator(self, obj):
        """Display admin override indicator"""
        if obj.is_admin_override:
            overrides = []
            if obj.age_requirement_override:
                overrides.append('Age')
            if obj.credential_requirement_override:
                overrides.append('Creds')
            if obj.capacity_override:
                overrides.append('Cap')
            
            override_text = ', '.join(overrides) if overrides else 'General'
            
            return format_html(
                '<span style="color: red; font-weight: bold;" title="{}">⚠ {}</span>',
                obj.admin_override_reason,
                override_text
            )
        
        return format_html('<span style="color: green;">✓</span>')
    admin_override_indicator.short_description = _('Override')
    
    def attendance_status(self, obj):
        """Display attendance status"""
        if obj.check_in_time and obj.check_out_time:
            hours = obj.actual_hours_worked or 0
            return format_html(
                '<span style="color: green;">✓ Complete<br/><small>{:.1f}h</small></span>',
                float(hours)
            )
        elif obj.check_in_time:
            return format_html('<span style="color: orange;">⏰ Checked In</span>')
        elif obj.status == Assignment.AssignmentStatus.NO_SHOW:
            return format_html('<span style="color: red;">❌ No Show</span>')
        elif obj.status in [Assignment.AssignmentStatus.ACTIVE, Assignment.AssignmentStatus.CONFIRMED]:
            return format_html('<span style="color: blue;">📅 Scheduled</span>')
        
        return format_html('<span style="color: gray;">-</span>')
    attendance_status.short_description = _('Attendance')
    
    def performance_display(self, obj):
        """Display performance rating"""
        if obj.performance_rating:
            stars = '★' * obj.performance_rating + '☆' * (5 - obj.performance_rating)
            return format_html(
                '<span title="Rating: {}/5">{}</span>',
                obj.performance_rating,
                stars
            )
        
        return format_html('<span style="color: gray;">-</span>')
    performance_display.short_description = _('Rating')
    
    def schedule_display(self, obj):
        """Detailed schedule for readonly display"""
        schedule_info = obj.get_schedule_info()
        time_commitment = obj.get_time_commitment()
        
        parts = []
        if schedule_info['start_date']:
            parts.append(f"Start: {schedule_info['start_date']}")
        if schedule_info['end_date']:
            parts.append(f"End: {schedule_info['end_date']}")
        if schedule_info['start_time']:
            parts.append(f"Time: {schedule_info['start_time']}-{schedule_info['end_time']}")
        if time_commitment and time_commitment['duration_days']:
            parts.append(f"Duration: {time_commitment['duration_days']} days")
        
        return format_html('<br/>'.join(parts) if parts else 'Not scheduled')
    schedule_display.short_description = _('Schedule Details')
    
    def time_commitment_display(self, obj):
        """Time commitment details for readonly display"""
        commitment = obj.get_time_commitment()
        if commitment:
            return format_html(
                'Duration: {} days<br/>Hours/day: {}<br/>Total estimated: {:.1f}h<br/>Actual worked: {:.1f}h',
                commitment['duration_days'],
                commitment['hours_per_day'],
                commitment['total_estimated_hours'],
                commitment['actual_hours_worked'] or 0
            )
        
        return 'Not calculated'
    time_commitment_display.short_description = _('Time Commitment')
    
    def validation_status_display(self, obj):
        """Validation status for readonly display"""
        errors = obj.validate_assignment()
        if errors:
            return format_html(
                '<span style="color: red;">❌ Issues:<br/>{}</span>',
                '<br/>'.join(errors)
            )
        
        return format_html('<span style="color: green;">✓ Valid</span>')
    validation_status_display.short_description = _('Validation Status')
    
    # Custom actions
    actions = [
        'approve_assignments', 'confirm_assignments', 'activate_assignments',
        'complete_assignments', 'cancel_assignments', 'mark_no_show',
        'send_reminders', 'check_in_volunteers', 'check_out_volunteers',
        'apply_admin_override', 'remove_admin_override', 'export_assignment_data'
    ]
    
    def approve_assignments(self, request, queryset):
        """Approve selected assignments"""
        updated = 0
        for assignment in queryset.filter(status=Assignment.AssignmentStatus.PENDING):
            assignment.approve(approved_by=request.user, notes="Bulk admin approval")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} assignment(s) were successfully approved.'
        )
    approve_assignments.short_description = _('Approve selected assignments')
    
    def confirm_assignments(self, request, queryset):
        """Confirm selected assignments"""
        updated = 0
        for assignment in queryset.filter(status=Assignment.AssignmentStatus.APPROVED):
            assignment.confirm(notes="Bulk admin confirmation")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} assignment(s) were confirmed.'
        )
    confirm_assignments.short_description = _('Confirm selected assignments')
    
    def activate_assignments(self, request, queryset):
        """Activate selected assignments"""
        updated = 0
        for assignment in queryset.filter(
            status__in=[Assignment.AssignmentStatus.APPROVED, Assignment.AssignmentStatus.CONFIRMED]
        ):
            assignment.activate(activated_by=request.user, notes="Bulk admin activation")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} assignment(s) were activated.'
        )
    activate_assignments.short_description = _('Activate selected assignments')
    
    def complete_assignments(self, request, queryset):
        """Complete selected assignments"""
        updated = 0
        for assignment in queryset.filter(status=Assignment.AssignmentStatus.ACTIVE):
            assignment.complete(completed_by=request.user, notes="Bulk admin completion")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} assignment(s) were marked as completed.'
        )
    complete_assignments.short_description = _('Mark selected assignments as completed')
    
    def cancel_assignments(self, request, queryset):
        """Cancel selected assignments"""
        updated = 0
        for assignment in queryset.exclude(
            status__in=[Assignment.AssignmentStatus.COMPLETED, Assignment.AssignmentStatus.CANCELLED]
        ):
            assignment.cancel(cancelled_by=request.user, reason="Bulk admin cancellation")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} assignment(s) were cancelled.'
        )
    cancel_assignments.short_description = _('Cancel selected assignments')
    
    def mark_no_show(self, request, queryset):
        """Mark selected assignments as no-show"""
        updated = 0
        for assignment in queryset.filter(
            status__in=[Assignment.AssignmentStatus.ACTIVE, Assignment.AssignmentStatus.CONFIRMED]
        ):
            assignment.mark_no_show(marked_by=request.user, notes="Bulk admin no-show marking")
            updated += 1
        
        self.message_user(
            request,
            f'{updated} assignment(s) were marked as no-show.'
        )
    mark_no_show.short_description = _('Mark selected assignments as no-show')
    
    def send_reminders(self, request, queryset):
        """Send reminders for selected assignments"""
        # This would integrate with notification system
        count = queryset.filter(
            status__in=[Assignment.AssignmentStatus.APPROVED, Assignment.AssignmentStatus.CONFIRMED]
        ).count()
        
        self.message_user(
            request,
            f'Reminders will be sent for {count} assignment(s). (Feature to be implemented)'
        )
    send_reminders.short_description = _('Send reminders for selected assignments')
    
    def check_in_volunteers(self, request, queryset):
        """Check in volunteers for selected assignments"""
        updated = 0
        for assignment in queryset.filter(
            status__in=[Assignment.AssignmentStatus.APPROVED, Assignment.AssignmentStatus.CONFIRMED],
            check_in_time__isnull=True
        ):
            assignment.check_in()
            updated += 1
        
        self.message_user(
            request,
            f'{updated} volunteer(s) were checked in.'
        )
    check_in_volunteers.short_description = _('Check in volunteers for selected assignments')
    
    def check_out_volunteers(self, request, queryset):
        """Check out volunteers for selected assignments"""
        updated = 0
        for assignment in queryset.filter(
            check_in_time__isnull=False,
            check_out_time__isnull=True
        ):
            assignment.check_out()
            updated += 1
        
        self.message_user(
            request,
            f'{updated} volunteer(s) were checked out.'
        )
    check_out_volunteers.short_description = _('Check out volunteers for selected assignments')
    
    def apply_admin_override(self, request, queryset):
        """Apply admin override to selected assignments"""
        if not request.user.is_staff:
            self.message_user(
                request,
                'Only staff users can apply admin overrides.',
                level='ERROR'
            )
            return
        
        # This would typically show a form for override reason
        # For now, we'll apply a generic override
        updated = 0
        for assignment in queryset.filter(is_admin_override=False):
            assignment.apply_admin_override(
                admin_user=request.user,
                reason="Bulk admin override applied via admin interface",
                override_types=['capacity']  # Default to capacity override
            )
            updated += 1
        
        self.message_user(
            request,
            f'Admin override applied to {updated} assignment(s).'
        )
    apply_admin_override.short_description = _('Apply admin override to selected assignments')
    
    def remove_admin_override(self, request, queryset):
        """Remove admin override from selected assignments"""
        if not request.user.is_staff:
            self.message_user(
                request,
                'Only staff users can remove admin overrides.',
                level='ERROR'
            )
            return
        
        updated = 0
        for assignment in queryset.filter(is_admin_override=True):
            assignment.remove_admin_override(
                admin_user=request.user,
                reason="Override removed via bulk admin action"
            )
            updated += 1
        
        self.message_user(
            request,
            f'Admin override removed from {updated} assignment(s).'
        )
    remove_admin_override.short_description = _('Remove admin override from selected assignments')
    
    def export_assignment_data(self, request, queryset):
        """Export assignment data (placeholder for future implementation)"""
        self.message_user(
            request,
            f'Export functionality for {queryset.count()} assignment(s) will be implemented.'
        )
    export_assignment_data.short_description = _('Export selected assignment data')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new assignment
            obj.assigned_by = request.user
        
        # Validate admin override requirements
        if obj.is_admin_override and not obj.admin_override_reason:
            obj.admin_override_reason = f"Admin override applied by {request.user.get_full_name()}"
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'volunteer', 'role', 'event', 'venue',
            'assigned_by', 'reviewed_by', 'approved_by',
            'status_changed_by', 'admin_override_by'
        )
    
    def has_change_permission(self, request, obj=None):
        """Custom permission logic"""
        if not super().has_change_permission(request, obj):
            return False
        
        # Allow role coordinators to manage assignments for their roles
        if obj and hasattr(request.user, 'coordinated_roles'):
            if obj.role in request.user.coordinated_roles.all():
                return True
        
        # Allow event managers to manage assignments in their events
        if obj and hasattr(request.user, 'managed_events'):
            if obj.event in request.user.managed_events.all():
                return True
        
        # Allow venue coordinators to manage assignments in their venues
        if obj and obj.venue and hasattr(request.user, 'coordinated_venues'):
            if obj.venue in request.user.coordinated_venues.all():
                return True
        
        return True
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit choices based on user permissions
        if hasattr(request.user, 'managed_events'):
            managed_events = request.user.managed_events.all()
            if managed_events.exists():
                form.base_fields['event'].queryset = managed_events
        
        return form
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamic readonly fields based on user permissions and assignment status"""
        readonly_fields = list(self.readonly_fields)
        
        # Make certain fields readonly for non-superusers
        if not request.user.is_superuser:
            readonly_fields.extend(['external_references'])
        
        # Make admin override fields readonly for non-staff
        if not request.user.is_staff:
            readonly_fields.extend([
                'is_admin_override', 'admin_override_reason', 'admin_override_by',
                'admin_override_date', 'age_requirement_override',
                'credential_requirement_override', 'capacity_override',
                'override_justification'
            ])
        
        # Make certain fields readonly if assignment is completed
        if obj and obj.is_completed():
            readonly_fields.extend([
                'volunteer', 'role', 'event', 'venue', 'assignment_type',
                'start_date', 'end_date', 'start_time', 'end_time'
            ])
        
        return readonly_fields
    
    def get_list_filter(self, request):
        """Dynamic list filters based on user permissions"""
        # Filter by managed events for event managers
        if hasattr(request.user, 'managed_events'):
            return super().get_list_filter(request)
        
        return super().get_list_filter(request)
