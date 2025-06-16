from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import VolunteerProfile
from .eoi_models import EOISubmission, EOIProfileInformation, EOIRecruitmentPreferences, EOIGamesInformation
from events.models import Assignment, Event, Role
from tasks.models import TaskCompletion

User = get_user_model()


class VolunteerProfileListSerializer(serializers.ModelSerializer):
    """Serializer for volunteer profile list view with essential information"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    experience_level_display = serializers.CharField(source='get_experience_level_display', read_only=True)
    availability_level_display = serializers.CharField(source='get_availability_level_display', read_only=True)
    
    # Computed fields
    age = serializers.SerializerMethodField()
    days_since_application = serializers.SerializerMethodField()
    has_active_assignments = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = VolunteerProfile
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'status', 'status_display', 'preferred_name',
            'experience_level', 'experience_level_display',
            'availability_level', 'availability_level_display',
            'application_date', 'review_date', 'approval_date',
            'age', 'days_since_application', 'has_active_assignments',
            'completion_rate', 'performance_rating',
            'is_corporate_volunteer', 'corporate_group_name',
            'background_check_status', 'reference_check_status',
            'created_at', 'updated_at'
        ]
    
    def get_age(self, obj):
        return obj.get_age()
    
    def get_days_since_application(self, obj):
        if obj.application_date:
            return (timezone.now() - obj.application_date).days
        return None
    
    def get_has_active_assignments(self, obj):
        return Assignment.objects.filter(
            volunteer=obj.user,
            status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']
        ).exists()
    
    def get_completion_rate(self, obj):
        total_tasks = TaskCompletion.objects.filter(volunteer=obj.user).count()
        if total_tasks == 0:
            return None
        completed_tasks = TaskCompletion.objects.filter(
            volunteer=obj.user,
            status__in=['APPROVED', 'VERIFIED']
        ).count()
        return round((completed_tasks / total_tasks) * 100, 1)


class VolunteerProfileDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed volunteer profile view with all information"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_address = serializers.CharField(source='user.get_full_address', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    status_changed_by_name = serializers.CharField(source='status_changed_by.get_full_name', read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    experience_level_display = serializers.CharField(source='get_experience_level_display', read_only=True)
    availability_level_display = serializers.CharField(source='get_availability_level_display', read_only=True)
    transport_method_display = serializers.CharField(source='get_transport_method_display', read_only=True)
    t_shirt_size_display = serializers.CharField(source='get_t_shirt_size_display', read_only=True)
    
    # Computed fields
    age = serializers.SerializerMethodField()
    experience_summary = serializers.SerializerMethodField()
    availability_summary = serializers.SerializerMethodField()
    preferences_summary = serializers.SerializerMethodField()
    current_assignments = serializers.SerializerMethodField()
    task_statistics = serializers.SerializerMethodField()
    training_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = VolunteerProfile
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone', 'user_address',
            'status', 'status_display', 'application_date', 'review_date', 'approval_date',
            'reviewed_by', 'reviewed_by_name', 'preferred_name',
            
            # Personal information
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'medical_conditions', 'dietary_requirements', 'mobility_requirements',
            
            # Experience and skills
            'experience_level', 'experience_level_display', 'previous_events',
            'special_skills', 'languages_spoken', 'experience_summary',
            
            # Availability
            'availability_level', 'availability_level_display', 'available_dates',
            'unavailable_dates', 'preferred_time_slots', 'max_hours_per_day',
            'availability_summary',
            
            # Preferences
            'preferred_roles', 'preferred_venues', 'preferred_sports', 'role_restrictions',
            'preferences_summary',
            
            # Physical capabilities
            'can_lift_heavy_items', 'can_stand_long_periods', 'can_work_outdoors',
            'can_work_with_crowds', 'has_own_transport', 'transport_method',
            'transport_method_display',
            
            # Uniform and equipment
            't_shirt_size', 't_shirt_size_display', 'requires_uniform', 'has_own_equipment',
            
            # Communication
            'preferred_communication_method', 'communication_frequency',
            
            # Training and verification
            'training_completed', 'training_required', 'training_preferences',
            'training_progress', 'background_check_status', 'background_check_date',
            'background_check_expiry', 'references', 'reference_check_status',
            
            # Motivation and goals
            'motivation', 'volunteer_goals', 'previous_volunteer_feedback',
            
            # Corporate volunteering
            'is_corporate_volunteer', 'corporate_group_name', 'group_leader_contact',
            
            # Consent and permissions
            'social_media_consent', 'photo_consent', 'testimonial_consent',
            
            # Performance
            'performance_rating', 'feedback_summary', 'commendations',
            'current_assignments', 'task_statistics',
            
            # Administrative
            'notes', 'tags', 'status_changed_at', 'status_changed_by',
            'status_changed_by_name', 'status_change_reason',
            'created_at', 'updated_at', 'age'
        ]
    
    def get_age(self, obj):
        return obj.get_age()
    
    def get_experience_summary(self, obj):
        return obj.get_experience_summary()
    
    def get_availability_summary(self, obj):
        return obj.get_availability_summary()
    
    def get_preferences_summary(self, obj):
        return obj.get_preferences_summary()
    
    def get_current_assignments(self, obj):
        assignments = Assignment.objects.filter(
            volunteer=obj.user,
            status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']
        ).select_related('role', 'role__event')
        
        return [{
            'id': str(assignment.id),
            'role_name': assignment.role.name,
            'event_name': assignment.role.event.name,
            'status': assignment.status,
            'assigned_date': assignment.assigned_at
        } for assignment in assignments]
    
    def get_task_statistics(self, obj):
        from django.db.models import Count, Q
        
        task_stats = TaskCompletion.objects.filter(volunteer=obj.user).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status__in=['APPROVED', 'VERIFIED'])),
            pending=Count('id', filter=Q(status='PENDING')),
            in_progress=Count('id', filter=Q(status__in=['SUBMITTED', 'UNDER_REVIEW']))
        )
        
        completion_rate = 0
        if task_stats['total'] > 0:
            completion_rate = round((task_stats['completed'] / task_stats['total']) * 100, 1)
        
        return {
            'total_tasks': task_stats['total'],
            'completed_tasks': task_stats['completed'],
            'pending_tasks': task_stats['pending'],
            'in_progress_tasks': task_stats['in_progress'],
            'completion_rate': completion_rate
        }
    
    def get_training_progress(self, obj):
        completed = len(obj.training_completed) if obj.training_completed else 0
        required = len(obj.training_required) if obj.training_required else 0
        
        progress_percentage = 0
        if required > 0:
            progress_percentage = round((completed / required) * 100, 1)
        
        return {
            'completed_modules': completed,
            'required_modules': required,
            'progress_percentage': progress_percentage,
            'outstanding_modules': max(0, required - completed)
        }


class VolunteerProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new volunteer profiles"""
    
    class Meta:
        model = VolunteerProfile
        fields = [
            'user', 'preferred_name', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relationship',
            'medical_conditions', 'dietary_requirements', 'mobility_requirements',
            'experience_level', 'previous_events', 'special_skills', 'languages_spoken',
            'availability_level', 'available_dates', 'unavailable_dates',
            'preferred_time_slots', 'max_hours_per_day', 'preferred_roles',
            'preferred_venues', 'preferred_sports', 'role_restrictions',
            'can_lift_heavy_items', 'can_stand_long_periods', 'can_work_outdoors',
            'can_work_with_crowds', 'has_own_transport', 'transport_method',
            't_shirt_size', 'requires_uniform', 'has_own_equipment',
            'preferred_communication_method', 'communication_frequency',
            'motivation', 'volunteer_goals', 'is_corporate_volunteer',
            'corporate_group_name', 'group_leader_contact',
            'social_media_consent', 'photo_consent', 'testimonial_consent'
        ]
    
    def validate_user(self, value):
        """Ensure user doesn't already have a volunteer profile"""
        if VolunteerProfile.objects.filter(user=value).exists():
            raise serializers.ValidationError(
                'User already has a volunteer profile'
            )
        return value
    
    def validate_max_hours_per_day(self, value):
        """Validate max hours per day"""
        if value < 1 or value > 24:
            raise serializers.ValidationError(
                'Max hours per day must be between 1 and 24'
            )
        return value


class VolunteerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating volunteer profiles"""
    
    class Meta:
        model = VolunteerProfile
        fields = [
            'preferred_name', 'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'medical_conditions', 'dietary_requirements',
            'mobility_requirements', 'experience_level', 'previous_events',
            'special_skills', 'languages_spoken', 'availability_level',
            'available_dates', 'unavailable_dates', 'preferred_time_slots',
            'max_hours_per_day', 'preferred_roles', 'preferred_venues',
            'preferred_sports', 'role_restrictions', 'can_lift_heavy_items',
            'can_stand_long_periods', 'can_work_outdoors', 'can_work_with_crowds',
            'has_own_transport', 'transport_method', 't_shirt_size',
            'requires_uniform', 'has_own_equipment', 'preferred_communication_method',
            'communication_frequency', 'motivation', 'volunteer_goals',
            'social_media_consent', 'photo_consent', 'testimonial_consent'
        ]


class VolunteerProfileStatusSerializer(serializers.ModelSerializer):
    """Serializer for volunteer profile status updates"""
    
    status_change_reason = serializers.CharField(write_only=True, required=False)
    reviewer_notes = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = VolunteerProfile
        fields = ['status', 'status_change_reason', 'reviewer_notes']
    
    def validate_status(self, value):
        """Validate status transition"""
        if self.instance:
            current_status = self.instance.status
            
            # Define valid transitions
            valid_transitions = {
                'PENDING': ['UNDER_REVIEW', 'APPROVED', 'REJECTED', 'WITHDRAWN'],
                'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'WAITLISTED', 'PENDING'],
                'APPROVED': ['ACTIVE', 'WAITLISTED', 'REJECTED'],
                'REJECTED': ['UNDER_REVIEW', 'PENDING'],
                'WAITLISTED': ['APPROVED', 'REJECTED', 'WITHDRAWN'],
                'ACTIVE': ['INACTIVE', 'SUSPENDED', 'WITHDRAWN'],
                'INACTIVE': ['ACTIVE', 'WITHDRAWN'],
                'SUSPENDED': ['ACTIVE', 'WITHDRAWN'],
                'WITHDRAWN': []  # Terminal state
            }
            
            if value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f'Cannot transition from {current_status} to {value}'
                )
        
        return value
    
    def update(self, instance, validated_data):
        """Update status with tracking"""
        status_change_reason = validated_data.pop('status_change_reason', '')
        reviewer_notes = validated_data.pop('reviewer_notes', '')
        
        # Track status change
        if 'status' in validated_data and instance.status != validated_data['status']:
            instance.status_changed_at = timezone.now()
            instance.status_changed_by = self.context['request'].user
            instance.status_change_reason = status_change_reason
            
            # Set review/approval dates
            new_status = validated_data['status']
            if new_status in ['APPROVED', 'REJECTED', 'WAITLISTED']:
                instance.review_date = timezone.now()
                instance.reviewed_by = self.context['request'].user
            
            if new_status == 'APPROVED':
                instance.approval_date = timezone.now()
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class VolunteerProfileStatsSerializer(serializers.Serializer):
    """Serializer for volunteer profile statistics"""
    
    profile_id = serializers.UUIDField(read_only=True)
    volunteer_name = serializers.CharField(read_only=True)
    summary = serializers.DictField(read_only=True)
    assignments = serializers.DictField(read_only=True)
    tasks = serializers.DictField(read_only=True)
    training = serializers.DictField(read_only=True)
    performance = serializers.DictField(read_only=True)


class VolunteerEOIIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for volunteer profile with EOI integration"""
    
    eoi_submission = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = VolunteerProfile
        fields = [
            'id', 'user', 'status', 'application_date',
            'eoi_submission', 'profile_completion'
        ]
    
    def get_eoi_submission(self, obj):
        """Get related EOI submission data"""
        try:
            eoi = EOISubmission.objects.get(user=obj.user)
            return {
                'id': str(eoi.id),
                'status': eoi.status,
                'volunteer_type': eoi.volunteer_type,
                'completion_percentage': eoi.completion_percentage,
                'submitted_at': eoi.submitted_at,
                'confirmation_email_sent': eoi.confirmation_email_sent
            }
        except EOISubmission.DoesNotExist:
            return None
    
    def get_profile_completion(self, obj):
        """Calculate profile completion percentage"""
        required_fields = [
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'experience_level',
            'availability_level', 't_shirt_size', 'preferred_communication_method'
        ]
        
        completed_fields = 0
        for field in required_fields:
            if getattr(obj, field):
                completed_fields += 1
        
        return {
            'percentage': round((completed_fields / len(required_fields)) * 100, 1),
            'completed_fields': completed_fields,
            'total_fields': len(required_fields),
            'missing_fields': [field for field in required_fields if not getattr(obj, field)]
        }


class VolunteerBulkOperationSerializer(serializers.Serializer):
    """Serializer for bulk volunteer operations"""
    
    BULK_ACTIONS = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('activate', 'Activate'),
        ('suspend', 'Suspend'),
        ('send_notification', 'Send Notification'),
        ('update_tags', 'Update Tags'),
        ('export_data', 'Export Data')
    ]
    
    volunteer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of volunteer profile IDs to perform action on"
    )
    action = serializers.ChoiceField(choices=BULK_ACTIONS)
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Tags to add/update (for update_tags action)"
    )
    
    def validate(self, data):
        """Validate bulk operation data"""
        if not data.get('volunteer_ids'):
            raise serializers.ValidationError({
                'volunteer_ids': 'At least one volunteer ID is required'
            })
        
        # Validate action-specific requirements
        action = data['action']
        if action in ['approve', 'reject', 'suspend'] and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': f'Reason is required for {action} action'
            })
        
        if action == 'update_tags' and not data.get('tags'):
            raise serializers.ValidationError({
                'tags': 'Tags list is required for update_tags action'
            })
        
        return data 