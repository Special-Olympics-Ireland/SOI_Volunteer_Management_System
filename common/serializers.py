from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import AuditLog, SystemConfig, AdminOverride

User = get_user_model()


class AuditLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()
    target_object_display = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ('id', 'timestamp')
    
    def get_user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name()} ({obj.user.username})"
        return "System"
    
    def get_target_object_display(self, obj):
        return obj.object_representation or "N/A"
    
    def get_duration_display(self, obj):
        if obj.duration_ms:
            if obj.duration_ms < 1000:
                return f"{obj.duration_ms}ms"
            else:
                return f"{obj.duration_ms / 1000:.2f}s"
        return "N/A"


class SystemConfigSerializer(serializers.ModelSerializer):
    created_by_display = serializers.SerializerMethodField()
    updated_by_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemConfig
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'version')
    
    def get_created_by_display(self, obj):
        if obj.created_by:
            return f"{obj.created_by.get_full_name()} ({obj.created_by.username})"
        return "System"
    
    def get_updated_by_display(self, obj):
        if obj.updated_by:
            return f"{obj.updated_by.get_full_name()} ({obj.updated_by.username})"
        return "System"


# AdminOverride Serializers

class AdminOverrideListSerializer(serializers.ModelSerializer):
    """Serializer for listing admin overrides with essential information"""
    
    requested_by_display = serializers.SerializerMethodField()
    approved_by_display = serializers.SerializerMethodField()
    target_object_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    override_type_display = serializers.CharField(source='get_override_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    impact_level_display = serializers.CharField(source='get_impact_level_display', read_only=True)
    is_effective = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AdminOverride
        fields = [
            'id', 'title', 'override_type', 'override_type_display', 'status', 'status_display',
            'risk_level', 'risk_level_display', 'impact_level', 'impact_level_display',
            'requested_by_display', 'approved_by_display', 'target_object_display',
            'is_emergency', 'priority_level', 'requested_at', 'approved_at',
            'effective_from', 'effective_until', 'is_effective', 'is_expired',
            'time_remaining', 'duration', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_requested_by_display(self, obj):
        if obj.requested_by:
            return f"{obj.requested_by.get_full_name()} ({obj.requested_by.username})"
        return "Unknown"
    
    def get_approved_by_display(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.get_full_name()} ({obj.approved_by.username})"
        return None
    
    def get_target_object_display(self, obj):
        if obj.target_object:
            return str(obj.target_object)
        return f"{obj.content_type.name} (ID: {obj.object_id})"
    
    def get_is_effective(self, obj):
        return obj.is_effective()
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_time_remaining(self, obj):
        remaining = obj.get_time_remaining()
        if remaining:
            days = remaining.days
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days} days, {hours} hours"
            elif hours > 0:
                return f"{hours} hours, {minutes} minutes"
            else:
                return f"{minutes} minutes"
        return None
    
    def get_duration(self, obj):
        duration = obj.get_duration()
        if duration:
            days = duration.days
            hours, remainder = divmod(duration.seconds, 3600)
            
            if days > 0:
                return f"{days} days, {hours} hours"
            elif hours > 0:
                return f"{hours} hours"
            else:
                return "Less than 1 hour"
        return None


class AdminOverrideDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for admin overrides with all information"""
    
    requested_by_display = serializers.SerializerMethodField()
    approved_by_display = serializers.SerializerMethodField()
    reviewed_by_display = serializers.SerializerMethodField()
    status_changed_by_display = serializers.SerializerMethodField()
    target_object_display = serializers.SerializerMethodField()
    content_type_display = serializers.SerializerMethodField()
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    override_type_display = serializers.CharField(source='get_override_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    impact_level_display = serializers.CharField(source='get_impact_level_display', read_only=True)
    monitoring_frequency_display = serializers.CharField(source='get_monitoring_frequency_display', read_only=True)
    
    # Computed fields
    is_effective = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AdminOverride
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'requested_at', 'approved_at',
            'applied_at', 'revoked_at', 'status_changed_at'
        )
    
    def get_requested_by_display(self, obj):
        if obj.requested_by:
            return f"{obj.requested_by.get_full_name()} ({obj.requested_by.username})"
        return "Unknown"
    
    def get_approved_by_display(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.get_full_name()} ({obj.approved_by.username})"
        return None
    
    def get_reviewed_by_display(self, obj):
        if obj.reviewed_by:
            return f"{obj.reviewed_by.get_full_name()} ({obj.reviewed_by.username})"
        return None
    
    def get_status_changed_by_display(self, obj):
        if obj.status_changed_by:
            return f"{obj.status_changed_by.get_full_name()} ({obj.status_changed_by.username})"
        return None
    
    def get_target_object_display(self, obj):
        if obj.target_object:
            return str(obj.target_object)
        return f"{obj.content_type.name} (ID: {obj.object_id})"
    
    def get_content_type_display(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"
    
    def get_is_effective(self, obj):
        return obj.is_effective()
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_time_remaining(self, obj):
        remaining = obj.get_time_remaining()
        if remaining:
            days = remaining.days
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days} days, {hours} hours"
            elif hours > 0:
                return f"{hours} hours, {minutes} minutes"
            else:
                return f"{minutes} minutes"
        return None
    
    def get_duration(self, obj):
        duration = obj.get_duration()
        if duration:
            days = duration.days
            hours, remainder = divmod(duration.seconds, 3600)
            
            if days > 0:
                return f"{days} days, {hours} hours"
            elif hours > 0:
                return f"{hours} hours"
            else:
                return "Less than 1 hour"
        return None


class AdminOverrideCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating admin overrides with validation"""
    
    # Content type handling
    content_type_id = serializers.IntegerField(write_only=True)
    object_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = AdminOverride
        fields = [
            'title', 'override_type', 'description', 'justification', 'business_case',
            'content_type_id', 'object_id', 'risk_level', 'impact_level',
            'risk_assessment', 'impact_assessment', 'override_data', 'original_values',
            'new_values', 'effective_from', 'effective_until', 'is_emergency',
            'priority_level', 'requires_immediate_action', 'compliance_notes',
            'regulatory_impact', 'documentation_required', 'requires_monitoring',
            'monitoring_frequency', 'tags', 'external_references', 'custom_fields'
        ]
    
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required")
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters")
        return value.strip()
    
    def validate_justification(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Justification is required for all overrides")
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Justification must be at least 20 characters")
        return value.strip()
    
    def validate_priority_level(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("Priority level must be between 1 and 10")
        return value
    
    def validate_content_type_id(self, value):
        try:
            ContentType.objects.get(id=value)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError("Invalid content type")
        return value
    
    def validate(self, attrs):
        # Validate effective dates
        effective_from = attrs.get('effective_from')
        effective_until = attrs.get('effective_until')
        
        if effective_from and effective_until:
            if effective_from >= effective_until:
                raise serializers.ValidationError({
                    'effective_until': 'Effective until date must be after effective from date'
                })
        
        # Emergency override validation
        is_emergency = attrs.get('is_emergency', False)
        if is_emergency:
            justification = attrs.get('justification', '')
            if len(justification.strip()) < 50:
                raise serializers.ValidationError({
                    'justification': 'Emergency overrides require detailed justification (minimum 50 characters)'
                })
            
            risk_level = attrs.get('risk_level', 'MEDIUM')
            if risk_level not in ['HIGH', 'CRITICAL']:
                raise serializers.ValidationError({
                    'risk_level': 'Emergency overrides must have HIGH or CRITICAL risk level'
                })
            
            # Set high priority for emergency overrides
            attrs['priority_level'] = min(attrs.get('priority_level', 5), 2)
        
        # High-risk override validation
        risk_level = attrs.get('risk_level', 'MEDIUM')
        if risk_level in ['HIGH', 'CRITICAL']:
            business_case = attrs.get('business_case', '')
            if not business_case or not business_case.strip():
                raise serializers.ValidationError({
                    'business_case': 'High-risk overrides require a business case'
                })
        
        return attrs
    
    def create(self, validated_data):
        # Set the requesting user
        validated_data['requested_by'] = self.context['request'].user
        
        # Handle content type
        content_type_id = validated_data.pop('content_type_id')
        validated_data['content_type_id'] = content_type_id
        
        return super().create(validated_data)


class AdminOverrideUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating admin overrides (limited fields)"""
    
    class Meta:
        model = AdminOverride
        fields = [
            'title', 'description', 'justification', 'business_case',
            'risk_assessment', 'impact_assessment', 'override_data',
            'original_values', 'new_values', 'effective_from', 'effective_until',
            'priority_level', 'compliance_notes', 'regulatory_impact',
            'documentation_required', 'requires_monitoring', 'monitoring_frequency',
            'tags', 'external_references', 'custom_fields'
        ]
    
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title is required")
        return value.strip()
    
    def validate_justification(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Justification is required")
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Justification must be at least 20 characters")
        return value.strip()
    
    def validate_priority_level(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("Priority level must be between 1 and 10")
        return value


class AdminOverrideStatusSerializer(serializers.Serializer):
    """Serializer for status change operations"""
    
    action = serializers.ChoiceField(choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('activate', 'Activate'),
        ('revoke', 'Revoke'),
        ('complete', 'Complete')
    ])
    notes = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        action = attrs.get('action')
        
        if action == 'reject' and not attrs.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Rejection reason is required'
            })
        
        if action == 'revoke' and not attrs.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Revocation reason is required'
            })
        
        return attrs


class AdminOverrideMonitoringSerializer(serializers.Serializer):
    """Serializer for monitoring updates"""
    
    monitoring_notes = serializers.CharField(required=True)
    
    def validate_monitoring_notes(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Monitoring notes are required")
        return value.strip()


class AdminOverrideBulkOperationSerializer(serializers.Serializer):
    """Serializer for bulk operations on admin overrides"""
    
    override_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('activate', 'Activate'),
        ('revoke', 'Revoke'),
        ('update_tags', 'Update Tags'),
        ('update_priority', 'Update Priority')
    ])
    notes = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    priority_level = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10
    )
    
    def validate(self, attrs):
        action = attrs.get('action')
        
        if action in ['reject', 'revoke'] and not attrs.get('reason'):
            raise serializers.ValidationError({
                'reason': f'{action.title()} reason is required'
            })
        
        if action == 'update_tags' and 'tags' not in attrs:
            raise serializers.ValidationError({
                'tags': 'Tags are required for update_tags action'
            })
        
        if action == 'update_priority' and 'priority_level' not in attrs:
            raise serializers.ValidationError({
                'priority_level': 'Priority level is required for update_priority action'
            })
        
        return attrs


class AdminOverrideStatsSerializer(serializers.Serializer):
    """Serializer for admin override statistics"""
    
    total_overrides = serializers.IntegerField()
    pending_overrides = serializers.IntegerField()
    approved_overrides = serializers.IntegerField()
    active_overrides = serializers.IntegerField()
    expired_overrides = serializers.IntegerField()
    revoked_overrides = serializers.IntegerField()
    emergency_overrides = serializers.IntegerField()
    high_risk_overrides = serializers.IntegerField()
    overrides_by_type = serializers.DictField()
    overrides_by_status = serializers.DictField()
    overrides_by_risk_level = serializers.DictField()
    recent_activity = serializers.ListField()
    expiring_soon = serializers.IntegerField()
    requires_monitoring = serializers.IntegerField() 