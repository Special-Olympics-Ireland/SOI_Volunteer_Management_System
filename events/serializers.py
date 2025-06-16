from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Event, Venue, Role, Assignment

User = get_user_model()

class EventListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for event lists and basic information
    """
    volunteer_progress = serializers.SerializerMethodField()
    registration_status = serializers.SerializerMethodField()
    venue_count = serializers.SerializerMethodField()
    role_count = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'slug', 'short_name', 'event_type', 'status',
            'description', 'tagline', 'start_date', 'end_date',
            'host_city', 'host_country', 'volunteer_target',
            'volunteer_progress', 'registration_status', 'venue_count',
            'role_count', 'duration_days', 'is_active', 'is_public',
            'is_featured', 'logo', 'banner_image', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'volunteer_progress', 'registration_status', 'venue_count',
            'role_count', 'duration_days', 'created_at', 'updated_at'
        ]
    
    def get_volunteer_progress(self, obj):
        """Get volunteer recruitment progress"""
        return {
            'current': obj.get_volunteer_count(),
            'target': obj.volunteer_target,
            'percentage': obj.get_volunteer_target_progress()
        }
    
    def get_registration_status(self, obj):
        """Get current registration status"""
        return obj.get_registration_status()
    
    def get_venue_count(self, obj):
        """Get number of venues"""
        return obj.get_venue_count()
    
    def get_role_count(self, obj):
        """Get total number of roles"""
        return obj.get_role_count()
    
    def get_duration_days(self, obj):
        """Get event duration in days"""
        return obj.get_duration_days()

class EventDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed event information
    """
    volunteer_progress = serializers.SerializerMethodField()
    registration_status = serializers.SerializerMethodField()
    venue_count = serializers.SerializerMethodField()
    role_count = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_ongoing = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()
    can_register_volunteers = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    event_managers_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'slug', 'short_name', 'event_type', 'status',
            'description', 'tagline', 'start_date', 'end_date',
            'registration_open_date', 'registration_close_date',
            'host_city', 'host_country', 'timezone',
            'volunteer_target', 'volunteer_minimum_age',
            'welcome_message', 'instructions', 'contact_information',
            'logo', 'banner_image', 'brand_colors',
            'is_active', 'is_public', 'is_featured',
            'volunteer_progress', 'registration_status', 'venue_count',
            'role_count', 'duration_days', 'is_upcoming', 'is_ongoing',
            'is_past', 'can_register_volunteers',
            'created_by_name', 'event_managers_names',
            'created_at', 'updated_at', 'status_changed_at'
        ]
        read_only_fields = [
            'id', 'volunteer_progress', 'registration_status', 'venue_count',
            'role_count', 'duration_days', 'is_upcoming', 'is_ongoing',
            'is_past', 'can_register_volunteers', 'created_by_name',
            'event_managers_names', 'created_at', 'updated_at', 'status_changed_at'
        ]
    
    def get_volunteer_progress(self, obj):
        """Get detailed volunteer recruitment progress"""
        return {
            'current': obj.get_volunteer_count(),
            'target': obj.volunteer_target,
            'percentage': obj.get_volunteer_target_progress(),
            'remaining': max(0, obj.volunteer_target - obj.get_volunteer_count())
        }
    
    def get_registration_status(self, obj):
        """Get detailed registration status"""
        status = obj.get_registration_status()
        return {
            'status': status,
            'can_register': obj.can_register_volunteers(),
            'open_date': obj.registration_open_date,
            'close_date': obj.registration_close_date
        }
    
    def get_venue_count(self, obj):
        """Get number of venues"""
        return obj.get_venue_count()
    
    def get_role_count(self, obj):
        """Get total number of roles"""
        return obj.get_role_count()
    
    def get_duration_days(self, obj):
        """Get event duration in days"""
        return obj.get_duration_days()
    
    def get_is_upcoming(self, obj):
        """Check if event is upcoming"""
        return obj.is_upcoming()
    
    def get_is_ongoing(self, obj):
        """Check if event is ongoing"""
        return obj.is_ongoing()
    
    def get_is_past(self, obj):
        """Check if event is past"""
        return obj.is_past()
    
    def get_can_register_volunteers(self, obj):
        """Check if volunteer registration is open"""
        return obj.can_register_volunteers()
    
    def get_created_by_name(self, obj):
        """Get creator's name"""
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_event_managers_names(self, obj):
        """Get event managers' names"""
        return [manager.get_full_name() for manager in obj.event_managers.all()]

class EventCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new events
    """
    
    class Meta:
        model = Event
        fields = [
            'name', 'slug', 'short_name', 'event_type', 'description',
            'tagline', 'start_date', 'end_date', 'registration_open_date',
            'registration_close_date', 'host_city', 'host_country',
            'timezone', 'volunteer_target', 'volunteer_minimum_age',
            'welcome_message', 'instructions', 'contact_information',
            'logo', 'banner_image', 'brand_colors', 'is_public', 'is_featured'
        ]
    
    def validate(self, data):
        """Validate event data"""
        # Validate dates
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError(
                "End date must be after start date."
            )
        
        # Validate registration dates
        if data.get('registration_open_date') and data.get('registration_close_date'):
            if data['registration_close_date'] <= data['registration_open_date']:
                raise serializers.ValidationError(
                    "Registration close date must be after open date."
                )
        
        # Validate volunteer target
        if data.get('volunteer_target', 0) < 0:
            raise serializers.ValidationError(
                "Volunteer target must be non-negative."
            )
        
        # Validate minimum age
        min_age = data.get('volunteer_minimum_age', 15)
        if min_age < 13 or min_age > 25:
            raise serializers.ValidationError(
                "Volunteer minimum age must be between 13 and 25."
            )
        
        return data
    
    def create(self, validated_data):
        """Create event with default configurations"""
        # Set creator from request context
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        
        return super().create(validated_data)

class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing events
    """
    
    class Meta:
        model = Event
        fields = [
            'name', 'slug', 'short_name', 'event_type', 'status',
            'description', 'tagline', 'start_date', 'end_date',
            'registration_open_date', 'registration_close_date',
            'host_city', 'host_country', 'timezone',
            'volunteer_target', 'volunteer_minimum_age',
            'welcome_message', 'instructions', 'contact_information',
            'logo', 'banner_image', 'brand_colors',
            'is_active', 'is_public', 'is_featured'
        ]
    
    def validate(self, data):
        """Validate event update data"""
        instance = self.instance
        
        # Validate dates
        start_date = data.get('start_date', instance.start_date)
        end_date = data.get('end_date', instance.end_date)
        
        if end_date < start_date:
            raise serializers.ValidationError(
                "End date must be after start date."
            )
        
        # Validate registration dates
        reg_open = data.get('registration_open_date', instance.registration_open_date)
        reg_close = data.get('registration_close_date', instance.registration_close_date)
        
        if reg_open and reg_close and reg_close <= reg_open:
            raise serializers.ValidationError(
                "Registration close date must be after open date."
            )
        
        # Validate volunteer target
        volunteer_target = data.get('volunteer_target', instance.volunteer_target)
        if volunteer_target < 0:
            raise serializers.ValidationError(
                "Volunteer target must be non-negative."
            )
        
        # Validate minimum age
        min_age = data.get('volunteer_minimum_age', instance.volunteer_minimum_age)
        if min_age < 13 or min_age > 25:
            raise serializers.ValidationError(
                "Volunteer minimum age must be between 13 and 25."
            )
        
        return data
    
    def update(self, instance, validated_data):
        """Update event with status change tracking"""
        request = self.context.get('request')
        
        # Track status changes
        if 'status' in validated_data and validated_data['status'] != instance.status:
            if request and request.user:
                instance.status_changed_by = request.user
        
        return super().update(instance, validated_data)

class EventConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for managing event configuration JSON fields
    """
    
    class Meta:
        model = Event
        fields = [
            'event_configuration', 'volunteer_configuration',
            'venue_configuration', 'role_configuration',
            'features_enabled', 'integrations_config'
        ]
    
    def validate_event_configuration(self, value):
        """Validate event configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Event configuration must be a JSON object.")
        return value
    
    def validate_volunteer_configuration(self, value):
        """Validate volunteer configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Volunteer configuration must be a JSON object.")
        return value
    
    def validate_venue_configuration(self, value):
        """Validate venue configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Venue configuration must be a JSON object.")
        return value
    
    def validate_role_configuration(self, value):
        """Validate role configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Role configuration must be a JSON object.")
        return value
    
    def validate_features_enabled(self, value):
        """Validate features configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Features configuration must be a JSON object.")
        return value
    
    def validate_integrations_config(self, value):
        """Validate integrations configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Integrations configuration must be a JSON object.")
        return value

class EventStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for event status management
    """
    status_change_notes = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Optional notes for status change"
    )
    
    class Meta:
        model = Event
        fields = ['status', 'status_change_notes']
    
    def update(self, instance, validated_data):
        """Update event status with audit trail"""
        new_status = validated_data.get('status')
        notes = validated_data.pop('status_change_notes', None)
        
        if new_status and new_status != instance.status:
            request = self.context.get('request')
            changed_by = request.user if request and request.user else None
            
            instance.change_status(new_status, changed_by, notes)
        
        return instance

class EventStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for event statistics and analytics
    """
    volunteer_stats = serializers.SerializerMethodField()
    venue_stats = serializers.SerializerMethodField()
    role_stats = serializers.SerializerMethodField()
    registration_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'slug', 'status', 'start_date', 'end_date',
            'volunteer_stats', 'venue_stats', 'role_stats', 'registration_stats'
        ]
        read_only_fields = ['id', 'name', 'slug', 'status', 'start_date', 'end_date']
    
    def get_volunteer_stats(self, obj):
        """Get volunteer statistics"""
        return {
            'total_assigned': obj.get_volunteer_count(),
            'target': obj.volunteer_target,
            'progress_percentage': obj.get_volunteer_target_progress(),
            'remaining_needed': max(0, obj.volunteer_target - obj.get_volunteer_count())
        }
    
    def get_venue_stats(self, obj):
        """Get venue statistics"""
        return {
            'total_venues': obj.get_venue_count(),
            # Additional venue stats would be calculated here
        }
    
    def get_role_stats(self, obj):
        """Get role statistics"""
        return {
            'total_roles': obj.get_role_count(),
            # Additional role stats would be calculated here
        }
    
    def get_registration_stats(self, obj):
        """Get registration statistics"""
        return {
            'status': obj.get_registration_status(),
            'can_register': obj.can_register_volunteers(),
            'open_date': obj.registration_open_date,
            'close_date': obj.registration_close_date
        }

# Venue Serializers

class VenueListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for venue lists and basic information
    """
    event_name = serializers.CharField(source='event.name', read_only=True)
    full_address = serializers.CharField(read_only=True)
    capacity_utilization = serializers.SerializerMethodField()
    available_capacity = serializers.SerializerMethodField()
    accessibility_features = serializers.SerializerMethodField()
    
    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'slug', 'short_name', 'event', 'event_name',
            'venue_type', 'status', 'full_address', 'city', 'country',
            'total_capacity', 'volunteer_capacity', 'spectator_capacity',
            'capacity_utilization', 'available_capacity',
            'accessibility_level', 'accessibility_features',
            'is_active', 'is_primary', 'requires_security_clearance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_capacity_utilization(self, obj):
        """Get venue capacity utilization percentage"""
        return obj.get_capacity_utilization()
    
    def get_available_capacity(self, obj):
        """Get venue available capacity"""
        return obj.get_available_capacity()
    
    def get_accessibility_features(self, obj):
        """Get venue accessibility features"""
        return obj.get_accessibility_features()


class VenueDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed venue information
    """
    event_name = serializers.CharField(source='event.name', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    full_address = serializers.CharField(read_only=True)
    coordinates = serializers.SerializerMethodField()
    capacity_utilization = serializers.SerializerMethodField()
    available_capacity = serializers.SerializerMethodField()
    assigned_volunteer_count = serializers.SerializerMethodField()
    role_count = serializers.SerializerMethodField()
    accessibility_features = serializers.SerializerMethodField()
    
    # User information
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    venue_coordinators_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Venue
        fields = [
            'id', 'event', 'event_name', 'event_slug', 'name', 'slug', 'short_name',
            'venue_type', 'status', 'description', 'purpose',
            'address_line_1', 'address_line_2', 'city', 'county', 'postal_code', 'country',
            'full_address', 'coordinates', 'latitude', 'longitude',
            'total_capacity', 'volunteer_capacity', 'spectator_capacity',
            'capacity_utilization', 'available_capacity', 'assigned_volunteer_count',
            'accessibility_level', 'wheelchair_accessible', 'accessible_parking',
            'accessible_toilets', 'hearing_loop', 'accessibility_features',
            'public_transport_access', 'parking_spaces', 'parking_cost',
            'facilities', 'catering_available', 'wifi_available', 'first_aid_station',
            'venue_configuration', 'operational_hours', 'equipment_available',
            'venue_manager', 'contact_phone', 'contact_email', 'emergency_contact',
            'venue_image', 'floor_plan', 'venue_map',
            'is_active', 'is_primary', 'requires_security_clearance',
            'role_count', 'created_by', 'created_by_name', 'venue_coordinators_info',
            'status_changed_at', 'status_changed_by', 'status_changed_by_name',
            'created_at', 'updated_at', 'notes', 'external_references'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'status_changed_at',
            'capacity_utilization', 'available_capacity', 'assigned_volunteer_count',
            'role_count', 'accessibility_features', 'coordinates', 'full_address'
        ]
    
    def get_coordinates(self, obj):
        """Get venue coordinates"""
        return obj.get_coordinates()
    
    def get_capacity_utilization(self, obj):
        """Get venue capacity utilization percentage"""
        return obj.get_capacity_utilization()
    
    def get_available_capacity(self, obj):
        """Get venue available capacity"""
        return obj.get_available_capacity()
    
    def get_assigned_volunteer_count(self, obj):
        """Get assigned volunteer count"""
        return obj.get_assigned_volunteer_count()
    
    def get_role_count(self, obj):
        """Get role count"""
        return obj.get_role_count()
    
    def get_accessibility_features(self, obj):
        """Get venue accessibility features"""
        return obj.get_accessibility_features()
    
    def get_venue_coordinators_info(self, obj):
        """Get venue coordinators information"""
        return [
            {
                'id': str(coordinator.id),
                'name': coordinator.get_full_name(),
                'email': coordinator.email
            }
            for coordinator in obj.venue_coordinators.all()
        ]


class VenueCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new venues with validation
    """
    
    class Meta:
        model = Venue
        fields = [
            'event', 'name', 'slug', 'short_name', 'venue_type', 'status',
            'description', 'purpose',
            'address_line_1', 'address_line_2', 'city', 'county', 'postal_code', 'country',
            'latitude', 'longitude',
            'total_capacity', 'volunteer_capacity', 'spectator_capacity',
            'accessibility_level', 'wheelchair_accessible', 'accessible_parking',
            'accessible_toilets', 'hearing_loop',
            'public_transport_access', 'parking_spaces', 'parking_cost',
            'facilities', 'catering_available', 'wifi_available', 'first_aid_station',
            'venue_configuration', 'operational_hours', 'equipment_available',
            'venue_manager', 'contact_phone', 'contact_email', 'emergency_contact',
            'is_active', 'is_primary', 'requires_security_clearance',
            'venue_coordinators', 'notes'
        ]
    
    def validate(self, data):
        """Custom validation for venue creation"""
        # Ensure slug is unique within the event
        event = data.get('event')
        slug = data.get('slug')
        
        if event and slug:
            if Venue.objects.filter(event=event, slug=slug).exists():
                raise serializers.ValidationError({
                    'slug': 'A venue with this slug already exists for this event.'
                })
        
        # Validate capacity values
        total_capacity = data.get('total_capacity', 0)
        volunteer_capacity = data.get('volunteer_capacity', 0)
        spectator_capacity = data.get('spectator_capacity', 0)
        
        if volunteer_capacity > total_capacity and total_capacity > 0:
            raise serializers.ValidationError({
                'volunteer_capacity': 'Volunteer capacity cannot exceed total capacity.'
            })
        
        if spectator_capacity > total_capacity and total_capacity > 0:
            raise serializers.ValidationError({
                'spectator_capacity': 'Spectator capacity cannot exceed total capacity.'
            })
        
        # Validate coordinates if provided
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is not None and not (-90 <= float(latitude) <= 90):
            raise serializers.ValidationError({
                'latitude': 'Latitude must be between -90 and 90 degrees.'
            })
        
        if longitude is not None and not (-180 <= float(longitude) <= 180):
            raise serializers.ValidationError({
                'longitude': 'Longitude must be between -180 and 180 degrees.'
            })
        
        return data
    
    def create(self, validated_data):
        """Create venue with proper handling of many-to-many fields"""
        venue_coordinators = validated_data.pop('venue_coordinators', [])
        
        venue = Venue.objects.create(**validated_data)
        
        if venue_coordinators:
            venue.venue_coordinators.set(venue_coordinators)
        
        return venue


class VenueUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating venues with status change tracking
    """
    
    class Meta:
        model = Venue
        fields = [
            'name', 'slug', 'short_name', 'venue_type', 'status',
            'description', 'purpose',
            'address_line_1', 'address_line_2', 'city', 'county', 'postal_code', 'country',
            'latitude', 'longitude',
            'total_capacity', 'volunteer_capacity', 'spectator_capacity',
            'accessibility_level', 'wheelchair_accessible', 'accessible_parking',
            'accessible_toilets', 'hearing_loop',
            'public_transport_access', 'parking_spaces', 'parking_cost',
            'facilities', 'catering_available', 'wifi_available', 'first_aid_station',
            'venue_configuration', 'operational_hours', 'equipment_available',
            'venue_manager', 'contact_phone', 'contact_email', 'emergency_contact',
            'is_active', 'is_primary', 'requires_security_clearance',
            'venue_coordinators', 'notes'
        ]
    
    def validate(self, data):
        """Custom validation for venue updates"""
        # Ensure slug is unique within the event (excluding current venue)
        slug = data.get('slug')
        
        if slug and self.instance:
            if Venue.objects.filter(
                event=self.instance.event, 
                slug=slug
            ).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError({
                    'slug': 'A venue with this slug already exists for this event.'
                })
        
        # Validate capacity values
        total_capacity = data.get('total_capacity', self.instance.total_capacity if self.instance else 0)
        volunteer_capacity = data.get('volunteer_capacity', self.instance.volunteer_capacity if self.instance else 0)
        spectator_capacity = data.get('spectator_capacity', self.instance.spectator_capacity if self.instance else 0)
        
        if volunteer_capacity > total_capacity and total_capacity > 0:
            raise serializers.ValidationError({
                'volunteer_capacity': 'Volunteer capacity cannot exceed total capacity.'
            })
        
        if spectator_capacity > total_capacity and total_capacity > 0:
            raise serializers.ValidationError({
                'spectator_capacity': 'Spectator capacity cannot exceed total capacity.'
            })
        
        # Validate coordinates if provided
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is not None and not (-90 <= float(latitude) <= 90):
            raise serializers.ValidationError({
                'latitude': 'Latitude must be between -90 and 90 degrees.'
            })
        
        if longitude is not None and not (-180 <= float(longitude) <= 180):
            raise serializers.ValidationError({
                'longitude': 'Longitude must be between -180 and 180 degrees.'
            })
        
        return data
    
    def update(self, instance, validated_data):
        """Update venue with proper handling of many-to-many fields"""
        venue_coordinators = validated_data.pop('venue_coordinators', None)
        
        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update many-to-many fields
        if venue_coordinators is not None:
            instance.venue_coordinators.set(venue_coordinators)
        
        return instance


class VenueConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for managing venue configuration settings
    """
    
    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'venue_configuration', 'facilities', 
            'operational_hours', 'equipment_available', 'emergency_contact'
        ]
        read_only_fields = ['id', 'name']
    
    def validate_venue_configuration(self, value):
        """Validate venue configuration JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError('Configuration must be a valid JSON object.')
        
        # Define required configuration keys
        required_keys = [
            'check_in_required', 'security_level', 'volunteer_break_area',
            'uniform_storage', 'capacity_monitoring'
        ]
        
        # Check for required keys (optional validation)
        missing_keys = [key for key in required_keys if key not in value]
        if missing_keys:
            # Just add default values instead of raising error
            for key in missing_keys:
                if key == 'check_in_required':
                    value[key] = True
                elif key == 'security_level':
                    value[key] = 'standard'
                elif key == 'volunteer_break_area':
                    value[key] = True
                elif key == 'uniform_storage':
                    value[key] = True
                elif key == 'capacity_monitoring':
                    value[key] = True
        
        return value
    
    def validate_facilities(self, value):
        """Validate facilities JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError('Facilities must be a valid JSON object.')
        
        # Ensure all values are boolean
        for facility, available in value.items():
            if not isinstance(available, bool):
                raise serializers.ValidationError(f'Facility "{facility}" must be true or false.')
        
        return value
    
    def validate_operational_hours(self, value):
        """Validate operational hours JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError('Operational hours must be a valid JSON object.')
        
        # Validate day structure
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'event_days']
        
        for day, hours in value.items():
            if day not in valid_days:
                raise serializers.ValidationError(f'Invalid day: {day}')
            
            if not isinstance(hours, dict):
                raise serializers.ValidationError(f'Hours for {day} must be an object.')
            
            required_hour_keys = ['open', 'close', 'closed']
            for key in required_hour_keys:
                if key not in hours:
                    raise serializers.ValidationError(f'Missing {key} for {day}.')
        
        return value


class VenueStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for venue status changes with audit trail
    """
    status_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Venue
        fields = ['id', 'name', 'status', 'status_reason', 'status_changed_at', 'status_changed_by']
        read_only_fields = ['id', 'name', 'status_changed_at', 'status_changed_by']
    
    def update(self, instance, validated_data):
        """Update venue status with audit trail"""
        new_status = validated_data.get('status')
        status_reason = validated_data.pop('status_reason', '')
        
        if new_status and new_status != instance.status:
            # Use the model's change_status method for proper audit trail
            request = self.context.get('request')
            changed_by = request.user if request else None
            
            instance.change_status(
                new_status=new_status,
                changed_by=changed_by,
                notes=status_reason
            )
        
        return instance


class VenueStatsSerializer(serializers.Serializer):
    """
    Serializer for venue statistics and analytics
    """
    venue_id = serializers.UUIDField()
    venue_name = serializers.CharField()
    
    def to_representation(self, instance):
        """Generate venue statistics"""
        if isinstance(instance, Venue):
            venue = instance
        else:
            venue = Venue.objects.get(id=instance)
        
        # Calculate statistics
        return {
            'venue_id': str(venue.id),
            'venue_name': venue.name,
            'event_name': venue.event.name,
            'venue_type': venue.venue_type,
            'status': venue.status,
            'capacity_stats': {
                'total_capacity': venue.total_capacity,
                'volunteer_capacity': venue.volunteer_capacity,
                'spectator_capacity': venue.spectator_capacity,
                'assigned_volunteers': venue.get_assigned_volunteer_count(),
                'available_capacity': venue.get_available_capacity(),
                'utilization_percentage': venue.get_capacity_utilization()
            },
            'role_stats': {
                'total_roles': venue.get_role_count(),
                'active_roles': venue.get_active_role_count()
            },
            'accessibility_info': {
                'level': venue.accessibility_level,
                'features': venue.get_accessibility_features(),
                'fully_accessible': venue.is_fully_accessible(),
                'basic_accessibility': venue.has_basic_accessibility()
            },
            'operational_status': {
                'is_active': venue.is_active,
                'is_primary': venue.is_primary,
                'requires_security_clearance': venue.requires_security_clearance,
                'has_coordinates': venue.has_coordinates()
            },
            'last_updated': venue.updated_at.isoformat()
        }


# Legacy serializers for backward compatibility
class VenueSerializer(VenueDetailSerializer):
    """Main venue serializer - alias for VenueDetailSerializer"""
    pass

# Role Serializers

class RoleListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for role lists and basic information
    """
    event_name = serializers.CharField(source='event.name', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    available_positions = serializers.SerializerMethodField()
    capacity_percentage = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    is_urgent = serializers.BooleanField(read_only=True)
    days_until_deadline = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'slug', 'short_name', 'event', 'event_name',
            'venue', 'venue_name', 'role_type', 'status', 'summary',
            'minimum_age', 'skill_level_required', 'total_positions',
            'filled_positions', 'available_positions', 'capacity_percentage',
            'is_full', 'is_urgent', 'is_featured', 'priority_level',
            'application_deadline', 'days_until_deadline', 'commitment_level',
            'estimated_hours_per_day', 'training_required', 'uniform_required',
            'meal_provided', 'transport_provided', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_available_positions(self, obj):
        """Get number of available positions"""
        return obj.get_available_positions()
    
    def get_capacity_percentage(self, obj):
        """Get capacity utilization percentage"""
        return obj.get_capacity_percentage()
    
    def get_is_full(self, obj):
        """Check if role is at capacity"""
        return obj.is_full()
    
    def get_days_until_deadline(self, obj):
        """Get days until application deadline"""
        return obj.get_days_until_deadline()


class RoleDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed role information
    """
    event_name = serializers.CharField(source='event.name', read_only=True)
    event_slug = serializers.CharField(source='event.slug', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_slug = serializers.CharField(source='venue.slug', read_only=True)
    
    # Capacity and availability
    available_positions = serializers.SerializerMethodField()
    capacity_percentage = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    is_understaffed = serializers.SerializerMethodField()
    can_accept_volunteers = serializers.SerializerMethodField()
    
    # Application status
    is_application_open = serializers.SerializerMethodField()
    days_until_deadline = serializers.SerializerMethodField()
    
    # User information
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    role_supervisor_name = serializers.CharField(source='role_supervisor.get_full_name', read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    role_coordinators_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'event', 'event_name', 'event_slug', 'venue', 'venue_name', 'venue_slug',
            'name', 'slug', 'short_name', 'role_type', 'status', 'description', 'summary',
            'minimum_age', 'maximum_age', 'skill_level_required',
            'physical_requirements', 'language_requirements',
            'required_credentials', 'preferred_credentials', 'justgo_credentials_required',
            'requires_garda_vetting', 'requires_child_protection', 'requires_security_clearance',
            'total_positions', 'filled_positions', 'minimum_volunteers',
            'available_positions', 'capacity_percentage', 'is_full', 'is_understaffed',
            'can_accept_volunteers', 'commitment_level', 'estimated_hours_per_day',
            'total_estimated_hours', 'schedule_requirements', 'availability_windows',
            'training_required', 'training_duration_hours', 'training_materials',
            'uniform_required', 'uniform_details', 'equipment_provided', 'equipment_required',
            'benefits', 'meal_provided', 'transport_provided', 'accommodation_provided',
            'role_configuration', 'custom_fields', 'role_supervisor', 'role_supervisor_name',
            'contact_person', 'contact_email', 'contact_phone', 'priority_level',
            'is_featured', 'is_urgent', 'is_public', 'application_deadline',
            'is_application_open', 'days_until_deadline', 'selection_criteria',
            'application_process', 'created_by', 'created_by_name', 'role_coordinators_info',
            'status_changed_at', 'status_changed_by', 'status_changed_by_name',
            'created_at', 'updated_at', 'notes', 'external_references'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'status_changed_at', 'status_changed_by'
        ]
    
    def get_available_positions(self, obj):
        """Get number of available positions"""
        return obj.get_available_positions()
    
    def get_capacity_percentage(self, obj):
        """Get capacity utilization percentage"""
        return obj.get_capacity_percentage()
    
    def get_is_full(self, obj):
        """Check if role is at capacity"""
        return obj.is_full()
    
    def get_is_understaffed(self, obj):
        """Check if role is understaffed"""
        return obj.is_understaffed()
    
    def get_can_accept_volunteers(self, obj):
        """Check if role can accept more volunteers"""
        return obj.can_accept_volunteers()
    
    def get_is_application_open(self, obj):
        """Check if applications are open"""
        return obj.is_application_open()
    
    def get_days_until_deadline(self, obj):
        """Get days until application deadline"""
        return obj.get_days_until_deadline()
    
    def get_role_coordinators_info(self, obj):
        """Get role coordinators information"""
        coordinators = obj.role_coordinators.all()
        return [
            {
                'id': str(coordinator.id),
                'name': coordinator.get_full_name(),
                'email': coordinator.email
            }
            for coordinator in coordinators
        ]


class RoleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new roles
    """
    
    class Meta:
        model = Role
        fields = [
            'event', 'venue', 'name', 'slug', 'short_name', 'role_type',
            'description', 'summary', 'minimum_age', 'maximum_age',
            'skill_level_required', 'physical_requirements', 'language_requirements',
            'required_credentials', 'preferred_credentials', 'justgo_credentials_required',
            'requires_garda_vetting', 'requires_child_protection', 'requires_security_clearance',
            'total_positions', 'minimum_volunteers', 'commitment_level',
            'estimated_hours_per_day', 'total_estimated_hours', 'schedule_requirements',
            'availability_windows', 'training_required', 'training_duration_hours',
            'training_materials', 'uniform_required', 'uniform_details',
            'equipment_provided', 'equipment_required', 'benefits',
            'meal_provided', 'transport_provided', 'accommodation_provided',
            'role_configuration', 'custom_fields', 'role_supervisor',
            'contact_person', 'contact_email', 'contact_phone', 'priority_level',
            'is_featured', 'is_urgent', 'is_public', 'application_deadline',
            'selection_criteria', 'application_process', 'role_coordinators'
        ]
    
    def validate(self, data):
        """Validate role data"""
        # Check age requirements
        min_age = data.get('minimum_age', 15)
        max_age = data.get('maximum_age')
        
        if max_age and min_age >= max_age:
            raise serializers.ValidationError({
                'maximum_age': 'Maximum age must be greater than minimum age.'
            })
        
        # Check position requirements
        total_positions = data.get('total_positions', 1)
        minimum_volunteers = data.get('minimum_volunteers', 1)
        
        if minimum_volunteers > total_positions:
            raise serializers.ValidationError({
                'minimum_volunteers': 'Minimum volunteers cannot exceed total positions.'
            })
        
        # Check time estimates
        hours_per_day = data.get('estimated_hours_per_day')
        total_hours = data.get('total_estimated_hours')
        
        if hours_per_day and hours_per_day > 24:
            raise serializers.ValidationError({
                'estimated_hours_per_day': 'Hours per day cannot exceed 24.'
            })
        
        if total_hours and hours_per_day and total_hours < hours_per_day:
            raise serializers.ValidationError({
                'total_estimated_hours': 'Total hours cannot be less than hours per day.'
            })
        
        # Validate venue belongs to event
        event = data.get('event')
        venue = data.get('venue')
        
        if venue and venue.event != event:
            raise serializers.ValidationError({
                'venue': 'Venue must belong to the selected event.'
            })
        
        return data
    
    def create(self, validated_data):
        """Create role with proper handling of many-to-many fields"""
        role_coordinators = validated_data.pop('role_coordinators', [])
        
        # Set created_by from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        role = Role.objects.create(**validated_data)
        
        # Set many-to-many fields
        if role_coordinators:
            role.role_coordinators.set(role_coordinators)
        
        return role


class RoleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing roles
    """
    
    class Meta:
        model = Role
        fields = [
            'name', 'short_name', 'description', 'summary', 'minimum_age',
            'maximum_age', 'skill_level_required', 'physical_requirements',
            'language_requirements', 'required_credentials', 'preferred_credentials',
            'justgo_credentials_required', 'requires_garda_vetting',
            'requires_child_protection', 'requires_security_clearance',
            'total_positions', 'minimum_volunteers', 'commitment_level',
            'estimated_hours_per_day', 'total_estimated_hours', 'schedule_requirements',
            'availability_windows', 'training_required', 'training_duration_hours',
            'training_materials', 'uniform_required', 'uniform_details',
            'equipment_provided', 'equipment_required', 'benefits',
            'meal_provided', 'transport_provided', 'accommodation_provided',
            'role_configuration', 'custom_fields', 'role_supervisor',
            'contact_person', 'contact_email', 'contact_phone', 'priority_level',
            'is_featured', 'is_urgent', 'is_public', 'application_deadline',
            'selection_criteria', 'application_process', 'role_coordinators'
        ]
    
    def validate(self, data):
        """Validate role update data"""
        instance = self.instance
        
        # Check age requirements
        min_age = data.get('minimum_age', instance.minimum_age)
        max_age = data.get('maximum_age', instance.maximum_age)
        
        if max_age and min_age >= max_age:
            raise serializers.ValidationError({
                'maximum_age': 'Maximum age must be greater than minimum age.'
            })
        
        # Check position requirements
        total_positions = data.get('total_positions', instance.total_positions)
        minimum_volunteers = data.get('minimum_volunteers', instance.minimum_volunteers)
        
        if minimum_volunteers > total_positions:
            raise serializers.ValidationError({
                'minimum_volunteers': 'Minimum volunteers cannot exceed total positions.'
            })
        
        # Check if reducing capacity below current assignments
        if 'total_positions' in data:
            current_assignments = instance.get_volunteer_count()
            if data['total_positions'] < current_assignments:
                raise serializers.ValidationError({
                    'total_positions': f'Cannot reduce capacity below current assignments ({current_assignments}).'
                })
        
        return data
    
    def update(self, instance, validated_data):
        """Update role with proper handling of many-to-many fields"""
        role_coordinators = validated_data.pop('role_coordinators', None)
        
        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update many-to-many fields
        if role_coordinators is not None:
            instance.role_coordinators.set(role_coordinators)
        
        return instance


class RoleStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for role status management
    """
    status_change_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'status', 'status_change_reason', 'status_changed_at', 'status_changed_by']
        read_only_fields = ['id', 'name', 'status_changed_at', 'status_changed_by']
    
    def update(self, instance, validated_data):
        """Update role status with audit trail"""
        new_status = validated_data.get('status')
        status_reason = validated_data.pop('status_change_reason', '')
        
        if new_status and new_status != instance.status:
            # Use the model's change_status method for proper audit trail
            request = self.context.get('request')
            changed_by = request.user if request else None
            
            instance.change_status(
                new_status=new_status,
                changed_by=changed_by,
                notes=status_reason
            )
        
        return instance


class RoleCapacitySerializer(serializers.Serializer):
    """
    Serializer for role capacity information and management
    """
    role_id = serializers.UUIDField()
    role_name = serializers.CharField()
    
    def to_representation(self, instance):
        """Generate role capacity information"""
        if isinstance(instance, Role):
            role = instance
        else:
            role = Role.objects.get(id=instance)
        
        return {
            'role_id': str(role.id),
            'role_name': role.name,
            'event_name': role.event.name,
            'venue_name': role.venue.name if role.venue else None,
            'role_type': role.role_type,
            'status': role.status,
            'capacity_info': {
                'total_positions': role.total_positions,
                'filled_positions': role.filled_positions,
                'available_positions': role.get_available_positions(),
                'minimum_volunteers': role.minimum_volunteers,
                'capacity_percentage': role.get_capacity_percentage(),
                'is_full': role.is_full(),
                'is_understaffed': role.is_understaffed(),
                'can_accept_volunteers': role.can_accept_volunteers()
            },
            'application_info': {
                'is_application_open': role.is_application_open(),
                'application_deadline': role.application_deadline.isoformat() if role.application_deadline else None,
                'days_until_deadline': role.get_days_until_deadline(),
                'is_urgent': role.is_urgent,
                'priority_level': role.priority_level
            },
            'requirements': {
                'minimum_age': role.minimum_age,
                'maximum_age': role.maximum_age,
                'skill_level_required': role.skill_level_required,
                'training_required': role.training_required,
                'requires_garda_vetting': role.requires_garda_vetting,
                'requires_child_protection': role.requires_child_protection,
                'requires_security_clearance': role.requires_security_clearance
            },
            'time_commitment': {
                'commitment_level': role.commitment_level,
                'estimated_hours_per_day': float(role.estimated_hours_per_day) if role.estimated_hours_per_day else None,
                'total_estimated_hours': float(role.total_estimated_hours) if role.total_estimated_hours else None
            },
            'last_updated': role.updated_at.isoformat()
        }


# Legacy serializer for backward compatibility
class RoleSerializer(RoleDetailSerializer):
    """Main role serializer - alias for RoleDetailSerializer"""
    pass

# Assignment Serializers

class AssignmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for assignment lists and basic information
    """
    volunteer_name = serializers.CharField(source='volunteer.get_full_name', read_only=True)
    volunteer_email = serializers.CharField(source='volunteer.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_level_display', read_only=True)
    is_active = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    days_until_start = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'volunteer', 'volunteer_name', 'volunteer_email',
            'role', 'role_name', 'event', 'event_name', 'venue', 'venue_name',
            'assignment_type', 'assignment_type_display', 'status', 'status_display',
            'priority_level', 'priority_display', 'assigned_date', 'start_date', 'end_date',
            'is_active', 'is_overdue', 'days_until_start', 'is_admin_override',
            'performance_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'assigned_date', 'created_at', 'updated_at']
    
    def get_is_active(self, obj):
        """Check if assignment is currently active"""
        return obj.is_active()
    
    def get_is_overdue(self, obj):
        """Check if assignment is overdue"""
        from django.utils import timezone
        if obj.start_date and obj.status in ['PENDING', 'APPROVED']:
            return obj.start_date < timezone.now().date()
        return False
    
    def get_days_until_start(self, obj):
        """Get days until assignment starts"""
        if obj.start_date:
            from django.utils import timezone
            delta = obj.start_date - timezone.now().date()
            return delta.days
        return None


class AssignmentDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed assignment information
    """
    volunteer_name = serializers.CharField(source='volunteer.get_full_name', read_only=True)
    volunteer_email = serializers.CharField(source='volunteer.email', read_only=True)
    volunteer_phone = serializers.CharField(source='volunteer.phone_number', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    role_description = serializers.CharField(source='role.description', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_address = serializers.CharField(source='venue.get_full_address', read_only=True)
    
    # Status and type displays
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_level_display', read_only=True)
    
    # Assignment state
    is_active = serializers.SerializerMethodField()
    is_pending = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    is_cancelled = serializers.SerializerMethodField()
    can_be_modified = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()
    
    # Time and duration
    duration_info = serializers.SerializerMethodField()
    schedule_info = serializers.SerializerMethodField()
    time_commitment = serializers.SerializerMethodField()
    
    # User information
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'volunteer', 'volunteer_name', 'volunteer_email', 'volunteer_phone',
            'role', 'role_name', 'role_description', 'event', 'event_name',
            'venue', 'venue_name', 'venue_address', 'assignment_type', 'assignment_type_display',
            'status', 'status_display', 'priority_level', 'priority_display',
            'assigned_date', 'start_date', 'end_date', 'start_time', 'end_time',
            'assignment_configuration', 'special_instructions', 'equipment_assigned',
            'uniform_assigned', 'application_date', 'review_date', 'approval_date',
            'confirmation_date', 'completion_date', 'is_admin_override',
            'admin_override_reason', 'admin_override_by', 'admin_override_date',
            'age_requirement_override', 'credential_requirement_override',
            'capacity_override', 'override_justification', 'performance_rating',
            'feedback_from_volunteer', 'feedback_from_supervisor', 'check_in_time',
            'check_out_time', 'actual_hours_worked', 'attendance_notes',
            'notification_preferences', 'last_notification_sent', 'reminder_count',
            'assigned_by', 'assigned_by_name', 'reviewed_by', 'reviewed_by_name',
            'approved_by', 'approved_by_name', 'status_changed_at', 'status_changed_by',
            'status_changed_by_name', 'status_change_reason', 'is_active', 'is_pending',
            'is_completed', 'is_cancelled', 'can_be_modified', 'can_be_cancelled',
            'duration_info', 'schedule_info', 'time_commitment', 'created_at',
            'updated_at', 'notes', 'external_references'
        ]
        read_only_fields = [
            'id', 'assigned_date', 'created_at', 'updated_at', 'status_changed_at'
        ]
    
    def get_is_active(self, obj):
        """Check if assignment is currently active"""
        return obj.is_active()
    
    def get_is_pending(self, obj):
        """Check if assignment is pending"""
        return obj.is_pending()
    
    def get_is_completed(self, obj):
        """Check if assignment is completed"""
        return obj.is_completed()
    
    def get_is_cancelled(self, obj):
        """Check if assignment is cancelled"""
        return obj.is_cancelled()
    
    def get_can_be_modified(self, obj):
        """Check if assignment can be modified"""
        return obj.can_be_modified()
    
    def get_can_be_cancelled(self, obj):
        """Check if assignment can be cancelled"""
        return obj.can_be_cancelled()
    
    def get_duration_info(self, obj):
        """Get assignment duration information"""
        return obj.get_duration()
    
    def get_schedule_info(self, obj):
        """Get assignment schedule information"""
        return obj.get_schedule_info()
    
    def get_time_commitment(self, obj):
        """Get time commitment information"""
        return obj.get_time_commitment()


class AssignmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new assignments
    """
    
    class Meta:
        model = Assignment
        fields = [
            'volunteer', 'role', 'event', 'venue', 'assignment_type',
            'priority_level', 'start_date', 'end_date', 'start_time', 'end_time',
            'assignment_configuration', 'special_instructions', 'equipment_assigned',
            'uniform_assigned', 'notification_preferences', 'notes'
        ]
    
    def validate(self, data):
        """Validate assignment data"""
        volunteer = data['volunteer']
        role = data['role']
        event = data['event']
        
        # Validate that role belongs to event
        if role.event != event:
            raise serializers.ValidationError(
                "Role must belong to the specified event."
            )
        
        # Validate venue if provided
        if data.get('venue') and data['venue'].event != event:
            raise serializers.ValidationError(
                "Venue must belong to the specified event."
            )
        
        # Check for duplicate assignments
        if Assignment.objects.filter(
            volunteer=volunteer, 
            role=role,
            status__in=['PENDING', 'APPROVED', 'CONFIRMED', 'ACTIVE']
        ).exists():
            raise serializers.ValidationError(
                "Volunteer is already assigned to this role."
            )
        
        # Validate dates
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "End date must be after start date."
                )
        
        # Validate times
        if data.get('start_time') and data.get('end_time'):
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError(
                    "End time must be after start time."
                )
        
        # Check role capacity (unless admin override)
        if not data.get('capacity_override', False):
            if role.is_full():
                raise serializers.ValidationError(
                    "Role is at full capacity. Use admin override if necessary."
                )
        
        # Check age requirements (unless admin override)
        if not data.get('age_requirement_override', False):
            volunteer_profile = getattr(volunteer, 'volunteerprofile', None)
            if volunteer_profile and volunteer_profile.date_of_birth:
                from django.utils import timezone
                age = (timezone.now().date() - volunteer_profile.date_of_birth).days // 365
                if not role.check_age_requirement(age):
                    raise serializers.ValidationError(
                        f"Volunteer does not meet age requirement (min: {role.minimum_age}, "
                        f"max: {role.maximum_age or 'none'})."
                    )
        
        return data
    
    def create(self, validated_data):
        """Create assignment with proper defaults"""
        # Set creator from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['assigned_by'] = request.user
        
        # Set venue from role if not provided
        if not validated_data.get('venue') and validated_data['role'].venue:
            validated_data['venue'] = validated_data['role'].venue
        
        # Set event from role if not provided
        if not validated_data.get('event'):
            validated_data['event'] = validated_data['role'].event
        
        return super().create(validated_data)


class AssignmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating assignments
    """
    
    class Meta:
        model = Assignment
        fields = [
            'assignment_type', 'priority_level', 'start_date', 'end_date',
            'start_time', 'end_time', 'assignment_configuration',
            'special_instructions', 'equipment_assigned', 'uniform_assigned',
            'performance_rating', 'feedback_from_volunteer', 'feedback_from_supervisor',
            'attendance_notes', 'notification_preferences', 'notes'
        ]
    
    def validate(self, data):
        """Validate assignment update data"""
        instance = self.instance
        
        # Check if assignment can be modified
        if not instance.can_be_modified():
            raise serializers.ValidationError(
                "Assignment cannot be modified in its current status."
            )
        
        # Validate dates
        start_date = data.get('start_date', instance.start_date)
        end_date = data.get('end_date', instance.end_date)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                "End date must be after start date."
            )
        
        # Validate times
        start_time = data.get('start_time', instance.start_time)
        end_time = data.get('end_time', instance.end_time)
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                "End time must be after start time."
            )
        
        # Validate performance rating
        if 'performance_rating' in data:
            rating = data['performance_rating']
            if rating is not None and (rating < 1 or rating > 5):
                raise serializers.ValidationError(
                    "Performance rating must be between 1 and 5."
                )
        
        return data
    
    def update(self, instance, validated_data):
        """Update assignment with audit trail"""
        # Track changes for audit
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Log significant changes
            significant_fields = ['start_date', 'end_date', 'assignment_type', 'priority_level']
            changes = {}
            for field in significant_fields:
                if field in validated_data:
                    old_value = getattr(instance, field)
                    new_value = validated_data[field]
                    if old_value != new_value:
                        changes[field] = {'old': old_value, 'new': new_value}
            
            if changes:
                # Add to notes for audit trail
                change_note = f"Updated by {request.user.get_full_name()}: {changes}"
                current_notes = instance.notes or ""
                instance.notes = f"{current_notes}\n{change_note}".strip()
        
        return super().update(instance, validated_data)


class AssignmentStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for assignment status management
    """
    status_change_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Assignment
        fields = ['id', 'status', 'status_change_reason', 'status_changed_at', 'status_changed_by']
        read_only_fields = ['id', 'status_changed_at', 'status_changed_by']
    
    def update(self, instance, validated_data):
        """Update assignment status with workflow validation"""
        new_status = validated_data.get('status')
        reason = validated_data.pop('status_change_reason', '')
        
        if new_status and new_status != instance.status:
            request = self.context.get('request')
            changed_by = request.user if request and request.user.is_authenticated else None
            
            # Use model's change_status method for proper workflow
            instance.change_status(new_status, changed_by=changed_by, reason=reason)
        
        return instance


class AssignmentWorkflowSerializer(serializers.Serializer):
    """
    Serializer for assignment workflow actions
    """
    action = serializers.ChoiceField(choices=[
        'approve', 'confirm', 'activate', 'complete', 'cancel', 
        'reject', 'withdraw', 'mark_no_show', 'suspend'
    ])
    notes = serializers.CharField(required=False, allow_blank=True)
    performance_rating = serializers.IntegerField(
        required=False, min_value=1, max_value=5
    )
    
    def validate(self, data):
        """Validate workflow action"""
        action = data['action']
        instance = self.context.get('assignment')
        
        if not instance:
            raise serializers.ValidationError("Assignment instance required.")
        
        # Validate action is allowed for current status
        valid_actions = {
            'PENDING': ['approve', 'reject', 'cancel'],
            'APPROVED': ['confirm', 'cancel', 'activate'],
            'CONFIRMED': ['activate', 'cancel', 'withdraw'],
            'ACTIVE': ['complete', 'cancel', 'suspend', 'mark_no_show'],
            'SUSPENDED': ['activate', 'cancel'],
        }
        
        current_status = instance.status
        if action not in valid_actions.get(current_status, []):
            raise serializers.ValidationError(
                f"Action '{action}' not allowed for status '{current_status}'."
            )
        
        # Performance rating only for complete action
        if action == 'complete' and 'performance_rating' not in data:
            data['performance_rating'] = None
        elif action != 'complete' and 'performance_rating' in data:
            raise serializers.ValidationError(
                "Performance rating only allowed for 'complete' action."
            )
        
        return data


class AssignmentAttendanceSerializer(serializers.ModelSerializer):
    """
    Serializer for assignment attendance tracking
    """
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'check_in_time', 'check_out_time', 'actual_hours_worked',
            'attendance_notes'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        """Validate attendance data"""
        check_in = data.get('check_in_time')
        check_out = data.get('check_out_time')
        
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError(
                "Check-out time must be after check-in time."
            )
        
        # Validate hours worked
        hours_worked = data.get('actual_hours_worked')
        if hours_worked is not None:
            if hours_worked < 0:
                raise serializers.ValidationError(
                    "Hours worked cannot be negative."
                )
            if hours_worked > 24:
                raise serializers.ValidationError(
                    "Hours worked cannot exceed 24 hours per day."
                )
        
        return data


class AssignmentBulkSerializer(serializers.Serializer):
    """
    Serializer for bulk assignment operations
    """
    assignment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=[
        'approve', 'cancel', 'activate', 'complete', 'send_notification'
    ])
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_assignment_ids(self, value):
        """Validate that all assignment IDs exist"""
        existing_ids = Assignment.objects.filter(
            id__in=value
        ).values_list('id', flat=True)
        
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(
                f"Assignment IDs not found: {list(missing_ids)}"
            )
        
        return value


class AssignmentSerializer(serializers.ModelSerializer):
    """Legacy assignment serializer for backward compatibility"""
    
    class Meta:
        model = Assignment
        fields = '__all__'

# Main Event serializer for backward compatibility
class EventSerializer(EventDetailSerializer):
    """Main Event serializer - comprehensive event data"""
    pass

class AssignmentStatsSerializer(serializers.Serializer):
    """Serializer for assignment statistics response"""
    summary = serializers.DictField()
    status_breakdown = serializers.DictField()
    type_breakdown = serializers.DictField()
    priority_breakdown = serializers.DictField()
    filters_applied = serializers.DictField() 